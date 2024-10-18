import os
import argparse
from pathlib import Path

from blender_autorender.config import AnimSpriteConfig, MaterialConfig
from blender_autorender.lib import entrypoint
from blender_autorender.material import entrypoint_material

def file_path(path: str):
    if os.path.isfile(path):
        return Path(path)
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


def parse_args():
    parser = argparse.ArgumentParser(description="Blender AutoRender")
    # First argument is the configuration file path
    parser.add_argument("config", help="Path to the configuration file", type=file_path)
    parser.add_argument(
        "--material", action="store_true", help="Whether to render in material mode."
    )

    return parser.parse_args()


def main():
    args = parse_args()
    print("Hello, world! Let's get started!")
    with open(args.config, "r") as f:
        config_json = f.read()
    if args.material:
        config = MaterialConfig.schema().loads(config_json)
        entrypoint_material(config, args.config)
    else:
        config = AnimSpriteConfig.schema().loads(config_json)
        entrypoint(config, args.config)
