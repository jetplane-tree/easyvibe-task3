import os
import time
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from core.bg_generator import (
    SCENE_PRESETS,
    STYLE_PROMPTS,
    STYLE_HINTS,
    generate_ai_background,
    get_scene_presets,
    _save_rgba_to_temp,
)

MOCK_OSS_URL = "https://oss.example.com/uploaded_image.png"


class TestStylePrompts:
    def test_all_styles_have_prompts(self):
        for style in ["promo", "minimal", "premium", "fresh", "social"]:
            assert style in STYLE_PROMPTS

    def test_prompts_are_scene_descriptions(self):
        """v2 prompts should not contain {product_name} placeholder."""
        for prompt in STYLE_PROMPTS.values():
            assert "{product_name}" not in prompt

    def test_all_styles_have_hints(self):
        for style in ["promo", "minimal", "premium", "fresh", "social"]:
            assert style in STYLE_HINTS

    def test_hints_are_short(self):
        """Hints should be brief, not full scene descriptions."""
        for hint in STYLE_HINTS.values():
            assert len(hint) < 30, f"Hint too long: {hint}"


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


def _make_product_image(w=400, h=400):
    """Create a test RGBA product image."""
    return Image.new("RGBA", (w, h), (255, 0, 0, 200))


def _make_result_image(w=800, h=800):
    """Create a test result image (what API would return)."""
    img = Image.new("RGB", (w, h), (100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _mock_submit_response(task_id="test-task-123"):
    """Mock response for task submission POST."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"output": {"task_id": task_id}}
    return resp


def _mock_poll_response(status="SUCCEEDED", n=1):
    """Mock response for task polling GET."""
    resp = MagicMock()
    resp.status_code = 200
    results = [{"url": f"https://example.com/result_{i}.png"} for i in range(n)]
    resp.json.return_value = {
        "output": {
            "task_status": status,
            "results": results if status == "SUCCEEDED" else [],
            "message": "task failed" if status == "FAILED" else "",
        }
    }
    resp.raise_for_status = MagicMock()
    return resp


def _mock_image_download(img_bytes):
    """Mock response for image download GET."""
    resp = MagicMock()
    resp.content = img_bytes
    return resp


@patch("core.bg_generator._upload_to_oss", return_value=MOCK_OSS_URL)
class TestGenerateAiBackground:
    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_successful_generation(self, mock_post, mock_get, mock_upload):
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image(800, 800)
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        result = generate_ai_background(product_img, "运动鞋", "promo", 800, 800)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Image.Image)
        assert result[0].size == (800, 800)
        assert result[0].mode == "RGB"

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_product_image_centered(self, mock_post, mock_get, mock_upload):
        """Verify that the submit call uses the uploaded OSS URL."""
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image(800, 800)
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image(200, 300)
        result = generate_ai_background(product_img, "鞋子", "minimal", 800, 800)

        # Verify POST payload uses the OSS URL
        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        assert payload["input"]["base_image_url"] == MOCK_OSS_URL
        assert len(result) == 1

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.post")
    def test_submit_failure_raises(self, mock_post, mock_upload):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "Bad Request"
        mock_post.return_value = resp

        product_img = _make_product_image()
        with pytest.raises(RuntimeError, match="AI背景生成提交失败"):
            generate_ai_background(product_img, "商品", "promo", 800, 800)

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_api_failure_raises(self, mock_post, mock_get, mock_upload):
        mock_post.return_value = _mock_submit_response()
        mock_get.return_value = _mock_poll_response("FAILED")

        product_img = _make_product_image()
        with pytest.raises(RuntimeError, match="AI背景生成失败"):
            generate_ai_background(product_img, "商品", "promo", 800, 800)

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.time.time")
    @patch("core.bg_generator.time.sleep")
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_timeout_raises(self, mock_post, mock_get, mock_sleep, mock_time, mock_upload):
        mock_post.return_value = _mock_submit_response()
        mock_get.return_value = _mock_poll_response("PENDING")
        mock_time.side_effect = [0, 0, 50, 100, 130]
        mock_sleep.return_value = None

        product_img = _make_product_image()
        with pytest.raises(RuntimeError, match="AI背景生成超时"):
            generate_ai_background(product_img, "商品", "promo", 800, 800)

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_prompt_composition(self, mock_post, mock_get, mock_upload):
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        generate_ai_background(
            product_img, "手表", "premium", 800, 800,
            scene_prompt="户外山野小径背景",
            custom_prompt="增加雾气效果",
        )

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        prompt = payload["input"]["ref_prompt"]
        # With user input, should use short hint (not full scene description)
        assert "高端" in prompt
        assert "户外山野小径背景" in prompt
        assert "增加雾气效果" in prompt
        # Should NOT contain the full default scene (岩板台面 etc.)
        assert "岩板台面" not in prompt

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_no_user_input_uses_full_default(self, mock_post, mock_get, mock_upload):
        """Without custom/scene prompt, full style description should be used."""
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        generate_ai_background(product_img, "手表", "premium", 800, 800)

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        prompt = payload["input"]["ref_prompt"]
        # Without user input, full default scene should be used
        assert "岩板台面" in prompt

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_n4_returns_4_images(self, mock_post, mock_get, mock_upload):
        mock_post.return_value = _mock_submit_response()
        img_bytes = [_make_result_image() for _ in range(4)]
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=4),
        ] + [_mock_image_download(b) for b in img_bytes]

        product_img = _make_product_image()
        result = generate_ai_background(product_img, "商品", "promo", 800, 800, n=4)

        assert len(result) == 4
        for img in result:
            assert isinstance(img, Image.Image)
            assert img.size == (800, 800)

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        assert payload["parameters"]["n"] == 4

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_temp_file_cleanup(self, mock_post, mock_get, mock_upload):
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()

        created_paths = []
        original_save = _save_rgba_to_temp

        def tracking_save(image):
            path = original_save(image)
            created_paths.append(path)
            return path

        with patch("core.bg_generator._save_rgba_to_temp", side_effect=tracking_save):
            result = generate_ai_background(product_img, "商品", "promo", 800, 800)

        assert len(created_paths) == 1
        assert not os.path.exists(created_paths[0])

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_unknown_style_defaults_to_minimal(self, mock_post, mock_get, mock_upload):
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        generate_ai_background(product_img, "商品", "nonexistent", 800, 800)

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        prompt = payload["input"]["ref_prompt"]
        assert "极简" in prompt

    def test_missing_api_key_raises(self, mock_upload):
        product_img = _make_product_image()
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
                generate_ai_background(product_img, "商品", "promo", 800, 800)

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    def test_upload_failure_raises(self, mock_upload):
        mock_upload.side_effect = RuntimeError("AI背景生成失败: 图片上传 OSS 失败")
        product_img = _make_product_image()
        with pytest.raises(RuntimeError, match="图片上传 OSS 失败"):
            generate_ai_background(product_img, "商品", "promo", 800, 800)

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_ref_image_passed_to_api(self, mock_post, mock_get, mock_upload):
        """When ref_image is provided, ref_image_url should be in API payload."""
        mock_upload.return_value = MOCK_OSS_URL
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        ref_img = Image.new("RGB", (200, 200), (0, 100, 200))
        generate_ai_background(
            product_img, "商品", "promo", 800, 800,
            ref_image=ref_img,
        )

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        assert "ref_image_url" in payload["input"]
        assert payload["input"]["ref_image_url"] == MOCK_OSS_URL

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_no_ref_image_omits_field(self, mock_post, mock_get, mock_upload):
        """Without ref_image, ref_image_url should NOT be in API payload."""
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        generate_ai_background(product_img, "商品", "promo", 800, 800)

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        assert "ref_image_url" not in payload["input"]

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"})
    @patch("core.bg_generator.requests.get")
    @patch("core.bg_generator.requests.post")
    def test_ref_image_uses_hint_not_full_prompt(self, mock_post, mock_get, mock_upload):
        """With ref_image and no text, prompt should use STYLE_HINTS not STYLE_PROMPTS."""
        mock_post.return_value = _mock_submit_response()
        img_bytes = _make_result_image()
        mock_get.side_effect = [
            _mock_poll_response("SUCCEEDED", n=1),
            _mock_image_download(img_bytes),
        ]

        product_img = _make_product_image()
        ref_img = Image.new("RGB", (200, 200), (0, 100, 200))
        generate_ai_background(
            product_img, "商品", "premium", 800, 800,
            ref_image=ref_img,
        )

        post_call = mock_post.call_args
        payload = post_call.kwargs.get("json") or post_call[1].get("json")
        prompt = payload["input"]["ref_prompt"]
        # Should use short hint, not full scene description
        assert "高端" in prompt
        assert "岩板台面" not in prompt
