import json
import os
import sqlite3
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "hotspots.db"
ENV_PATH = ROOT / ".env"
OUTPUT_PATH = ROOT / "analysis" / "latest.md"
MAX_POSTS = 60


def load_env():
    """读取项目 .env，不打印其中的密钥。"""
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def load_latest_posts():
    """只读取 fetched_at 最新的一批数据。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        batch = conn.execute(
            "SELECT MAX(fetched_at) FROM posts"
        ).fetchone()[0]

        if not batch:
            raise SystemExit("数据库没有数据，请先运行 python fetch.py")

        rows = conn.execute(
            """
            SELECT platform, title, heat
            FROM posts
            WHERE fetched_at = ?
            ORDER BY platform, heat DESC
            LIMIT ?
            """,
            (batch, MAX_POSTS),
        ).fetchall()

        posts = [dict(row) for row in rows]
        return batch, posts

    finally:
        conn.close()


def build_prompt(batch, posts):
    """把数据库记录整理成固定分析任务。"""
    posts_json = json.dumps(
        posts,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
请分析以下跨平台热点数据。

数据批次：{batch}
输入数量：{len(posts)} 条

写作要求：
1. 只根据输入数据分析，不补充未提供的新闻事实。
2. 报告面向希望快速了解热点的读者，先给结论，再展开细节。
3. 语言自然、简洁，避免空泛套话和重复罗列标题。
4. 同一个热点不要在多个部分反复详细解释。
5. 总长度控制在 1200～1800 字。
6. 不要为了追求数量强行归纳主题或跨平台共振。

请严格输出以下 Markdown 结构：

# 今日热点分析

用 2～3 句话概括本批热点最值得关注的变化，作为开篇总览。

## 一、中文摘要

列出 4～6 条最重要的信息。
每条不超过 80 字，并标注涉及平台。
优先选择有明确事件、项目或技术价值的信息，不简单复述热榜。

## 二、主题聚类

用 Markdown 表格归纳 3～5 个主题，列固定为：

| 主题 | 本批热点反映的重点 | 代表性热点（标注平台） |

每个主题最多列 3 个代表性热点。
表格内容应简短，不要在单元格中写成长段文章。

## 三、跨平台共振判断

分成两类：

### 强共振
仅当至少两个平台关注同一具体事件、项目、漏洞或技术进展时列出。
说明涉及平台和共同对象；如果没有，写“本批未发现明确的强共振”。

### 趋势共振
可以归纳 AI、安全、开发者工具等宽口径共同趋势，
但必须明确这是主题层面的相似，而不是同一事件。
最多列 3 项，每项用 1～2 句话说明平台和理由。

## 四、简短结论

用 2～3 句话总结本批热点反映的技术关注方向，
并指出哪些判断只是宽口径趋势，避免过度解读。

热点数据如下：
{posts_json}
"""


def call_model(prompt):
    """根据 AI_PROVIDER 选择 GLM 或 DeepSeek。"""
    provider = os.getenv("AI_PROVIDER", "glm").lower()

    if provider == "glm":
        api_key = os.getenv("GLM_API_KEY")
        base_url = os.getenv("GLM_BASE_URL")
        model = os.getenv("GLM_MODEL")
    elif provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL")
        model = os.getenv("DEEPSEEK_MODEL")
    else:
        raise SystemExit("AI_PROVIDER 只能是 glm 或 deepseek")

    if not api_key or not base_url or not model:
        raise SystemExit(
            f"{provider} 的 API_KEY、BASE_URL 或 MODEL 未配置完整"
        )

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=120.0,
        max_retries=1,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是严谨的跨平台技术热点分析助手。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=8192,
    )

    content = response.choices[0].message.content

    if not content or not content.strip():
        raise RuntimeError("模型返回了空报告")

    return model, content.strip()


def main():
    load_env()
    batch, posts = load_latest_posts()

    if not posts:
        raise SystemExit("最新批次没有可分析的记录")

    print(
        f"正在分析 {len(posts)} 条热点，"
        f"数据批次：{batch}"
    )

    prompt = build_prompt(batch, posts)

    # API 调用失败时直接退出，不覆盖上一次成功报告。
    model, report = call_model(prompt)

    final_report = (
        f"> 数据批次：{batch}  \n"
        f"> 分析模型：{model}  \n"
        f"> 输入热点：{len(posts)} 条\n\n"
        f"{report}\n"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(final_report, encoding="utf-8")

    print(f"报告已保存到：{OUTPUT_PATH}")
    print("\n" + final_report)


if __name__ == "__main__":
    main()