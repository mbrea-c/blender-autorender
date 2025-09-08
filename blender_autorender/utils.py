from pathlib import Path
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
