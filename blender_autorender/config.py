from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from pathlib import Path


@dataclass_json
@dataclass
class ObjConfig:
    object_name: str
    action_name: str


@dataclass_json
@dataclass
class CameraConfig:
    # Options: FRONT, SIDE, TOP
    view: str = "TOP"
    ortho_scale: float = 2


@dataclass_json
@dataclass
class AnimSpriteConfig:
    # Path to the .blend file to load. If relative, is relative to config file
    blend_file_path: Path
    # Path to the output directory. If relative, is relative to config file
    output_dir: Path
    sprite_size: int  # Size of each sprite (64x64, 128x128, etc.)
    sheet_width: int  # Number of sprites per row in the spritesheet

    start_frame: int = 1
    end_frame: int = 24
    frame_step: int = 1
    include_last_frame: bool = False
    camera: CameraConfig = field(default_factory=CameraConfig)
    object_configs: list[ObjConfig] = field(default_factory=list)

@dataclass_json
@dataclass
class MaterialConfig:
    # Path to the .blend file to load. If relative, is relative to config file
    blend_file_path: Path
    material_name: str
    # Path to the output directory. If relative, is relative to config file
    output_dir: Path
    sprite_size: int  # Size of each sprite (64x64, 128x128, etc.)
