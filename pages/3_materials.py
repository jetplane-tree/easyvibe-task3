# pages/3_materials.py
import streamlit as st
import os
from PIL import Image
from data.db import Database

st.set_page_config(page_title="素材库", layout="wide")
st.title("素材库")

db = Database()

# Search bar
search_query = st.text_input("🔍 搜索商品", placeholder="输入商品名称关键词...")

if search_query:
    materials = db.search_materials(search_query)
else:
    materials = db.list_materials()

if not materials:
    st.info("素材库为空，在生成页面勾选「保存到素材库」即可添加商品素材")
else:
    st.caption(f"共 {len(materials)} 个商品素材")

    cols = st.columns(3)
    for i, mat in enumerate(materials):
        with cols[i % 3]:
            with st.container(border=True):
                # Show image if exists
                if mat.get("image_path") and os.path.exists(mat["image_path"]):
                    img = Image.open(mat["image_path"])
                    st.image(img, use_container_width=True)
                else:
                    st.markdown("🖼️ *图片未找到*")

                st.markdown(f"**{mat['name']}**")
                st.caption(f"¥{mat['price']}")
                for sp in mat.get("selling_points", []):
                    st.markdown(f"- {sp}")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("去生成", key=f"gen_{mat['id']}"):
                        st.session_state["prefill_material"] = mat
                        st.switch_page("pages/1_generate.py")
                with col_b:
                    if st.button("编辑", key=f"edit_{mat['id']}"):
                        st.session_state[f"editing_mat_{mat['id']}"] = True
                with col_c:
                    if st.button("删除", key=f"del_{mat['id']}"):
                        db.delete_material(mat["id"])
                        st.rerun()

                # Inline edit form
                if st.session_state.get(f"editing_mat_{mat['id']}"):
                    new_name = st.text_input("名称", value=mat["name"], key=f"en_{mat['id']}")
                    new_price = st.number_input("价格", value=mat["price"], key=f"ep_{mat['id']}")
                    new_sps = st.text_area("卖点（每行一个）",
                                           value="\n".join(mat.get("selling_points", [])),
                                           key=f"esp_{mat['id']}")
                    if st.button("保存", key=f"save_{mat['id']}"):
                        db.update_material(
                            mat["id"],
                            name=new_name,
                            price=new_price,
                            selling_points=[s.strip() for s in new_sps.split("\n") if s.strip()],
                        )
                        del st.session_state[f"editing_mat_{mat['id']}"]
                        st.rerun()
