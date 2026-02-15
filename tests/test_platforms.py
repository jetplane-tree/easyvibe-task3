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
