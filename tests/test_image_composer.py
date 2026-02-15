from unittest.mock import patch
from PIL import Image
from core.image_composer import compose_images


def test_compose_images_single_platform():
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 255))
    product_info = {
        "name": "测试商品",
        "selling_points": ["卖点1", "卖点2"],
        "price": 99.9,
    }

    with patch("core.image_composer.remove_background") as mock_bg:
        mock_bg.return_value = product_img
        results = compose_images(
            product_image=product_img,
            product_info=product_info,
            platforms=["taobao"],
            template_style="promo",
        )

    assert "taobao" in results
    assert isinstance(results["taobao"], Image.Image)
    assert results["taobao"].size == (800, 800)


def test_compose_images_multi_platform():
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 255))
    product_info = {
        "name": "测试商品",
        "selling_points": ["卖点1"],
        "price": 50,
    }

    with patch("core.image_composer.remove_background") as mock_bg:
        mock_bg.return_value = product_img
        results = compose_images(
            product_image=product_img,
            product_info=product_info,
            platforms=["taobao", "pinduoduo", "douyin"],
            template_style="promo",
        )

    assert len(results) == 3
    assert results["pinduoduo"].size == (750, 352)
    assert results["douyin"].size == (720, 960)
