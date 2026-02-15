from PIL import Image
from core.bg_remover import remove_background


def test_remove_background_returns_rgba(sample_product_image):
    result = remove_background(sample_product_image)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGBA"


def test_remove_background_from_bytes():
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    result = remove_background(buf)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGBA"
