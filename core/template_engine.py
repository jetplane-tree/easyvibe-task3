import json
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional


def load_template(path: str) -> dict:
    """Load a template JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_templates(directory: str) -> list[dict]:
    """List all template JSON files in a directory, return their parsed contents."""
    templates = []
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".json"):
            tpl = load_template(os.path.join(directory, fname))
            tpl["_filename"] = fname
            templates.append(tpl)
    return templates


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a CJK-supporting font, fall back to default."""
    font_candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_gradient(draw: ImageDraw.Draw, width: int, height: int, colors: list[str]):
    """Draw a vertical linear gradient background."""
    from_color = tuple(int(colors[0].lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    to_color = tuple(int(colors[1].lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    for y in range(height):
        ratio = y / height
        r = int(from_color[0] + (to_color[0] - from_color[0]) * ratio)
        g = int(from_color[1] + (to_color[1] - from_color[1]) * ratio)
        b = int(from_color[2] + (to_color[2] - from_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _parse_color(color_str: str) -> tuple:
    """Parse hex color string to RGB or RGBA tuple."""
    c = color_str.lstrip("#")
    if len(c) == 6:
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))
    elif len(c) == 8:
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4, 6))
    return (0, 0, 0)


def render_image(
    template: dict,
    product_image: Image.Image,
    product_info: dict,
    logo: Optional[Image.Image] = None,
) -> Image.Image:
    """Render a product main image based on template config."""
    canvas_w = template["canvas"]["width"]
    canvas_h = template["canvas"]["height"]
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Draw background
    bg = template.get("background", {})
    bg_type = bg.get("type", "solid")
    bg_colors = bg.get("colors", ["#FFFFFF"])
    if bg_type == "gradient" and len(bg_colors) >= 2:
        _draw_gradient(draw, canvas_w, canvas_h, bg_colors)
    elif bg_type == "solid":
        canvas.paste(
            Image.new("RGB", (canvas_w, canvas_h), _parse_color(bg_colors[0]))
        )
        draw = ImageDraw.Draw(canvas)

    # Render elements
    for elem in template.get("elements", []):
        elem_type = elem["type"]
        if elem_type == "product_image":
            _place_product_image(canvas, product_image, elem, canvas_w, canvas_h)
        elif elem_type == "title":
            _draw_text(draw, product_info.get("name", ""), elem, canvas_w)
        elif elem_type == "price":
            prefix = elem.get("prefix", "¥")
            price_text = f"{prefix}{product_info.get('price', '')}"
            _draw_text(draw, price_text, elem, canvas_w)
        elif elem_type == "selling_points":
            points = product_info.get("selling_points", [])
            _draw_selling_points(draw, points, elem, canvas_w)

    # Overlay logo
    if logo is not None:
        logo_w = min(logo.width, canvas_w // 6)
        ratio = logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        pos = (canvas_w - logo_w - 20, canvas_h - logo_h - 20)
        if logo_resized.mode == "RGBA":
            canvas.paste(logo_resized, pos, logo_resized)
        else:
            canvas.paste(logo_resized, pos)

    return canvas


def _place_product_image(canvas, product_img, elem, canvas_w, canvas_h):
    """Resize and center-paste the product image onto canvas."""
    max_w = int(canvas_w * elem.get("max_width_pct", 60) / 100)
    max_h = int(canvas_h * elem.get("max_height_pct", 55) / 100)
    ratio = min(max_w / product_img.width, max_h / product_img.height)
    new_w = int(product_img.width * ratio)
    new_h = int(product_img.height * ratio)
    resized = product_img.resize((new_w, new_h), Image.LANCZOS)
    x = (canvas_w - new_w) // 2
    y = (canvas_h - new_h) // 2
    if resized.mode == "RGBA":
        canvas.paste(resized, (x, y), resized)
    else:
        canvas.paste(resized, (x, y))


def _draw_text(draw, text, elem, canvas_w):
    """Draw a text element on the canvas."""
    font_size = elem.get("font_size", 28)
    bold = elem.get("font_weight", "normal") == "bold"
    font = _get_font(font_size, bold)
    color = _parse_color(elem.get("color", "#000000"))
    x = elem.get("x", 0)
    y = elem.get("y", 0)
    if x == "center":
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (canvas_w - text_w) // 2
    draw.text((x, y), text, fill=color, font=font)


def _draw_selling_points(draw, points, elem, canvas_w):
    """Draw selling point tags."""
    if not points:
        return
    font_size = elem.get("font_size", 18)
    font = _get_font(font_size)
    color = _parse_color(elem.get("color", "#FFFFFF"))
    bg_color = _parse_color(elem.get("bg_color", "#FF0000CC"))
    x_start = elem.get("x", 0)
    y_start = elem.get("y", 0)
    padding = 8
    for i, point in enumerate(points):
        y = y_start + i * (font_size + 16)
        bbox = draw.textbbox((0, 0), point, font=font)
        text_w = bbox[2] - bbox[0]
        rect_coords = [
            x_start - padding,
            y - padding,
            x_start + text_w + padding,
            y + font_size + padding,
        ]
        # Use rounded_rectangle if available, otherwise fall back to rectangle
        if hasattr(draw, "rounded_rectangle"):
            draw.rounded_rectangle(rect_coords, radius=4, fill=bg_color)
        else:
            draw.rectangle(rect_coords, fill=bg_color)
        draw.text((x_start, y), point, fill=color, font=font)
