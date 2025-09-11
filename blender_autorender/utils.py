# pyright: basic

from pathlib import Path
from typing import Any
from uuid import uuid4
from PIL import Image
import numpy as np

def pack_channels(
    red: Path | None,
    green: Path | None,
    blue: Path | None,
    output_file_name: str,
    img_size: int,
    output_dir: Path,
) -> Path:
    def load_or_default(
        img_path: Path | None,
        default_value: int = 0,
        default_alpha: int = 0,
        size: tuple[int, int] | None = None,
    ) -> Image.Image:
        if img_path:
            img = Image.open(img_path).convert("LA")
            if size:
                img = img.resize(size)
        else:
            assert size is not None
            l = Image.new("L", size, color=default_value)
            a = Image.new("L", size, color=default_alpha)
            img = Image.merge("LA", (l, a))
        return img

    red_img = load_or_default(
        red,
        default_value=0,
        default_alpha=0,
        size=(img_size, img_size),
    )
    green_img = load_or_default(
        green,
        default_value=0,
        default_alpha=0,
        size=(img_size, img_size),
    )
    blue_img = load_or_default(
        blue,
        default_value=0,
        default_alpha=0,
        size=(img_size, img_size),
    )
    alphas = []
    for img in (red_img, green_img, blue_img):
        assert img.mode == "LA"
        alphas.append(np.array(img.getchannel("A"), dtype=np.uint8))

    alpha_max = np.maximum.reduce(alphas)
    alpha_img = Image.fromarray(alpha_max, mode="L")

    merged = Image.merge(
        "RGBA",
        (
            red_img.getchannel("L"),
            green_img.getchannel("L"),
            blue_img.getchannel("L"),
            alpha_img,
        ),
    )
    if not output_dir.exists():
        output_dir.mkdir()
    path = output_dir.joinpath(output_file_name)
    merged.save(path)
    return path


Material = Any


def reconnect_bsdf_input(
    material: Material,
    bsdf_input_name: str,
) -> Material | None:
    """
    This function creates a BSDF material where the provided input name is reconnected as an emission output.
    Assumes the provided material has a BSDF_PRINCIPLED directly connected to the surface input of the material output.
    """
    new_mat = material.copy()
    new_mat.rename(f"___{bsdf_input_name.replace(' ', '')}Export_{uuid4()}")
    new_mat.use_nodes = True
    nt = new_mat.node_tree

    # Find Material Output
    for node in nt.nodes:
        if node.type == "OUTPUT_MATERIAL":
            out_node = node
            break
    else:
        print(f"Material {material.name}: Could not find material output")
        return None

    surface_input = out_node.inputs.get("Surface")
    if not surface_input or not surface_input.is_linked:
        print(f"Material {material.name}: Material output surface not linked")
        return None

    surface_input_link = surface_input.links[0]
    surface_source_node = surface_input_link.from_node

    if surface_source_node.type == "BSDF_PRINCIPLED":
        # Make an Emission node
        emission = nt.nodes.new("ShaderNodeEmission")
        emission.location = surface_source_node.location

        # Use the BSDF base color as emission input
        base_input = surface_source_node.inputs[bsdf_input_name]
        if base_input.is_linked:
            nt.links.new(base_input.links[0].from_socket, emission.inputs["Color"])
        else:
            if isinstance(base_input.default_value, float):
                val = base_input.default_value
                emission.inputs["Color"].default_value = (val, val, val, 1.0)
            else:
                emission.inputs["Color"].default_value = base_input.default_value

        # Reconnect emission -> output
        nt.links.new(emission.outputs["Emission"], surface_input_link.to_socket)

        # Optionally: mute the original BSDF
        surface_source_node.mute = True
    return new_mat
