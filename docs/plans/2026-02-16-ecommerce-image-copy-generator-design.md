# 电商主图 & 文案自动生成工具 — 设计文档

## 概述

帮助电商运营自动生成商品主图和文案的 Web 工具。运营上传商品图片和信息后，工具自动合成多平台主图并生成营销文案，替代手动做图写文案的重复劳动。

## 技术栈

- **前端/界面**: Streamlit
- **图片合成**: Pillow
- **自动抠图**: rembg
- **文案生成**: OpenAI GPT API
- **数据存储**: SQLite + 本地文件系统

## 目标平台

多平台通用，支持自动适配：

| 平台 | 主图尺寸 | 文案特点 |
|------|---------|---------|
| 淘宝/天猫 | 800x800 | 标题限 60 字符 |
| 拼多多 | 750x352 | 偏性价比/促销风格 |
| 抖音电商 | 竖版为主 | 吸引点击，短平快 |
| 小红书 | 1080x1440 竖版 | 种草风，生活化 |

## 分阶段实施

### Phase 1：核心生成功能

**商品信息输入（三种方式）：**

1. **在线录入** — 表单填写商品名称、卖点(1-3个)、价格 + 上传商品图片
2. **批量导入** — 上传 Excel/CSV（商品名称|卖点1|卖点2|卖点3|价格|图片文件名）+ 图片 zip 压缩包
3. **从素材库选择** — 选取已保存的商品素材（Phase 3 实现后可用）

**生成配置：**

- 选择目标平台（可多选，一键生成多平台）
- 选择模板风格（促销爆款/简约白底/高端质感/清新文艺/社交种草）
- 选择文案风格（促销紧迫感/种草安利风/专业参数风）
- 勾选是否保存到素材库

**生成结果：**

- 每个平台一张主图（自动适配尺寸）
- 2 条候选文案（标题 + 卖点描述）
- 打包下载所有结果

**主图合成逻辑：**

1. rembg 自动去除商品图背景
2. 根据模板配置添加：背景色/渐变、商品图居中、商品名称、卖点标签、价格标签、装饰元素
3. 根据平台自动适配画布尺寸
4. 支持叠加店铺 Logo/水印

**文案生成逻辑：**

- 输入：商品信息 + 目标平台 + 文案风格
- 调用 OpenAI GPT 生成
- 每次输出 2 条候选文案
- 自动适配平台字数限制和风格特点

### Phase 2：模板管理 + Logo 管理

**模板数据结构（JSON）：**

```json
{
  "name": "促销爆款",
  "platform": "taobao",
  "canvas": { "width": 800, "height": 800 },
  "background": { "type": "gradient", "colors": ["#FF4444", "#FF6B6B"] },
  "elements": [
    { "type": "product_image", "position": "center", "size": "60%" },
    { "type": "title", "position": "top", "font_size": 36, "color": "#FFFFFF" },
    { "type": "price", "position": "bottom-left", "font_size": 48, "color": "#FFD700" },
    { "type": "selling_points", "position": "right", "style": "tags" },
    { "type": "decoration", "asset": "burst_star.png", "position": "top-right" }
  ]
}
```

**模板管理页面：**

- 缩略图列表展示所有模板
- 新建/编辑/复制/删除模板
- 内置 5-10 套预设模板

**店铺 Logo 管理：**

- 上传店铺 Logo
- 设置 Logo 默认位置和大小
- 生成时自动叠加

### Phase 3：素材库 + 历史记录

**数据库设计（SQLite）：**

```sql
-- 素材库
CREATE TABLE materials (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    selling_points TEXT,  -- JSON array
    price REAL,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 生成历史
CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY,
    material_id INTEGER REFERENCES materials(id),
    template_name TEXT,
    platform TEXT,
    copy_style TEXT,
    generated_image_path TEXT,
    generated_copy TEXT,  -- JSON with 2 candidates
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**素材库页面：**

- 列表展示已保存商品素材（缩略图 + 基本信息）
- 搜索/筛选
- 编辑/删除
- 点击素材 → 跳转生成页面，自动填充信息

**历史记录页面：**

- 按时间倒序展示生成记录
- 显示：主图缩略图 + 文案预览 + 使用的模板和平台
- 支持重新下载、基于历史记录重新生成

## 页面结构

```
├── 生成页面（首页）     ← Phase 1
├── 模板管理            ← Phase 2
├── 素材库              ← Phase 3
└── 历史记录            ← Phase 3
```

## 项目目录结构

```
easyvibe-task3/
├── app.py                  # Streamlit 主入口
├── pages/
│   ├── generate.py         # 生成页面
│   ├── templates.py        # 模板管理页面
│   ├── materials.py        # 素材库页面
│   └── history.py          # 历史记录页面
├── core/
│   ├── image_composer.py   # 图片合成引擎
│   ├── copy_generator.py   # 文案生成（OpenAI）
│   ├── template_engine.py  # 模板解析引擎
│   └── bg_remover.py       # 抠图模块
├── templates/              # 内置模板 JSON + 装饰素材
├── data/
│   ├── db.py               # SQLite 数据库操作
│   ├── uploads/            # 用户上传的图片
│   └── outputs/            # 生成的结果图片
├── requirements.txt
└── docs/plans/
```
