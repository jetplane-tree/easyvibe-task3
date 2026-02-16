import os
from PIL import Image
from typing import Optional
from core.template_engine import list_templates, render_image
from core.platforms import get_platform_config

try:
    from core.bg_remover import remove_background
except ImportError:
    # rembg may not be installed; remove_background will be patched in tests
    def remove_background(input_image):
        raise RuntimeError("rembg is not installed. Install it or use skip_bg_removal=True.")

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "presets")

# Map style keywords to template name prefixes (Chinese)
STYLE_MAP = {
    "promo": "促销",
    "minimal": "简约",
    "premium": "高端",
    "fresh": "清新",
    "social": "社交",
    "ai_promo": "AI促销",
    "ai_minimal": "AI简约",
    "ai_premium": "AI高端",
    "ai_fresh": "AI清新",
    "ai_social": "AI社交",
}


def _find_template_for_platform(platform: str, style: str) -> dict:
    """Find the best matching template for a platform and style."""
    templates = list_templates(PRESETS_DIR)
    platform_config = get_platform_config(platform)
    style_keyword = STYLE_MAP.get(style, style)

    # Try exact match: platform + style
    for tpl in templates:
        if tpl.get("platform") == platform and style_keyword in tpl.get("name", ""):
            return tpl

    # Fallback: any template with matching style, adapt canvas size
    for tpl in templates:
        if style_keyword in tpl.get("name", ""):
            adapted = dict(tpl)
            adapted["canvas"] = {"width": platform_config["width"], "height": platform_config["height"]}
            return adapted

    # Last fallback: first template, adapt canvas
    if templates:
        adapted = dict(templates[0])
        adapted["canvas"] = {"width": platform_config["width"], "height": platform_config["height"]}
        return adapted

    # Emergency: bare template
    return {
        "name": "default",
        "canvas": {"width": platform_config["width"], "height": platform_config["height"]},
        "background": {"type": "solid", "colors": ["#FFFFFF"]},
        "elements": [
            {"type": "product_image", "x": "center", "y": "center", "max_width_pct": 70, "max_height_pct": 65},
        ],
    }


def compose_images(
    product_image: Image.Image,
    product_info: dict,
    platforms: list[str],
    template_style: str = "promo",
    logo: Optional[Image.Image] = None,
    skip_bg_removal: bool = False,
    ai_bg_override: Optional[Image.Image] = None,
) -> dict[str, Image.Image]:
    """Compose product images for multiple platforms.

    Args:
        product_image: original product image
        product_info: dict with name, selling_points, price
        platforms: list of platform keys
        template_style: style key (promo, minimal, premium, fresh, social)
        logo: optional store logo
        skip_bg_removal: skip rembg if image already has transparent bg

    Returns:
        Dict mapping platform key to composed PIL Image
    """
    if not skip_bg_removal:
        clean_image = remove_background(product_image)
    else:
        clean_image = product_image

    results = {}
    for platform in platforms:
        template = _find_template_for_platform(platform, template_style)
        composed = render_image(template, clean_image, product_info, logo=logo, ai_bg_override=ai_bg_override)
        results[platform] = composed

    return results
