import csv
import io
import sqlite3
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "hotspots.db"
REPORT_PATH = ROOT / "analysis" / "latest.md"

PLATFORM_LABELS = {
    "hackernews": "HackerNews",
    "github": "GitHub",
    "juejin": "掘金",
    "zhihu": "知乎",
    "bilibili": "B站",
}


def platform_label(platform):
    return PLATFORM_LABELS.get(platform, platform)


def load_latest_posts():
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
    if not REPORT_PATH.exists():
        return None

    return REPORT_PATH.read_text(encoding="utf-8")



def apply_theme():
    palette = {
        "BG": "#f8f8f8",
        "PANEL": "#ffffff",
        "TEXT": "#12141f",
        "MUTED": "#5f6b7a",
        "BORDER": "#dbe2ea",
        "ACCENT": "#0064e6",
        "SOFT": "#eef4fb",
    }

    css = """
    <style>
    :root {
        --bg: __BG__;
        --panel: __PANEL__;
        --text: __TEXT__;
        --muted: __MUTED__;
        --border: __BORDER__;
        --accent: __ACCENT__;
        --soft: __SOFT__;
    }

    html, body, .stApp {
        font-family: -apple-system, BlinkMacSystemFont,
            "PingFang SC", "Microsoft YaHei", sans-serif;
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background: var(--bg);
        color: var(--text);
    }

    .block-container {
        max-width: 1500px;
        padding-top: 28px;
    }

    .stApp, .stApp p, .stApp li, .stApp label {
        color: var(--text);
    }

    .stApp p, .stApp li {
        font-size: 16px;
        line-height: 1.65;
    }

    .hero-kicker {
        color: var(--accent);
        font-family: "SFMono-Regular", Consolas, monospace;
        font-size: 12px;
        letter-spacing: 0.15em;
        margin-bottom: 6px;
    }

    .hero-title {
        color: var(--text);
        font-size: 30px;
        font-weight: 700;
        line-height: 1.25;
        white-space: nowrap;
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: 14px;
        margin-top: 7px;
    }

    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 24px;
        padding: 14px 0 18px;
        margin-bottom: 22px;
        border-bottom: 1px solid var(--border);
        color: var(--muted);
        font-size: 13px;
    }

    .hero-meta strong {
        color: var(--text);
        font-weight: 600;
        margin-left: 5px;
    }

    /* 将单选导航变为大点击区域的文字导航，隐藏小圆点。 */
    div[data-testid="stRadio"] [role="radiogroup"] {
        gap: 6px;
    }

    div[data-testid="stRadio"] [role="radiogroup"] label {
        min-height: 44px;
        padding: 9px 13px;
        border-bottom: 2px solid transparent;
        cursor: pointer;
    }

    div[data-testid="stRadio"] [role="radiogroup"] label > div:first-child {
        display: none;
    }

    div[data-testid="stRadio"] [role="radiogroup"] label:hover {
        background: var(--soft);
    }

    div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {
        color: var(--accent);
        font-weight: 650;
    }

    .stButton button,
    .stDownloadButton button {
        min-height: 42px;
        color: var(--text);
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 7px;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        color: var(--accent);
        border-color: var(--accent);
        background: var(--soft);
    }

    [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px 18px;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] p {
        color: var(--muted);
    }

    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] div {
        color: var(--text);
    }

    [data-testid="stTextInput"] input {
        color: var(--text);
        background: var(--panel);
        border-color: var(--border);
    }

    [data-baseweb="select"] > div {
        color: var(--text);
        background: var(--panel);
        border-color: var(--border);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        min-height: 44px;
        color: var(--muted);
    }

    .stTabs [data-baseweb="tab"] p {
        color: var(--muted);
    }

    .stTabs [aria-selected="true"],
    .stTabs [aria-selected="true"] p {
        color: var(--accent);
    }

    .table-wrap {
        max-height: 630px;
        overflow: auto;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--panel);
        margin-bottom: 14px;
    }

    .hotspot-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }

    .hotspot-table th {
        position: sticky;
        top: 0;
        z-index: 1;
        padding: 12px 14px;
        text-align: left;
        color: var(--muted);
        background: var(--panel);
        border-bottom: 1px solid var(--border);
        font-family: "SFMono-Regular", Consolas, monospace;
        font-size: 12px;
        letter-spacing: 0.05em;
    }

    .hotspot-table td {
        padding: 11px 14px;
        color: var(--text);
        border-bottom: 1px solid var(--border);
        vertical-align: top;
        line-height: 1.5;
    }

    .hotspot-table tr:last-child td {
        border-bottom: none;
    }

    .hotspot-table tbody tr:hover {
        background: var(--soft);
    }

    .hotspot-table a {
        color: var(--accent);
        text-decoration: none;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-all;
    }

    .hotspot-table a:hover {
        text-decoration: underline;
    }

    .platform-cell {
        white-space: nowrap;
        font-weight: 600;
    }

    .heat-cell {
        font-family: "SFMono-Regular", Consolas, monospace;
        white-space: nowrap;
    }

    button:focus-visible, a:focus-visible, input:focus-visible {
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px;
    }

    @media (max-width: 700px) {
        .hero-title {
            font-size: 24px;
            white-space: normal;
        }

        .block-container {
            padding-top: 18px;
        }
    }
    </style>
    """

    for key, value in palette.items():
        css = css.replace(f"__{key}__", value)

    st.markdown(css, unsafe_allow_html=True)


def sort_posts(posts, descending):
    with_heat = [post for post in posts if post["heat"] is not None]
    without_heat = [post for post in posts if post["heat"] is None]

    with_heat.sort(
        key=lambda post: post["heat"],
        reverse=descending,
    )

    return with_heat + without_heat


def posts_to_csv(posts):
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["platform", "title", "url", "heat", "fetched_at"],
    )
    writer.writeheader()
    writer.writerows(posts)
    return output.getvalue().encode("utf-8-sig")


def safe_link(url):
    if not url or not url.startswith(("https://", "http://")):
        return "—"

    href = escape(url, quote=True)
    display_url = escape(url)

    return (
        f'<a href="{href}" '
        'target="_blank" rel="noopener noreferrer">'
        f'{display_url}</a>'
    )


def render_post_table(posts, table_id):
    if not posts:
        st.info("当前条件下没有匹配的热点。")
        return

    rows = []

    for post in posts:
        heat = post["heat"] if post["heat"] is not None else "—"

        rows.append(
            "<tr>"
            f'<td class="platform-cell">'
            f'{escape(platform_label(post["platform"]))}</td>'
            f"<td>{escape(post['title'])}</td>"
            f"<td>{safe_link(post['url'])}</td>"
            f'<td class="heat-cell">{heat}</td>'
            f"<td>{escape(post['fetched_at'])}</td>"
            "</tr>"
        )

    table = (
        '<div class="table-wrap">'
        '<table class="hotspot-table">'
        "<thead><tr>"
        '<th scope="col">平台</th>'
        '<th scope="col">标题</th>'
        '<th scope="col">链接</th>'
        '<th scope="col">热度</th>'
        '<th scope="col">抓取时间</th>'
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )

    st.markdown(table, unsafe_allow_html=True)

    st.download_button(
        "导出当前列表 CSV",
        data=posts_to_csv(posts),
        file_name=f"hotspots-{table_id}.csv",
        mime="text/csv",
        key=f"download-{table_id}",
    )


st.set_page_config(
    page_title="跨平台热点监控",
    layout="wide",
)


apply_theme()

batch, posts = load_latest_posts()
batch_text = batch or "暂无数据"

title_col, nav_col = st.columns(
    [2.5, 2.2],
    vertical_alignment="center",
)

with title_col:
    st.markdown(
        """
        <div class="hero-kicker">HOTSPOT MONITOR</div>
        <div class="hero-title">跨平台热点监控系统</div>
        <div class="hero-subtitle">
            OpenCLI 抓取 · SQLite 存储 · DeepSeek 分析
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav_col:
    page = st.segmented_control(
        "页面导航",
        ["热点数据", "分析报告"],
        default="热点数据",
        selection_mode="single",
        label_visibility="collapsed",
        key="page_nav",
    ) or "热点数据"


st.markdown(
    f"""
    <div class="hero-meta">
        <span>自然语言入口<strong>Hermes Agent</strong></span>
        <span>主力分析模型<strong>DeepSeek Flash</strong></span>
        <span>当前批次<strong>{escape(batch_text)}</strong></span>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "热点数据":
    if not batch:
        st.warning("数据库中还没有数据，请先运行 python fetch.py")
        st.stop()

    platforms = sorted({post["platform"] for post in posts})

    # 概览卡片显示到分钟，例如 10-30 11:40。
    batch_short = batch[5:16]

    col1, col2, col3 = st.columns(3)
    col1.metric("本批热点", len(posts))
    col2.metric("监控平台", len(platforms))
    col3.metric("最新批次", batch_short)

    search_col, sort_col = st.columns([3, 1])

    with search_col:
        keyword = st.text_input(
            "搜索标题",
            placeholder="输入关键词，例如 AI、安全、Python",
        ).strip()

    with sort_col:
        sort_choice = st.selectbox(
            "排序方式",
            ["热度从高到低", "热度从低到高"],
        )

    if keyword:
        posts = [
            post
            for post in posts
            if keyword.casefold() in post["title"].casefold()
        ]

    posts = sort_posts(
        posts,
        descending=sort_choice == "热度从高到低",
    )

    tab_labels = ["全部"] + [
        platform_label(platform)
        for platform in platforms
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_post_table(posts, "all")

    for index, platform in enumerate(platforms, start=1):
        with tabs[index]:
            platform_posts = [
                post
                for post in posts
                if post["platform"] == platform
            ]
            render_post_table(platform_posts, platform)

else:
    report = load_report()

    if report is None:
        st.warning("还没有分析报告，请先运行 python analyze.py")
        st.stop()

    st.download_button(
        "下载分析报告",
        data=report,
        file_name="hotspot-analysis.md",
        mime="text/markdown",
    )

    with st.container(border=True):
        st.markdown(report)