import json
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont
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


def _sample_brightness(image, x, y, w, h):
    """Sample average brightness of a region on the image. Returns 0-255."""
    sx, sy = max(0, int(x)), max(0, int(y))
    ex = min(image.width, sx + int(w))
    ey = min(image.height, sy + int(h))
    if ex <= sx or ey <= sy:
        return 128
    region = image.crop((sx, sy, ex, ey)).convert("RGB")
    pixels = list(region.getdata())
    if not pixels:
        return 128
    return sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels) / len(pixels)


# --- New rendering helper functions ---


def _draw_overlay_bands(canvas, bg_config):
    """Draw gradient overlay bands at top/bottom for text readability."""
    w, h = canvas.size
    overlay_color = _parse_color(bg_config.get("overlay_color", "#000000"))
    r, g, b = overlay_color[:3]

    # Top band: 25% of canvas height, fade from alpha=160 to 0
    top_h = int(h * 0.25)
    top_band = Image.new("RGBA", (w, top_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(top_band, "RGBA")
    for y in range(top_h):
        alpha = int(160 * (1 - y / top_h))
        draw.line([(0, y), (w, y)], fill=(r, g, b, alpha))
    canvas.alpha_composite(top_band, (0, 0))

    # Bottom band: 25%, fade from 0 to alpha=160
    bot_h = int(h * 0.25)
    bot_band = Image.new("RGBA", (w, bot_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bot_band, "RGBA")
    for y in range(bot_h):
        alpha = int(160 * y / bot_h)
        draw.line([(0, y), (w, y)], fill=(r, g, b, alpha))
    canvas.alpha_composite(bot_band, (0, h - bot_h))


def _draw_product_glow(canvas, cx, cy, glow_w, glow_h, glow_color):
    """Draw a radial glow behind the product."""
    cw, ch = canvas.size
    glow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    r, g, b = _parse_color(glow_color)[:3]
    for i in range(20):
        ratio = i / 20
        rx = int(glow_w * 0.3 * (1 + ratio))
        ry = int(glow_h * 0.3 * (1 + ratio))
        alpha = int(60 * (1 - ratio))
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(r, g, b, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(25))
    canvas.alpha_composite(glow)


def _draw_price_badge(canvas, text, elem, canvas_w):
    """Draw price inside a gradient badge."""
    font = _get_font(elem["font_size"], True)
    draw_tmp = ImageDraw.Draw(canvas)
    bbox = draw_tmp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad_x, pad_y = 30, 16
    badge_w = tw + pad_x * 2
    badge_h = th + pad_y * 2

    bx = (canvas_w - badge_w) // 2 if elem.get("x") == "center" else elem["x"]
    by = elem["y"]

    # Gradient rounded rectangle badge
    badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge, "RGBA")
    badge_colors = elem.get("badge_colors", ["#FF4444", "#CC0000"])
    c1, c2 = _parse_color(badge_colors[0]), _parse_color(badge_colors[1])
    for row in range(badge_h):
        ratio = row / badge_h
        cr = int(c1[0] + (c2[0] - c1[0]) * ratio)
        cg = int(c1[1] + (c2[1] - c1[1]) * ratio)
        cb = int(c1[2] + (c2[2] - c1[2]) * ratio)
        badge_draw.line([(0, row), (badge_w, row)], fill=(cr, cg, cb, 230))

    # Pill-shaped mask
    mask = Image.new("L", (badge_w, badge_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [0, 0, badge_w - 1, badge_h - 1], radius=badge_h // 2, fill=255
    )
    badge.putalpha(mask)
    canvas.alpha_composite(badge, (bx, by))

    # Draw text on canvas
    draw_rgba = ImageDraw.Draw(canvas, "RGBA")
    tx = bx + pad_x
    ty = by + pad_y
    color = _parse_color(elem.get("color", "#FFFFFF"))
    draw_rgba.text((tx, ty), text, fill=color, font=font)


def _draw_title_banner(canvas, text, elem, canvas_w):
    """Draw title text on a semi-transparent banner."""
    font = _get_font(elem["font_size"], elem.get("font_weight") == "bold")
    draw_tmp = ImageDraw.Draw(canvas)
    bbox = draw_tmp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad_x, pad_y = 40, 12
    banner_w = tw + pad_x * 2
    banner_h = th + pad_y * 2
    bx = (canvas_w - banner_w) // 2 if elem.get("x") == "center" else elem["x"]
    by = elem["y"]

    banner_color = _parse_color(elem.get("banner_color", "#00000088"))
    banner = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(banner, "RGBA")
    b_draw.rounded_rectangle(
        [0, 0, banner_w - 1, banner_h - 1], radius=8, fill=banner_color
    )
    canvas.alpha_composite(banner, (bx, by))

    draw_rgba = ImageDraw.Draw(canvas, "RGBA")
    tx = bx + pad_x
    ty = by + pad_y
    color = _parse_color(elem.get("color", "#FFFFFF"))
    stroke_w = elem.get("stroke_width", 0)
    stroke_c = _parse_color(elem.get("stroke_color", "#00000066"))
    if stroke_w > 0:
        draw_rgba.text(
            (tx, ty), text, fill=color, font=font,
            stroke_width=stroke_w, stroke_fill=stroke_c,
        )
    else:
        draw_rgba.text((tx, ty), text, fill=color, font=font)


def _draw_bokeh(canvas, bg_config):
    """Draw decorative bokeh circles."""
    w, h = canvas.size
    bokeh_config = bg_config.get("bokeh", {})
    if not bokeh_config:
        return
    color = _parse_color(bokeh_config.get("color", "#FFFFFF"))
    count = bokeh_config.get("count", 15)
    seed = bokeh_config.get("seed", 42)

    rng = random.Random(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")

    r, g, b = color[:3]
    for _ in range(count):
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        radius = rng.randint(8, 40)
        alpha = rng.randint(20, 60)
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(r, g, b, alpha),
        )

    layer = layer.filter(ImageFilter.GaussianBlur(6))
    canvas.alpha_composite(layer)


# --- End new rendering helpers ---


def render_image(
    template: dict,
    product_image: Image.Image,
    product_info: dict,
    logo: Optional[Image.Image] = None,
    ai_bg_override: Optional[Image.Image] = None,
    ai_composed_override: Optional[Image.Image] = None,
) -> Image.Image:
    """Render a product main image based on template config."""
    canvas_w = template["canvas"]["width"]
    canvas_h = template["canvas"]["height"]

    # If ai_composed_override is provided, use it as base (product already in scene)
    has_composed = ai_composed_override is not None

    if has_composed:
        canvas = ai_composed_override
        if canvas.size != (canvas_w, canvas_h):
            canvas = canvas.resize((canvas_w, canvas_h), Image.LANCZOS)
        canvas = canvas.convert("RGBA")
        draw = ImageDraw.Draw(canvas, "RGBA")
    else:
        canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)

    # 1. Draw background (skip if composed override — background already includes product)
    bg = template.get("background", {})
    if not has_composed:
        bg_type = bg.get("type", "solid")
        bg_colors = bg.get("colors", ["#FFFFFF"])
        if bg_type == "ai":
            if ai_bg_override is not None:
                ai_bg = ai_bg_override
                if ai_bg.size != (canvas_w, canvas_h):
                    ai_bg = ai_bg.resize((canvas_w, canvas_h), Image.LANCZOS)
                canvas = ai_bg.convert("RGB")
                draw = ImageDraw.Draw(canvas)
            else:
                from core.bg_generator import generate_ai_background

                try:
                    ai_bgs = generate_ai_background(
                        product_image=product_image,
                        product_name=product_info.get("name", "商品"),
                        style=bg.get("style", "minimal"),
                        width=canvas_w,
                        height=canvas_h,
                        scene_prompt=product_info.get("scene_prompt", ""),
                        custom_prompt=product_info.get("custom_prompt", ""),
                        n=1,
                    )
                    canvas = ai_bgs[0]
                    draw = ImageDraw.Draw(canvas)
                except Exception:
                    fallback_colors = bg.get("fallback_colors", ["#FFFFFF", "#F0F0F0"])
                    _draw_gradient(draw, canvas_w, canvas_h, fallback_colors)
        elif bg_type == "gradient" and len(bg_colors) >= 2:
            _draw_gradient(draw, canvas_w, canvas_h, bg_colors)
        elif bg_type == "solid":
            canvas.paste(
                Image.new("RGB", (canvas_w, canvas_h), _parse_color(bg_colors[0]))
            )
            draw = ImageDraw.Draw(canvas)

    # 2. Convert canvas to RGBA for alpha compositing
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # 3. Decoration layer: overlay bands + bokeh (skip for composed images — AI bg is complete)
    if not has_composed:
        if bg.get("overlay_color"):
            _draw_overlay_bands(canvas, bg)
        _draw_bokeh(canvas, bg)

    # 4. Render elements (skip product_image if composed override — product already in scene)
    for elem in template.get("elements", []):
        elem_type = elem["type"]

        # Adaptive text color for composed images — analyze background brightness
        if has_composed and elem_type in ("title", "price", "selling_points"):
            y_pos = elem.get("y", 0)
            x_pos = elem.get("x", 0)
            font_sz = elem.get("font_size", 28)
            is_center = (x_pos == "center")
            sx = 0 if is_center else x_pos
            sw = canvas_w if is_center else canvas_w // 2
            brightness = _sample_brightness(canvas, sx, y_pos, sw, font_sz + 20)

            elem = dict(elem)  # copy to avoid mutating template
            if brightness < 128:
                # Dark background → light text
                if elem_type == "price":
                    elem["color"] = "#FFD54F"
                elif elem_type == "selling_points":
                    elem["color"] = "#FFFFFF99"
                else:
                    elem["color"] = "#FFFFFFDD"
                elem["stroke_color"] = "#00000055"
                elem.setdefault("stroke_width", 1)
            else:
                # Light background → dark text
                if elem_type == "price":
                    elem["color"] = "#C0392B"
                elif elem_type == "selling_points":
                    elem["color"] = "#55555599"
                else:
                    elem["color"] = "#333333DD"
                elem["stroke_color"] = "#FFFFFF44"
                elem.setdefault("stroke_width", 1)

        if elem_type == "product_image":
            if has_composed:
                continue
            _place_product_image(canvas, product_image, elem, canvas_w, canvas_h)
        elif elem_type == "title":
            title_text = product_info.get("name", "")
            if elem.get("style") == "banner":
                _draw_title_banner(canvas, title_text, elem, canvas_w)
            else:
                _draw_text(draw, title_text, elem, canvas_w)
        elif elem_type == "price":
            prefix = elem.get("prefix", "¥")
            price_text = f"{prefix}{product_info.get('price', '')}"
            if elem.get("style") == "badge":
                _draw_price_badge(canvas, price_text, elem, canvas_w)
            else:
                _draw_text(draw, price_text, elem, canvas_w)
        elif elem_type == "selling_points":
            points = product_info.get("selling_points", [])
            _draw_selling_points(canvas, draw, points, elem, canvas_w)

    # 5. Overlay logo
    if logo is not None:
        logo_w = min(logo.width, canvas_w // 6)
        ratio = logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        pos = (canvas_w - logo_w - 20, canvas_h - logo_h - 20)
        if logo_resized.mode == "RGBA":
            canvas.alpha_composite(logo_resized, pos)
        else:
            canvas.paste(logo_resized, pos)

    # 6. Convert back to RGB for output
    return canvas.convert("RGB")


def _place_product_image(canvas, product_img, elem, canvas_w, canvas_h):
    """Resize and center-paste the product image onto canvas with glow and shadow."""
    max_w = int(canvas_w * elem.get("max_width_pct", 60) / 100)
    max_h = int(canvas_h * elem.get("max_height_pct", 55) / 100)
    ratio = min(max_w / product_img.width, max_h / product_img.height)
    new_w = int(product_img.width * ratio)
    new_h = int(product_img.height * ratio)
    resized = product_img.resize((new_w, new_h), Image.LANCZOS)
    x = (canvas_w - new_w) // 2
    y = (canvas_h - new_h) // 2

    # Draw radial glow behind product if configured
    glow_color = elem.get("glow_color")
    if glow_color:
        cx = x + new_w // 2
        cy = y + new_h // 2
        _draw_product_glow(canvas, cx, cy, new_w, new_h, glow_color)

    # Draw elliptical shadow beneath the product
    shadow_h = 20
    shadow = Image.new("RGBA", (new_w, new_h + shadow_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse(
        [int(new_w * 0.15), new_h - 10, int(new_w * 0.85), new_h + 15],
        fill=(0, 0, 0, 40),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas.alpha_composite(shadow, (x, y))

    if resized.mode == "RGBA":
        canvas.alpha_composite(resized, (x, y))
    else:
        canvas.paste(resized, (x, y))


def _draw_text(draw, text, elem, canvas_w):
    """Draw a text element with optional stroke and shadow."""
    font_size = elem.get("font_size", 28)
    bold = elem.get("font_weight", "normal") == "bold"
    font = _get_font(font_size, bold)
    color = _parse_color(elem.get("color", "#000000"))
    stroke_width = elem.get("stroke_width", 0)
    stroke_color = _parse_color(elem.get("stroke_color", "#00000066"))
    x = elem.get("x", 0)
    y = elem.get("y", 0)
    if x == "center":
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (canvas_w - text_w) // 2

    # Shadow: auto-contrast based on text brightness
    r, g, b = color[:3]
    text_brightness = 0.299 * r + 0.587 * g + 0.114 * b
    shadow_color = (0, 0, 0, 80) if text_brightness > 128 else (255, 255, 255, 60)
    draw.text((x + 2, y + 2), text, fill=shadow_color, font=font)

    # Main text with optional stroke
    if stroke_width > 0:
        draw.text(
            (x, y), text, fill=color, font=font,
            stroke_width=stroke_width, stroke_fill=stroke_color,
        )
    else:
        draw.text((x, y), text, fill=color, font=font)


def _draw_selling_points(canvas, draw, points, elem, canvas_w):
    """Draw selling point tags with vertical, horizontal, or plain layout."""
    if not points:
        return
    font_size = elem.get("font_size", 18)
    font = _get_font(font_size)
    color = _parse_color(elem.get("color", "#FFFFFF"))
    bg_color = _parse_color(elem.get("bg_color", "#FF0000CC"))
    x_start = elem.get("x", 0)
    y_start = elem.get("y", 0)
    padding = 8
    layout = elem.get("layout", "vertical")

    if layout == "plain":
        # Plain text layout: points joined by · separator, text shadow only, no background
        separator = "  ·  "
        full_text = separator.join(points)
        bbox = draw.textbbox((0, 0), full_text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (canvas_w - text_w) // 2 if x_start == "center" else x_start
        # Shadow: auto-contrast based on text brightness
        r, g, b = color[:3]
        text_brightness = 0.299 * r + 0.587 * g + 0.114 * b
        shadow_color = (0, 0, 0, 60) if text_brightness > 128 else (255, 255, 255, 40)
        draw.text((x + 1, y_start + 1), full_text, fill=shadow_color, font=font)
        draw.text((x, y_start), full_text, fill=color, font=font)
    elif layout == "horizontal":
        # Horizontal capsule layout with auto-wrap
        gap = 10
        cur_x = x_start
        cur_y = y_start
        for point in points:
            bbox = draw.textbbox((0, 0), point, font=font)
            text_w = bbox[2] - bbox[0]
            tag_w = text_w + padding * 2
            tag_h = font_size + padding * 2

            # Wrap to next line if exceeding canvas width
            if cur_x + tag_w > canvas_w - x_start and cur_x != x_start:
                cur_x = x_start
                cur_y += tag_h + gap

            # Draw capsule background
            tag = Image.new("RGBA", (tag_w, tag_h), (0, 0, 0, 0))
            tag_draw = ImageDraw.Draw(tag, "RGBA")
            tag_draw.rounded_rectangle(
                [0, 0, tag_w - 1, tag_h - 1],
                radius=tag_h // 2,
                fill=bg_color,
            )
            canvas.alpha_composite(tag, (cur_x, cur_y))

            # Draw text
            draw_rgba = ImageDraw.Draw(canvas, "RGBA")
            draw_rgba.text((cur_x + padding, cur_y + padding), point, fill=color, font=font)

            cur_x += tag_w + gap
    else:
        # Original vertical layout
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
            if hasattr(draw, "rounded_rectangle"):
                draw.rounded_rectangle(rect_coords, radius=4, fill=bg_color)
            else:
                draw.rectangle(rect_coords, fill=bg_color)
            draw.text((x_start, y), point, fill=color, font=font)
