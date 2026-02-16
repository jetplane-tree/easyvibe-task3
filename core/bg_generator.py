import os
from io import BytesIO

import requests
from dashscope import ImageSynthesis
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Scene presets grouped by product category
SCENE_PRESETS = {
    "运动鞋/运动装备": [
        {"label": "运动场跑道", "prompt": "专业运动场跑道背景，动感模糊光线，速度感"},
        {"label": "户外山野", "prompt": "户外山野小径背景，阳光穿透树林，自然清新"},
        {"label": "健身房", "prompt": "现代健身房背景，金属质感器械虚化，专业运动氛围"},
        {"label": "城市街拍", "prompt": "城市街道背景，霓虹灯光虚化，潮流街头风"},
    ],
    "数码/电子产品": [
        {"label": "科技深空", "prompt": "深蓝色科技背景，光粒子效果，未来感"},
        {"label": "极简桌面", "prompt": "极简工作桌面背景，浅灰大理石纹理，柔和侧光"},
        {"label": "渐变光效", "prompt": "深色渐变背景，蓝紫色科技光效，霓虹光线"},
        {"label": "白色展台", "prompt": "纯白色产品展台背景，柔和环境光，商业摄影"},
    ],
    "美妆/护肤": [
        {"label": "花瓣水滴", "prompt": "粉色花瓣散落背景，晶莹水滴，柔焦梦幻"},
        {"label": "大理石台面", "prompt": "白色大理石台面背景，金色点缀，高级质感"},
        {"label": "自然植物", "prompt": "绿色植物叶片背景，露水光泽，天然有机感"},
        {"label": "丝绸质感", "prompt": "丝绸织物褶皱背景，柔和光影，奢华高级"},
    ],
    "食品/饮品": [
        {"label": "木质餐桌", "prompt": "温暖木质餐桌背景，自然光照射，家庭温馨感"},
        {"label": "深色美食", "prompt": "深色调美食摄影背景，侧光打亮，高级餐厅氛围"},
        {"label": "田园清新", "prompt": "绿色田园背景，阳光洒落，有机天然"},
        {"label": "纯色极简", "prompt": "纯色极简背景，柔和漫射光，干净通透"},
    ],
    "服装/配饰": [
        {"label": "时尚秀场", "prompt": "时尚秀场T台背景，聚光灯效果，高级时装氛围"},
        {"label": "街头潮流", "prompt": "涂鸦墙壁背景，城市街头风，潮流年轻"},
        {"label": "自然户外", "prompt": "户外自然风光背景，柔和日落光线，文艺气息"},
        {"label": "纯白影棚", "prompt": "专业影棚白色背景，柔光箱照明，商业级"},
    ],
    "家居/生活": [
        {"label": "温馨客厅", "prompt": "温馨客厅场景背景，柔和灯光，居家生活感"},
        {"label": "北欧极简", "prompt": "北欧极简家居背景，白色空间，自然采光"},
        {"label": "日式和风", "prompt": "日式和风背景，竹子元素，禅意宁静"},
        {"label": "绿植花艺", "prompt": "室内绿植花艺背景，阳光窗台，生活美学"},
    ],
}

# Style-specific prompt templates (upgraded with professional photography terms)
STYLE_PROMPTS = {
    "promo": "电商促销氛围背景，红色喜庆色调，动感光效粒子装饰，径向渐变光晕，高饱和度，适合{product_name}展示，无文字无水印，专业商业摄影光效，4K高清",
    "minimal": "极简白色背景，柔和漫射光照明，淡灰色渐变，干净通透，适合{product_name}展示，无文字无水印，专业产品摄影，高端简洁",
    "premium": "高端深色背景，深蓝黑色调，金色光效粒子点缀，奢华丝绒质感，柔和聚光灯，适合{product_name}展示，无文字无水印，专业商业摄影，高级感",
    "fresh": "清新自然背景，浅绿色柔和渐变，植物叶片虚化元素，阳光斑驳效果，适合{product_name}展示，无文字无水印，自然光摄影风格",
    "social": "社交媒体风格背景，粉色梦幻渐变，柔焦光斑装饰，少女心配色，适合{product_name}种草内容，无文字无水印，ins风格摄影",
}

NEGATIVE_PROMPT = "文字,水印,logo,人物,产品,商品"

# Sizes supported by wanx-v1
SUPPORTED_SIZES = [
    (1024, 1024),
    (720, 1280),
    (1280, 720),
    (768, 1152),
]


def _match_size(width: int, height: int) -> str:
    """Match the closest supported wanx-v1 size by aspect ratio."""
    target_ratio = width / height
    best = min(SUPPORTED_SIZES, key=lambda s: abs(s[0] / s[1] - target_ratio))
    return f"{best[0]}*{best[1]}"


def get_scene_presets() -> dict:
    """Return scene preset dictionary for UI display."""
    return SCENE_PRESETS


def generate_ai_background(
    product_name: str,
    style: str,
    width: int,
    height: int,
    scene_prompt: str = "",
    custom_prompt: str = "",
    n: int = 1,
) -> list[Image.Image]:
    """Generate AI background image(s) via DashScope.

    Args:
        product_name: product name used to build the prompt
        style: one of promo/minimal/premium/fresh/social
        width: target canvas width
        height: target canvas height
        scene_prompt: optional scene description from presets
        custom_prompt: optional user-supplied extra description
        n: number of images to generate

    Returns:
        List of PIL RGB Images of the requested size

    Raises:
        RuntimeError: if the API call fails
    """
    prompt_template = STYLE_PROMPTS.get(style, STYLE_PROMPTS["minimal"])
    prompt = prompt_template.format(product_name=product_name)

    # Append scene and custom prompts
    if scene_prompt:
        prompt = f"{prompt}，{scene_prompt}"
    if custom_prompt:
        prompt = f"{prompt}，{custom_prompt}"

    size_str = _match_size(width, height)

    response = ImageSynthesis.call(
        model="wanx-v1",
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        n=n,
        size=size_str,
    )

    if response.status_code == 200 and response.output.get("results"):
        images = []
        for result in response.output["results"]:
            image_url = result["url"]
            img_data = requests.get(image_url, timeout=30).content
            bg_image = Image.open(BytesIO(img_data)).convert("RGB")
            if bg_image.size != (width, height):
                bg_image = bg_image.resize((width, height), Image.LANCZOS)
            images.append(bg_image)
        return images

    raise RuntimeError(f"AI背景生成失败: {response.message}")
