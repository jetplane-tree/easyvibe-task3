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
