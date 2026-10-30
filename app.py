import sqlite3
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "hotspots.db"
REPORT_PATH = ROOT / "analysis" / "latest.md"


def load_latest_posts():
    """读取最新抓取批次，不触发新的抓取。"""
    if not DB_PATH.exists():
        return None, []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        batch = conn.execute(
            "SELECT MAX(fetched_at) FROM posts"
        ).fetchone()[0]

        if not batch:
            return None, []

        rows = conn.execute(
            """
            SELECT platform, title, url, heat, fetched_at
            FROM posts
            WHERE fetched_at = ?
            ORDER BY platform, heat DESC
            """,
            (batch,),
        ).fetchall()

        return batch, [dict(row) for row in rows]

    finally:
        conn.close()


def load_report():
    """读取已经生成的报告，不在看板里调用模型。"""
    if not REPORT_PATH.exists():
        return None

    return REPORT_PATH.read_text(encoding="utf-8")


st.set_page_config(
    page_title="跨平台热点监控",
    page_icon="🔥",
    layout="wide",
)

st.title("跨平台热点监控系统")

page = st.sidebar.radio(
    "功能页面",
    ["今日热点", "分析摘要"],
)

if page == "今日热点":
    batch, posts = load_latest_posts()

    if not batch:
        st.warning("数据库中还没有数据，请先运行 python fetch.py")
        st.stop()

    st.caption(f"当前展示批次：{batch}")

    platforms = sorted(
        {post["platform"] for post in posts}
    )

    selected_platforms = st.sidebar.multiselect(
        "按平台筛选",
        options=platforms,
        default=platforms,
    )

    filtered_posts = [
        post
        for post in posts
        if post["platform"] in selected_platforms
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("本批热点", len(posts))
    col2.metric("平台数量", len(platforms))
    col3.metric("当前显示", len(filtered_posts))

    if not filtered_posts:
        st.info("请至少选择一个平台")
    else:
        st.dataframe(
            filtered_posts,
            hide_index=True,
            use_container_width=True,
            column_config={
                "platform": st.column_config.TextColumn("平台"),
                "title": st.column_config.TextColumn("标题"),
                "url": st.column_config.LinkColumn("链接"),
                "heat": st.column_config.NumberColumn("热度"),
                "fetched_at": st.column_config.TextColumn("抓取时间"),
            },
        )

else:
    report = load_report()

    if report is None:
        st.warning("还没有分析报告，请先运行 python analyze.py")
    else:
        st.markdown(report)