import os
from core.template_engine import load_template, list_templates, render_image
from PIL import Image

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "presets")


def test_load_template():
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    assert tpl["name"] == "促销爆款"
    assert tpl["canvas"]["width"] == 800
    assert len(tpl["elements"]) > 0


def test_list_templates():
    templates = list_templates(PRESETS_DIR)
    assert len(templates) >= 2
    names = [t["name"] for t in templates]
    assert "促销爆款" in names
    assert "简约白底" in names


def test_render_image_returns_pil_image():
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {
        "name": "测试商品",
        "selling_points": ["卖点1", "卖点2"],
        "price": 99.9,
    }
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)
    assert result.size == (800, 800)


def test_render_image_with_logo():
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    logo = Image.new("RGBA", (100, 50), (0, 0, 255, 200))
    product_info = {
        "name": "测试商品",
        "selling_points": ["卖点1"],
        "price": 59.9,
    }
    result = render_image(tpl, product_img, product_info, logo=logo)
    assert isinstance(result, Image.Image)
