from pathlib import Path
import bpy
import os
from dataclasses import dataclass
from PIL import Image


@dataclass
class Config:
    object_name: str
    action_name: str
    camera_view: str  # Options: FRONT, SIDE, TOP
    output_dir: Path
    sprite_size: int  # Size of each sprite (64x64, 128x128, etc.)
    sheet_width: int  # Number of sprites per row in the spritesheet
    frame_step: int


def set_action_for_object(obj_name, action_name):
    """Set the animation action for the given object."""
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        raise ValueError(f"Object {obj_name} not found")

    action = bpy.data.actions.get(action_name)
    if not action:
        raise ValueError(f"Action {action_name} not found")

    # Assign the action to the object
    obj.animation_data_create()
    obj.animation_data.action = action


def set_camera_orthographic_view(view="FRONT"):
    """Set the camera to orthographic and orient it to the given view."""
    cam = bpy.data.objects.get("Camera")
    if not cam:
        raise ValueError("No camera object found.")

    # Set the camera to orthographic mode
    cam.data.type = "ORTHO"

    cam.data.ortho_scale = 2.0

    # Position the camera based on the view
    if view == "FRONT":
        cam.location = (0, -10, 0)
        cam.rotation_euler = (0, 0, 0)
    elif view == "SIDE":
        cam.location = (-10, 0, 0)
        cam.rotation_euler = (0, 1.5708, 0)  # 90 degrees rotation
    elif view == "TOP":
        cam.location = (0, 0, 10)
        cam.rotation_euler = (0, 0, 0)  # 90 degrees rotation in X
    else:
        raise ValueError(f"Unknown camera view: {view}")


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


def render_diffuse(config: Config, frame: int):
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
    image_output_node.base_path = os.path.join(config.output_dir, "diffuse")
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

    pathmaker = lambda t: os.path.join(config.output_dir, f"{t}/{t}_{frame:04d}.png")

    return pathmaker("diffuse")


def render_normal(config: Config, frame: int):
    """Configure Blender to output specific render passes (Diffuse and Normal)."""

    setup(config, frame)

    output_path = os.path.join(config.output_dir, f"normal/normal_{frame:04d}.png")

    # Clear existing materials
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

    scene = bpy.context.scene
    scene.use_nodes = True
    cleanup_nodes()
    scene.use_nodes = False

    scene.render.image_settings.file_format = "PNG"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.filepath = output_path

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


def setup(config: Config, frame: int):
    bpy.ops.wm.revert_mainfile()

    configure_transparent_background()

    # Set action and camera view
    set_action_for_object(config.object_name, config.action_name)
    set_camera_orthographic_view(config.camera_view)
    # Prepare for rendering
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = config.sprite_size
    scene.render.resolution_y = config.sprite_size
    bpy.context.scene.frame_set(frame)


def render_spritesheet(config: Config):
    """Render an animation as a spritesheet."""

    # Ensure output directory exists
    if not os.path.exists(config.output_dir):
        os.makedirs(config.output_dir)

    # Get scene info
    scene = bpy.context.scene
    frame_start, frame_end = get_action_frame_range(config.action_name)
    # frame_start = scene.frame_start
    # frame_end = scene.frame_end
    total_frames = frame_end - frame_start + 1

    # Variables for spritesheet dimensions
    sprites_per_row = config.sheet_width
    num_rows = (total_frames + sprites_per_row - 1) // sprites_per_row
    spritesheet_width = sprites_per_row * config.sprite_size
    spritesheet_height = num_rows * config.sprite_size

    # Render each frame as an image for each pass (Diffuse and Normal)
    diffuse_files = []
    normal_files = []
    for frame in range(frame_start, frame_end + 1, config.frame_step):
        diffuse_path = render_diffuse(config, frame)
        normal_path = render_normal(config, frame)
        diffuse_files.append(diffuse_path)
        normal_files.append(normal_path)


    # Diffuse Spritesheet
    diffuse_spritesheet = Image.new("RGBA", (spritesheet_width, spritesheet_height))
    for index, diffuse_file in enumerate(diffuse_files):
        diffuse_image = Image.open(diffuse_file)
        x = (index % sprites_per_row) * config.sprite_size
        y = (index // sprites_per_row) * config.sprite_size
        diffuse_spritesheet.paste(diffuse_image, (x, y))

    diffuse_spritesheet_output_path = os.path.join(
        config.output_dir, "spritesheet_diffuse.png"
    )
    diffuse_spritesheet.save(diffuse_spritesheet_output_path)
    print(f"Diffuse Spritesheet saved at {diffuse_spritesheet_output_path}")

    # Normal Spritesheet
    normal_spritesheet = Image.new("RGBA", (spritesheet_width, spritesheet_height))
    for index, normal_file in enumerate(normal_files):
        normal_image = Image.open(normal_file)
        x = (index % sprites_per_row) * config.sprite_size
        y = (index // sprites_per_row) * config.sprite_size
        normal_spritesheet.paste(normal_image, (x, y))

    normal_spritesheet_output_path = os.path.join(
        config.output_dir, "spritesheet_normal.png"
    )
    normal_spritesheet.save(normal_spritesheet_output_path)
    print(f"Normal Spritesheet saved at {normal_spritesheet_output_path}")


# Example configuration
config = Config(
    object_name="metarig",
    action_name="Walk",
    camera_view="TOP",  # Options: FRONT, SIDE, TOP
    output_dir=Path("test_output_spritesheet"),
    sprite_size=64,  # Size of each sprite (64x64, 128x128, etc.)
    sheet_width=10,  # Number of sprites per row in the spritesheet
    frame_step=6,  # Number of sprites per row in the spritesheet
)

# Call the function to render the spritesheet
render_spritesheet(config)
