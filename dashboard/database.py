"""
database.py
Kết nối MotherDuck và load dữ liệu từ tầng Gold (lakehouse).
"""
import os
import streamlit as st
import duckdb

GOLD_TABLE = "youtube_analytics_lakehouse.main_youtube_gold.wide_video_analytics"


@st.cache_resource
def get_connection():
    """Tạo (và cache) kết nối duckdb tới MotherDuck."""
    os.environ["motherduck_token"] = st.secrets["MOTHERDUCK_TOKEN"]
    return duckdb.connect("md:")


@st.cache_data(ttl=3600)
def get_summary_stats(country_sel: str, category_sel: str):
    """Tính COUNT/AVG cho các card tổng quan bằng aggregate query chạy THẲNG
    trên MotherDuck, không kéo dữ liệu thô về client -> luôn đúng 100% trên
    toàn bộ dữ liệu và không lo timeout DOWNLOAD_BRIDGE_DATA, vì kết quả trả
    về chỉ có đúng 1 dòng."""
    con = get_connection()
    where_clauses, params = [], []
    if country_sel and country_sel != "Tất cả":
        where_clauses.append("country_code = ?")
        params.append(country_sel)
    if category_sel and category_sel != "Tất cả":
        where_clauses.append("category_name = ?")
        params.append(category_sel)
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT
            COUNT(*)                       AS total_records,
            COUNT(DISTINCT video_id)       AS unique_videos,
            COUNT(DISTINCT channel_title)  AS unique_channels,
            AVG(engagement_rate)           AS avg_engagement
        FROM {GOLD_TABLE}
        {where_sql}
    """
    row = con.execute(query, params).df().iloc[0]
    return {
        "total_records": int(row["total_records"]),
        "unique_videos": int(row["unique_videos"]),
        "unique_channels": int(row["unique_channels"]),
        "avg_engagement": float(row["avg_engagement"]) if row["avg_engagement"] is not None else 0.0,
    }


@st.cache_data(ttl=3600)
def load_data():
    """Load toàn bộ bảng cần thiết từ tầng Gold. Cache 1 giờ để tránh query lại
    liên tục mỗi lần rerun (ví dụ khi đổi filter sidebar)."""
    con = get_connection()

    df_gold = con.sql(f"""
        SELECT * FROM {GOLD_TABLE}
    """).df()

    df_category = con.sql("""
        SELECT category_name, avg_engagement_rate, unique_videos, trending_records
        FROM youtube_analytics_lakehouse.main_youtube_gold.gold_category_performance
        ORDER BY avg_engagement_rate DESC
    """).df()

    df_country = con.sql("""
        SELECT country_code, avg_engagement_rate, unique_videos, trending_records
        FROM youtube_analytics_lakehouse.main_youtube_gold.gold_country_performance
        ORDER BY avg_engagement_rate DESC
    """).df()

    df_model_results = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.ml_model_results
        ORDER BY r2 DESC
    """).df()

    df_predictions = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.ml_predictions
    """).df()

    return df_gold, df_category, df_country, df_model_results, df_predictions