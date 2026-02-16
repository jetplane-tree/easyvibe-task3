# EasyVibe — 电商主图 & 文案生成器

一键生成多平台电商主图和营销文案的 Streamlit 应用。上传商品图片，自动抠图、AI 生成背景、合成主图，同时生成匹配的营销文案。

## 功能

- **AI 背景生成** — 基于通义万相，支持场景预设（按品类分类）和自定义 prompt
- **智能抠图** — 使用 rembg 自动移除商品背景
- **主图合成** — 多平台尺寸适配（淘宝 800×800、小红书 1080×1440 等），支持多种模板风格
- **营销文案** — 基于 DeepSeek，支持多种文案风格
- **模板管理** — 内置多套预设模板（清新、高端、促销、社交），支持自定义
- **素材库** — 管理上传的商品素材，支持搜索、编辑、删除
- **历史记录** — 查看生成历史，支持下载和重新生成

## 项目结构

```
├── app.py                  # Streamlit 入口
├── pages/
│   ├── 1_generate.py       # 主图 & 文案生成页
│   ├── 2_templates.py      # 模板管理页
│   ├── 3_materials.py      # 素材库页
│   └── 4_history.py        # 历史记录页
├── core/
│   ├── bg_generator.py     # AI 背景生成（通义万相）
│   ├── bg_remover.py       # 背景移除（rembg）
│   ├── copy_generator.py   # 营销文案生成（DeepSeek）
│   ├── image_composer.py   # 主图合成
│   ├── platforms.py        # 平台尺寸配置
│   └── template_engine.py  # 模板引擎
├── templates/presets/      # 预设模板 JSON
├── data/                   # 运行时数据（uploads/outputs/db）
└── tests/                  # 测试
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 API Key：

```bash
cp .env.example .env
```

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

- **DEEPSEEK_API_KEY** — 用于文案生成（DeepSeek API）
- **DASHSCOPE_API_KEY** — 用于 AI 背景生成（阿里云通义万相）

### 3. 启动应用

```bash
streamlit run app.py
```

## 技术栈

- **前端**：Streamlit
- **AI 背景**：阿里云通义万相（DashScope）
- **AI 文案**：DeepSeek
- **抠图**：rembg
- **图像处理**：Pillow
