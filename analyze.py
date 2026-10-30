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

只根据给定数据分析，不要补充输入中没有的新闻事实。
跨平台共振指不同平台同时关注相同或高度相近的主题，
不要求标题完全相同；如果没有明确共振，请如实说明。

请输出结构清晰的中文 Markdown，严格包含以下部分：

# 今日热点分析

## 一、主题聚类
归纳 3～5 个主要主题。
每个主题列出代表性热点，并标注平台。

## 二、中文摘要
用 5～8 个要点概括本批热点的重要内容。
每个要点尽量标注对应平台。

## 三、跨平台共振判断
列出真正出现在至少两个平台上的相同或相近主题，
说明涉及平台和判断理由。
若没有明确共振，直接写“本批未发现明确的跨平台共振”。

## 四、简短结论
用 2～3 句话总结本批热点整体反映出的技术关注方向。

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