from pydantic import BaseModel, Field, RootModel
from typing import List, Literal
from pathlib import Path


class ObjConfig(BaseModel):
    object_name: str
    action_name: str | None


class CameraConfig(BaseModel):
    # Options: FRONT, SIDE, TOP
    view: str = "TOP"
    ortho_scale: float = 2


class AnimSpriteConfig(BaseModel):
    variant: Literal["anim_sprite"]
    blend_file_path: Path
    # Used to create a named directory for the outputs
    id: str

    sprite_size: int  # Size of each sprite (64x64, 128x128, etc.)
    sheet_width: int  # Number of sprites per row in the spritesheet

    start_frame: int = 1
    end_frame: int = 24
    frame_step: int = 1
    include_last_frame: bool = False
    camera: CameraConfig = Field(default_factory=CameraConfig)
    object_configs: list[ObjConfig] = Field(default_factory=list)


class MaterialConfig(BaseModel):
    variant: Literal["material"]
    blend_file_path: Path
    # Used to create a named directory for the outputs
    id: str
    # Name of material in blend file
    material_name: str
    # Size of each sprite (64x64, 128x128, etc.)
    sprite_size: int


class BakeConfig(BaseModel):
    step: int = 1


class ActionConfig(BaseModel):
    action_name: str
    bake_config: BakeConfig


class AnimSceneConfig(BaseModel):
    variant: Literal["anim_scene"]
    blend_file_path: Path
    # Used to create a named directory for the outputs
    id: str
    object_name: str
    action_configs: List[ActionConfig] = Field(default_factory=list)


class AssetConfig(RootModel):
    root: MaterialConfig | AnimSpriteConfig | AnimSceneConfig


class AssetCollection(BaseModel):
    # Used to create a named directory for the outputs
    id: str
    asset_configs: List[Path] = Field(default_factory=list)


class TopLevelConfig(BaseModel):
    output_dir: Path = Field(default_factory=lambda: Path("outputs"))
    collections: List[AssetCollection]
