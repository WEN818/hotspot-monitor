import json
import sqlite3
import subprocess
from pathlib import Path

# 无论从哪里启动脚本，数据库都放在项目根目录。
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "hotspots.db"

# 每个源依次记录：平台名、抓取命令、热度字段名。
SOURCES = [
    (
        "hackernews",
        ["opencli", "hackernews", "top", "-f", "json"],
        "score",
    ),
    (
        "juejin",
        ["opencli", "juejin", "hot", "-f", "json"],
        "hot_rank",
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


def fetch_source(platform, command, heat_field):
    """调用一个 OpenCLI 源，并转换成数据库需要的记录。"""
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
        title = item.get("title")

        # 没有标题的记录无法入库，跳过单条，不影响其他记录。
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
        total = 0

        for platform, command, heat_field in SOURCES:
            try:
                posts = fetch_source(platform, command, heat_field)
            except Exception as exc:
                # 单个平台失败，只记录错误，继续处理后面的平台。
                print(f"[失败] {platform}: {exc}")
                continue

            conn.executemany(
                """
                INSERT INTO posts (platform, title, url, heat)
                VALUES (?, ?, ?, ?)
                """,
                posts,
            )
            conn.commit()

            print(f"[成功] {platform}: 入库 {len(posts)} 条")
            total += len(posts)

        print(f"本次合计入库：{total} 条")

        # 所有平台都失败时，以非零状态退出，方便以后 cron 识别。
        if total == 0:
            raise SystemExit("错误：所有平台均抓取失败")

    finally:
        conn.close()


if __name__ == "__main__":
    main()