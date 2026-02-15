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
