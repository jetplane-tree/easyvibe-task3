import os
from unittest.mock import patch, MagicMock
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


def test_render_output_is_rgb():
    """Verify render_image outputs RGB mode (converted from RGBA pipeline)."""
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "测试", "selling_points": ["卖点"], "price": 100}
    result = render_image(tpl, product_img, product_info)
    assert result.mode == "RGB"


def test_render_with_overlay_bands():
    """Template with overlay_color should render without errors."""
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    assert "overlay_color" in tpl["background"]
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "测试", "selling_points": ["卖点"], "price": 100}
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"


def test_render_with_bokeh():
    """Template with bokeh config should render without errors."""
    tpl = load_template(os.path.join(PRESETS_DIR, "premium_taobao.json"))
    assert "bokeh" in tpl["background"]
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "测试", "selling_points": ["卖点"], "price": 100}
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)


def test_render_price_badge():
    """Template with price badge style should render without errors."""
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    price_elem = [e for e in tpl["elements"] if e["type"] == "price"][0]
    assert price_elem.get("style") == "badge"
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "测试", "selling_points": ["卖点"], "price": 299}
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)


def test_render_title_banner():
    """Template with title banner style should render without errors."""
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    title_elem = [e for e in tpl["elements"] if e["type"] == "title"][0]
    assert title_elem.get("style") == "banner"
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "旗舰商品名称", "selling_points": [], "price": 199}
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)


def test_render_horizontal_selling_points():
    """Template with horizontal selling points layout should render."""
    tpl = load_template(os.path.join(PRESETS_DIR, "promo_taobao.json"))
    sp_elem = [e for e in tpl["elements"] if e["type"] == "selling_points"][0]
    assert sp_elem.get("layout") == "horizontal"
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {
        "name": "测试",
        "selling_points": ["轻量透气", "缓震回弹", "耐磨大底", "潮流配色"],
        "price": 599,
    }
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)


def test_render_product_glow():
    """Template with glow_color should render with glow effect."""
    tpl = load_template(os.path.join(PRESETS_DIR, "premium_taobao.json"))
    pi_elem = [e for e in tpl["elements"] if e["type"] == "product_image"][0]
    assert pi_elem.get("glow_color") is not None
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "测试", "selling_points": ["卖点"], "price": 100}
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)


def test_render_ai_template_with_fallback():
    """AI template should fallback gracefully when AI generation fails."""
    tpl = load_template(os.path.join(PRESETS_DIR, "ai_promo_taobao.json"))
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {
        "name": "AI测试商品",
        "selling_points": ["卖点1", "卖点2"],
        "price": 399,
    }
    with patch("core.bg_generator.generate_ai_background", side_effect=Exception("API error")):
        result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"
    assert result.size == (800, 800)


def test_render_all_templates_no_error():
    """All templates should render without errors."""
    templates = list_templates(PRESETS_DIR)
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {
        "name": "全模板测试",
        "selling_points": ["卖点A", "卖点B"],
        "price": 199,
    }
    for tpl in templates:
        bg_type = tpl.get("background", {}).get("type")
        if bg_type == "ai":
            with patch("core.bg_generator.generate_ai_background", side_effect=Exception("skip")):
                result = render_image(tpl, product_img, product_info)
        else:
            result = render_image(tpl, product_img, product_info)
        assert isinstance(result, Image.Image), f"Failed for template: {tpl['name']}"
        assert result.mode == "RGB", f"Not RGB for template: {tpl['name']}"


def test_render_minimal_template_no_decorations():
    """Minimal template without overlay/bokeh should still work fine."""
    tpl = load_template(os.path.join(PRESETS_DIR, "minimal_taobao.json"))
    assert "overlay_color" not in tpl.get("background", {})
    assert "bokeh" not in tpl.get("background", {})
    product_img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
    product_info = {"name": "简约测试", "price": 50}
    result = render_image(tpl, product_img, product_info)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"
