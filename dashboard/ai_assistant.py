"""
ai_assistant.py
AI Data Assistant — GenBI 2 tầng ưu tiên:
  Ưu tiên 1 (Học từ ngữ cảnh): AI trả lời trực tiếp từ Bản tóm tắt (Summary)
    có sẵn nếu đủ thông tin — nhanh, không tốn truy vấn.
  Ưu tiên 2 (Truy vấn SQL): Nếu Bản tóm tắt không đủ chi tiết, AI tự viết
    SQL DuckDB -> Python thực thi trên MotherDuck -> AI đọc kết quả trả lời.

Toàn bộ pipeline chạy phía Python (backend) vì iframe HTML của dashboard
không thể tự kết nối trực tiếp tới MotherDuck.
"""
import pandas as pd
import requests
import streamlit as st
import time

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

GOLD_SCHEMA = """
Bảng: youtube_analytics_lakehouse.main_youtube_gold.wide_video_analytics
- video_id (VARCHAR): mã video
- channel_title (VARCHAR): tên kênh YouTube
- category_name (VARCHAR): danh mục video (nếu có)
- country_code (VARCHAR): mã quốc gia nơi video trending (nếu có)
- engagement_rate (DOUBLE): tỉ lệ tương tác (%)
- publish_hour (INT): giờ đăng video (0-23)
- publish_dayofweek (INT): thứ trong tuần đăng video (0=Thứ 2 ... 6=Chủ nhật, nếu có)
- trending_year (INT), trending_month (INT): năm/tháng video lên trending
LƯU Ý QUAN TRỌNG: bảng này KHÔNG có tên/tiêu đề video (không có cột title).
Muốn lấy tên video, tags, mô tả, thumbnail, giờ đăng gốc... phải JOIN với
dim_video bằng video_id (xem bên dưới).

Bảng: youtube_analytics_lakehouse.main_youtube_gold.fact_video_trending
(bảng fact chi tiết từng lần video lên trending, đã có sẵn category_name/channel_title)
- video_key, country_key, category_key, channel_key, trending_date_key
- video_id (VARCHAR), country_code, category_id, category_name, channel_title
- trending_date (DATE)
- views, likes, dislikes, comment_count (BIGINT)
- like_rate, comment_rate, engagement_rate (DOUBLE)
- comments_disabled, ratings_disabled, video_error_or_removed (BOOLEAN)

Bảng: youtube_analytics_lakehouse.main_youtube_gold.dim_video
(bảng dimension chứa TÊN VIDEO — join với video_id ở wide_video_analytics/fact_video_trending khi câu hỏi cần tên/tiêu đề video)
- video_key, video_id (VARCHAR)
- country_code, channel_title, category_id, category_name
- title (VARCHAR): TÊN/TIÊU ĐỀ VIDEO
- tags (VARCHAR), description (VARCHAR), thumbnail_link (VARCHAR)
- publish_time (TIMESTAMP)

Bảng: youtube_analytics_lakehouse.main_youtube_gold.dim_channel
- channel_key, country_code, channel_title

Bảng: youtube_analytics_lakehouse.main_youtube_gold.dim_category
- category_key, country_code, category_id, category_name

Bảng: youtube_analytics_lakehouse.main_youtube_gold.dim_country
- country_key, country_code

Bảng: youtube_analytics_lakehouse.main_youtube_gold.dim_date
- date_key, date_day (DATE), year, month, day
- month_start, week_start (TIMESTAMP), year_month (VARCHAR), day_name (VARCHAR)

Bảng: youtube_analytics_lakehouse.main_youtube_gold.gold_category_performance
- category_name, avg_engagement_rate, unique_videos, trending_records

Bảng: youtube_analytics_lakehouse.main_youtube_gold.gold_country_performance
- country_code, avg_engagement_rate, unique_videos, trending_records

Bảng: youtube_analytics_lakehouse.main_youtube_gold.gold_top_channels
(số liệu tổng hợp sẵn theo kênh, không cần tự groupby)
- channel_title, country_code
- trending_records, unique_videos, unique_categories
- total_views, total_likes, total_dislikes, total_comments (HUGEINT)
- avg_views, avg_likes, avg_comments, avg_like_rate, avg_comment_rate, avg_engagement_rate (DOUBLE)

Bảng: youtube_analytics_lakehouse.main_youtube_gold.gold_trending_by_month
(số liệu tổng hợp sẵn theo tháng, có breakdown theo country_code/category_name)
- year, month, year_month, month_start
- country_code, category_name
- trending_records, unique_videos, unique_channels
- total_views, total_likes, total_dislikes, total_comments (HUGEINT)
- avg_views, avg_likes, avg_comments, avg_like_rate, avg_comment_rate, avg_engagement_rate (DOUBLE)

Bảng: youtube_analytics_lakehouse.main_youtube_gold.ml_predictions
- video_id, category_name, country_code
- actual_engagement (DOUBLE): engagement thực tế
- predicted_engagement (DOUBLE): engagement mô hình dự đoán
- residual (DOUBLE): actual_engagement - predicted_engagement

Bảng: youtube_analytics_lakehouse.main_youtube_gold.ml_model_results
- model, r2, rmse, mae, r2_log, rmse_log
""".strip()

MODE_LABEL = {
    "summary": "⚡ Từ dữ liệu tóm tắt",
    "sql": "🔍 Truy vấn SQL",
    "error": "⚠️ Lỗi truy vấn",
}


def build_data_summary(country_sel, category_sel, total_records, unique_videos,
                        unique_channels, avg_engagement, best_model,
                        df_category, df_country, df_model_results, dow_records,
                        df_top_channels=None, df_trending_month=None):
    """Bản tóm tắt số liệu đã tính sẵn (theo filter sidebar hiện tại).
    Đây là 'bộ nhớ nhanh' Ưu tiên 1 mà AI dùng trước, không cần đụng SQL.

    df_top_channels / df_trending_month lấy từ 2 bảng Gold có sẵn
    (gold_top_channels, gold_trending_by_month) — tổng hợp trên TOÀN BỘ
    dữ liệu, không theo filter sidebar."""
    lines = [
        f"- Đang lọc theo: Quốc gia = {country_sel} | Danh mục = {category_sel}",
        f"- Tổng số bản ghi: {total_records:,}",
        f"- Số video duy nhất: {unique_videos:,}",
        f"- Số kênh: {unique_channels:,}",
        f"- Engagement Rate trung bình: {avg_engagement:.2f}%",
        f"- Model ML tốt nhất: {best_model['model']} (R2={best_model['r2']:.4f}, RMSE={best_model['rmse']:.4f})",
        "- Top 5 danh mục theo Engagement Rate trung bình (toàn bộ dữ liệu, không theo filter):",
    ]
    for _, r in df_category.head(5).iterrows():
        lines.append(f"    • {r['category_name']}: {r['avg_engagement_rate']:.2f}")
    lines.append("- Top 5 quốc gia theo Engagement Rate trung bình (toàn bộ dữ liệu, không theo filter):")
    for _, r in df_country.head(5).iterrows():
        lines.append(f"    • {r['country_code']}: {r['avg_engagement_rate']:.2f}")
    lines.append("- Bảng so sánh các mô hình ML:")
    for _, r in df_model_results.iterrows():
        lines.append(f"    • {r['model']}: R2={r['r2']:.4f}, RMSE={r['rmse']:.4f}, MAE={r['mae']:.4f}")
    lines.append("- Engagement trung bình theo thứ trong tuần:")
    for d in dow_records:
        lines.append(f"    • {d['label']}: {d['eng']:.2f}")

    if df_top_channels is not None and len(df_top_channels):
        lines.append("- Top 5 kênh theo Engagement Rate trung bình (toàn bộ dữ liệu, không theo filter):")
        for _, r in df_top_channels.head(5).iterrows():
            lines.append(
                f"    • {r['channel_title']} ({r['country_code']}): "
                f"avg_engagement={r['avg_engagement_rate']:.2f}, "
                f"{int(r['unique_videos'])} video, avg_views={r['avg_views']:.0f}"
            )

    if df_trending_month is not None and len(df_trending_month):
        recent = df_trending_month.sort_values(["year", "month"]).tail(6)
        lines.append("- Xu hướng 6 tháng gần nhất (tổng hợp theo tháng, toàn bộ dữ liệu):")
        for period, g in recent.groupby("year_month"):
            total_records_m = int(g["trending_records"].sum())
            avg_eng_m = g["avg_engagement_rate"].mean()
            lines.append(f"    • {period}: {total_records_m:,} bản ghi, avg_engagement={avg_eng_m:.2f}")

    return "\n".join(lines)


class AIServiceError(Exception):
    """Lỗi khi gọi Groq API — dùng để bắt và hiển thị thông báo thân thiện,
    tránh làm sập cả app Streamlit bằng traceback thô."""
    pass


def call_groq(messages, temperature=0.2, max_tokens=700, max_retries=2):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 429:
                # Rate limit -> chờ rồi thử lại (backoff tăng dần), thay vì crash ngay.
                last_err = f"Groq đang bị giới hạn tần suất (429 Too Many Requests)."
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise AIServiceError(
                    "AI đang bị giới hạn tần suất gọi (quá nhiều request/phút). "
                    "Bạn đợi khoảng 30-60 giây rồi hỏi lại nhé."
                )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            last_err = "timeout"
            if attempt < max_retries:
                continue
            raise AIServiceError("AI phản hồi quá lâu (timeout). Bạn thử hỏi lại nhé.")
        except requests.exceptions.RequestException as e:
            raise AIServiceError(f"Không gọi được AI: {e}")
    raise AIServiceError(f"Không gọi được AI sau {max_retries + 1} lần thử: {last_err}")


def is_safe_select(sql: str) -> bool:
    s = sql.strip().strip(";").lower()
    if not s.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "create",
                 "attach", "copy", "pragma", "call", "export", "load "]
    return not any(k in s for k in forbidden)


def _trim_history(history, max_turns=3, max_chars=400):
    """Lấy tối đa `max_turns` cặp hỏi-đáp gần nhất, cắt bớt nội dung dài để
    tránh phình prompt/token. history: list[{"role","content"}] (không có
    key mode/sql)."""
    if not history:
        return []
    trimmed = []
    for msg in history[-(max_turns * 2):]:
        content = (msg.get("content") or "").strip()
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        trimmed.append({"role": msg["role"], "content": content})
    return trimmed


def ask_ai(question: str, data_summary: str, con, history=None):
    """
    Ưu tiên 1: AI nhìn Bản tóm tắt có sẵn trước.
      Nếu đủ dữ liệu để trả lời -> trả lời ngay, KHÔNG đụng tới SQL/MotherDuck.
    Ưu tiên 2: Nếu Bản tóm tắt không đủ chi tiết,
      AI tự viết SQL DuckDB -> Python thực thi trên MotherDuck -> AI đọc kết quả trả lời.

    history: vài lượt hội thoại gần nhất (list[{"role","content"}]), giúp AI
      hiểu các câu hỏi nối tiếp kiểu 'video đó', 'kênh này'... thay vì xử lý
      mỗi câu hỏi hoàn toàn độc lập.

    Trả về: (mode, sql_or_None, answer_text, result_df)
      mode: "summary" | "sql" | "error"
    """
    history_msgs = _trim_history(history)

    router_prompt = [
        {"role": "system", "content":
            "Bạn là AI phân tích dữ liệu YouTube Trending. Bạn có sẵn một BẢN TÓM TẮT dữ liệu dưới đây:\n\n"
            f"{data_summary}\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "0) Đây là hội thoại nhiều lượt. Nếu câu hỏi hiện tại dùng đại từ/ám chỉ mơ hồ như "
            "'video đó', 'kênh này', 'cái đó', 'so với trên'..., hãy tìm TÊN/GIÁ TRỊ CỤ THỂ "
            "(tên video, tên kênh, danh mục...) đã xuất hiện ngay trong câu trả lời gần nhất "
            "của chính bạn ở lượt hội thoại trước, rồi DÙNG THẲNG giá trị đó (dạng chuỗi literal "
            "trong mệnh đề WHERE, ví dụ WHERE d.title = 'Tên video chính xác') để viết câu SQL "
            "MỚI, ĐƠN GIẢN cho câu hỏi hiện tại. TUYỆT ĐỐI KHÔNG viết lại subquery để "
            "'tính toán lại' xem video/kênh đó là gì — giá trị đó đã biết rồi, chỉ cần tra cứu "
            "thêm thông tin liên quan (JOIN thêm bảng cần thiết). Nếu không tìm thấy giá trị cụ "
            "thể nào trong lượt trước, cứ viết SQL theo cách hiểu hợp lý nhất, không được bỏ qua "
            "câu hỏi.\n"
            "1) Nếu câu hỏi CÓ THỂ trả lời đầy đủ, chính xác chỉ bằng BẢN TÓM TẮT ở trên (ví dụ: hỏi số liệu "
            "tổng quan, top danh mục/quốc gia, thông tin model, ngày đăng tốt nhất...), hãy trả lời NGAY bằng "
            "tiếng Việt, ngắn gọn, có số liệu cụ thể lấy từ Bản tóm tắt. TUYỆT ĐỐI không thêm gì khác.\n"
            "2) Nếu câu hỏi cần dữ liệu CHI TIẾT hơn mà Bản tóm tắt KHÔNG có (ví dụ: hỏi về 1 kênh cụ thể, "
            "1 video cụ thể, một điều kiện lọc/so sánh chưa được tổng hợp sẵn), thì KHÔNG được đoán hay bịa số liệu. "
            "Thay vào đó CHỈ trả về DUY NHẤT một dòng bắt đầu chính xác bằng 'SQL:' theo sau là câu lệnh SQL "
            "DuckDB (SELECT) để tra cứu, dựa trên schema Gold sau:\n"
            f"{GOLD_SCHEMA}\n"
            "3) LƯU Ý JOIN: wide_video_analytics và fact_video_trending KHÔNG có tên/tiêu đề video. "
            "Nếu câu hỏi cần TÊN VIDEO (ví dụ 'video nào trending nhất tên gì', 'video có nhiều view nhất là video nào'), "
            "BẮT BUỘC phải JOIN với bảng dim_video bằng video_id để lấy cột title, KHÔNG được bịa tên hay chỉ trả video_id. "
            "4) BẮT BUỘC dùng ĐẦY ĐỦ tên bảng có schema (catalog.schema.table) như trong danh sách schema ở trên, "
            "TUYỆT ĐỐI không viết tên bảng rút gọn (ví dụ phải viết "
            "'youtube_analytics_lakehouse.main_youtube_gold.fact_video_trending', không được viết 'fact_video_trending'), "
            "kể cả khi đặt alias cho bảng.\n"
            "5) LƯU Ý GRAIN DỮ LIỆU: fact_video_trending và wide_video_analytics có THỂ chứa NHIỀU DÒNG "
            "cho CÙNG MỘT video (1 video trending nhiều ngày và/hoặc nhiều quốc gia = nhiều dòng). "
            "Khi câu hỏi hỏi TOP N VIDEO theo 1 chỉ số (views, likes, comment_count, engagement_rate...), "
            "PHẢI GROUP BY video_id (kèm title nếu JOIN dim_video) và lấy MAX()/tổng hợp phù hợp cho chỉ số đó, "
            "để KHÔNG trả về cùng 1 video lặp lại nhiều lần trong danh sách. "
            "Ví dụ: SELECT d.title, MAX(f.comment_count) AS comment_count "
            "FROM youtube_analytics_lakehouse.main_youtube_gold.fact_video_trending f "
            "JOIN youtube_analytics_lakehouse.main_youtube_gold.dim_video d ON f.video_id = d.video_id "
            "GROUP BY d.title ORDER BY comment_count DESC LIMIT 5\n"
            "Không thêm giải thích, không markdown, không dấu ```."},
        *history_msgs,
        {"role": "user", "content": question},
    ]

    try:
        first_resp = call_groq(router_prompt, temperature=0.1, max_tokens=500)
    except AIServiceError as e:
        return "error", None, str(e), pd.DataFrame()

    # Ưu tiên 1: AI tự quyết định Bản tóm tắt là đủ -> trả lời thẳng
    if not first_resp.strip().upper().startswith("SQL:"):
        return "summary", None, first_resp.strip(), pd.DataFrame()

    # Ưu tiên 2: Bản tóm tắt không đủ -> AI đã sinh SQL, giờ thực thi trên MotherDuck
    sql = first_resp.split(":", 1)[1].strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    if not is_safe_select(sql):
        return "error", sql, "Câu hỏi này chưa thể chuyển thành truy vấn an toàn trên dữ liệu. Bạn thử hỏi cụ thể hơn nhé.", pd.DataFrame()

    try:
        result_df = con.sql(sql).df()
    except Exception as e:
        return "error", sql, f"AI đã sinh SQL nhưng thực thi bị lỗi: {e}", pd.DataFrame()

    # Bước 4: gửi kết quả ngược lại cho AI để diễn giải + đưa lời khuyên
    result_txt = result_df.head(20).to_string(index=False) if len(result_df) else "Không có dữ liệu trả về."
    answer_prompt = [
        {"role": "system", "content":
            "Bạn là chuyên gia phân tích dữ liệu YouTube Trending. Dựa CHÍNH XÁC vào bảng kết quả "
            "truy vấn được cung cấp, trả lời câu hỏi bằng tiếng Việt, ngắn gọn, có số liệu cụ thể, "
            "và đưa ra 1 gợi ý chiến lược ngắn nếu phù hợp. Không bịa số liệu ngoài bảng kết quả."},
        *history_msgs,
        {"role": "user", "content": f"Câu hỏi: {question}\n\nKết quả truy vấn SQL:\n{result_txt}"},
    ]
    try:
        answer = call_groq(answer_prompt, temperature=0.3, max_tokens=500)
    except AIServiceError as e:
        return "error", sql, str(e), result_df
    return "sql", sql, answer, result_df


def render_ai_assistant_ui(con, data_summary: str):
    """Render toàn bộ UI của AI Data Assistant (chat 2 tầng ưu tiên) trong Streamlit.

    Vùng lịch sử chat được giới hạn chiều cao và tự scroll riêng (st.container
    height=...), ô nhập luôn nằm ngay bên dưới — không phải cuộn hết trang mới
    thấy ô nhập. Toàn bộ logic AI/SQL/session_state giữ nguyên như cũ.
    """
    st.markdown(
        '<div style="display:flex;align-items:center;gap:9px;'
        'font-size:1.2rem;font-weight:800;color:#1e293b;margin:.2rem 0 .8rem">'
        '<i class="bi bi-robot" style="color:#7c3aed"></i> AI Data Assistant</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Xem dữ liệu tóm tắt AI đang dùng"):
        st.text(data_summary)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_box = st.container(height=520)
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                if msg.get("mode"):
                    st.caption(MODE_LABEL.get(msg["mode"], ""))
                st.markdown(msg["content"])
                if msg.get("sql"):
                    with st.expander("Xem câu lệnh SQL do AI sinh ra"):
                        st.code(msg["sql"], language="sql")

    question = st.chat_input("Hỏi AI: 'Engagement trung bình là bao nhiêu?' hoặc 'Kênh ABC có bao nhiêu video?'")
    if question:
        # Chụp lại lịch sử TRƯỚC khi thêm câu hỏi hiện tại vào, để AI có ngữ
        # cảnh các lượt hỏi-đáp trước đó (vd: 'video đó', 'kênh này'...).
        history_for_ai = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history
        ]

        st.session_state.chat_history.append({"role": "user", "content": question, "mode": None, "sql": None})
        with chat_box:
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                if not GROQ_API_KEY:
                    mode, sql, answer, result_df = "error", None, "Chưa cấu hình GROQ_API_KEY trong st.secrets nên AI chưa thể trả lời.", pd.DataFrame()
                    st.markdown(answer)
                else:
                    try:
                        with st.spinner("AI đang kiểm tra Bản tóm tắt trước..."):
                            mode, sql, answer, result_df = ask_ai(question, data_summary, con, history=history_for_ai)
                    except Exception as e:
                        # Lưới an toàn cuối cùng: dù lỗi gì bất ngờ xảy ra, KHÔNG
                        # để cả app Streamlit sập với traceback thô ra UI.
                        mode, sql, answer, result_df = (
                            "error", None,
                            f"Có lỗi ngoài dự kiến khi AI xử lý câu hỏi: {e}. Bạn thử hỏi lại nhé.",
                            pd.DataFrame(),
                        )
                    st.caption(MODE_LABEL.get(mode, ""))
                    st.markdown(answer)
                    if sql:
                        with st.expander("Xem câu lệnh SQL do AI sinh ra"):
                            st.code(sql, language="sql")
                    if len(result_df):
                        st.dataframe(result_df, use_container_width=True)

        st.session_state.chat_history.append({"role": "assistant", "content": answer, "mode": mode, "sql": sql})
