"""
app.py
Entry point của dashboard.

Cấu trúc điều hướng (2 cấp, toàn bộ dùng st.tabs native của Streamlit):
  Top nav:   Dashboard | AI Data Assistant
  Trong "Dashboard":
      Header nhỏ "YouTube Analytics"
      Sub-tab:  Tổng quan | Danh mục & Quốc gia | Kết quả ML
      -> Bộ lọc Quốc gia / Danh mục CHỈ nằm trong sub-tab "Tổng quan",
         không hiển thị ở 2 sub-tab còn lại (tránh gây hiểu nhầm filter
         áp dụng chéo).

Icon dùng Bootstrap Icons (CDN) thay cho emoji.
"""
import sys

import pandas as pd
import streamlit as st

from database import get_connection, load_data, get_summary_stats
from utils import DOW_NAMES, find_col, to_j
from dashboard_renderer import render_dashboard_html, BOOTSTRAP_ICONS_CDN
from ai_assistant import build_data_summary, render_ai_assistant_ui

sys.stdout.reconfigure(encoding="utf-8")

st.set_page_config(
    page_title="YouTube Trending Analytics",
    layout="wide",
)

st.markdown(BOOTSTRAP_ICONS_CDN, unsafe_allow_html=True)

st.markdown("""
<style>
    #MainMenu, footer, [data-testid="stToolbar"] {display:none!important;}
    header[data-testid="stHeader"] {background:transparent!important; box-shadow:none!important;}

    .block-container {
        padding-top:1rem!important;
        padding-bottom:1rem!important;
        padding-left:1.4rem!important;
        padding-right:1.4rem!important;
        max-width:100%!important;
    }
    div[data-testid="element-container"] {margin-top:0!important;}
    iframe {border:none!important; display:block!important; width:100%!important;}
/* --- PHẦN TOP NAV (RADIO) --- */
    /* Ẩn tiêu đề mặc định của widget radio */
    div[data-testid="stRadio"] > label { display: none !important; }

    /* Kéo cả HÀNG chứa radio rộng thêm đúng bằng phần padding-right của
       block-container, rồi bù margin-right âm tương ứng -> radio nằm lọt
       vào đúng vùng padding đó, tức là sát ngay mép phải thật của trang.
       Cách này an toàn hơn nhiều so với margin âm trên phần tử con nằm
       sâu bên trong, vì nó không phụ thuộc overflow của các thẻ cha. */
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"]) {
        width: calc(100% + 1.4rem) !important;
        margin-right: -1.4rem !important;
    }

    div[data-testid="stRadio"] {
        width: 100% !important;
        display: flex !important;
        justify-content: flex-end !important;
    }

    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important; /* Ngăn nút bị nhảy xuống dòng */
        gap: 8px !important;
        justify-content: flex-end !important;
        width: auto !important;
        padding-bottom: 0 !important;
    }

    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 8px 16px !important;
        border-radius: 10px !important; /* Bo góc đều cho giống nút bấm */
        font-weight: 600 !important;
        font-size: .9rem !important;
        color: #64748b !important;
        margin: 0 !important;
        cursor: pointer !important;
        white-space: nowrap !important; /* Ép chữ Dashboard luôn nằm trên 1 dòng */
        background: #f8fafc;
        border: 1px solid #e2e8f0;
    }

    /* Style khi nút được chọn */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        color: #7c3aed !important;
        background: rgba(124, 58, 237, 0.08) !important;
        border-color: #7c3aed !important;
    }

    /* Ẩn dấu chấm tròn radio và các icon thừa của Streamlit */
    div[data-testid="stRadio"] svg, 
    div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }
    
    /* Fix lỗi khoảng trống dư thừa trong label của Streamlit */
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
    }
    /* Sub-tab (Tổng quan / Danh mục & Quốc gia / Kết quả ML) — dạng pill segmented */
    .stTabs [data-baseweb="tab-list"] {
        background:#f3f1fb; border-bottom:none; border-radius:12px;
        padding:4px; gap:2px; display:inline-flex; width:auto;
    }
    .stTabs [data-baseweb="tab"] {
        height:34px; padding:0 16px; border-radius:9px;
        font-weight:600; font-size:.83rem; color:#64748b;
    }
    .stTabs [aria-selected="true"] {
        background:#ffffff !important; color:#7c3aed !important;
        box-shadow:0 1px 3px rgba(15,23,42,.10);
    }
    .stTabs [data-baseweb="tab-highlight"] {display:none!important;}
    .stTabs [data-baseweb="tab-border"] {display:none!important;}

    .app-header {
        display:flex; align-items:center; gap:9px; height:42px;
        font-size:1.15rem; font-weight:800; color:#1e293b;
    }
    .app-header i {color:#7c3aed; font-size:1.1rem;}

    .filter-title {
        display:flex; align-items:center; gap:7px;
        font-size:.76rem; font-weight:700; color:#94a3b8;
        text-transform:uppercase; letter-spacing:.06em; margin-bottom:.6rem;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px!important;}
    div[data-testid="stSelectbox"] label {
        display:flex; align-items:center; gap:6px;
        font-weight:600; color:#475569; font-size:.85rem;
    }
    div[data-testid="stSelectbox"] > div > div {
        background:#fbfaff; border:1px solid #e9d5ff; border-radius:10px;
    }
</style>
""", unsafe_allow_html=True)

con = get_connection()

with st.spinner("Đang tải dữ liệu..."):
    (df_gold, df_category, df_country, df_model_results, df_predictions,
     df_top_channels, df_trending_month) = load_data()

col_country = find_col(df_gold, ["country_code", "country"])
col_category = find_col(df_gold, ["category_name", "category"])
col_dow = find_col(df_gold, ["publish_dayofweek", "publish_day_of_week", "dow"])

col_country_pred = find_col(df_predictions, ["country_code", "country"])
col_category_pred = find_col(df_predictions, ["category_name", "category"])

# Card tổng quan cho 2 sub-tab KHÔNG có filter (Danh mục & Quốc gia / Kết quả
# ML) và giá trị mặc định cho AI Assistant khi chưa có filter nào -- tính
# bằng aggregate SQL trên toàn bộ dữ liệu, không phụ thuộc df_gold sample.
stats_all = get_summary_stats("Tất cả", "Tất cả")

nav_l, nav_r = st.columns([8, 2])
with nav_l:
    st.markdown(
        '<div class="app-header"><i class="bi bi-youtube"></i> YouTube Analytics</div>',
        unsafe_allow_html=True,
    )
with nav_r:
    nav_choice = st.radio(
        "Điều hướng",
        ["Dashboard", "AI Data Assistant"],
        horizontal=True,
        label_visibility="collapsed",
        key="top_nav",
    )

if nav_choice == "Dashboard":
    if len(df_category) == 0:
        st.error("Cảnh báo: Bảng gold_category_performance đang trống!")

    sub_ov, sub_cat, sub_ml = st.tabs(["Tổng quan", "Danh mục & Quốc gia", "Kết quả ML"])

    # ---------------------------------------------------------------
    # SUB-TAB 1: TỔNG QUAN — bộ lọc CHỈ nằm ở đây
    # ---------------------------------------------------------------
    with sub_ov:
        with st.container(border=True):
            st.markdown(
                '<div class="filter-title"><i class="bi bi-funnel"></i> Bộ lọc</div>',
                unsafe_allow_html=True,
            )
            f1, f2 = st.columns(2)
            with f1:
                if col_country:
                    country_opts = ["Tất cả"] + sorted(df_gold[col_country].dropna().unique().tolist())
                    country_sel = st.selectbox("Quốc gia", country_opts, key="f_country")
                else:
                    country_sel = "Tất cả"
            with f2:
                if col_category:
                    category_opts = ["Tất cả"] + sorted(df_gold[col_category].dropna().unique().tolist())
                    category_sel = st.selectbox("Danh mục", category_opts, key="f_category")
                else:
                    category_sel = "Tất cả"

        df_f = df_gold.copy()
        if col_country and country_sel != "Tất cả":
            df_f = df_f[df_f[col_country] == country_sel]
        if col_category and category_sel != "Tất cả":
            df_f = df_f[df_f[col_category] == category_sel]

        if df_f.empty:
            st.warning("Không có dữ liệu khớp bộ lọc — tạm hiển thị toàn bộ dữ liệu.")
            df_f = df_gold.copy()

        # Card tổng quan tính bằng aggregate SQL trên MotherDuck -> đúng
        # 100% trên toàn bộ dữ liệu theo đúng filter hiện tại.
        df_stats = get_summary_stats(country_sel, category_sel)

        df_pred_f = df_predictions.copy()
        if col_country_pred and country_sel != "Tất cả":
            df_pred_f = df_pred_f[df_pred_f[col_country_pred] == country_sel]
        if col_category_pred and category_sel != "Tất cả":
            df_pred_f = df_pred_f[df_pred_f[col_category_pred] == category_sel]
        if df_pred_f.empty:
            df_pred_f = df_predictions.copy()

        total_records = df_stats["total_records"]
        unique_videos = df_stats["unique_videos"]
        unique_channels = df_stats["unique_channels"]
        avg_engagement = df_stats["avg_engagement"]
        best_model = df_model_results.iloc[0]

        monthly = df_f.groupby(["trending_year", "trending_month"]).size().reset_index(name="count")
        monthly["period"] = monthly["trending_year"].astype(str) + "-" + monthly["trending_month"].astype(str).str.zfill(2)
        monthly = monthly.sort_values("period")

        hourly = df_f.groupby("publish_hour")["engagement_rate"].mean().reset_index()
        top_ch = df_f.groupby("channel_title")["engagement_rate"].mean().nlargest(8).reset_index()

        if col_dow:
            dow_series = df_f.groupby(col_dow)["engagement_rate"].mean().reindex(range(7))
            dow_records = [
                {"label": DOW_NAMES[i], "eng": (0.0 if pd.isna(v) else float(v))}
                for i, v in enumerate(dow_series)
            ]
        else:
            dow_records = [{"label": d, "eng": 0.0} for d in DOW_NAMES]

        sample_pred = df_pred_f[(df_pred_f["actual_engagement"] < 25) & (df_pred_f["predicted_engagement"] < 25)]
        sample_pred = sample_pred.sample(min(800, len(sample_pred)), random_state=42) if len(sample_pred) else sample_pred

        residuals_ov = df_pred_f[(df_pred_f["residual"] > -15) & (df_pred_f["residual"] < 15)]["residual"].tolist()

        monthly_j = to_j(monthly[["period", "count"]].to_dict("records"))
        hourly_j = to_j(hourly.rename(columns={"engagement_rate": "eng"}).to_dict("records"))
        top_ch_j = to_j(top_ch.to_dict("records"))
        dow_j = to_j(dow_records)
        pred_j_ov = to_j(sample_pred[["actual_engagement", "predicted_engagement"]].to_dict("records"))
        res_j_ov = to_j(residuals_ov[:3000])
        category_j = to_j(df_category.head(15).to_dict("records"))
        country_j = to_j(df_country.to_dict("records"))
        model_j = to_j(df_model_results.to_dict("records"))

        data_summary = build_data_summary(
            country_sel=country_sel,
            category_sel=category_sel,
            total_records=total_records,
            unique_videos=unique_videos,
            unique_channels=unique_channels,
            avg_engagement=avg_engagement,
            best_model=best_model,
            df_category=df_category,
            df_country=df_country,
            df_model_results=df_model_results,
            dow_records=dow_records,
            df_top_channels=df_top_channels,
            df_trending_month=df_trending_month,
        )

        html_ov = render_dashboard_html(
            total_records=total_records,
            unique_videos=unique_videos,
            unique_channels=unique_channels,
            avg_engagement=avg_engagement,
            best_model=best_model,
            monthly_j=monthly_j,
            category_j=category_j,
            country_j=country_j,
            hourly_j=hourly_j,
            top_ch_j=top_ch_j,
            dow_j=dow_j,
            model_j=model_j,
            pred_j=pred_j_ov,
            res_j=res_j_ov,
            active_page="ov",
        )
        st.components.v1.html(html_ov.strip(), height=980, scrolling=True)

    # ---------------------------------------------------------------
    # SUB-TAB 2: DANH MỤC & QUỐC GIA — KHÔNG có bộ lọc, dùng toàn bộ dữ liệu
    # ---------------------------------------------------------------
    with sub_cat:
        residuals_full = df_predictions[
            (df_predictions["residual"] > -15) & (df_predictions["residual"] < 15)
        ]["residual"].tolist()
        sample_pred_full = df_predictions[
            (df_predictions["actual_engagement"] < 25) & (df_predictions["predicted_engagement"] < 25)
        ]
        sample_pred_full = (
            sample_pred_full.sample(min(800, len(sample_pred_full)), random_state=42)
            if len(sample_pred_full) else sample_pred_full
        )

        html_cat = render_dashboard_html(
            total_records=stats_all["total_records"],
            unique_videos=stats_all["unique_videos"],
            unique_channels=stats_all["unique_channels"],
            avg_engagement=stats_all["avg_engagement"],
            best_model=df_model_results.iloc[0],
            monthly_j="[]",
            category_j=to_j(df_category.head(15).to_dict("records")),
            country_j=to_j(df_country.to_dict("records")),
            hourly_j="[]",
            top_ch_j="[]",
            dow_j="[]",
            model_j=to_j(df_model_results.to_dict("records")),
            pred_j=to_j(sample_pred_full[["actual_engagement", "predicted_engagement"]].to_dict("records")),
            res_j=to_j(residuals_full[:3000]),
            active_page="cat",
        )
        st.components.v1.html(html_cat.strip(), height=760, scrolling=True)

    # ---------------------------------------------------------------
    # SUB-TAB 3: KẾT QUẢ ML — KHÔNG có bộ lọc, dùng toàn bộ dữ liệu
    # ---------------------------------------------------------------
    with sub_ml:
        residuals_full_ml = df_predictions[
            (df_predictions["residual"] > -15) & (df_predictions["residual"] < 15)
        ]["residual"].tolist()
        sample_pred_ml = df_predictions[
            (df_predictions["actual_engagement"] < 25) & (df_predictions["predicted_engagement"] < 25)
        ]
        sample_pred_ml = (
            sample_pred_ml.sample(min(800, len(sample_pred_ml)), random_state=42)
            if len(sample_pred_ml) else sample_pred_ml
        )

        html_ml = render_dashboard_html(
            total_records=stats_all["total_records"],
            unique_videos=stats_all["unique_videos"],
            unique_channels=stats_all["unique_channels"],
            avg_engagement=stats_all["avg_engagement"],
            best_model=df_model_results.iloc[0],
            monthly_j="[]",
            category_j="[]",
            country_j="[]",
            hourly_j="[]",
            top_ch_j="[]",
            dow_j="[]",
            model_j=to_j(df_model_results.to_dict("records")),
            pred_j=to_j(sample_pred_ml[["actual_engagement", "predicted_engagement"]].to_dict("records")),
            res_j=to_j(residuals_full_ml[:3000]),
            active_page="ml",
        )
        st.components.v1.html(html_ml.strip(), height=900, scrolling=True)

else:
    # nav_choice khác "Dashboard" nên nhánh if phía trên KHÔNG chạy trong lượt
    # này (khác với st.tabs, if/else chỉ thực thi đúng 1 nhánh) -> tự tính lại
    # data_summary ở đây, dùng giá trị filter đã lưu trong session_state từ
    # lần gần nhất người dùng còn ở tab Tổng quan (mặc định "Tất cả" nếu chưa
    # từng mở tab đó).
    country_sel = st.session_state.get("f_country", "Tất cả")
    category_sel = st.session_state.get("f_category", "Tất cả")

    df_f = df_gold.copy()
    if col_country and country_sel != "Tất cả":
        df_f = df_f[df_f[col_country] == country_sel]
    if col_category and category_sel != "Tất cả":
        df_f = df_f[df_f[col_category] == category_sel]
    if df_f.empty:
        df_f = df_gold.copy()

    df_stats = get_summary_stats(country_sel, category_sel)
    total_records = df_stats["total_records"]
    unique_videos = df_stats["unique_videos"]
    unique_channels = df_stats["unique_channels"]
    avg_engagement = df_stats["avg_engagement"]
    best_model = df_model_results.iloc[0]

    if col_dow:
        dow_series = df_f.groupby(col_dow)["engagement_rate"].mean().reindex(range(7))
        dow_records = [
            {"label": DOW_NAMES[i], "eng": (0.0 if pd.isna(v) else float(v))}
            for i, v in enumerate(dow_series)
        ]
    else:
        dow_records = [{"label": d, "eng": 0.0} for d in DOW_NAMES]

    data_summary = build_data_summary(
        country_sel=country_sel,
        category_sel=category_sel,
        total_records=total_records,
        unique_videos=unique_videos,
        unique_channels=unique_channels,
        avg_engagement=avg_engagement,
        best_model=best_model,
        df_category=df_category,
        df_country=df_country,
        df_model_results=df_model_results,
        dow_records=dow_records,
        df_top_channels=df_top_channels,
        df_trending_month=df_trending_month,
    )

    render_ai_assistant_ui(con, data_summary)