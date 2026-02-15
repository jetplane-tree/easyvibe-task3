# pages/4_history.py
import streamlit as st
import os
from PIL import Image
from data.db import Database

st.set_page_config(page_title="历史记录", layout="wide")
st.title("历史记录")

db = Database()
history = db.list_history(limit=100)

if not history:
    st.info("暂无生成记录")
else:
    st.caption(f"共 {len(history)} 条记录")

    for record in history:
        with st.container(border=True):
            col_img, col_info, col_action = st.columns([1, 2, 1])

            with col_img:
                img_path = record.get("generated_image_path", "")
                if img_path and os.path.exists(img_path):
                    st.image(Image.open(img_path), use_container_width=True)
                else:
                    st.markdown("🖼️ *图片未找到*")

            with col_info:
                st.markdown(f"**{record.get('product_name', '未知商品')}**")
                st.caption(f"模板: {record.get('template_name', '-')} | 平台: {record.get('platform', '-')} | 风格: {record.get('copy_style', '-')}")
                st.caption(f"生成时间: {record.get('created_at', '-')}")

                copies = record.get("generated_copy", [])
                if copies:
                    for j, c in enumerate(copies):
                        st.markdown(f"**文案 {j+1}:** {c.get('title', '')}")

            with col_action:
                # Re-download
                img_path = record.get("generated_image_path", "")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        st.download_button(
                            "下载图片",
                            data=f.read(),
                            file_name=os.path.basename(img_path),
                            key=f"dl_{record['id']}",
                        )

                # Re-generate
                mat_id = record.get("material_id")
                if mat_id:
                    mat = db.get_material(mat_id)
                    if mat and st.button("重新生成", key=f"regen_{record['id']}"):
                        st.session_state["prefill_material"] = mat
                        st.switch_page("pages/1_generate.py")
