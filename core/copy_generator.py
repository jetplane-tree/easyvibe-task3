# core/copy_generator.py
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from core.platforms import get_platform_config

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com",
)

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
{{"candidates": [{{"title": "商品标题", "selling_points": ["卖点描述1", "卖点描述2", "卖点描述3"]}}, {{"title": "商品标题", "selling_points": ["卖点描述1", "卖点描述2", "卖点描述3"]}}]}}"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )

    content = response.choices[0].message.content.strip()
    # Handle possible markdown code block wrapping
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(content)
    return data["candidates"]
