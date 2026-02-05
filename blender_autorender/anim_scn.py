# pyright: strict
from blender_autorender.utils import run_with_redirected_logs

import os
from pathlib import Path
import tempfile
from typing import Any
from blender_autorender.config import ActionConfig, AnimSceneConfig
import bpy

bpy: Any


class AnimSceneProcessor:
    def __init__(
        self, config: AnimSceneConfig, toplevel_output_dir: Path, log_path: Path
    ):
        self.config = config
        self.output_dir = toplevel_output_dir.joinpath("anim_scenes").joinpath(
            config.id
        )
        self.log_path = log_path

    def process(self):
        run_with_redirected_logs(self.log_path, lambda: self._process())

    def _process(self):
        bpy.ops.wm.open_mainfile(filepath=str(self.config.blend_file_path))

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self._clear_all_object_animations()
        self._delete_unwanted_anims()
        self._setup()

        for action_config in self.config.action_configs:
            self._bake_action(action_config)

        for action_config in self.config.action_configs:
            self._move_action_to_nla(action_config)

        self._clear_active_animation()
        self._export_gltf()

    def _clear_all_object_animations(self):
        for obj in bpy.data.objects:
            if obj.animation_data:
                obj.animation_data_clear()

    def _delete_unwanted_anims(self):
        animset = {a.action_name for a in self.config.action_configs}

        for action in bpy.data.actions:
            if action.name not in animset:
                bpy.data.actions.remove(action)

    def _bake_action(self, config: ActionConfig):
        obj = bpy.data.objects[self.config.object_name]
        action = bpy.data.actions[config.action_name]

        obj.animation_data.action = action

        bpy.context.view_layer.update()

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")

        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        if obj.animation_data.nla_tracks:
            obj.animation_data.nla_tracks.clear()

        if obj.type == "ARMATURE":
            bpy.ops.object.mode_set(mode="POSE")
            bpy.ops.pose.select_all(action="SELECT")

        bpy.ops.nla.bake(
            frame_start=int(action.frame_range[0]),
            frame_end=int(action.frame_range[1]),
            step=config.bake_config.step,
            only_selected=False,
            visual_keying=True,
            clear_constraints=False,
            clear_parents=False,
            use_current_action=True,
        )

    def _setup(self):
        obj = bpy.data.objects[self.config.object_name]
        if obj.animation_data is None:
            obj.animation_data_create()

    def _move_action_to_nla(self, config: ActionConfig):
        obj = bpy.data.objects[self.config.object_name]
        action = bpy.data.actions[config.action_name]
        track = obj.animation_data.nla_tracks.new()
        track.name = config.action_name
        strip = track.strips.new(config.action_name, int(action.frame_range[0]), action)
        strip.action = action

    def _clear_active_animation(self):
        obj = bpy.data.objects[self.config.object_name]
        obj.animation_data.action = None

    def _export_gltf(self):
        bpy.ops.export_scene.gltf(
            filepath=str(self.output_dir.joinpath("model.glb")),
            export_format="GLB",
            export_animations=True,
            export_animation_mode="ACTIONS",
            export_force_sampling=False,
            export_apply=True,
        )

    def _save_temp_for_debug(self, name: str = "debug_scene"):
        temp_dir = tempfile.mkdtemp()
        temp_file_path = f"{temp_dir}/{name}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=temp_file_path)
        print(f"Scene saved to temporary file: {temp_file_path}")
