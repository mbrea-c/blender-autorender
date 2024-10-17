import os
import argparse
from pathlib import Path

from blender_autorender.config import Config
from blender_autorender.lib import entrypoint


def file_path(path: str):
    if os.path.isfile(path):
        return Path(path)
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


def parse_args():
    parser = argparse.ArgumentParser(description="Blender AutoRender")
    # First argument is the configuration file path
    parser.add_argument("config", help="Path to the configuration file", type=file_path)

    return parser.parse_args()


def main():
    args = parse_args()
    print("Hello, world! Let's get started!")
    with open(args.config, "r") as f:
        config_json = f.read()
    config = Config.schema().loads(config_json)
    entrypoint(config, args.config)
