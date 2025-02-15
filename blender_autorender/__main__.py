import os
import argparse
from pathlib import Path

from blender_autorender.config import TopLevelConfig
from blender_autorender.anim_sprite import entrypoint
from blender_autorender.material import entrypoint_material


def file_path(path: str):
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
        required=True,
    )

    return parser.parse_args()


def main():
    args = parse_args()
    print("Hello, world! Let's get started!")
    with open(args.config, "r") as f:
        config_json = f.read()
    config: TopLevelConfig = TopLevelConfig.schema().loads(config_json)
    blend_file_path = resolve_path(args.config, config.blend_file_path)
    output_dir = resolve_path(args.config, config.output_dir)
    for material_config in config.material_configs:
        entrypoint_material(
            config=material_config,
            blend_file_path=blend_file_path,
            toplevel_output_dir=output_dir,
        )
    for anim_sprite_config in config.anim_sprite_configs:
        entrypoint(
            config=anim_sprite_config,
            blend_file_path=blend_file_path,
            toplevel_output_dir=output_dir,
        )


def resolve_path(config_path: Path, potentially_relative_path: Path) -> Path:
    root = config_path.parent
    return (
        potentially_relative_path
        if Path(potentially_relative_path).is_absolute()
        else root.joinpath(potentially_relative_path)
    )
