import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from core.bg_generator import (
    SCENE_PRESETS,
    STYLE_PROMPTS,
    _match_size,
    generate_ai_background,
    get_scene_presets,
)


class TestMatchSize:
    def test_square_maps_to_1024x1024(self):
        assert _match_size(800, 800) == "1024*1024"

    def test_portrait_maps_to_768x1152(self):
        # 1080/1440 = 0.75, closest to 768/1152 = 0.667
        assert _match_size(1080, 1440) == "768*1152"

    def test_landscape_maps_to_1280x720(self):
        assert _match_size(1280, 720) == "1280*720"

    def test_custom_ratio_picks_closest(self):
        # 750x352 is landscape-ish
        result = _match_size(750, 352)
        assert result == "1280*720"


class TestStylePrompts:
    def test_all_styles_have_prompts(self):
        for style in ["promo", "minimal", "premium", "fresh", "social"]:
            assert style in STYLE_PROMPTS

    def test_prompt_includes_product_name_placeholder(self):
        for prompt_tpl in STYLE_PROMPTS.values():
            assert "{product_name}" in prompt_tpl


class TestScenePresets:
    def test_all_categories_have_at_least_3_scenes(self):
        for category, scenes in SCENE_PRESETS.items():
            assert len(scenes) >= 3, f"Category '{category}' has fewer than 3 scenes"

    def test_each_scene_has_label_and_prompt(self):
        for category, scenes in SCENE_PRESETS.items():
            for scene in scenes:
                assert "label" in scene, f"Scene in '{category}' missing 'label'"
                assert "prompt" in scene, f"Scene in '{category}' missing 'prompt'"
                assert len(scene["label"]) > 0
                assert len(scene["prompt"]) > 0

    def test_get_scene_presets_returns_same_dict(self):
        result = get_scene_presets()
        assert result is SCENE_PRESETS

    def test_scene_labels_unique_within_category(self):
        for category, scenes in SCENE_PRESETS.items():
            labels = [s["label"] for s in scenes]
            assert len(labels) == len(set(labels)), f"Duplicate labels in '{category}'"


class TestGenerateAiBackground:
    def _make_mock_response(self, success=True, n=1):
        """Create a mock DashScope response."""
        resp = MagicMock()
        if success:
            resp.status_code = 200
            # Create small test images
            results = []
            img_bytes_list = []
            for i in range(n):
                img = Image.new("RGB", (1024, 1024), (100 + i * 30, 150, 200))
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                results.append({"url": f"https://example.com/bg_{i}.png"})
                img_bytes_list.append(buf.getvalue())
            resp.output = {"results": results}
            return resp, img_bytes_list
        else:
            resp.status_code = 400
            resp.output = {}
            resp.message = "API error"
            return resp, None

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_successful_generation(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        result = generate_ai_background("运动鞋", "promo", 800, 800)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Image.Image)
        assert result[0].size == (800, 800)
        assert result[0].mode == "RGB"

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_image_resized_to_target(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        # Request non-standard size; should resize from 1024x1024
        result = generate_ai_background("鞋子", "minimal", 600, 600)
        assert result[0].size == (600, 600)

    @patch("core.bg_generator.ImageSynthesis.call")
    def test_api_failure_raises_runtime_error(self, mock_call):
        mock_resp, _ = self._make_mock_response(success=False)
        mock_call.return_value = mock_resp

        with pytest.raises(RuntimeError, match="AI背景生成失败"):
            generate_ai_background("商品", "promo", 800, 800)

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_prompt_uses_correct_style(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        generate_ai_background("手表", "premium", 800, 800)

        call_kwargs = mock_call.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt")
        assert "高端" in prompt
        assert "手表" in prompt

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_unknown_style_defaults_to_minimal(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        generate_ai_background("商品", "nonexistent", 800, 800)

        call_kwargs = mock_call.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt")
        assert "极简" in prompt

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_scene_prompt_appended(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        generate_ai_background(
            "运动鞋", "promo", 800, 800,
            scene_prompt="专业运动场跑道背景，动感模糊光线，速度感",
        )

        call_kwargs = mock_call.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt")
        assert "运动场跑道" in prompt
        assert "运动鞋" in prompt

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_custom_prompt_appended(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        generate_ai_background(
            "鞋子", "minimal", 800, 800,
            custom_prompt="蓝色海洋背景，夏日清凉感",
        )

        call_kwargs = mock_call.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt")
        assert "蓝色海洋背景" in prompt

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_scene_and_custom_prompt_combined(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        generate_ai_background(
            "鞋子", "promo", 800, 800,
            scene_prompt="户外山野小径背景",
            custom_prompt="增加雾气效果",
        )

        call_kwargs = mock_call.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt")
        assert "户外山野小径背景" in prompt
        assert "增加雾气效果" in prompt

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_n4_returns_4_images(self, mock_call, mock_get):
        mock_resp, img_bytes_list = self._make_mock_response(success=True, n=4)
        mock_call.return_value = mock_resp

        # Each URL fetch returns the corresponding image bytes
        mock_get.side_effect = [MagicMock(content=b) for b in img_bytes_list]

        result = generate_ai_background("商品", "promo", 800, 800, n=4)

        assert len(result) == 4
        for img in result:
            assert isinstance(img, Image.Image)
            assert img.size == (800, 800)

        # Verify n=4 was passed to the API
        call_kwargs = mock_call.call_args
        assert (call_kwargs.kwargs.get("n") or call_kwargs[1].get("n")) == 4

    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.ImageSynthesis.call")
    def test_backward_compatible_no_new_params(self, mock_call, mock_get):
        """Calling without new params should work the same as before."""
        mock_resp, img_bytes_list = self._make_mock_response(success=True)
        mock_call.return_value = mock_resp
        mock_get.return_value = MagicMock(content=img_bytes_list[0])

        result = generate_ai_background("商品", "promo", 800, 800)

        assert isinstance(result, list)
        assert len(result) == 1

        # No scene/custom prompt should be appended
        call_kwargs = mock_call.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt")
        # The prompt should end with the style template content, no trailing comma
        assert prompt == STYLE_PROMPTS["promo"].format(product_name="商品")
