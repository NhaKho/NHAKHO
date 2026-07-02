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

Bảng: youtube_analytics_lakehouse.main_youtube_gold.gold_category_performance
- category_name, avg_engagement_rate, unique_videos, trending_records

Bảng: youtube_analytics_lakehouse.main_youtube_gold.gold_country_performance
- country_code, avg_engagement_rate, unique_videos, trending_records

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
                        df_category, df_country, df_model_results, dow_records):
    """Bản tóm tắt số liệu đã tính sẵn (theo filter sidebar hiện tại).
    Đây là 'bộ nhớ nhanh' Ưu tiên 1 mà AI dùng trước, không cần đụng SQL."""
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
    return "\n".join(lines)


def call_groq(messages, temperature=0.2, max_tokens=700):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def is_safe_select(sql: str) -> bool:
    s = sql.strip().strip(";").lower()
    if not s.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "create",
                 "attach", "copy", "pragma", "call", "export", "load "]
    return not any(k in s for k in forbidden)


def ask_ai(question: str, data_summary: str, con):
    """
    Ưu tiên 1: AI nhìn Bản tóm tắt có sẵn trước.
      Nếu đủ dữ liệu để trả lời -> trả lời ngay, KHÔNG đụng tới SQL/MotherDuck.
    Ưu tiên 2: Nếu Bản tóm tắt không đủ chi tiết,
      AI tự viết SQL DuckDB -> Python thực thi trên MotherDuck -> AI đọc kết quả trả lời.

    Trả về: (mode, sql_or_None, answer_text, result_df)
      mode: "summary" | "sql" | "error"
    """
    router_prompt = [
        {"role": "system", "content":
            "Bạn là AI phân tích dữ liệu YouTube Trending. Bạn có sẵn một BẢN TÓM TẮT dữ liệu dưới đây:\n\n"
            f"{data_summary}\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1) Nếu câu hỏi CÓ THỂ trả lời đầy đủ, chính xác chỉ bằng BẢN TÓM TẮT ở trên (ví dụ: hỏi số liệu "
            "tổng quan, top danh mục/quốc gia, thông tin model, ngày đăng tốt nhất...), hãy trả lời NGAY bằng "
            "tiếng Việt, ngắn gọn, có số liệu cụ thể lấy từ Bản tóm tắt. TUYỆT ĐỐI không thêm gì khác.\n"
            "2) Nếu câu hỏi cần dữ liệu CHI TIẾT hơn mà Bản tóm tắt KHÔNG có (ví dụ: hỏi về 1 kênh cụ thể, "
            "1 video cụ thể, một điều kiện lọc/so sánh chưa được tổng hợp sẵn), thì KHÔNG được đoán hay bịa số liệu. "
            "Thay vào đó CHỈ trả về DUY NHẤT một dòng bắt đầu chính xác bằng 'SQL:' theo sau là câu lệnh SQL "
            "DuckDB (SELECT) để tra cứu, dựa trên schema Gold sau:\n"
            f"{GOLD_SCHEMA}\n"
            "Không thêm giải thích, không markdown, không dấu ```."},
        {"role": "user", "content": question},
    ]
    first_resp = call_groq(router_prompt, temperature=0.1, max_tokens=500)

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
        {"role": "user", "content": f"Câu hỏi: {question}\n\nKết quả truy vấn SQL:\n{result_txt}"},
    ]
    answer = call_groq(answer_prompt, temperature=0.3, max_tokens=500)
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
        st.session_state.chat_history.append({"role": "user", "content": question, "mode": None, "sql": None})
        with chat_box:
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                if not GROQ_API_KEY:
                    mode, sql, answer, result_df = "error", None, "Chưa cấu hình GROQ_API_KEY trong st.secrets nên AI chưa thể trả lời.", pd.DataFrame()
                    st.markdown(answer)
                else:
                    with st.spinner("AI đang kiểm tra Bản tóm tắt trước..."):
                        mode, sql, answer, result_df = ask_ai(question, data_summary, con)
                    st.caption(MODE_LABEL.get(mode, ""))
                    st.markdown(answer)
                    if sql:
                        with st.expander("Xem câu lệnh SQL do AI sinh ra"):
                            st.code(sql, language="sql")
                    if len(result_df):
                        st.dataframe(result_df, use_container_width=True)

        st.session_state.chat_history.append({"role": "assistant", "content": answer, "mode": mode, "sql": sql})