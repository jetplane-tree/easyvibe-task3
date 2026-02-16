# pages/1_generate.py
import streamlit as st
import os
import io
import zipfile
from PIL import Image
from core.platforms import PLATFORMS
from core.copy_generator import COPY_STYLES, generate_copy
from core.image_composer import compose_images
from core.bg_generator import get_scene_presets, generate_ai_background
from data.db import Database

st.set_page_config(page_title="生成主图 & 文案", layout="wide")
st.title("生成主图 & 文案")

# Handle prefill from materials library
prefill = st.session_state.pop("prefill_material", None)

SCENE_PRESETS = get_scene_presets()


def _render_ai_bg_controls(key_prefix: str = ""):
    """Render AI background controls (category, scene, custom prompt). Returns (scene_prompt, custom_prompt)."""
    st.markdown("**AI 背景设置**")

    category = st.selectbox(
        "商品品类",
        options=["不指定"] + list(SCENE_PRESETS.keys()),
        key=f"{key_prefix}ai_category",
    )

    scene_prompt = ""
    if category != "不指定":
        scenes = SCENE_PRESETS[category]
        scene_labels = ["不指定"] + [s["label"] for s in scenes]
        scene_choice = st.selectbox(
            "推荐场景",
            options=scene_labels,
            key=f"{key_prefix}ai_scene",
        )
        if scene_choice != "不指定":
            scene_prompt = next(s["prompt"] for s in scenes if s["label"] == scene_choice)

    custom_prompt = st.text_input(
        "补充描述（可选）",
        placeholder="例：蓝色海洋背景，夏日清凉感",
        key=f"{key_prefix}ai_custom_prompt",
    )

    return scene_prompt, custom_prompt


# --- Input section ---
input_method = st.radio("商品信息来源", ["在线录入", "批量导入", "从素材库选择"], horizontal=True)

if input_method == "在线录入":
    col_input, col_output = st.columns([1, 1])

    with col_input:
        st.subheader("商品信息")
        uploaded_file = st.file_uploader("上传商品图片", type=["jpg", "jpeg", "png"])
        product_name = st.text_input("商品名称", value=prefill["name"] if prefill else "", placeholder="例：超轻透气运动鞋")
        sp1 = st.text_input("卖点 1", value=prefill["selling_points"][0] if prefill and len(prefill.get("selling_points", [])) > 0 else "", placeholder="例：透气网面")
        sp2 = st.text_input("卖点 2（可选）", value=prefill["selling_points"][1] if prefill and len(prefill.get("selling_points", [])) > 1 else "", placeholder="例：轻便舒适")
        sp3 = st.text_input("卖点 3（可选）", value=prefill["selling_points"][2] if prefill and len(prefill.get("selling_points", [])) > 2 else "", placeholder="例：防滑耐磨")
        price = st.number_input("价格 (¥)", min_value=0.01, value=prefill["price"] if prefill else 99.9, step=0.1)

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
        use_ai_bg = st.checkbox("使用 AI 生成背景（需要通义万相 API Key）", value=False)

        scene_prompt = ""
        custom_prompt = ""
        if use_ai_bg:
            scene_prompt, custom_prompt = _render_ai_bg_controls(key_prefix="inline_")

        copy_style = st.selectbox(
            "文案风格",
            options=list(COPY_STYLES.keys()),
            format_func=lambda k: COPY_STYLES[k]["label"],
        )

        # Logo upload
        logo_file = st.file_uploader("店铺 Logo（可选）", type=["png", "jpg", "jpeg"])

        save_to_materials = st.checkbox("保存到素材库", value=False)

        generate_btn = st.button("🚀 一键生成", type="primary", use_container_width=True)

    # --- Output section ---
    with col_output:
        if generate_btn:
            # Clear previous generation state
            for key in ["gen_images", "gen_copies", "gen_saved", "bg_candidates"]:
                st.session_state.pop(key, None)

            if not uploaded_file or not product_name or not sp1 or not selected_platforms:
                st.error("请填写商品名称、至少一个卖点，上传图片，并选择至少一个平台")
            else:
                selling_points = [sp for sp in [sp1, sp2, sp3] if sp]
                product_info = {
                    "name": product_name,
                    "selling_points": selling_points,
                    "price": price,
                    "scene_prompt": scene_prompt,
                    "custom_prompt": custom_prompt,
                }

                product_img = Image.open(uploaded_file)
                logo = Image.open(logo_file) if logo_file else None

                actual_style = f"ai_{template_style}" if use_ai_bg else template_style

                # Store context for later use (radio switch, etc.)
                st.session_state["gen_context"] = {
                    "product_info": product_info,
                    "selected_platforms": selected_platforms,
                    "actual_style": actual_style,
                    "copy_style": copy_style,
                    "save_to_materials": save_to_materials,
                    "use_ai_bg": use_ai_bg,
                    "template_style": template_style,
                }
                st.session_state["gen_product_img"] = product_img
                st.session_state["gen_logo"] = logo

                # AI background candidate generation
                if use_ai_bg:
                    from core.bg_remover import remove_background
                    from core.platforms import get_platform_config
                    platform_cfg = get_platform_config(selected_platforms[0])
                    canvas_w = platform_cfg["width"]
                    canvas_h = platform_cfg["height"]

                    with st.spinner("正在去除背景..."):
                        rgba_product = remove_background(product_img)

                    with st.spinner("正在生成 AI 背景候选..."):
                        try:
                            bg_candidates = generate_ai_background(
                                product_image=rgba_product,
                                product_name=product_name,
                                style=template_style,
                                width=canvas_w,
                                height=canvas_h,
                                scene_prompt=scene_prompt,
                                custom_prompt=custom_prompt,
                                n=4,
                            )
                            st.session_state["bg_candidates"] = bg_candidates
                            st.session_state["bg_gen_params"] = {
                                "product_name": product_name,
                                "style": template_style,
                                "width": canvas_w,
                                "height": canvas_h,
                                "scene_prompt": scene_prompt,
                                "custom_prompt": custom_prompt,
                            }
                        except Exception as e:
                            st.warning(f"AI 背景生成失败，将使用模板默认背景: {e}")
                            st.session_state.pop("bg_candidates", None)
                else:
                    # Non-AI mode: generate immediately and store results
                    st.session_state.pop("bg_candidates", None)
                    with st.spinner("正在生成主图..."):
                        images = compose_images(
                            product_image=product_img,
                            product_info=product_info,
                            platforms=selected_platforms,
                            template_style=actual_style,
                            logo=logo,
                        )
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
                    st.session_state["gen_images"] = images
                    st.session_state["gen_copies"] = copies
                    st.session_state["gen_saved"] = False

        # --- Candidate selection (persists across reruns via session_state) ---
        if "bg_candidates" in st.session_state and st.session_state.get("gen_context", {}).get("use_ai_bg"):
            bg_candidates = st.session_state["bg_candidates"]
            st.subheader("选择 AI 背景")
            cols = st.columns(4)
            for i, bg_img in enumerate(bg_candidates):
                with cols[i]:
                    st.image(bg_img, use_container_width=True, caption=f"方案 {i+1}")

            selected_bg_idx = st.radio(
                "选择背景方案",
                options=list(range(len(bg_candidates))),
                format_func=lambda x: f"方案 {x+1}",
                horizontal=True,
                key="inline_bg_select",
            )
            selected_ai_composed = bg_candidates[selected_bg_idx]

            col_regen, col_confirm = st.columns(2)
            with col_regen:
                if st.button("🔄 重新生成（点击后请再按一键生成）", key="inline_regenerate"):
                    st.session_state.pop("bg_candidates", None)
                    st.session_state.pop("gen_images", None)
                    st.session_state.pop("gen_copies", None)
                    st.rerun()
            with col_confirm:
                if st.button("✅ 使用该方案生成", key="inline_confirm", type="primary"):
                    ctx = st.session_state["gen_context"]
                    product_img = st.session_state["gen_product_img"]
                    logo = st.session_state.get("gen_logo")
                    product_info = ctx["product_info"]
                    with st.spinner("正在生成主图..."):
                        images = compose_images(
                            product_image=product_img,
                            product_info=product_info,
                            platforms=ctx["selected_platforms"],
                            template_style=ctx["actual_style"],
                            logo=logo,
                            skip_bg_removal=True,
                            ai_composed_override=selected_ai_composed,
                        )
                    with st.spinner("正在生成文案..."):
                        try:
                            copies = generate_copy(
                                product_name=product_info["name"],
                                selling_points=product_info["selling_points"],
                                price=product_info["price"],
                                platform=ctx["selected_platforms"][0],
                                style=ctx["copy_style"],
                            )
                        except Exception as e:
                            st.error(f"文案生成失败: {e}")
                            copies = []
                    st.session_state["gen_images"] = images
                    st.session_state["gen_copies"] = copies
                    st.session_state["gen_saved"] = False
                    st.session_state.pop("bg_candidates", None)
                    st.rerun()

        # --- Display results (persists across reruns) ---
        if "gen_images" in st.session_state:
            images = st.session_state["gen_images"]
            copies = st.session_state.get("gen_copies", [])
            ctx = st.session_state.get("gen_context", {})
            product_info = ctx.get("product_info", {})

            # Save to materials & history (only once per generation)
            if not st.session_state.get("gen_saved"):
                db = Database()
                material_id = None
                if ctx.get("save_to_materials") and "gen_product_img" in st.session_state:
                    upload_dir = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
                    os.makedirs(upload_dir, exist_ok=True)
                    p_img = st.session_state["gen_product_img"]
                    img_save_path = os.path.join(upload_dir, f"{product_info.get('name', 'product')}_{id(p_img)}.png")
                    p_img.save(img_save_path)
                    material_id = db.save_material(product_info["name"], product_info.get("selling_points", []), product_info.get("price", 0), img_save_path)
                    st.success("已保存到素材库")

                output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
                os.makedirs(output_dir, exist_ok=True)
                for platform_key, img in images.items():
                    out_path = os.path.join(output_dir, f"{product_info.get('name', 'product')}_{platform_key}.png")
                    img.save(out_path)
                    db.save_history(
                        material_id=material_id or 0,
                        template_name=ctx.get("template_style", ""),
                        platform=platform_key,
                        copy_style=ctx.get("copy_style", ""),
                        image_path=out_path,
                        copies=copies,
                    )
                st.session_state["gen_saved"] = True

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
                file_name=f"{product_info.get('name', 'product')}_outputs.zip",
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
    batch_ai_bg = st.checkbox("使用 AI 生成背景（需要通义万相 API Key）", value=False, key="batch_ai_bg")

    batch_scene_prompt = ""
    batch_custom_prompt = ""
    if batch_ai_bg:
        batch_scene_prompt, batch_custom_prompt = _render_ai_bg_controls(key_prefix="batch_")

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
                            "scene_prompt": batch_scene_prompt,
                            "custom_prompt": batch_custom_prompt,
                        }
                        batch_actual_style = f"ai_{batch_style}" if batch_ai_bg else batch_style

                        # For AI bg: early removal + v2 composed override
                        batch_composed = None
                        if batch_ai_bg:
                            from core.bg_remover import remove_background
                            from core.platforms import get_platform_config
                            platform_cfg = get_platform_config(batch_platforms[0])
                            rgba_product = remove_background(product_img)
                            try:
                                candidates = generate_ai_background(
                                    product_image=rgba_product,
                                    product_name=name,
                                    style=batch_style,
                                    width=platform_cfg["width"],
                                    height=platform_cfg["height"],
                                    scene_prompt=batch_scene_prompt,
                                    custom_prompt=batch_custom_prompt,
                                    n=1,
                                )
                                batch_composed = candidates[0]
                            except Exception:
                                pass

                        images = compose_images(
                            product_img, product_info_batch, batch_platforms, batch_actual_style,
                            skip_bg_removal=True if batch_composed else False,
                            ai_composed_override=batch_composed,
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

elif input_method == "从素材库选择":
    db = Database()
    materials = db.list_materials()
    if not materials:
        st.info("素材库为空，请先通过「在线录入」保存商品素材")
    else:
        mat_options = {f"{m['name']} (¥{m['price']})": m for m in materials}
        selected_name = st.selectbox("选择商品素材", options=list(mat_options.keys()))
        selected_mat = mat_options[selected_name]

        st.markdown(f"**商品名称:** {selected_mat['name']}")
        st.markdown(f"**价格:** ¥{selected_mat['price']}")
        st.markdown(f"**卖点:** {', '.join(selected_mat.get('selling_points', []))}")

        # Show image if available
        if selected_mat.get("image_path") and os.path.exists(selected_mat["image_path"]):
            st.image(Image.open(selected_mat["image_path"]), width=200)

        st.subheader("生成配置")
        mat_platforms = st.multiselect(
            "目标平台",
            options=list(PLATFORMS.keys()),
            default=["taobao"],
            format_func=lambda k: PLATFORMS[k]["label"],
            key="mat_platforms",
        )
        mat_template_style = st.selectbox(
            "模板风格",
            options=["promo", "minimal", "premium", "fresh", "social"],
            format_func=lambda k: {"promo": "促销爆款", "minimal": "简约白底", "premium": "高端质感", "fresh": "清新文艺", "social": "社交种草"}[k],
            key="mat_style",
        )
        mat_ai_bg = st.checkbox("使用 AI 生成背景（需要通义万相 API Key）", value=False, key="mat_ai_bg")

        mat_scene_prompt = ""
        mat_custom_prompt = ""
        if mat_ai_bg:
            mat_scene_prompt, mat_custom_prompt = _render_ai_bg_controls(key_prefix="mat_")

        mat_copy_style = st.selectbox(
            "文案风格",
            options=list(COPY_STYLES.keys()),
            format_func=lambda k: COPY_STYLES[k]["label"],
            key="mat_copy_style",
        )

        if st.button("🚀 一键生成", type="primary", key="mat_generate"):
            # Clear previous generation state
            for key in ["mat_gen_images", "mat_gen_copies", "mat_gen_saved", "mat_bg_candidates"]:
                st.session_state.pop(key, None)

            if not mat_platforms:
                st.error("请选择至少一个平台")
            elif not selected_mat.get("image_path") or not os.path.exists(selected_mat["image_path"]):
                st.error("商品图片不存在，请重新上传")
            else:
                product_img = Image.open(selected_mat["image_path"])
                product_info = {
                    "name": selected_mat["name"],
                    "selling_points": selected_mat.get("selling_points", []),
                    "price": selected_mat["price"],
                    "scene_prompt": mat_scene_prompt,
                    "custom_prompt": mat_custom_prompt,
                }

                mat_actual_style = f"ai_{mat_template_style}" if mat_ai_bg else mat_template_style

                # Store context for later use
                st.session_state["mat_gen_context"] = {
                    "product_info": product_info,
                    "selected_platforms": mat_platforms,
                    "actual_style": mat_actual_style,
                    "copy_style": mat_copy_style,
                    "mat_id": selected_mat["id"],
                    "use_ai_bg": mat_ai_bg,
                    "template_style": mat_template_style,
                }
                st.session_state["mat_gen_product_img"] = product_img

                if mat_ai_bg:
                    from core.bg_remover import remove_background
                    from core.platforms import get_platform_config
                    platform_cfg = get_platform_config(mat_platforms[0])
                    canvas_w = platform_cfg["width"]
                    canvas_h = platform_cfg["height"]

                    with st.spinner("正在去除背景..."):
                        rgba_product = remove_background(product_img)

                    with st.spinner("正在生成 AI 背景候选..."):
                        try:
                            bg_candidates = generate_ai_background(
                                product_image=rgba_product,
                                product_name=selected_mat["name"],
                                style=mat_template_style,
                                width=canvas_w,
                                height=canvas_h,
                                scene_prompt=mat_scene_prompt,
                                custom_prompt=mat_custom_prompt,
                                n=4,
                            )
                            st.session_state["mat_bg_candidates"] = bg_candidates
                        except Exception as e:
                            st.warning(f"AI 背景生成失败，将使用模板默认背景: {e}")
                            st.session_state.pop("mat_bg_candidates", None)
                else:
                    # Non-AI mode: generate immediately
                    st.session_state.pop("mat_bg_candidates", None)
                    with st.spinner("正在生成主图..."):
                        gen_images = compose_images(
                            product_image=product_img,
                            product_info=product_info,
                            platforms=mat_platforms,
                            template_style=mat_actual_style,
                        )
                    with st.spinner("正在生成文案..."):
                        try:
                            gen_copies = generate_copy(
                                product_name=selected_mat["name"],
                                selling_points=selected_mat.get("selling_points", []),
                                price=selected_mat["price"],
                                platform=mat_platforms[0],
                                style=mat_copy_style,
                            )
                        except Exception as e:
                            st.error(f"文案生成失败: {e}")
                            gen_copies = []
                    st.session_state["mat_gen_images"] = gen_images
                    st.session_state["mat_gen_copies"] = gen_copies
                    st.session_state["mat_gen_saved"] = False

        # --- Candidate selection (persists across reruns via session_state) ---
        if "mat_bg_candidates" in st.session_state and st.session_state.get("mat_gen_context", {}).get("use_ai_bg"):
            bg_candidates = st.session_state["mat_bg_candidates"]
            st.subheader("选择 AI 背景")
            cols = st.columns(4)
            for i, bg_img in enumerate(bg_candidates):
                with cols[i]:
                    st.image(bg_img, use_container_width=True, caption=f"方案 {i+1}")

            selected_bg_idx = st.radio(
                "选择背景方案",
                options=list(range(len(bg_candidates))),
                format_func=lambda x: f"方案 {x+1}",
                horizontal=True,
                key="mat_bg_select",
            )
            selected_ai_composed = bg_candidates[selected_bg_idx]

            col_regen, col_confirm = st.columns(2)
            with col_regen:
                if st.button("🔄 重新生成（点击后请再按一键生成）", key="mat_regenerate"):
                    st.session_state.pop("mat_bg_candidates", None)
                    st.session_state.pop("mat_gen_images", None)
                    st.session_state.pop("mat_gen_copies", None)
                    st.rerun()
            with col_confirm:
                if st.button("✅ 使用该方案生成", key="mat_confirm", type="primary"):
                    ctx = st.session_state["mat_gen_context"]
                    product_img = st.session_state["mat_gen_product_img"]
                    product_info = ctx["product_info"]
                    with st.spinner("正在生成主图..."):
                        gen_images = compose_images(
                            product_image=product_img,
                            product_info=product_info,
                            platforms=ctx["selected_platforms"],
                            template_style=ctx["actual_style"],
                            skip_bg_removal=True,
                            ai_composed_override=selected_ai_composed,
                        )
                    with st.spinner("正在生成文案..."):
                        try:
                            gen_copies = generate_copy(
                                product_name=product_info["name"],
                                selling_points=product_info.get("selling_points", []),
                                price=product_info["price"],
                                platform=ctx["selected_platforms"][0],
                                style=ctx["copy_style"],
                            )
                        except Exception as e:
                            st.error(f"文案生成失败: {e}")
                            gen_copies = []
                    st.session_state["mat_gen_images"] = gen_images
                    st.session_state["mat_gen_copies"] = gen_copies
                    st.session_state["mat_gen_saved"] = False
                    st.session_state.pop("mat_bg_candidates", None)
                    st.rerun()

        # --- Display results (persists across reruns) ---
        if "mat_gen_images" in st.session_state:
            gen_images = st.session_state["mat_gen_images"]
            gen_copies = st.session_state.get("mat_gen_copies", [])
            ctx = st.session_state.get("mat_gen_context", {})

            # Save history (only once per generation)
            if not st.session_state.get("mat_gen_saved"):
                db_mat = Database()
                output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
                os.makedirs(output_dir, exist_ok=True)
                for pk, img in gen_images.items():
                    out_path = os.path.join(output_dir, f"{ctx.get('product_info', {}).get('name', 'product')}_{pk}.png")
                    img.save(out_path)
                    db_mat.save_history(
                        material_id=ctx.get("mat_id", 0),
                        template_name=ctx.get("template_style", ""),
                        platform=pk,
                        copy_style=ctx.get("copy_style", ""),
                        image_path=out_path,
                        copies=gen_copies,
                    )
                st.session_state["mat_gen_saved"] = True

            st.subheader("生成结果")
            for pk, img in gen_images.items():
                st.markdown(f"**{PLATFORMS[pk]['label']}** ({img.size[0]}x{img.size[1]})")
                st.image(img, use_container_width=True)

            if gen_copies:
                st.subheader("候选文案")
                for i, ci in enumerate(gen_copies):
                    with st.expander(f"文案方案 {i + 1}", expanded=True):
                        st.markdown(f"**标题：** {ci.get('title', '')}")
                        for sp in ci.get("selling_points", []):
                            st.markdown(f"- {sp}")

            # Download
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for pk, img in gen_images.items():
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    zf.writestr(f"{pk}_main.png", buf.getvalue())
            zip_buffer.seek(0)
            st.download_button("📦 下载全部", data=zip_buffer, file_name=f"{ctx.get('product_info', {}).get('name', 'product')}_outputs.zip", mime="application/zip")
