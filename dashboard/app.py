import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq

st.set_page_config(
    page_title="YouTube Trending Analytics",
    page_icon="",
    layout="wide"
)

@st.cache_resource
def get_connection():
    import os
    os.environ["motherduck_token"] = st.secrets["MOTHERDUCK_TOKEN"]
    return duckdb.connect("md:")

con = get_connection()

@st.cache_data(ttl=3600)
def load_data():
    df_gold = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.wide_video_analytics
        LIMIT 50000
    """).df()

    df_category = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.gold_category_performance
    """).df()

    df_country = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.gold_country_performance
    """).df()

    df_predictions = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.ml_predictions
    """).df()

    df_model_results = con.sql("""
        SELECT * FROM youtube_analytics_lakehouse.main_youtube_gold.ml_model_results
    """).df()

    return df_gold, df_category, df_country, df_predictions, df_model_results

df_gold, df_category, df_country, df_predictions, df_model_results = load_data()

st.sidebar.title("YouTube Analytics")
page = st.sidebar.radio("Chon trang", [
    "Overview",
    "Category and Country",
    "ML Predictions",
    "AI Insights"
])

if page == "Overview":
    st.title("YouTube Trending - Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tong so records", f"{len(df_gold):,}")
    col2.metric("So video unique", f"{df_gold['video_id'].nunique():,}")
    col3.metric("So channel", f"{df_gold['channel_title'].nunique():,}")
    col4.metric("Avg Engagement Rate", f"{df_gold['engagement_rate'].mean():.2f}%")

    st.subheader("Trending theo thang")
    monthly = df_gold.groupby(['trending_year', 'trending_month']).size().reset_index(name='count')
    monthly['period'] = monthly['trending_year'].astype(str) + '-' + monthly['trending_month'].astype(str).str.zfill(2)
    fig = px.bar(monthly, x='period', y='count', title='So video trending theo thang')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Channel co Engagement cao nhat")
    top_channels = df_gold.groupby('channel_title')['engagement_rate'].mean().nlargest(10).reset_index()
    fig2 = px.bar(top_channels, x='engagement_rate', y='channel_title',
                  orientation='h', title='Top 10 Channels by Avg Engagement Rate')
    st.plotly_chart(fig2, use_container_width=True)

elif page == "Category and Country":
    st.title("Phan tich Category va Country")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Engagement Rate theo Category")
        fig = px.bar(
            df_category.sort_values('avg_engagement_rate', ascending=True).tail(10),
            x='avg_engagement_rate', y='category_name',
            orientation='h', color='avg_engagement_rate',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Engagement Rate theo Country")
        fig2 = px.bar(
            df_country.sort_values('avg_engagement_rate', ascending=False),
            x='country_code', y='avg_engagement_rate',
            color='avg_engagement_rate', color_continuous_scale='Reds'
        )
        st.plotly_chart(fig2, use_container_width=True)

elif page == "ML Predictions":
    st.title("Ket qua ML Model")

    st.subheader("So sanh cac Models")
    fig = px.bar(
        df_model_results.sort_values('r2', ascending=False),
        x='model', y='r2',
        color='r2', color_continuous_scale='RdYlGn',
        title='R2 Score - Orig Space (cao hon = tot hon)'
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Actual vs Predicted")
        sample = df_predictions.sample(min(2000, len(df_predictions)))
        fig2 = px.scatter(
            sample, x='actual_engagement', y='predicted_engagement',
            opacity=0.4, title='Actual vs Predicted Engagement Rate'
        )
        fig2.add_shape(type='line', x0=0, y0=0,
                       x1=sample['actual_engagement'].max(),
                       y1=sample['actual_engagement'].max(),
                       line=dict(color='red', dash='dash'))
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Phan phoi Residuals")
        fig3 = px.histogram(df_predictions, x='residual', nbins=60,
                            title='Phan phoi Residuals')
        st.plotly_chart(fig3, use_container_width=True)

elif page == "AI Insights":
    st.title("AI Insights - Powered by Llama 3")

    top_cat = df_category.sort_values('avg_engagement_rate', ascending=False).head(5)
    top_country = df_country.sort_values('avg_engagement_rate', ascending=False).head(5)
    best_model_row = df_model_results.sort_values('r2', ascending=False).iloc[0]

    context = f"""
    Du lieu YouTube Trending Analytics:
    - Tong so records: {len(df_gold):,}
    - Avg Engagement Rate toan dataset: {df_gold['engagement_rate'].mean():.2f}%

    Top 5 Category co Engagement cao nhat:
    {top_cat[['category_name','avg_engagement_rate']].to_string(index=False)}

    Top 5 Country co Engagement cao nhat:
    {top_country[['country_code','avg_engagement_rate']].to_string(index=False)}

    Best ML Model: {best_model_row['model']} - R2={best_model_row['r2']:.4f}, RMSE={best_model_row['rmse']:.4f}
    """

    st.text_area("Context gui cho AI:", context, height=200)

    question = st.text_input(
        "Hoi AI ve du lieu:",
        placeholder="Vi du: Category nao nen tap trung de tang engagement?"
    )

    if st.button("Hoi AI") and question:
        with st.spinner("Dang hoi Llama 3..."):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system",
                        "content": "Ban la chuyen gia phan tich du lieu YouTube. Tra loi bang tieng Viet, ngan gon, co so lieu cu the."
                    },
                    {
                        "role": "user",
                        "content": f"Du lieu:\n{context}\n\nCau hoi: {question}"
                    }
                ]
            )
            answer = response.choices[0].message.content
            st.success(answer)
