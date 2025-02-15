import os
from pathlib import Path
from typing import Any
from blender_autorender.config import ActionConfig, AnimSceneConfig
import bpy

bpy: Any

class AnimSceneProcessor:
    def __init__(
        self,
        config: AnimSceneConfig,
        blend_file_path: Path,
        toplevel_output_dir: Path,
    ):
        self.config = config
        self.blend_file_path = blend_file_path
        self.output_dir = toplevel_output_dir.joinpath("spritesheets").joinpath(
            config.id
        )

    def process(self):
        bpy.ops.wm.open_mainfile(filepath=str(self.blend_file_path))

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for action_config in self.config.action_configs:
            self._bake_action(action_config)
            self._move_action_to_nla(action_config)

        self._export_gltf()

    def _bake_action(self, config: ActionConfig):
        obj = bpy.data.objects[self.config.object_name]
        action = bpy.data.actions[config.action_name]

        obj.animation_data.action = action

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")

        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.active_action = action

        bpy.ops.nla.bake(
            frame_start=int(action.frame_range[0]),
            frame_end=int(action.frame_range[1]),
            step=config.bake_config.step,
            only_selected=False,
            visual_keying=True,
            clear_constraints=True,
            clear_parents=False,
            use_current_action=True,
        )

    def _move_action_to_nla(self, config: ActionConfig):
        obj = bpy.data.objects[self.config.object_name]
        action = bpy.data.actions[config.action_name]
        track = obj.animation_data.nla_tracks.new()
        track.name = config.action_name
        strip = track.strips.new(config.action_name, int(action.frame_range[0]), action)
        strip.action = action

    def _export_gltf(self):
        bpy.ops.export_scene.gltf(
            filepath=str(self.output_dir.joinpath("model.glb")),
            export_format="GLB",
            export_animations=True,
            export_animation_mode="ACTIONS",
            export_force_sampling=False,
        )
