# pages/2_templates.py
import streamlit as st
import os
import json
import copy
from core.template_engine import list_templates, load_template, render_image
from PIL import Image

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "presets")

st.set_page_config(page_title="模板管理", layout="wide")
st.title("模板管理")

# --- List all templates ---
templates = list_templates(PRESETS_DIR)

tab_list, tab_create = st.tabs(["模板列表", "新建模板"])

with tab_list:
    cols = st.columns(3)
    for i, tpl in enumerate(templates):
        with cols[i % 3]:
            # Generate preview with dummy data
            dummy_img = Image.new("RGBA", (200, 200), (100, 150, 200, 255))
            dummy_info = {"name": "示例商品", "selling_points": ["卖点A", "卖点B"], "price": 99.9}
            preview = render_image(tpl, dummy_img, dummy_info)

            st.image(preview, caption=tpl["name"], use_container_width=True)
            st.caption(f"平台: {tpl.get('platform', '通用')} | 尺寸: {tpl['canvas']['width']}x{tpl['canvas']['height']}")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("编辑", key=f"edit_{i}"):
                    st.session_state["editing_template"] = tpl
                    st.session_state["editing_filename"] = tpl.get("_filename", "")
            with col_b:
                if st.button("复制", key=f"copy_{i}"):
                    new_tpl = copy.deepcopy(tpl)
                    new_tpl["name"] = tpl["name"] + " (副本)"
                    new_filename = tpl.get("_filename", "template.json").replace(".json", "_copy.json")
                    with open(os.path.join(PRESETS_DIR, new_filename), "w", encoding="utf-8") as f:
                        clean = {k: v for k, v in new_tpl.items() if not k.startswith("_")}
                        json.dump(clean, f, ensure_ascii=False, indent=2)
                    st.rerun()
            with col_c:
                if st.button("删除", key=f"del_{i}"):
                    fname = tpl.get("_filename")
                    if fname:
                        os.remove(os.path.join(PRESETS_DIR, fname))
                        st.rerun()

    # Edit form
    if "editing_template" in st.session_state:
        st.divider()
        st.subheader(f"编辑模板: {st.session_state['editing_template']['name']}")
        tpl = st.session_state["editing_template"]

        new_name = st.text_input("模板名称", value=tpl["name"])
        new_platform = st.selectbox("平台", ["taobao", "pinduoduo", "douyin", "xiaohongshu"],
                                     index=["taobao", "pinduoduo", "douyin", "xiaohongshu"].index(tpl.get("platform", "taobao")))
        new_width = st.number_input("画布宽度", value=tpl["canvas"]["width"], step=10)
        new_height = st.number_input("画布高度", value=tpl["canvas"]["height"], step=10)

        bg_type = st.selectbox("背景类型", ["solid", "gradient"],
                                index=0 if tpl.get("background", {}).get("type") == "solid" else 1)
        color1 = st.color_picker("颜色 1", value=tpl.get("background", {}).get("colors", ["#FFFFFF"])[0])
        color2 = st.color_picker("颜色 2", value=tpl.get("background", {}).get("colors", ["#FFFFFF", "#FFFFFF"])[-1])

        if st.button("保存修改"):
            updated = copy.deepcopy(tpl)
            updated["name"] = new_name
            updated["platform"] = new_platform
            updated["canvas"] = {"width": int(new_width), "height": int(new_height)}
            updated["background"] = {"type": bg_type, "colors": [color1, color2] if bg_type == "gradient" else [color1]}

            fname = st.session_state.get("editing_filename", "template.json")
            with open(os.path.join(PRESETS_DIR, fname), "w", encoding="utf-8") as f:
                clean = {k: v for k, v in updated.items() if not k.startswith("_")}
                json.dump(clean, f, ensure_ascii=False, indent=2)
            del st.session_state["editing_template"]
            st.success("模板已保存")
            st.rerun()

with tab_create:
    st.subheader("新建模板")
    new_tpl_name = st.text_input("模板名称", key="new_name")
    new_tpl_platform = st.selectbox("目标平台", ["taobao", "pinduoduo", "douyin", "xiaohongshu"], key="new_platform")
    new_bg_type = st.selectbox("背景类型", ["solid", "gradient"], key="new_bg")
    new_color1 = st.color_picker("颜色 1", value="#FFFFFF", key="nc1")
    new_color2 = st.color_picker("颜色 2", value="#EEEEEE", key="nc2")
    new_font_size = st.slider("标题字号", 16, 60, 32, key="nfs")
    new_font_color = st.color_picker("标题颜色", value="#333333", key="nfc")
    new_price_size = st.slider("价格字号", 16, 60, 36, key="nps")
    new_price_color = st.color_picker("价格颜色", value="#E74C3C", key="npc")

    from core.platforms import get_platform_config
    pc = get_platform_config(new_tpl_platform)

    if st.button("创建模板"):
        if not new_tpl_name:
            st.error("请输入模板名称")
        else:
            tpl_data = {
                "name": new_tpl_name,
                "platform": new_tpl_platform,
                "canvas": {"width": pc["width"], "height": pc["height"]},
                "background": {
                    "type": new_bg_type,
                    "colors": [new_color1, new_color2] if new_bg_type == "gradient" else [new_color1],
                },
                "elements": [
                    {"type": "product_image", "x": "center", "y": "center", "max_width_pct": 60, "max_height_pct": 55},
                    {"type": "title", "x": "center", "y": 40, "font_size": new_font_size, "color": new_font_color, "font_weight": "bold"},
                    {"type": "price", "x": "center", "y": pc["height"] - 80, "font_size": new_price_size, "color": new_price_color, "prefix": "¥"},
                    {"type": "selling_points", "x": 50, "y": pc["height"] - 130, "font_size": 18, "color": "#333333", "style": "tags", "bg_color": "#EEEEEE88"},
                ],
            }
            fname = f"{new_tpl_name}_{new_tpl_platform}.json".replace(" ", "_")
            with open(os.path.join(PRESETS_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(tpl_data, f, ensure_ascii=False, indent=2)
            st.success(f"模板 '{new_tpl_name}' 已创建")
            st.rerun()
