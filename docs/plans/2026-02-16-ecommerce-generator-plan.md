# 电商主图 & 文案自动生成工具 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Streamlit web app that lets e-commerce operators upload product images, auto-generate platform-specific main images (with background removal, template composition) and marketing copy (via OpenAI GPT).

**Architecture:** Streamlit multi-page app with core modules for image composition (Pillow + rembg), copy generation (OpenAI), and template engine (JSON configs). SQLite for persistence in later phases. Three phases: core generation → template management → material library + history.

**Tech Stack:** Python 3.11+, Streamlit, Pillow, rembg, openai, pandas, openpyxl, SQLite3

---

## Phase 1: Core Generation

### Task 1: Project scaffolding & dependencies

**Files:**
- Create: `requirements.txt`
- Create: `app.py`
- Create: `core/__init__.py`
- Create: `pages/__init__.py`
- Create: `data/__init__.py`
- Create: `templates/`
- Create: `.env.example`

**Step 1: Create requirements.txt**

```txt
streamlit>=1.30.0
Pillow>=10.0.0
rembg>=2.0.50
openai>=1.0.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
```

**Step 2: Create .env.example**

```
OPENAI_API_KEY=your_api_key_here
```

**Step 3: Create directory structure**

```bash
mkdir -p core pages data/uploads data/outputs templates/presets templates/assets
touch core/__init__.py pages/__init__.py data/__init__.py
```

**Step 4: Create app.py (Streamlit entry point)**

```python
import streamlit as st

st.set_page_config(
    page_title="电商主图 & 文案生成器",
    page_icon="🛍️",
    layout="wide",
)

st.title("电商主图 & 文案生成器")
st.markdown("上传商品图片和信息，一键生成多平台主图和营销文案")
```

**Step 5: Install dependencies & verify Streamlit runs**

```bash
pip install -r requirements.txt
streamlit run app.py
```

Expected: Streamlit opens in browser showing title and description.

**Step 6: Commit**

```bash
git add requirements.txt .env.example app.py core/ pages/ data/ templates/
git commit -m "feat: project scaffolding with dependencies and directory structure"
```

---

### Task 2: Platform config module

**Files:**
- Create: `core/platforms.py`
- Create: `tests/test_platforms.py`

**Step 1: Write the failing test**

```python
# tests/test_platforms.py
from core.platforms import PLATFORMS, get_platform_config


def test_platforms_has_required_keys():
    for name, config in PLATFORMS.items():
        assert "label" in config
        assert "width" in config
        assert "height" in config
        assert "title_max_chars" in config


def test_get_platform_config_returns_correct():
    config = get_platform_config("taobao")
    assert config["width"] == 800
    assert config["height"] == 800


def test_get_platform_config_unknown_raises():
    try:
        get_platform_config("unknown_platform")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_platforms.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.platforms'`

**Step 3: Write implementation**

```python
# core/platforms.py

PLATFORMS = {
    "taobao": {
        "label": "淘宝/天猫",
        "width": 800,
        "height": 800,
        "title_max_chars": 60,
        "style_hint": "通用电商风格",
    },
    "pinduoduo": {
        "label": "拼多多",
        "width": 750,
        "height": 352,
        "title_max_chars": 50,
        "style_hint": "性价比、促销、低价优惠",
    },
    "douyin": {
        "label": "抖音电商",
        "width": 720,
        "height": 960,
        "title_max_chars": 40,
        "style_hint": "短平快、吸引点击、竖版",
    },
    "xiaohongshu": {
        "label": "小红书",
        "width": 1080,
        "height": 1440,
        "title_max_chars": 20,
        "style_hint": "种草风、生活化、文艺",
    },
}


def get_platform_config(platform_key: str) -> dict:
    """Get platform config by key. Raises KeyError if not found."""
    return PLATFORMS[platform_key]
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_platforms.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add core/platforms.py tests/test_platforms.py
git commit -m "feat: add platform config module with 4 platforms"
```

---

### Task 3: Background removal module

**Files:**
- Create: `core/bg_remover.py`
- Create: `tests/test_bg_remover.py`
- Create: `tests/fixtures/` (test images)

**Step 1: Create a test fixture image**

```python
# tests/conftest.py
import pytest
from PIL import Image
import os

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_product_image():
    """Create a simple test image with a colored square on white background."""
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    img = Image.new("RGBA", (400, 400), (255, 255, 255, 255))
    # Draw a red square in center (simulating a product)
    for x in range(100, 300):
        for y in range(100, 300):
            img.putpixel((x, y), (255, 0, 0, 255))
    path = os.path.join(FIXTURES_DIR, "test_product.png")
    img.save(path)
    return path
```

**Step 2: Write the failing test**

```python
# tests/test_bg_remover.py
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
```

**Step 3: Run test to verify it fails**

```bash
python -m pytest tests/test_bg_remover.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 4: Write implementation**

```python
# core/bg_remover.py
from PIL import Image
from rembg import remove
from io import BytesIO
from typing import Union


def remove_background(input_image: Union[str, BytesIO]) -> Image.Image:
    """Remove background from product image.

    Args:
        input_image: file path (str) or BytesIO object

    Returns:
        RGBA PIL Image with background removed
    """
    if isinstance(input_image, str):
        img = Image.open(input_image)
    else:
        img = Image.open(input_image)

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    output = remove(img)
    return output
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_bg_remover.py -v
```

Expected: 2 passed (note: first run may be slow as rembg downloads model)

**Step 6: Commit**

```bash
git add core/bg_remover.py tests/test_bg_remover.py tests/conftest.py
git commit -m "feat: add background removal module using rembg"
```

---

### Task 4: Template engine — loading & rendering

**Files:**
- Create: `core/template_engine.py`
- Create: `tests/test_template_engine.py`
- Create: `templates/presets/promo_taobao.json`
- Create: `templates/presets/minimal_taobao.json`

**Step 1: Create 2 preset template JSON files**

```json
// templates/presets/promo_taobao.json
{
  "name": "促销爆款",
  "platform": "taobao",
  "canvas": { "width": 800, "height": 800 },
  "background": { "type": "gradient", "colors": ["#FF4444", "#FF6B6B"] },
  "elements": [
    { "type": "product_image", "x": "center", "y": "center", "max_width_pct": 60, "max_height_pct": 55 },
    { "type": "title", "x": "center", "y": 40, "font_size": 36, "color": "#FFFFFF", "font_weight": "bold" },
    { "type": "price", "x": 50, "y": 700, "font_size": 52, "color": "#FFD700", "prefix": "¥" },
    { "type": "selling_points", "x": 500, "y": 650, "font_size": 20, "color": "#FFFFFF", "style": "tags", "bg_color": "#FF0000CC" }
  ]
}
```

```json
// templates/presets/minimal_taobao.json
{
  "name": "简约白底",
  "platform": "taobao",
  "canvas": { "width": 800, "height": 800 },
  "background": { "type": "solid", "colors": ["#FFFFFF"] },
  "elements": [
    { "type": "product_image", "x": "center", "y": "center", "max_width_pct": 70, "max_height_pct": 65 },
    { "type": "title", "x": "center", "y": 730, "font_size": 28, "color": "#333333", "font_weight": "normal" },
    { "type": "price", "x": "center", "y": 770, "font_size": 24, "color": "#E74C3C", "prefix": "¥" }
  ]
}
```

**Step 2: Write the failing test**

```python
# tests/test_template_engine.py
import os
import json
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
```

**Step 3: Run test to verify it fails**

```bash
python -m pytest tests/test_template_engine.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 4: Write implementation**

```python
# core/template_engine.py
import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
    # Common CJK font paths (macOS, Linux, Windows)
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
    from_color = tuple(int(colors[0].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    to_color = tuple(int(colors[1].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
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
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
    elif len(c) == 8:
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4, 6))
    return (0, 0, 0)


def render_image(
    template: dict,
    product_image: Image.Image,
    product_info: dict,
    logo: Optional[Image.Image] = None,
) -> Image.Image:
    """Render a product main image based on template config.

    Args:
        template: parsed template dict
        product_image: RGBA product image (background already removed)
        product_info: dict with keys: name, selling_points, price
        logo: optional store logo image

    Returns:
        Composed PIL Image
    """
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
        canvas.paste(Image.new("RGB", (canvas_w, canvas_h), _parse_color(bg_colors[0])))
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

    # Overlay logo if provided
    if logo is not None:
        logo_w = min(logo.width, canvas_w // 6)
        ratio = logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        # Place at bottom-right with padding
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

    # Maintain aspect ratio
    ratio = min(max_w / product_img.width, max_h / product_img.height)
    new_w = int(product_img.width * ratio)
    new_h = int(product_img.height * ratio)
    resized = product_img.resize((new_w, new_h), Image.LANCZOS)

    # Center position
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

    for i, point in enumerate(points):
        y = y_start + i * (font_size + 16)
        bbox = draw.textbbox((0, 0), point, font=font)
        text_w = bbox[2] - bbox[0]
        # Draw tag background
        padding = 8
        draw.rounded_rectangle(
            [x_start - padding, y - padding, x_start + text_w + padding, y + font_size + padding],
            radius=4,
            fill=bg_color,
        )
        draw.text((x_start, y), point, fill=color, font=font)
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_template_engine.py -v
```

Expected: 4 passed

**Step 6: Commit**

```bash
git add core/template_engine.py tests/test_template_engine.py templates/presets/
git commit -m "feat: add template engine with loading, listing, and rendering"
```

---

### Task 5: Copy generator module (OpenAI)

**Files:**
- Create: `core/copy_generator.py`
- Create: `tests/test_copy_generator.py`

**Step 1: Write the failing test**

We mock the OpenAI API to avoid real API calls in tests.

```python
# tests/test_copy_generator.py
from unittest.mock import patch, MagicMock
from core.copy_generator import generate_copy, COPY_STYLES


def test_copy_styles_exist():
    assert "promo" in COPY_STYLES
    assert "seeding" in COPY_STYLES
    assert "professional" in COPY_STYLES


def test_generate_copy_returns_two_candidates():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"candidates": [{"title": "标题1", "selling_points": ["卖点A"]}, {"title": "标题2", "selling_points": ["卖点B"]}]}'))
    ]

    with patch("core.copy_generator.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        results = generate_copy(
            product_name="测试商品",
            selling_points=["好用", "便宜"],
            price=99.9,
            platform="taobao",
            style="promo",
        )

    assert len(results) == 2
    assert "title" in results[0]
    assert "selling_points" in results[0]


def test_generate_copy_with_different_styles():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"candidates": [{"title": "T1", "selling_points": ["S1"]}, {"title": "T2", "selling_points": ["S2"]}]}'))
    ]

    for style in COPY_STYLES:
        with patch("core.copy_generator.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response
            results = generate_copy(
                product_name="商品",
                selling_points=["卖点"],
                price=50,
                platform="taobao",
                style=style,
            )
            assert len(results) == 2
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_copy_generator.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# core/copy_generator.py
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from core.platforms import get_platform_config

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

COPY_STYLES = {
    "promo": {
        "label": "促销紧迫感",
        "prompt_hint": "使用紧迫感、限时优惠、数字对比等促销手法，语气强烈有感染力",
    },
    "seeding": {
        "label": "种草安利风",
        "prompt_hint": "像朋友推荐一样自然，用口语化表达，强调使用体验和感受",
    },
    "professional": {
        "label": "专业参数风",
        "prompt_hint": "突出产品参数、材质、工艺等专业信息，语气客观专业有说服力",
    },
}


def generate_copy(
    product_name: str,
    selling_points: list[str],
    price: float,
    platform: str,
    style: str,
) -> list[dict]:
    """Generate 2 candidate copies for a product.

    Args:
        product_name: name of the product
        selling_points: list of selling point strings
        price: product price
        platform: platform key (taobao, pinduoduo, etc.)
        style: copy style key (promo, seeding, professional)

    Returns:
        List of 2 dicts, each with keys: title, selling_points (list of strings)
    """
    platform_config = get_platform_config(platform)
    style_config = COPY_STYLES[style]

    prompt = f"""你是一位资深电商文案专家。请为以下商品生成2套营销文案。

商品信息：
- 商品名称：{product_name}
- 核心卖点：{', '.join(selling_points)}
- 价格：¥{price}

目标平台：{platform_config['label']}
平台风格提示：{platform_config['style_hint']}
标题字数限制：{platform_config['title_max_chars']}字以内

文案风格要求：{style_config['prompt_hint']}

请严格按以下JSON格式返回，不要添加任何其他内容：
{{
  "candidates": [
    {{
      "title": "商品标题（不超过{platform_config['title_max_chars']}字）",
      "selling_points": ["卖点描述1", "卖点描述2", "卖点描述3"]
    }},
    {{
      "title": "商品标题（不超过{platform_config['title_max_chars']}字）",
      "selling_points": ["卖点描述1", "卖点描述2", "卖点描述3"]
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )

    content = response.choices[0].message.content.strip()
    # Handle possible markdown code block wrapping
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(content)
    return data["candidates"]
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_copy_generator.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add core/copy_generator.py tests/test_copy_generator.py
git commit -m "feat: add copy generator module with OpenAI GPT and 3 styles"
```

---

### Task 6: Image composer — orchestrator module

**Files:**
- Create: `core/image_composer.py`
- Create: `tests/test_image_composer.py`

This module orchestrates: bg removal → template rendering → output for all selected platforms.

**Step 1: Write the failing test**

```python
# tests/test_image_composer.py
from unittest.mock import patch, MagicMock
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
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_image_composer.py -v
```

Expected: FAIL

**Step 3: Write implementation**

```python
# core/image_composer.py
import os
from PIL import Image
from typing import Optional
from core.bg_remover import remove_background
from core.template_engine import list_templates, render_image
from core.platforms import get_platform_config

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "presets")

# Map style keywords to template name prefixes
STYLE_MAP = {
    "promo": "促销",
    "minimal": "简约",
    "premium": "高端",
    "fresh": "清新",
    "social": "社交",
}


def _find_template_for_platform(platform: str, style: str) -> dict:
    """Find the best matching template for a platform and style.

    Falls back to first template matching platform, then any template
    with matching style, then first available template.
    """
    templates = list_templates(PRESETS_DIR)
    platform_config = get_platform_config(platform)
    style_keyword = STYLE_MAP.get(style, style)

    # Try exact match: platform + style
    for tpl in templates:
        if tpl.get("platform") == platform and style_keyword in tpl.get("name", ""):
            return tpl

    # Fallback: any template, adapt canvas size to platform
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
    # Remove background once
    if not skip_bg_removal:
        clean_image = remove_background(product_image)
    else:
        clean_image = product_image

    results = {}
    for platform in platforms:
        template = _find_template_for_platform(platform, template_style)
        composed = render_image(template, clean_image, product_info, logo=logo)
        results[platform] = composed

    return results
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_image_composer.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add core/image_composer.py tests/test_image_composer.py
git commit -m "feat: add image composer orchestrator for multi-platform generation"
```

---

### Task 7: Streamlit generate page — single product input

**Files:**
- Create: `pages/1_generate.py`
- Modify: `app.py`

**Step 1: Update app.py for multi-page navigation**

```python
# app.py
import streamlit as st

st.set_page_config(
    page_title="电商主图 & 文案生成器",
    page_icon="🛍️",
    layout="wide",
)

st.title("电商主图 & 文案生成器")
st.markdown("上传商品图片和信息，一键生成多平台主图和营销文案")
st.markdown("👈 请在左侧菜单选择功能页面")
```

**Step 2: Create generate page**

```python
# pages/1_generate.py
import streamlit as st
import os
import io
import zipfile
from PIL import Image
from core.platforms import PLATFORMS
from core.copy_generator import COPY_STYLES, generate_copy
from core.image_composer import compose_images

st.set_page_config(page_title="生成主图 & 文案", layout="wide")
st.title("生成主图 & 文案")

# --- Input section ---
input_method = st.radio("商品信息来源", ["在线录入", "批量导入"], horizontal=True)

if input_method == "在线录入":
    col_input, col_output = st.columns([1, 1])

    with col_input:
        st.subheader("商品信息")
        uploaded_file = st.file_uploader("上传商品图片", type=["jpg", "jpeg", "png"])
        product_name = st.text_input("商品名称", placeholder="例：超轻透气运动鞋")
        sp1 = st.text_input("卖点 1", placeholder="例：透气网面")
        sp2 = st.text_input("卖点 2（可选）", placeholder="例：轻便舒适")
        sp3 = st.text_input("卖点 3（可选）", placeholder="例：防滑耐磨")
        price = st.number_input("价格 (¥)", min_value=0.01, value=99.9, step=0.1)

        st.subheader("生成配置")
        selected_platforms = st.multiselect(
            "目标平台（可多选）",
            options=list(PLATFORMS.keys()),
            default=["taobao"],
            format_func=lambda k: PLATFORMS[k]["label"],
        )
        template_style = st.selectbox(
            "模板风格",
            options=["promo", "minimal", "premium", "fresh", "social"],
            format_func=lambda k: {"promo": "促销爆款", "minimal": "简约白底", "premium": "高端质感", "fresh": "清新文艺", "social": "社交种草"}[k],
        )
        copy_style = st.selectbox(
            "文案风格",
            options=list(COPY_STYLES.keys()),
            format_func=lambda k: COPY_STYLES[k]["label"],
        )

        # Logo upload
        logo_file = st.file_uploader("店铺 Logo（可选）", type=["png", "jpg", "jpeg"])

        generate_btn = st.button("🚀 一键生成", type="primary", use_container_width=True)

    # --- Output section ---
    with col_output:
        if generate_btn:
            if not uploaded_file or not product_name or not sp1 or not selected_platforms:
                st.error("请填写商品名称、至少一个卖点，上传图片，并选择至少一个平台")
            else:
                selling_points = [sp for sp in [sp1, sp2, sp3] if sp]
                product_info = {
                    "name": product_name,
                    "selling_points": selling_points,
                    "price": price,
                }

                product_img = Image.open(uploaded_file)
                logo = Image.open(logo_file) if logo_file else None

                # Generate images
                with st.spinner("正在生成主图..."):
                    images = compose_images(
                        product_image=product_img,
                        product_info=product_info,
                        platforms=selected_platforms,
                        template_style=template_style,
                        logo=logo,
                    )

                # Generate copy
                with st.spinner("正在生成文案..."):
                    try:
                        copies = generate_copy(
                            product_name=product_name,
                            selling_points=selling_points,
                            price=price,
                            platform=selected_platforms[0],
                            style=copy_style,
                        )
                    except Exception as e:
                        st.error(f"文案生成失败: {e}")
                        copies = []

                # Display results
                st.subheader("生成结果")

                for platform_key, img in images.items():
                    platform_label = PLATFORMS[platform_key]["label"]
                    st.markdown(f"**{platform_label}** ({img.size[0]}x{img.size[1]})")
                    st.image(img, use_container_width=True)

                if copies:
                    st.subheader("候选文案")
                    for i, copy in enumerate(copies):
                        with st.expander(f"文案方案 {i + 1}", expanded=True):
                            st.markdown(f"**标题：** {copy.get('title', '')}")
                            for sp in copy.get("selling_points", []):
                                st.markdown(f"- {sp}")

                # Download all as zip
                st.subheader("下载")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for platform_key, img in images.items():
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format="PNG")
                        zf.writestr(f"{platform_key}_main.png", img_buffer.getvalue())
                    if copies:
                        copy_text = ""
                        for i, copy in enumerate(copies):
                            copy_text += f"=== 文案方案 {i + 1} ===\n"
                            copy_text += f"标题：{copy.get('title', '')}\n"
                            for sp in copy.get("selling_points", []):
                                copy_text += f"- {sp}\n"
                            copy_text += "\n"
                        zf.writestr("copy.txt", copy_text)

                zip_buffer.seek(0)
                st.download_button(
                    "📦 下载全部（图片 + 文案）",
                    data=zip_buffer,
                    file_name=f"{product_name}_outputs.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

elif input_method == "批量导入":
    st.info("📋 批量导入功能：上传 Excel 文件 + 图片压缩包")

    col1, col2 = st.columns(2)
    with col1:
        excel_file = st.file_uploader("上传 Excel/CSV 文件", type=["xlsx", "csv"])
    with col2:
        zip_file = st.file_uploader("上传图片压缩包", type=["zip"])

    if excel_file:
        import pandas as pd
        if excel_file.name.endswith(".csv"):
            df = pd.read_csv(excel_file)
        else:
            df = pd.read_excel(excel_file)
        st.dataframe(df, use_container_width=True)
        st.caption(f"共 {len(df)} 个商品")

    st.subheader("生成配置")
    batch_platforms = st.multiselect(
        "目标平台",
        options=list(PLATFORMS.keys()),
        default=["taobao"],
        format_func=lambda k: PLATFORMS[k]["label"],
        key="batch_platforms",
    )
    batch_style = st.selectbox(
        "模板风格",
        options=["promo", "minimal", "premium", "fresh", "social"],
        format_func=lambda k: {"promo": "促销爆款", "minimal": "简约白底", "premium": "高端质感", "fresh": "清新文艺", "social": "社交种草"}[k],
        key="batch_style",
    )
    batch_copy_style = st.selectbox(
        "文案风格",
        options=list(COPY_STYLES.keys()),
        format_func=lambda k: COPY_STYLES[k]["label"],
        key="batch_copy_style",
    )

    if st.button("🚀 批量生成", type="primary"):
        if not excel_file or not zip_file or not batch_platforms:
            st.error("请上传 Excel 和图片压缩包，并选择平台")
        else:
            import pandas as pd
            import zipfile as zf_mod

            if excel_file.name.endswith(".csv"):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)

            # Extract images from zip
            image_map = {}
            with zf_mod.ZipFile(zip_file) as z:
                for name in z.namelist():
                    if name.lower().endswith((".png", ".jpg", ".jpeg")):
                        image_map[os.path.basename(name)] = z.read(name)

            progress = st.progress(0)
            all_results = io.BytesIO()
            with zf_mod.ZipFile(all_results, "w") as out_zip:
                for idx, row in df.iterrows():
                    progress.progress((idx + 1) / len(df))
                    name = str(row.get("商品名称", row.iloc[0]))
                    sps = [str(row.get(f"卖点{i}", row.iloc[i] if i < len(row) else "")) for i in range(1, 4) if pd.notna(row.get(f"卖点{i}", row.iloc[i] if i < len(row) else None))]
                    price_val = float(row.get("价格", row.iloc[-1] if len(row) > 4 else 0))
                    img_name = str(row.get("图片文件名", row.iloc[-1] if len(row) > 5 else ""))

                    if img_name in image_map:
                        product_img = Image.open(io.BytesIO(image_map[img_name]))
                        product_info = {"name": name, "selling_points": sps, "price": price_val}
                        images = compose_images(product_img, product_info, batch_platforms, batch_style)
                        for pk, img in images.items():
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            out_zip.writestr(f"{name}/{pk}_main.png", buf.getvalue())

            all_results.seek(0)
            st.download_button("📦 下载全部结果", data=all_results, file_name="batch_outputs.zip", mime="application/zip")
```

**Step 3: Run Streamlit and manually verify**

```bash
streamlit run app.py
```

Expected: app runs, left sidebar shows "1_generate" page, form renders correctly.

**Step 4: Commit**

```bash
git add app.py pages/1_generate.py
git commit -m "feat: add generate page with single product and batch import UI"
```

---

### Task 8: More preset templates

**Files:**
- Create: `templates/presets/premium_taobao.json`
- Create: `templates/presets/fresh_taobao.json`
- Create: `templates/presets/social_xiaohongshu.json`

**Step 1: Create 3 additional preset templates**

```json
// templates/presets/premium_taobao.json
{
  "name": "高端质感",
  "platform": "taobao",
  "canvas": { "width": 800, "height": 800 },
  "background": { "type": "gradient", "colors": ["#1A1A2E", "#16213E"] },
  "elements": [
    { "type": "product_image", "x": "center", "y": "center", "max_width_pct": 55, "max_height_pct": 55 },
    { "type": "title", "x": "center", "y": 50, "font_size": 32, "color": "#E0C097", "font_weight": "bold" },
    { "type": "price", "x": "center", "y": 720, "font_size": 36, "color": "#E0C097", "prefix": "¥" },
    { "type": "selling_points", "x": 50, "y": 680, "font_size": 18, "color": "#CCCCCC", "style": "tags", "bg_color": "#33333388" }
  ]
}
```

```json
// templates/presets/fresh_taobao.json
{
  "name": "清新文艺",
  "platform": "taobao",
  "canvas": { "width": 800, "height": 800 },
  "background": { "type": "gradient", "colors": ["#E8F5E9", "#FFF9C4"] },
  "elements": [
    { "type": "product_image", "x": "center", "y": "center", "max_width_pct": 60, "max_height_pct": 55 },
    { "type": "title", "x": "center", "y": 40, "font_size": 30, "color": "#2E7D32", "font_weight": "normal" },
    { "type": "price", "x": "center", "y": 740, "font_size": 28, "color": "#558B2F", "prefix": "¥" },
    { "type": "selling_points", "x": 50, "y": 680, "font_size": 18, "color": "#33691E", "style": "tags", "bg_color": "#C8E6C944" }
  ]
}
```

```json
// templates/presets/social_xiaohongshu.json
{
  "name": "社交种草",
  "platform": "xiaohongshu",
  "canvas": { "width": 1080, "height": 1440 },
  "background": { "type": "gradient", "colors": ["#FFF5F5", "#FFE0E6"] },
  "elements": [
    { "type": "product_image", "x": "center", "y": 400, "max_width_pct": 65, "max_height_pct": 45 },
    { "type": "title", "x": "center", "y": 80, "font_size": 44, "color": "#D63384", "font_weight": "bold" },
    { "type": "price", "x": "center", "y": 1300, "font_size": 40, "color": "#E91E63", "prefix": "¥" },
    { "type": "selling_points", "x": 100, "y": 1100, "font_size": 24, "color": "#AD1457", "style": "tags", "bg_color": "#F8BBD044" }
  ]
}
```

**Step 2: Run existing template tests to verify no regressions**

```bash
python -m pytest tests/test_template_engine.py -v
```

Expected: all tests pass, `list_templates` now returns 5 templates

**Step 3: Commit**

```bash
git add templates/presets/
git commit -m "feat: add premium, fresh, and social preset templates"
```

---

## Phase 2: Template Management + Logo Management

### Task 9: Template management page

**Files:**
- Create: `pages/2_templates.py`

**Step 1: Create template management page**

```python
# pages/2_templates.py
import streamlit as st
import os
import json
import copy
from core.template_engine import list_templates, load_template, render_image
from PIL import Image

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "presets")

st.set_page_config(page_title="模板管理", layout="wide")
st.title("模板管理")

# --- List all templates ---
templates = list_templates(PRESETS_DIR)

tab_list, tab_create = st.tabs(["模板列表", "新建模板"])

with tab_list:
    cols = st.columns(3)
    for i, tpl in enumerate(templates):
        with cols[i % 3]:
            # Generate preview with dummy data
            dummy_img = Image.new("RGBA", (200, 200), (100, 150, 200, 255))
            dummy_info = {"name": "示例商品", "selling_points": ["卖点A", "卖点B"], "price": 99.9}
            preview = render_image(tpl, dummy_img, dummy_info)

            st.image(preview, caption=tpl["name"], use_container_width=True)
            st.caption(f"平台: {tpl.get('platform', '通用')} | 尺寸: {tpl['canvas']['width']}x{tpl['canvas']['height']}")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("编辑", key=f"edit_{i}"):
                    st.session_state["editing_template"] = tpl
                    st.session_state["editing_filename"] = tpl.get("_filename", "")
            with col_b:
                if st.button("复制", key=f"copy_{i}"):
                    new_tpl = copy.deepcopy(tpl)
                    new_tpl["name"] = tpl["name"] + " (副本)"
                    new_filename = tpl.get("_filename", "template.json").replace(".json", "_copy.json")
                    with open(os.path.join(PRESETS_DIR, new_filename), "w", encoding="utf-8") as f:
                        clean = {k: v for k, v in new_tpl.items() if not k.startswith("_")}
                        json.dump(clean, f, ensure_ascii=False, indent=2)
                    st.rerun()
            with col_c:
                if st.button("删除", key=f"del_{i}"):
                    fname = tpl.get("_filename")
                    if fname:
                        os.remove(os.path.join(PRESETS_DIR, fname))
                        st.rerun()

    # Edit form
    if "editing_template" in st.session_state:
        st.divider()
        st.subheader(f"编辑模板: {st.session_state['editing_template']['name']}")
        tpl = st.session_state["editing_template"]

        new_name = st.text_input("模板名称", value=tpl["name"])
        new_platform = st.selectbox("平台", ["taobao", "pinduoduo", "douyin", "xiaohongshu"],
                                     index=["taobao", "pinduoduo", "douyin", "xiaohongshu"].index(tpl.get("platform", "taobao")))
        new_width = st.number_input("画布宽度", value=tpl["canvas"]["width"], step=10)
        new_height = st.number_input("画布高度", value=tpl["canvas"]["height"], step=10)

        bg_type = st.selectbox("背景类型", ["solid", "gradient"],
                                index=0 if tpl.get("background", {}).get("type") == "solid" else 1)
        color1 = st.color_picker("颜色 1", value=tpl.get("background", {}).get("colors", ["#FFFFFF"])[0])
        color2 = st.color_picker("颜色 2", value=tpl.get("background", {}).get("colors", ["#FFFFFF", "#FFFFFF"])[-1])

        if st.button("保存修改"):
            updated = copy.deepcopy(tpl)
            updated["name"] = new_name
            updated["platform"] = new_platform
            updated["canvas"] = {"width": int(new_width), "height": int(new_height)}
            updated["background"] = {"type": bg_type, "colors": [color1, color2] if bg_type == "gradient" else [color1]}

            fname = st.session_state.get("editing_filename", "template.json")
            with open(os.path.join(PRESETS_DIR, fname), "w", encoding="utf-8") as f:
                clean = {k: v for k, v in updated.items() if not k.startswith("_")}
                json.dump(clean, f, ensure_ascii=False, indent=2)
            del st.session_state["editing_template"]
            st.success("模板已保存")
            st.rerun()

with tab_create:
    st.subheader("新建模板")
    new_tpl_name = st.text_input("模板名称", key="new_name")
    new_tpl_platform = st.selectbox("目标平台", ["taobao", "pinduoduo", "douyin", "xiaohongshu"], key="new_platform")
    new_bg_type = st.selectbox("背景类型", ["solid", "gradient"], key="new_bg")
    new_color1 = st.color_picker("颜色 1", value="#FFFFFF", key="nc1")
    new_color2 = st.color_picker("颜色 2", value="#EEEEEE", key="nc2")
    new_font_size = st.slider("标题字号", 16, 60, 32, key="nfs")
    new_font_color = st.color_picker("标题颜色", value="#333333", key="nfc")
    new_price_size = st.slider("价格字号", 16, 60, 36, key="nps")
    new_price_color = st.color_picker("价格颜色", value="#E74C3C", key="npc")

    from core.platforms import get_platform_config
    pc = get_platform_config(new_tpl_platform)

    if st.button("创建模板"):
        if not new_tpl_name:
            st.error("请输入模板名称")
        else:
            tpl_data = {
                "name": new_tpl_name,
                "platform": new_tpl_platform,
                "canvas": {"width": pc["width"], "height": pc["height"]},
                "background": {
                    "type": new_bg_type,
                    "colors": [new_color1, new_color2] if new_bg_type == "gradient" else [new_color1],
                },
                "elements": [
                    {"type": "product_image", "x": "center", "y": "center", "max_width_pct": 60, "max_height_pct": 55},
                    {"type": "title", "x": "center", "y": 40, "font_size": new_font_size, "color": new_font_color, "font_weight": "bold"},
                    {"type": "price", "x": "center", "y": pc["height"] - 80, "font_size": new_price_size, "color": new_price_color, "prefix": "¥"},
                    {"type": "selling_points", "x": 50, "y": pc["height"] - 130, "font_size": 18, "color": "#333333", "style": "tags", "bg_color": "#EEEEEE88"},
                ],
            }
            fname = f"{new_tpl_name}_{new_tpl_platform}.json".replace(" ", "_")
            with open(os.path.join(PRESETS_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(tpl_data, f, ensure_ascii=False, indent=2)
            st.success(f"模板 '{new_tpl_name}' 已创建")
            st.rerun()
```

**Step 2: Run Streamlit and manually verify**

```bash
streamlit run app.py
```

Expected: "模板管理" page shows template previews, edit/copy/delete buttons work, create tab allows new templates.

**Step 3: Commit**

```bash
git add pages/2_templates.py
git commit -m "feat: add template management page with CRUD operations"
```

---

## Phase 3: Material Library + History

### Task 10: Database setup module

**Files:**
- Create: `data/db.py`
- Create: `tests/test_db.py`

**Step 1: Write the failing test**

```python
# tests/test_db.py
import os
import tempfile
from data.db import Database


def test_database_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        # Tables should exist after init
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "materials" in tables
        assert "generation_history" in tables
        db.close()


def test_save_and_get_material():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        mid = db.save_material("测试商品", ["卖点1", "卖点2"], 99.9, "/fake/path.png")
        assert mid > 0
        material = db.get_material(mid)
        assert material["name"] == "测试商品"
        assert material["price"] == 99.9
        db.close()


def test_list_materials():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        db.save_material("商品A", ["卖点"], 10, "/a.png")
        db.save_material("商品B", ["卖点"], 20, "/b.png")
        materials = db.list_materials()
        assert len(materials) == 2
        db.close()


def test_search_materials():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        db.save_material("运动鞋A", ["透气"], 100, "/a.png")
        db.save_material("连衣裙B", ["显瘦"], 200, "/b.png")
        results = db.search_materials("运动")
        assert len(results) == 1
        assert results[0]["name"] == "运动鞋A"
        db.close()


def test_delete_material():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        mid = db.save_material("商品", ["卖点"], 10, "/a.png")
        db.delete_material(mid)
        assert db.get_material(mid) is None
        db.close()


def test_save_and_list_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        mid = db.save_material("商品", ["卖点"], 10, "/a.png")
        hid = db.save_history(mid, "促销爆款", "taobao", "promo", "/out.png", [{"title": "T", "selling_points": ["S"]}])
        assert hid > 0
        history = db.list_history()
        assert len(history) == 1
        assert history[0]["template_name"] == "促销爆款"
        db.close()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_db.py -v
```

Expected: FAIL

**Step 3: Write implementation**

```python
# data/db.py
import sqlite3
import json
import os


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "app.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                selling_points TEXT,
                price REAL,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER REFERENCES materials(id),
                template_name TEXT,
                platform TEXT,
                copy_style TEXT,
                generated_image_path TEXT,
                generated_copy TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def save_material(self, name: str, selling_points: list, price: float, image_path: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO materials (name, selling_points, price, image_path) VALUES (?, ?, ?, ?)",
            (name, json.dumps(selling_points, ensure_ascii=False), price, image_path),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_material(self, material_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["selling_points"] = json.loads(d["selling_points"]) if d["selling_points"] else []
        return d

    def list_materials(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM materials ORDER BY created_at DESC").fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["selling_points"] = json.loads(d["selling_points"]) if d["selling_points"] else []
            results.append(d)
        return results

    def search_materials(self, keyword: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM materials WHERE name LIKE ? ORDER BY created_at DESC",
            (f"%{keyword}%",),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["selling_points"] = json.loads(d["selling_points"]) if d["selling_points"] else []
            results.append(d)
        return results

    def update_material(self, material_id: int, **kwargs):
        allowed = {"name", "selling_points", "price", "image_path"}
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed:
                if k == "selling_points":
                    v = json.dumps(v, ensure_ascii=False)
                updates.append(f"{k} = ?")
                values.append(v)
        if updates:
            values.append(material_id)
            self.conn.execute(f"UPDATE materials SET {', '.join(updates)} WHERE id = ?", values)
            self.conn.commit()

    def delete_material(self, material_id: int):
        self.conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        self.conn.commit()

    def save_history(self, material_id: int, template_name: str, platform: str,
                     copy_style: str, image_path: str, copies: list) -> int:
        cursor = self.conn.execute(
            "INSERT INTO generation_history (material_id, template_name, platform, copy_style, generated_image_path, generated_copy) VALUES (?, ?, ?, ?, ?, ?)",
            (material_id, template_name, platform, copy_style, image_path, json.dumps(copies, ensure_ascii=False)),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_history(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT h.*, m.name as product_name FROM generation_history h LEFT JOIN materials m ON h.material_id = m.id ORDER BY h.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["generated_copy"] = json.loads(d["generated_copy"]) if d["generated_copy"] else []
            results.append(d)
        return results

    def close(self):
        self.conn.close()
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_db.py -v
```

Expected: 6 passed

**Step 5: Commit**

```bash
git add data/db.py tests/test_db.py
git commit -m "feat: add SQLite database module for materials and history"
```

---

### Task 11: Materials library page

**Files:**
- Create: `pages/3_materials.py`

**Step 1: Create materials page**

```python
# pages/3_materials.py
import streamlit as st
import os
from PIL import Image
from data.db import Database

st.set_page_config(page_title="素材库", layout="wide")
st.title("素材库")

db = Database()

# Search bar
search_query = st.text_input("🔍 搜索商品", placeholder="输入商品名称关键词...")

if search_query:
    materials = db.search_materials(search_query)
else:
    materials = db.list_materials()

if not materials:
    st.info("素材库为空，在生成页面勾选「保存到素材库」即可添加商品素材")
else:
    st.caption(f"共 {len(materials)} 个商品素材")

    cols = st.columns(3)
    for i, mat in enumerate(materials):
        with cols[i % 3]:
            with st.container(border=True):
                # Show image if exists
                if mat.get("image_path") and os.path.exists(mat["image_path"]):
                    img = Image.open(mat["image_path"])
                    st.image(img, use_container_width=True)
                else:
                    st.markdown("🖼️ *图片未找到*")

                st.markdown(f"**{mat['name']}**")
                st.caption(f"¥{mat['price']}")
                for sp in mat.get("selling_points", []):
                    st.markdown(f"- {sp}")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("去生成", key=f"gen_{mat['id']}"):
                        st.session_state["prefill_material"] = mat
                        st.switch_page("pages/1_generate.py")
                with col_b:
                    if st.button("编辑", key=f"edit_{mat['id']}"):
                        st.session_state[f"editing_mat_{mat['id']}"] = True
                with col_c:
                    if st.button("删除", key=f"del_{mat['id']}"):
                        db.delete_material(mat["id"])
                        st.rerun()

                # Inline edit form
                if st.session_state.get(f"editing_mat_{mat['id']}"):
                    new_name = st.text_input("名称", value=mat["name"], key=f"en_{mat['id']}")
                    new_price = st.number_input("价格", value=mat["price"], key=f"ep_{mat['id']}")
                    new_sps = st.text_area("卖点（每行一个）",
                                           value="\n".join(mat.get("selling_points", [])),
                                           key=f"esp_{mat['id']}")
                    if st.button("保存", key=f"save_{mat['id']}"):
                        db.update_material(
                            mat["id"],
                            name=new_name,
                            price=new_price,
                            selling_points=[s.strip() for s in new_sps.split("\n") if s.strip()],
                        )
                        del st.session_state[f"editing_mat_{mat['id']}"]
                        st.rerun()
```

**Step 2: Run Streamlit and manually verify**

```bash
streamlit run app.py
```

Expected: Materials page shows empty state message or list of saved materials.

**Step 3: Commit**

```bash
git add pages/3_materials.py
git commit -m "feat: add materials library page with search, edit, delete"
```

---

### Task 12: History page

**Files:**
- Create: `pages/4_history.py`

**Step 1: Create history page**

```python
# pages/4_history.py
import streamlit as st
import os
from PIL import Image
from data.db import Database

st.set_page_config(page_title="历史记录", layout="wide")
st.title("历史记录")

db = Database()
history = db.list_history(limit=100)

if not history:
    st.info("暂无生成记录")
else:
    st.caption(f"共 {len(history)} 条记录")

    for record in history:
        with st.container(border=True):
            col_img, col_info, col_action = st.columns([1, 2, 1])

            with col_img:
                img_path = record.get("generated_image_path", "")
                if img_path and os.path.exists(img_path):
                    st.image(Image.open(img_path), use_container_width=True)
                else:
                    st.markdown("🖼️ *图片未找到*")

            with col_info:
                st.markdown(f"**{record.get('product_name', '未知商品')}**")
                st.caption(f"模板: {record.get('template_name', '-')} | 平台: {record.get('platform', '-')} | 风格: {record.get('copy_style', '-')}")
                st.caption(f"生成时间: {record.get('created_at', '-')}")

                copies = record.get("generated_copy", [])
                if copies:
                    for j, c in enumerate(copies):
                        st.markdown(f"**文案 {j+1}:** {c.get('title', '')}")

            with col_action:
                # Re-download
                img_path = record.get("generated_image_path", "")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        st.download_button(
                            "下载图片",
                            data=f.read(),
                            file_name=os.path.basename(img_path),
                            key=f"dl_{record['id']}",
                        )

                # Re-generate: go to generate page with prefilled material
                mat_id = record.get("material_id")
                if mat_id:
                    mat = db.get_material(mat_id)
                    if mat and st.button("重新生成", key=f"regen_{record['id']}"):
                        st.session_state["prefill_material"] = mat
                        st.switch_page("pages/1_generate.py")
```

**Step 2: Run Streamlit and manually verify**

```bash
streamlit run app.py
```

Expected: History page shows empty state or records.

**Step 3: Commit**

```bash
git add pages/4_history.py
git commit -m "feat: add history page with download and re-generate"
```

---

### Task 13: Wire up save-to-materials & save-history in generate page

**Files:**
- Modify: `pages/1_generate.py`

**Step 1: Add database integration to generate page**

Add these changes to `pages/1_generate.py`:

1. Import Database: `from data.db import Database`
2. Add "save to materials" checkbox and logic after generation
3. Save generation history after each successful generation
4. Add "from materials library" option as a third input method
5. Handle `st.session_state["prefill_material"]` to auto-fill form

Key additions:
- After successful image generation, if "save to materials" is checked, save the product image to `data/uploads/` and call `db.save_material()`
- After generation, call `db.save_history()` with the output image path saved to `data/outputs/`
- Add radio option "从素材库选择" that shows a selectbox of saved materials

**Step 2: Run Streamlit and test full flow manually**

```bash
streamlit run app.py
```

Test flow:
1. Upload image, fill info, check "save to materials", generate → verify material appears in materials page
2. Generate again → verify record appears in history page
3. Go to materials → click "go to generate" → verify form pre-filled

**Step 3: Commit**

```bash
git add pages/1_generate.py
git commit -m "feat: wire up materials saving and history recording in generate page"
```

---

### Task 14: Final integration test & cleanup

**Step 1: Run all unit tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass

**Step 2: Run Streamlit and do a full end-to-end test**

```bash
streamlit run app.py
```

Manual test checklist:
- [ ] Upload product image → fills form → select multi-platform → generate → images show for each platform
- [ ] Copy generates 2 candidates with correct style
- [ ] Download zip works with images + copy text
- [ ] Save to materials checkbox works
- [ ] Batch import with Excel + zip works
- [ ] Template management: view, create, edit, copy, delete
- [ ] Materials library: search, edit, delete, "go to generate"
- [ ] History: view records, download, re-generate

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete e-commerce image & copy generator v1.0"
```
