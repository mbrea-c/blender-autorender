from pathlib import Path
from typing import Any
import bpy
import os
from PIL import Image

from blender_autorender.config import CameraConfig, AnimSpriteConfig, ObjConfig

bpy: Any


def set_action_for_object(obj_name: str, action_name: str):
    """Set the animation action for the given object."""
    obj: Any = bpy.data.objects.get(obj_name)
    if not obj:
        raise ValueError(f"Object {obj_name} not found")

    action: Any = bpy.data.actions.get(action_name)
    if not action:
        raise ValueError(f"Action {action_name} not found")

    # Assign the action to the object
    obj.animation_data_create()
    obj.animation_data.action = action


def set_actions_for_objects(objects: list[ObjConfig]):
    for obj_config in objects:
        if obj_config.action_name is not None:
            set_action_for_object(obj_config.object_name, obj_config.action_name)


def apply_camera_config(cam_config: CameraConfig):
    """Set the camera to orthographic and orient it to the given view."""
    cam: Any = bpy.data.objects.get("Camera")
    if not cam:
        raise ValueError("No camera object found.")

    # Set the camera to orthographic mode
    cam.data.type = "ORTHO"

    cam.data.ortho_scale = cam_config.ortho_scale

    # Position the camera based on the view
    if cam_config.view == "FRONT":
        cam.location = (0, -10, 0)
        cam.rotation_euler = (0, 0, 0)
    elif cam_config.view == "SIDE":
        cam.location = (-10, 0, 0)
        cam.rotation_euler = (0, 1.5708, 0)  # 90 degrees rotation
    elif cam_config.view == "TOP":
        cam.location = (0, 0, 10)
        cam.rotation_euler = (0, 0, 0)  # 90 degrees rotation in X
    else:
        raise ValueError(f"Unknown camera view: {cam_config.view}")


def configure_transparent_background():
    """Configure Blender render settings for transparent background."""
    scene = bpy.context.scene
    scene.render.film_transparent = True

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render_frame(output_path, frame):
    """Render the current frame to the output path."""
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)


def cleanup_nodes():
    scene = bpy.context.scene
    tree = scene.node_tree

    tree.nodes.clear()


def render_diffuse_extract(
    config: AnimSpriteConfig, frame: int, output_dir: Path
) -> Path:
    """Render out the raw albedo by directing the material base color to an emissive material node, and using that as the output.

    Only works if the final output of each material used is a BSDF node.
    """
    setup(config, frame)

    original_materials = dict()

    for i, obj_config in enumerate(config.object_configs):
        obj = bpy.data.objects.get(obj_config.object_name)
        if not obj.material_slots:
            mat = bpy.data.materials.new(name=f"{obj.name}_Material")
            mat.use_nodes = True
            obj.data.materials.append(mat)
        for j, slot in enumerate(obj.material_slots):
            if not slot.material:
                mat = bpy.data.materials.new(name=f"{obj.name}_{j}_Material")
                mat.use_nodes = True
                slot.material = mat

            print(f"Obj {obj_config.object_name} slot {j}: Replacing material")
            original_materials[(i, j)] = slot.material

            new_mat = slot.material.copy()
            new_mat.rename(f"___BaseColorExport_{i}_{j}")
            new_mat.use_nodes = True
            nt = new_mat.node_tree

            # Find Material Output
            for node in nt.nodes:
                if node.type == "OUTPUT_MATERIAL":
                    out_node = node
                    break
            else:
                print(
                    f"Obj {obj_config.object_name} slot {j}: Could not find material output"
                )
                continue

            surface_input = out_node.inputs.get("Surface")
            if not surface_input or not surface_input.is_linked:
                print(
                    f"Obj {obj_config.object_name} slot {j}: Material output surface not linked"
                )
                continue
            surface_input_link = surface_input.links[0]
            surface_source_node = surface_input_link.from_node

            if surface_source_node.type == "BSDF_PRINCIPLED":
                # Make an Emission node
                emission = nt.nodes.new("ShaderNodeEmission")
                emission.location = surface_source_node.location

                # Use the BSDF base color as emission input
                base_input = surface_source_node.inputs["Base Color"]
                if base_input.is_linked:
                    nt.links.new(
                        base_input.links[0].from_socket, emission.inputs["Color"]
                    )
                else:
                    emission.inputs["Color"].default_value = base_input.default_value

                # Reconnect emission -> output
                nt.links.new(emission.outputs["Emission"], surface_input_link.to_socket)

                # Optionally: mute the original BSDF
                surface_source_node.mute = True
            slot.material = new_mat

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.film_transparent = True
    scene.render.filepath = ""
    # Set "view transform" to "Raw"
    scene.view_settings.view_transform = "Raw"

    # Set image output settings
    scene.render.image_settings.file_format = (
        "PNG"  # Ensure output as PNG (supports alpha for diffuse)
    )
    scene.render.image_settings.color_mode = (
        "RGBA"  # Enable transparency (for diffuse if needed)
    )
    scene.render.filter_size = 0.01

    # Switch on nodes and get reference
    scene.use_nodes = True
    cleanup_nodes()
    tree = scene.node_tree
    world_tree = scene.world.node_tree
    links = tree.links

    bg_node = world_tree.nodes["Background"]
    bg_node.inputs["Strength"].default_value = 0.0

    # Create a node for outputting the rendered image
    image_output_node = tree.nodes.new(type="CompositorNodeOutputFile")
    image_output_node.label = "Image_Output"
    image_output_node.base_path = str(output_dir.joinpath("diffuse"))
    image_output_node.file_slots[0].path = f"diffuse_####"
    image_output_node.location = 400, 0

    # Create a node for the output from the renderer
    render_layers_node = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers_node.location = 0, 0

    # Link to compositor output
    links.new(render_layers_node.outputs["Image"], image_output_node.inputs["Image"])

    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)

    pathmaker = lambda t: output_dir.joinpath(f"{t}/{t}_{frame:04d}.png")

    return pathmaker("diffuse")


def render_diffuse_legacy(
    config: AnimSpriteConfig, frame: int, output_dir: Path
) -> Path:
    """Configure Blender to output specific render passes (Diffuse and Normal)."""
    setup(config, frame)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    view_layer = scene.view_layers["ViewLayer"]
    scene.render.film_transparent = True
    scene.render.filepath = ""
    # Set "view transform" to "Raw"
    scene.view_settings.view_transform = "Raw"

    # Enable Diffuse and Normal passes
    view_layer.use_pass_diffuse_color = True  # Enable diffuse pass
    view_layer.use_pass_normal = True  # Enable normal map pass
    view_layer.use_pass_z = True  # Enable normal map pass

    # Set image output settings
    scene.render.image_settings.file_format = (
        "PNG"  # Ensure output as PNG (supports alpha for diffuse)
    )
    scene.render.image_settings.color_mode = (
        "RGBA"  # Enable transparency (for diffuse if needed)
    )
    scene.render.filter_size = 0.01

    # Switch on nodes and get reference
    scene.use_nodes = True
    cleanup_nodes()
    tree = scene.node_tree
    world_tree = scene.world.node_tree
    links = tree.links

    bg_node = world_tree.nodes["Background"]
    bg_node.inputs["Strength"].default_value = 0.0

    # Create a node for outputting the rendered image
    image_output_node = tree.nodes.new(type="CompositorNodeOutputFile")
    image_output_node.label = "Image_Output"
    image_output_node.base_path = str(output_dir.joinpath("diffuse"))
    image_output_node.file_slots[0].path = f"diffuse_####"
    image_output_node.location = 400, 0

    # Create a node for the output from the renderer
    render_layers_node = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers_node.location = 0, 0

    # Create a Separate RGBA node to split the image into RGBA components
    separate_rgba_node = tree.nodes.new(type="CompositorNodeSepRGBA")
    separate_rgba_node.location = 200, 100

    # Link the Image output to the Separate RGBA node
    links.new(
        render_layers_node.outputs["Image"], separate_rgba_node.inputs[0]
    )  # Image to Separate RGBA

    alpha_over_node = tree.nodes.new(type="CompositorNodeAlphaOver")
    alpha_over_node.location = 200, 0

    # Link the diffuse color and image outputs to the Alpha Over node
    links.new(separate_rgba_node.outputs["A"], alpha_over_node.inputs[0])
    links.new(
        render_layers_node.outputs["Image"], alpha_over_node.inputs[1]
    )  # Image to Alpha Over (Image 2)
    links.new(
        render_layers_node.outputs["DiffCol"], alpha_over_node.inputs[2]
    )  # Diffuse Color to Alpha Over (Image 1)

    # Link all the nodes together
    links.new(alpha_over_node.outputs["Image"], image_output_node.inputs["Image"])

    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)

    pathmaker = lambda t: output_dir.joinpath(f"{t}/{t}_{frame:04d}.png")

    return pathmaker("diffuse")


def render_normal(config: AnimSpriteConfig, frame: int, output_dir: Path) -> Path:
    """Configure Blender to output specific render passes (Diffuse and Normal)."""

    setup(config, frame)

    output_path = output_dir.joinpath(f"normal/normal_{frame:04d}.png")

    # Clear existing materials
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

    scene = bpy.context.scene
    scene.use_nodes = True
    cleanup_nodes()
    scene.use_nodes = False

    scene.render.image_settings.file_format = "PNG"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.filepath = str(output_path)

    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.sequencer_colorspace_settings.name = "Non-Color"

    scene.display.shading.type = "SOLID"
    scene.display.shading.light = "MATCAP"
    scene.display.shading.studio_light = "check_normal+y.exr"
    # Adjust the light settings if needed (for studio light)
    scene.display.shading.use_scene_lights = False  # Disable scene lights
    scene.display.shading.use_scene_world = False  # Disable scene world
    scene.display.shading.show_specular_highlight = False  # Disable scene world

    bpy.ops.render.render(write_still=True)

    return output_path


def render_frame_with_passes(output_dir, frame, obj_name):
    """Configure Blender to output specific render passes (Diffuse and Normal)."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    view_layer = scene.view_layers["ViewLayer"]
    scene.render.film_transparent = True
    # Set "view transform" to "Raw"
    scene.view_settings.view_transform = "Raw"

    # Enable Diffuse and Normal passes
    view_layer.use_pass_diffuse_color = True  # Enable diffuse pass
    view_layer.use_pass_normal = True  # Enable normal map pass
    view_layer.use_pass_z = True  # Enable normal map pass

    # Set image output settings
    scene.render.image_settings.file_format = (
        "PNG"  # Ensure output as PNG (supports alpha for diffuse)
    )
    scene.render.image_settings.color_mode = (
        "RGBA"  # Enable transparency (for diffuse if needed)
    )
    scene.render.filter_size = 0.01

    # Switch on nodes and get reference
    scene.use_nodes = True
    tree = scene.node_tree
    world_tree = scene.world.node_tree
    links = tree.links

    tree.nodes.clear()

    bg_node = world_tree.nodes["Background"]
    bg_node.inputs["Strength"].default_value = 0.0

    # Create a node for outputting the rendered image
    image_output_node = tree.nodes.new(type="CompositorNodeOutputFile")
    image_output_node.label = "Image_Output"
    image_output_node.base_path = os.path.join(output_dir, "diffuse")
    image_output_node.file_slots[0].path = f"diffuse_####"
    image_output_node.location = 400, 0

    # Create a node for outputting the depth of each pixel from the camera
    depth_output_node = tree.nodes.new(type="CompositorNodeOutputFile")
    depth_output_node.label = "Depth_Output"
    depth_output_node.base_path = os.path.join(output_dir, "depth")
    depth_output_node.file_slots[0].path = f"depth_####"
    depth_output_node.location = 400, -100

    # Create a node for outputting the surface normals of each pixel
    normal_output_node = tree.nodes.new(type="CompositorNodeOutputFile")
    normal_output_node.label = "Normal_Output"
    normal_output_node.base_path = os.path.join(output_dir, "normal")
    normal_output_node.file_slots[0].path = f"normal_####"
    normal_output_node.location = 400, -300

    # Create a node for the output from the renderer
    render_layers_node = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers_node.location = 0, 0

    # Create a Separate RGBA node to split the image into RGBA components
    separate_rgba_node = tree.nodes.new(type="CompositorNodeSepRGBA")
    separate_rgba_node.location = 200, 100

    # Link the Image output to the Separate RGBA node
    links.new(
        render_layers_node.outputs["Image"], separate_rgba_node.inputs[0]
    )  # Image to Separate RGBA

    alpha_over_node = tree.nodes.new(type="CompositorNodeAlphaOver")
    alpha_over_node.location = 200, 0

    # Link the diffuse color and image outputs to the Alpha Over node
    links.new(separate_rgba_node.outputs["A"], alpha_over_node.inputs[0])
    links.new(
        render_layers_node.outputs["Image"], alpha_over_node.inputs[1]
    )  # Image to Alpha Over (Image 2)
    links.new(
        render_layers_node.outputs["DiffCol"], alpha_over_node.inputs[2]
    )  # Diffuse Color to Alpha Over (Image 1)

    # Add custom shader node setup to output camera space normals
    object_to_render = bpy.data.objects.get(
        obj_name
    )  # Assuming your object name is 'metarig'

    if object_to_render and object_to_render.type == "MESH":
        material = bpy.data.materials.new(name="CameraSpaceNormalMaterial")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Remove existing nodes
        nodes.clear()

        # Create the shader nodes for camera space normal output
        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        output_node.location = 400, 0

        emission_node = nodes.new(type="ShaderNodeEmission")
        emission_node.location = 200, 0

        geometry_node = nodes.new(type="ShaderNodeNewGeometry")
        geometry_node.location = 0, 0

        # Connect the normal output from the Geometry node to the Emission shader
        links.new(geometry_node.outputs["Normal"], emission_node.inputs["Color"])
        links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])

        # Assign the material to the object
        if object_to_render.data.materials:
            object_to_render.data.materials[0] = material
        else:
            object_to_render.data.materials.append(material)

    # Link all the nodes together
    links.new(alpha_over_node.outputs["Image"], image_output_node.inputs["Image"])
    links.new(render_layers_node.outputs["Depth"], depth_output_node.inputs["Image"])
    links.new(render_layers_node.outputs["Normal"], normal_output_node.inputs["Image"])

    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)

    pathmaker = lambda t: os.path.join(output_dir, f"{t}/{t}_{frame:04d}.png")

    return pathmaker("diffuse"), pathmaker("normal"), pathmaker("depth")


def get_action_frame_range(action_name):
    """Get the start and end frame of the specified action."""
    action = bpy.data.actions.get(action_name)

    if not action:
        raise ValueError(f"Action {action_name} not found.")

    # Initialize min and max frame values
    min_frame = float("inf")
    max_frame = float("-inf")

    # Loop through all F-curves in the action
    for fcurve in action.fcurves:
        # For each F-curve, loop through the keyframes (keyframe_points)
        for keyframe in fcurve.keyframe_points:
            frame = keyframe.co.x  # `co.x` gives the frame number
            min_frame = min(min_frame, frame)
            max_frame = max(max_frame, frame)

    return int(min_frame), int(max_frame)


def setup(config: AnimSpriteConfig, frame: int):
    bpy.ops.wm.revert_mainfile()

    configure_transparent_background()

    # Set action and camera view
    set_actions_for_objects(config.object_configs)
    apply_camera_config(config.camera)
    # Prepare for rendering
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = config.sprite_size
    scene.render.resolution_y = config.sprite_size
    bpy.context.scene.frame_set(frame)


def build_spritesheet(
    sprite_paths: list[Path],
    output_file_name: str,
    config: AnimSpriteConfig,
    output_dir: Path,
):
    num_sprites = len(sprite_paths)
    num_rows = num_sprites // config.sheet_width + (
        1 if num_sprites % config.sheet_width != 0 else 0
    )
    spritesheet_width = config.sheet_width * config.sprite_size
    spritesheet_height = num_rows * config.sprite_size
    spritesheet = Image.new("RGBA", (spritesheet_width, spritesheet_height))
    for index, diffuse_file in enumerate(sprite_paths):
        diffuse_image = Image.open(diffuse_file)
        x = (index % config.sheet_width) * config.sprite_size
        y = (index // config.sheet_width) * config.sprite_size
        spritesheet.paste(diffuse_image, (x, y))

    spritesheet_output_path = output_dir.joinpath(output_file_name)
    spritesheet.save(spritesheet_output_path)
    print(f"Spritesheet saved at {spritesheet_output_path}")


def render_spritesheet(
    config: AnimSpriteConfig, blend_file_path: Path, output_dir: Path
):
    """Render an animation as a spritesheet."""

    bpy.ops.wm.open_mainfile(filepath=str(blend_file_path))

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Render each frame as an image for each pass (Diffuse and Normal)
    diffuse_files = []
    normal_files = []

    frame = config.start_frame

    condition = (
        (lambda frame: frame <= config.end_frame)
        if config.include_last_frame
        else (lambda frame: frame < config.end_frame)
    )

    while condition(frame):
        diffuse_path = render_diffuse_extract(config, frame, output_dir=output_dir)
        normal_path = render_normal(config, frame, output_dir=output_dir)
        diffuse_files.append(diffuse_path)
        normal_files.append(normal_path)

        frame += config.frame_step

    build_spritesheet(
        diffuse_files, "spritesheet_diffuse.png", config, output_dir=output_dir
    )
    build_spritesheet(
        normal_files, "spritesheet_normal.png", config, output_dir=output_dir
    )


def validations(config: AnimSpriteConfig):
    if (config.end_frame - config.end_frame + 1) % config.frame_step != 0:
        raise ValueError("Frame step does not divide the total number of frames")


def entrypoint(
    config: AnimSpriteConfig, blend_file_path: Path, toplevel_output_dir: Path
):
    output_dir = toplevel_output_dir.joinpath("spritesheets").joinpath(config.id)

    validations(config)

    render_spritesheet(config, blend_file_path=blend_file_path, output_dir=output_dir)
