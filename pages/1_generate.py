# pages/1_generate.py
import streamlit as st
import os
import io
import zipfile
from PIL import Image
from core.platforms import PLATFORMS
from core.copy_generator import COPY_STYLES, generate_copy
from core.image_composer import compose_images

st.set_page_config(page_title="生成主图 & 文案", layout="wide")
st.title("生成主图 & 文案")

# --- Input section ---
input_method = st.radio("商品信息来源", ["在线录入", "批量导入"], horizontal=True)

if input_method == "在线录入":
    col_input, col_output = st.columns([1, 1])

    with col_input:
        st.subheader("商品信息")
        uploaded_file = st.file_uploader("上传商品图片", type=["jpg", "jpeg", "png"])
        product_name = st.text_input("商品名称", placeholder="例：超轻透气运动鞋")
        sp1 = st.text_input("卖点 1", placeholder="例：透气网面")
        sp2 = st.text_input("卖点 2（可选）", placeholder="例：轻便舒适")
        sp3 = st.text_input("卖点 3（可选）", placeholder="例：防滑耐磨")
        price = st.number_input("价格 (¥)", min_value=0.01, value=99.9, step=0.1)

        st.subheader("生成配置")
        selected_platforms = st.multiselect(
            "目标平台（可多选）",
            options=list(PLATFORMS.keys()),
            default=["taobao"],
            format_func=lambda k: PLATFORMS[k]["label"],
        )
        template_style = st.selectbox(
            "模板风格",
            options=["promo", "minimal", "premium", "fresh", "social"],
            format_func=lambda k: {
                "promo": "促销爆款",
                "minimal": "简约白底",
                "premium": "高端质感",
                "fresh": "清新文艺",
                "social": "社交种草",
            }[k],
        )
        copy_style = st.selectbox(
            "文案风格",
            options=list(COPY_STYLES.keys()),
            format_func=lambda k: COPY_STYLES[k]["label"],
        )

        # Logo upload
        logo_file = st.file_uploader("店铺 Logo（可选）", type=["png", "jpg", "jpeg"])

        generate_btn = st.button("🚀 一键生成", type="primary", use_container_width=True)

    # --- Output section ---
    with col_output:
        if generate_btn:
            if not uploaded_file or not product_name or not sp1 or not selected_platforms:
                st.error("请填写商品名称、至少一个卖点，上传图片，并选择至少一个平台")
            else:
                selling_points = [sp for sp in [sp1, sp2, sp3] if sp]
                product_info = {
                    "name": product_name,
                    "selling_points": selling_points,
                    "price": price,
                }

                product_img = Image.open(uploaded_file)
                logo = Image.open(logo_file) if logo_file else None

                # Generate images
                with st.spinner("正在生成主图..."):
                    images = compose_images(
                        product_image=product_img,
                        product_info=product_info,
                        platforms=selected_platforms,
                        template_style=template_style,
                        logo=logo,
                    )

                # Generate copy
                with st.spinner("正在生成文案..."):
                    try:
                        copies = generate_copy(
                            product_name=product_name,
                            selling_points=selling_points,
                            price=price,
                            platform=selected_platforms[0],
                            style=copy_style,
                        )
                    except Exception as e:
                        st.error(f"文案生成失败: {e}")
                        copies = []

                # Display results
                st.subheader("生成结果")

                for platform_key, img in images.items():
                    platform_label = PLATFORMS[platform_key]["label"]
                    st.markdown(f"**{platform_label}** ({img.size[0]}x{img.size[1]})")
                    st.image(img, use_container_width=True)

                if copies:
                    st.subheader("候选文案")
                    for i, copy_item in enumerate(copies):
                        with st.expander(f"文案方案 {i + 1}", expanded=True):
                            st.markdown(f"**标题：** {copy_item.get('title', '')}")
                            for sp in copy_item.get("selling_points", []):
                                st.markdown(f"- {sp}")

                # Download all as zip
                st.subheader("下载")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for platform_key, img in images.items():
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format="PNG")
                        zf.writestr(f"{platform_key}_main.png", img_buffer.getvalue())
                    if copies:
                        copy_text = ""
                        for i, copy_item in enumerate(copies):
                            copy_text += f"=== 文案方案 {i + 1} ===\n"
                            copy_text += f"标题：{copy_item.get('title', '')}\n"
                            for sp in copy_item.get("selling_points", []):
                                copy_text += f"- {sp}\n"
                            copy_text += "\n"
                        zf.writestr("copy.txt", copy_text)

                zip_buffer.seek(0)
                st.download_button(
                    "📦 下载全部（图片 + 文案）",
                    data=zip_buffer,
                    file_name=f"{product_name}_outputs.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

elif input_method == "批量导入":
    st.info("📋 批量导入功能：上传 Excel 文件 + 图片压缩包")

    col1, col2 = st.columns(2)
    with col1:
        excel_file = st.file_uploader("上传 Excel/CSV 文件", type=["xlsx", "csv"])
    with col2:
        zip_file = st.file_uploader("上传图片压缩包", type=["zip"])

    if excel_file:
        import pandas as pd

        if excel_file.name.endswith(".csv"):
            df = pd.read_csv(excel_file)
        else:
            df = pd.read_excel(excel_file)
        st.dataframe(df, use_container_width=True)
        st.caption(f"共 {len(df)} 个商品")

    st.subheader("生成配置")
    batch_platforms = st.multiselect(
        "目标平台",
        options=list(PLATFORMS.keys()),
        default=["taobao"],
        format_func=lambda k: PLATFORMS[k]["label"],
        key="batch_platforms",
    )
    batch_style = st.selectbox(
        "模板风格",
        options=["promo", "minimal", "premium", "fresh", "social"],
        format_func=lambda k: {
            "promo": "促销爆款",
            "minimal": "简约白底",
            "premium": "高端质感",
            "fresh": "清新文艺",
            "social": "社交种草",
        }[k],
        key="batch_style",
    )
    batch_copy_style = st.selectbox(
        "文案风格",
        options=list(COPY_STYLES.keys()),
        format_func=lambda k: COPY_STYLES[k]["label"],
        key="batch_copy_style",
    )

    if st.button("🚀 批量生成", type="primary"):
        if not excel_file or not zip_file or not batch_platforms:
            st.error("请上传 Excel 和图片压缩包，并选择平台")
        else:
            import pandas as pd
            import zipfile as zf_mod

            if excel_file.name.endswith(".csv"):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)

            # Extract images from zip
            image_map = {}
            with zf_mod.ZipFile(zip_file) as z:
                for name in z.namelist():
                    if name.lower().endswith((".png", ".jpg", ".jpeg")):
                        image_map[os.path.basename(name)] = z.read(name)

            progress = st.progress(0)
            all_results = io.BytesIO()
            with zf_mod.ZipFile(all_results, "w") as out_zip:
                for idx, row in df.iterrows():
                    progress.progress((idx + 1) / len(df))
                    name = str(row.get("商品名称", row.iloc[0]))
                    sps = []
                    for j in range(1, 4):
                        col_name = f"卖点{j}"
                        val = row.get(col_name, None)
                        if val is not None and str(val) != "nan":
                            sps.append(str(val))
                    price_val = float(row.get("价格", 0))
                    img_name = str(row.get("图片文件名", ""))

                    if img_name in image_map:
                        product_img = Image.open(io.BytesIO(image_map[img_name]))
                        product_info_batch = {
                            "name": name,
                            "selling_points": sps,
                            "price": price_val,
                        }
                        images = compose_images(
                            product_img, product_info_batch, batch_platforms, batch_style
                        )
                        for pk, img in images.items():
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            out_zip.writestr(f"{name}/{pk}_main.png", buf.getvalue())

            all_results.seek(0)
            st.download_button(
                "📦 下载全部结果",
                data=all_results,
                file_name="batch_outputs.zip",
                mime="application/zip",
            )
