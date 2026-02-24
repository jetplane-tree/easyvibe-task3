# 参考图生成商品背景

## 需求

支持上传 1 张参考图（风格/场景），让 AI 根据参考图生成商品背景。

## 背景来源三选一

勾选 AI 背景后，用户选择背景来源：

- **场景预设**：分类 → 场景下拉（现有）
- **参考图**：上传 1 张图 + 可选文字微调（新增）
- **纯文字描述**：自定义 prompt（现有）

## 技术方案

`wanx-background-generation-v2` API 原生支持 `ref_image_url` 参数，改动量小。

### 改动文件

| 文件 | 改动量 | 说明 |
|------|--------|------|
| `core/bg_generator.py` | 小 | `generate_ai_background()` 新增 `ref_image` 参数，上传 OSS 后传 `ref_image_url` 给 API |
| `core/image_composer.py` | 小 | 透传 `ref_image` |
| `pages/1_generate.py` | 中 | 三个输入模式加背景来源选择器 + 参考图上传 |
| `tests/test_bg_generator.py` | 小 | 新增参考图测试用例 |

### Prompt 策略

- 参考图 + 无文字：`ref_image_url` + `STYLE_HINTS[style]`
- 参考图 + 有文字微调：`ref_image_url` + 用户文字 + `STYLE_HINTS[style]`
- 场景预设（不变）：无 `ref_image_url` + 场景描述
- 纯文字（不变）：无 `ref_image_url` + 用户文字

### 数据流

```
用户上传参考图 → 上传 OSS → API ref_image_url
                                    +
商品透明底图 → 上传 OSS → API base_image_url
                                    +
文字微调(可选) ─────────→ API ref_prompt
                                    ↓
                            API 生成 4 张候选
                                    ↓
                            羽化混合贴回原始商品
                                    ↓
                            用户选择 → 最终成图
```
