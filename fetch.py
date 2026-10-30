import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "hotspots.db"

# 平台名、抓取命令、标题字段、热度字段。
SOURCES = [
    (
        "hackernews",
        ["opencli", "hackernews", "top", "-f", "json"],
        "title",
        "score",
    ),
    (
        "juejin",
        ["opencli", "juejin", "hot", "-f", "json"],
        "title",
        "hot_rank",
    ),
    (
        "github",
        ["opencli", "github-trending", "repos", "-f", "json"],
        "repo",
        "starsSince",
    ),
]


def init_db(conn):
    """如果 posts 表不存在，就创建它。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            heat INTEGER,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def fetch_source(platform, command, title_field, heat_field):
    """调用一个 OpenCLI 源，并转换成数据库记录。"""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"OpenCLI 执行失败：{result.stderr[:500]}"
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"返回内容不是有效 JSON：{result.stdout[:500]}"
        ) from exc

    if not payload.get("ok"):
        raise RuntimeError(f"OpenCLI 返回失败：{payload}")

    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("返回 JSON 中没有 data 列表")

    posts = []
    for item in data:
        title = item.get(title_field)

        if not title:
            continue

        posts.append(
            (
                platform,
                title,
                item.get("url"),
                item.get(heat_field),
            )
        )

    if not posts:
        raise ValueError("该源没有可入库的有效记录")

    return posts


def main():
    conn = sqlite3.connect(DB_PATH)

    try:
        init_db(conn)

        # 本次运行只生成一次时间，所有成功平台共享这个批次时间。
        batch_time = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        total = 0

        for platform, command, title_field, heat_field in SOURCES:
            try:
                posts = fetch_source(
                    platform,
                    command,
                    title_field,
                    heat_field,
                )
            except Exception as exc:
                # 单源失败不会阻断后面的源。
                print(f"[失败] {platform}: {exc}")
                continue

            # 给每条记录追加同一个批次时间。
            rows = [
                post + (batch_time,)
                for post in posts
            ]

            conn.executemany(
                """
                INSERT INTO posts
                    (platform, title, url, heat, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

            print(f"[成功] {platform}: 入库 {len(posts)} 条")
            total += len(posts)

        print(f"本次合计入库：{total} 条")

        if total == 0:
            raise SystemExit("错误：所有平台均抓取失败")

    finally:
        conn.close()


if __name__ == "__main__":
    main()