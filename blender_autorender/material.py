from pathlib import Path
from typing import Any
from blender_autorender.config import MaterialConfig
from blender_autorender.utils import pack_channels
import bpy
import os

bpy: Any


# Function to create a plane object and assign a material to it
def create_plane_with_material(material_name):
    # Check if the material exists
    for mat in bpy.data.materials:
        print(mat)
    if material_name not in bpy.data.materials:
        raise Exception(f"Material '{material_name}' not found.")

    # Create a new plane
    bpy.ops.mesh.primitive_plane_add(
        size=2, enter_editmode=False, align="WORLD", location=(0, 0, 0)
    )
    obj = bpy.context.object  # Get the newly created object

    # Ensure the object has the material
    material = bpy.data.materials[material_name]
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

    return obj


# Function to bake a given type of texture (e.g., Diffuse, Normal, Roughness)
def bake_texture(config: MaterialConfig, texture_type: str, file_output: Path):
    obj = bpy.context.view_layer.objects.active

    # Set the object to active and ensure it's in Object mode
    bpy.ops.object.select_all(action="DESELECT")  # Deselect all objects
    obj.select_set(True)  # Select our object
    bpy.context.view_layer.objects.active = obj

    # Create a new image for baking
    image = bpy.data.images.new(
        f"{texture_type}.png", width=config.sprite_size, height=config.sprite_size
    )

    # Create a new image texture node in the material
    material = bpy.data.materials[config.material_name]
    node_tree = material.node_tree
    nodes = node_tree.nodes
    image_node = nodes.new(type="ShaderNodeTexImage")
    image_node.image = image
    node_tree.nodes.active = image_node  # Set the new node as the active one

    # Bake only diffuse color without any lighting
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_diffuse = True
    bpy.context.scene.render.bake.use_pass_color = True

    # Set bake settings based on the texture type
    if texture_type == "diffuse":
        bpy.ops.object.bake(type="DIFFUSE")
    elif texture_type == "normal":
        bpy.ops.object.bake(type="NORMAL")
    elif texture_type == "roughness":
        bpy.ops.object.bake(type="ROUGHNESS")
    else:
        raise ValueError(f"Unknown texture type: {texture_type}")

    # Save the baked image to file
    image.filepath_raw = str(file_output)
    image.file_format = "PNG"
    image.save()

    # Cleanup: Remove the image node from the material
    nodes.remove(image_node)

    print(f"{texture_type.capitalize()} map saved to: {file_output}")


# Main function to bake and save all maps
def bake_material_maps(config: MaterialConfig, blend_file_path: Path, output_dir: Path):
    bpy.ops.wm.open_mainfile(filepath=str(blend_file_path))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create a plane and apply the material
    create_plane_with_material(config.material_name)

    roughness_path = output_dir.joinpath("roughness.png")
    metallic_path = output_dir.joinpath("metallic.png")

    # Bake Diffuse map
    bake_texture(
        config=config,
        texture_type="diffuse",
        file_output=output_dir.joinpath("diffuse.png"),
    )

    # Bake Normal map
    bake_texture(
        config=config,
        texture_type="normal",
        file_output=output_dir.joinpath("normal.png"),
    )

    # Bake Roughness map
    bake_texture(
        config=config,
        texture_type="roughness",
        file_output=roughness_path,
    )

    # Bake metallic map
    # bake_texture(
    #     material_name=config.material_name,
    #     texture_type="metallic",
    #     file_output=metallic_path,
    # )

    pack_channels(
        None,
        roughness_path,
        None,
        output_file_name="orm.png",
        img_size=config.sprite_size,
        output_dir=output_dir,
    )

    print("Baking completed!")

    # Clean up: Delete the plane object after baking
    bpy.ops.object.delete()


def entrypoint_material(
    config: MaterialConfig, blend_file_path: Path, toplevel_output_dir: Path
):
    output_dir = toplevel_output_dir.joinpath("materials").joinpath(config.id)
    bake_material_maps(config, blend_file_path=blend_file_path, output_dir=output_dir)
