import pytest
from PIL import Image
import os

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_product_image():
    """Create a simple test image with a colored square on white background."""
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    img = Image.new("RGBA", (400, 400), (255, 255, 255, 255))
    for x in range(100, 300):
        for y in range(100, 300):
            img.putpixel((x, y), (255, 0, 0, 255))
    path = os.path.join(FIXTURES_DIR, "test_product.png")
    img.save(path)
    return path
