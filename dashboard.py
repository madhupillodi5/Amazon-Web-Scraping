"""
dashboard.py
------------
New feature: an interactive Streamlit dashboard for exploring the latest
pipeline run and historical price trends stored in SQLite.

Run with:
    streamlit run dashboard.py
"""

import pandas as pd
import streamlit as st

import config
from modules.database import load_all_queries, load_price_history
from modules.visualizer import (
    plotly_brand_comparison,
    plotly_price_trend,
    plotly_price_vs_rating,
)

st.set_page_config(page_title="Amazon Product Intelligence", layout="wide")
st.title("🛒 Amazon Product Intelligence Dashboard")
st.caption("Competitive benchmarking built on scraped/synthetic product data.")

queries = load_all_queries()
if not queries:
    st.warning(
        "No data yet. Run the pipeline first, e.g.:\n\n"
        "`python main.py --query \"wireless earbuds\" --demo`"
    )
    st.stop()

selected_query = st.sidebar.selectbox("Select a tracked search query", queries)
history_df = load_price_history(selected_query)

if history_df.empty:
    st.warning(f"No stored data found for '{selected_query}'.")
    st.stop()

latest_run_time = history_df["scraped_at"].max()
latest_df = history_df[history_df["scraped_at"] == latest_run_time].copy()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Products (latest run)", len(latest_df))
col2.metric("Avg. Price", f"${latest_df['price'].mean():.2f}")
col3.metric("Avg. Rating", f"{latest_df['rating'].mean():.2f} ★")
col4.metric("Snapshots Stored", history_df["scraped_at"].nunique())

st.subheader("Price vs. Rating")
st.plotly_chart(plotly_price_vs_rating(latest_df), use_container_width=True)

col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Average Price by Brand")
    st.plotly_chart(plotly_brand_comparison(latest_df), use_container_width=True)

with col_right:
    st.subheader("Sentiment Breakdown")
    if "sentiment_label" in latest_df:
        st.bar_chart(latest_df["sentiment_label"].value_counts())

if history_df["scraped_at"].nunique() > 1:
    st.subheader("Price Trend Across Runs")
    top_titles = latest_df.sort_values("review_count", ascending=False)["title"].head(8)
    trend_subset = history_df[history_df["title"].isin(top_titles)]
    st.plotly_chart(plotly_price_trend(trend_subset), use_container_width=True)
else:
    st.info("Run the pipeline again for the same query later to unlock price-trend charts.")

st.subheader("Full Product Table")
st.dataframe(
    latest_df.sort_values("value_score", ascending=False)
    if "value_score" in latest_df else latest_df,
    use_container_width=True,
)
