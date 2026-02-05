import os
import argparse
from pathlib import Path

from blender_autorender.anim_scn import AnimSceneProcessor
from blender_autorender.config import (
    TopLevelConfig,
    AssetConfig,
    MaterialConfig,
    AnimSpriteConfig,
    AnimSceneConfig,
)
from blender_autorender.anim_sprite import entrypoint
from blender_autorender.material import entrypoint_material


def file_path(path: str) -> Path:
    if os.path.isfile(path):
        return Path(path)
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


def parse_args():
    parser = argparse.ArgumentParser(description="Blender AutoRender")
    # First argument is the configuration file path
    parser.add_argument(
        "-c",
        "--config",
        help="Path to the configuration file",
        type=file_path,
        required=False,
        default=Path("autorender.json"),
    )
    parser.add_argument(
        "-a",
        "--asset-collection",
        help="If specified, render only the provided asset collection",
        type=str,
        required=False,
        default=None,
    )

    return parser.parse_args()


def main():
    args = parse_args()
    print("👋 Hello, world! Let's get started!")
    with open(args.config, "r") as f:
        config_json = f.read()
    config: TopLevelConfig = TopLevelConfig.model_validate_json(config_json)
    output_dir = resolve_path(args.config, config.output_dir)
    log_path = resolve_path(args.config, Path("autorender.log"))
    for collection in config.collections:
        collection_output_dir = output_dir.joinpath(collection.id)

        print(
            f"Processing collection {collection.id}, results will be saved in {collection_output_dir}"
        )

        for asset_config_path in collection.asset_configs:
            asset_config_path = resolve_path(args.config, asset_config_path)
            with open(asset_config_path, "r") as f:
                asset_config_json = f.read()
            asset_config: AssetConfig = AssetConfig.model_validate_json(
                asset_config_json
            )
            print(f" - Rendering {asset_config.root.variant} from {asset_config_path}")
            if isinstance(asset_config.root, MaterialConfig):
                asset_config.root.blend_file_path = resolve_path(
                    asset_config_path, asset_config.root.blend_file_path
                )
                entrypoint_material(
                    config=asset_config.root,
                    toplevel_output_dir=collection_output_dir,
                    log_path=log_path,
                )
            elif isinstance(asset_config.root, AnimSpriteConfig):
                asset_config.root.blend_file_path = resolve_path(
                    asset_config_path, asset_config.root.blend_file_path
                )
                entrypoint(
                    config=asset_config.root,
                    toplevel_output_dir=collection_output_dir,
                    log_path=log_path,
                )
            elif isinstance(asset_config.root, AnimSceneConfig):
                asset_config.root.blend_file_path = resolve_path(
                    asset_config_path, asset_config.root.blend_file_path
                )
                processor = AnimSceneProcessor(
                    config=asset_config.root,
                    toplevel_output_dir=collection_output_dir,
                    log_path=log_path,
                )
                processor.process()
            else:
                print(f"Unrecognized asset config variant: {type(asset_config.root)}")
                exit(1)

        print(f"Finished collection {collection.id}!")


def resolve_path(config_path: Path, potentially_relative_path: Path) -> Path:
    root = config_path.parent
    return (
        potentially_relative_path
        if Path(potentially_relative_path).is_absolute()
        else root.joinpath(potentially_relative_path)
    )
