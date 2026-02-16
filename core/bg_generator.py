import os
import tempfile
import time
from io import BytesIO

import requests
from dashscope.utils.oss_utils import check_and_upload_local
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

BG_GEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/background-generation/generation/"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

# Scene presets grouped by product category
SCENE_PRESETS = {
    "运动鞋/运动装备": [
        {
            "label": "水泥操场",
            "prompt": "灰色水泥地面，午后斜阳投下栏杆阴影，背景虚化的红色塑胶跑道，胶片色调",
        },
        {
            "label": "山野小径",
            "prompt": "碎石泥土小路，两侧野草和蕨类植物，树林间漏下的斑驳光影，清晨薄雾",
        },
        {
            "label": "球场木地板",
            "prompt": "枫木纹理体育馆地板，窗户射入的侧光在地面形成光带，背景虚化的看台",
        },
        {
            "label": "城市天台",
            "prompt": "水泥天台地面，远处城市天际线虚化，傍晚蓝调时刻，冷色调氛围",
        },
    ],
    "数码/电子产品": [
        {
            "label": "水磨石台面",
            "prompt": "浅灰色水磨石台面，左侧窗光形成明暗过渡，背景是白色墙面和一小段阴影",
        },
        {
            "label": "深色桌面",
            "prompt": "深胡桃木桌面，顶光照射形成圆形光晕，背景纯黑色渐变消失",
        },
        {
            "label": "混凝土台面",
            "prompt": "浅色清水混凝土台面，表面有自然气孔纹理，柔和的漫射光，背景是浅灰色磨砂墙",
        },
        {
            "label": "亚克力展台",
            "prompt": "透明亚克力圆形展台，底部有淡淡的倒影，纯白背景，摄影棚柔光箱布光",
        },
    ],
    "美妆/护肤": [
        {
            "label": "奶油底色",
            "prompt": "奶油白色亚麻布背景，表面有自然褶皱纹理，侧面打入一束暖色窗光",
        },
        {
            "label": "石膏与干花",
            "prompt": "白色石膏纹理台面，旁边散落几支干燥的芦苇穗，莫兰迪色调，杂志感",
        },
        {
            "label": "大理石台面",
            "prompt": "卡拉拉白色大理石台面，灰色纹路清晰可见，背景虚化的黄铜镜面和绿植",
        },
        {
            "label": "水波纹光影",
            "prompt": "浅粉米色背景，阳光透过水面投射的焦散波纹光影在墙上晃动，通透清澈",
        },
    ],
    "食品/饮品": [
        {
            "label": "原木桌面",
            "prompt": "老橡木桌面有自然的年轮纹理和使用痕迹，侧窗自然光照射，背景虚化的厨房",
        },
        {
            "label": "暗调料理",
            "prompt": "深色板岩石板台面，从左上方打入的单灯侧光，背景全黑，明暗对比强烈",
        },
        {
            "label": "野餐草地",
            "prompt": "浅绿色草坪上铺着棉麻格纹餐布，午后温暖阳光，浅景深虚化的树影",
        },
        {
            "label": "白色瓷砖",
            "prompt": "白色方形瓷砖台面，砖缝灰色勾线清晰，正上方平光照射，干净利落",
        },
    ],
    "服装/配饰": [
        {
            "label": "棉麻背景布",
            "prompt": "自然褶皱的米白色棉麻背景布，柔和的侧光在布面形成光影层次，杂志编辑风",
        },
        {
            "label": "旧墙面",
            "prompt": "斑驳的灰白色老墙面，有自然的水渍和裂纹痕迹，窗光从右侧射入，胶片质感",
        },
        {
            "label": "金属百叶窗",
            "prompt": "百叶窗投下的平行条纹光影落在浅灰色墙面上，午后阳光，温暖光线",
        },
        {
            "label": "纯白摄影棚",
            "prompt": "白色无缝背景纸，从两侧柔光箱打出的包围光，地面有轻微倒影",
        },
    ],
    "家居/生活": [
        {
            "label": "窗边晨光",
            "prompt": "白色窗帘透进的晨间散射光，浅色原木窗台，窗外是虚化的绿色植物",
        },
        {
            "label": "水泥与绿植",
            "prompt": "微水泥质感灰色台面，旁边有一小盆尤加利叶，背景是白色拱形壁龛",
        },
        {
            "label": "日式和室",
            "prompt": "天然榻榻米纹理地面，背景是白色障子纸拉门，温暖的低角度侧光",
        },
        {
            "label": "藤编质感",
            "prompt": "藤编圆形托盘台面，背景是浅米色粗糙肌理墙面，自然采光，温暖柔和",
        },
    ],
}

# Style-specific background descriptions (v2: describe environment ONLY, never mention product)
STYLE_PROMPTS = {
    "promo": (
        "正红色渐变背景，白色圆形展台，台面有清晰倒影，"
        "正上方聚光灯照射，几条对角线金色光束，画面干净利落"
    ),
    "minimal": (
        "浅灰色水磨石台面，大面积留白的浅米色墙面背景，"
        "左侧薄纱窗帘透过柔和窗光，淡淡投影，极简克制"
    ),
    "premium": (
        "深色岩板台面，深墨绿色到黑色渐变背景，"
        "左上方窄角度射灯照明，台面微微镜面反射，低沉内敛，高端杂志广告感"
    ),
    "fresh": (
        "原木色小圆桌，散落的尤加利叶，"
        "午后阳光从右侧窗户斜射留下窗框光影，色调温暖偏暖黄，胶片感"
    ),
    "social": (
        "奶油白色褶皱丝绒布，柔焦淡杏色调背景，"
        "上方散射自然光通透明亮，一小束干花和摊开的杂志，氛围感"
    ),
}

# Short style atmosphere hints — used when user provides custom/scene prompt
# to avoid overriding user's intent with overly specific scene descriptions
STYLE_HINTS = {
    "promo": "画面明亮鲜艳，有促销氛围",
    "minimal": "干净极简，大面积留白",
    "premium": "高端暗调，质感内敛",
    "fresh": "清新自然，色调温暖",
    "social": "通透明亮，氛围感",
}

POLL_INTERVAL = 3
MAX_POLL_TIME = 120


def get_scene_presets() -> dict:
    """Return scene preset dictionary for UI display."""
    return SCENE_PRESETS


def _save_rgba_to_temp(image: Image.Image) -> str:
    """Save RGBA image to a temporary PNG file, return the file path."""
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    image.save(path, format="PNG")
    return path


def _upload_to_oss(local_path: str, api_key: str) -> str:
    """Upload a local file to DashScope OSS, return the HTTP URL."""
    file_url_local = f"file://{local_path}"
    is_upload, oss_url, _ = check_and_upload_local(
        model="wanx-background-generation-v2",
        content=file_url_local,
        api_key=api_key,
    )
    if not is_upload or not oss_url:
        raise RuntimeError("AI背景生成失败: 图片上传 OSS 失败")
    return oss_url


def _submit_task(base_image_url: str, ref_prompt: str, n: int, api_key: str) -> str:
    """Submit an async background generation task, return task_id."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
        "X-DashScope-OssResourceResolve": "enable",
    }
    payload = {
        "model": "wanx-background-generation-v2",
        "input": {
            "base_image_url": base_image_url,
            "ref_prompt": ref_prompt,
        },
        "parameters": {
            "n": n,
        },
    }
    resp = requests.post(BG_GEN_URL, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        detail = resp.text
        raise RuntimeError(f"AI背景生成提交失败: {detail}")
    data = resp.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"AI背景生成提交失败: 未返回 task_id, response={data}")
    return task_id


def _poll_result(task_id: str, api_key: str) -> dict:
    """Poll task status until SUCCEEDED/FAILED or timeout."""
    headers = {"Authorization": f"Bearer {api_key}"}
    url = TASK_URL.format(task_id=task_id)
    start = time.time()
    while time.time() - start < MAX_POLL_TIME:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("output", {}).get("task_status")
        if status == "SUCCEEDED":
            return data
        if status == "FAILED":
            err_msg = data.get("output", {}).get("message", "unknown error")
            raise RuntimeError(f"AI背景生成失败: {err_msg}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError("AI背景生成超时")


def generate_ai_background(
    product_image: Image.Image,
    product_name: str,
    style: str,
    width: int,
    height: int,
    scene_prompt: str = "",
    custom_prompt: str = "",
    n: int = 1,
) -> list[Image.Image]:
    """Generate AI background with product composited via DashScope v2.

    Uses raw HTTP to the /background-generation/ endpoint (not ImageSynthesis SDK,
    which hardcodes /image-synthesis/ endpoint).
    File upload to OSS is done via dashscope.utils.oss_utils.

    Args:
        product_image: RGBA product image (transparent background)
        product_name: product name (for logging/context)
        style: one of promo/minimal/premium/fresh/social
        width: target canvas width
        height: target canvas height
        scene_prompt: optional scene description from presets
        custom_prompt: optional user-supplied extra description
        n: number of images to generate

    Returns:
        List of PIL RGB Images with product naturally composited into scene

    Raises:
        RuntimeError: if the API call fails or times out
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未设置")

    # 1. Place product_image centered on a (width, height) transparent canvas at 60%
    scale = min(width / product_image.width, height / product_image.height) * 0.60
    new_w = int(product_image.width * scale)
    new_h = int(product_image.height * scale)
    resized_product = product_image.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = (width - new_w) // 2
    y = (height - new_h) // 2
    canvas.paste(resized_product, (x, y), resized_product if resized_product.mode == "RGBA" else None)

    # 2. Save to temp file and upload to OSS
    temp_path = _save_rgba_to_temp(canvas)
    try:
        base_image_url = _upload_to_oss(temp_path, api_key)

        # 3. Compose prompt: purely descriptive, no instructions to the model.
        #    Product integrity is guaranteed by re-paste in step 5, not by prompt.
        has_user_input = bool(custom_prompt) or bool(scene_prompt)
        parts = []
        if custom_prompt:
            parts.append(custom_prompt)
        if scene_prompt:
            parts.append(scene_prompt)
        if has_user_input:
            hint = STYLE_HINTS.get(style, STYLE_HINTS["minimal"])
            parts.append(hint)
        else:
            style_default = STYLE_PROMPTS.get(style, STYLE_PROMPTS["minimal"])
            parts.append(style_default)
        prompt = "，".join(parts)

        # 4. Submit async task and poll
        task_id = _submit_task(base_image_url, prompt, n, api_key)
        result_data = _poll_result(task_id, api_key)

        # 5. Download result images and re-composite original product
        #    The API may alter product pixels, so we paste the original product
        #    back on top to guarantee pixel-perfect preservation.
        results = result_data.get("output", {}).get("results", [])
        if not results:
            raise RuntimeError("AI背景生成失败: 未返回结果图片")

        images = []
        for result in results:
            image_url = result.get("url")
            if not image_url:
                continue
            img_data = requests.get(image_url, timeout=30).content
            img = Image.open(BytesIO(img_data)).convert("RGB")
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
            # Re-paste original product to preserve integrity
            img_rgba = img.convert("RGBA")
            img_rgba.paste(
                resized_product, (x, y),
                resized_product if resized_product.mode == "RGBA" else None,
            )
            images.append(img_rgba.convert("RGB"))

        if not images:
            raise RuntimeError("AI背景生成失败: 无法下载结果图片")

        return images
    finally:
        # 6. Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)
