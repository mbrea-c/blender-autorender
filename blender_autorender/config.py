from dataclasses import dataclass, field
from typing import List
from dataclasses_json import dataclass_json
import dataclasses_json.cfg
from pathlib import Path

dataclasses_json.cfg.global_config.encoders[Path] = str
dataclasses_json.cfg.global_config.decoders[Path] = Path


@dataclass_json
@dataclass
class ObjConfig:
    object_name: str
    action_name: str | None


@dataclass_json
@dataclass
class CameraConfig:
    # Options: FRONT, SIDE, TOP
    view: str = "TOP"
    ortho_scale: float = 2


@dataclass_json
@dataclass
class AnimSpriteConfig:
    # Used to create a named directory for the outputs
    id: str

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
    # Used to create a named directory for the outputs
    id: str
    # Name of material in blend file
    material_name: str
    # Size of each sprite (64x64, 128x128, etc.)
    sprite_size: int


@dataclass_json
@dataclass
class BakeConfig:
    step: int = 1


@dataclass_json
@dataclass
class ActionConfig:
    action_name: str
    bake_config: BakeConfig


@dataclass_json
@dataclass
class AnimSceneConfig:
    # Used to create a named directory for the outputs
    id: str
    object_name: str
    action_configs: list[ActionConfig] = field(default_factory=list)


@dataclass_json
@dataclass
class TopLevelConfig:
    # Path to the .blend file to load. If relative, is relative to config file
    blend_file_path: Path
    # Path to the output directory. If relative, is relative to config file
    output_dir: Path
    # If present, a material will be processed from the given blend file
    material_configs: List[MaterialConfig] = field(default_factory=list)
    # If present, an animated sprite will be processed from the given blend file
    anim_sprite_configs: List[AnimSpriteConfig] = field(default_factory=list)
    # If present, a gltf animated scene will be processed from the given blend file
    anim_scene_configs: List[AnimSceneConfig] = field(default_factory=list)
