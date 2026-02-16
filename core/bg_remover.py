from PIL import Image
from rembg import remove
from io import BytesIO
from typing import Union


def remove_background(input_image: Union[str, BytesIO, Image.Image]) -> Image.Image:
    """Remove background from product image.

    Args:
        input_image: file path (str), BytesIO object, or PIL Image

    Returns:
        RGBA PIL Image with background removed
    """
    if isinstance(input_image, Image.Image):
        img = input_image
    elif isinstance(input_image, str):
        img = Image.open(input_image)
    else:
        img = Image.open(input_image)

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    output = remove(img)
    return output
