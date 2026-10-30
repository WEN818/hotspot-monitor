---
name: hotspot-monitor
description: 抓取并分析跨平台技术热点。当用户要求更新热点、抓取热点、分析现有热点、生成热点报告或执行完整热点监控时使用。
---

# 跨平台热点监控

## 项目位置

项目目录：

`/Users/keira/CODE_CODE/hotspot-monitor`

只允许使用项目原有的 Python：

`/Users/keira/CODE_CODE/hotspot-monitor/venv/bin/python`

## 允许执行的命令

抓取热点：

    /Users/keira/CODE_CODE/hotspot-monitor/venv/bin/python /Users/keira/CODE_CODE/hotspot-monitor/fetch.py

分析最新一批热点：

    /Users/keira/CODE_CODE/hotspot-monitor/venv/bin/python /Users/keira/CODE_CODE/hotspot-monitor/analyze.py

## 任务选择

1. 用户只要求抓取或更新数据：只运行 `fetch.py`。
2. 用户只要求分析现有数据：只运行 `analyze.py`。
3. 用户要求抓取并分析、更新报告或执行完整监控：先运行 `fetch.py`，成功后再运行 `analyze.py`。
4. 如果 `fetch.py` 返回非零退出码，停止后续分析并如实报告错误。

## 安全边界

- 只能执行上面列出的固定命令，不得自行添加其他 shell 命令。
- 不读取、打印或复制 `.env`、API Key、Cookie 和浏览器登录信息。
- 不安装或卸载软件，不删除文件，不修改 Git 或 cron 配置。
- 不自动启动 Streamlit，只告诉用户报告位于 `analysis/latest.md`。
- 单个平台失败但脚本整体成功时，如实说明成功和失败的平台。

## 完成后的回复

简要说明：

1. 实际执行了哪些脚本；
2. 各平台抓取是否成功及入库条数；
3. 分析报告是否生成；
4. 提醒用户刷新 Streamlit 看板。
