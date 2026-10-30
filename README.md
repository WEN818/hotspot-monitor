# 跨平台热点监控系统

基于 Hermes Agent、OpenCLI、SQLite、DeepSeek 和 Streamlit 的课程项目。

用户可以用一句自然语言触发热点抓取与分析，并在本地网页看板中查看最新热点和中文分析报告。

## 核心功能

- 支持 HackerNews、GitHub Trending、掘金三个公开热点源；
- 单个平台失败时记录错误，不阻断其他平台；
- 使用 SQLite 保存多批次热点数据；
- 使用 DeepSeek 生成主题聚类、中文摘要和跨平台共振判断；
- 支持 GLM 免费模型调试；
- Streamlit 提供“今日热点”和“分析摘要”两页；
- 支持 Hermes 自然语言触发；
- 支持 cron 自动执行抓取与分析。

## 系统架构

自然语言交互链路：

    用户自然语言
      → Hermes Agent / hotspot-monitor skill
      → fetch.py
      → OpenCLI
      → SQLite hotspots.db
      → analyze.py
      → DeepSeek API
      → analysis/latest.md
      → Streamlit 看板

定时任务链路：

    cron
      → scripts/run_pipeline.sh
      → fetch.py
      → analyze.py
      → Streamlit 读取最新结果

定时链路不经过 Hermes，以减少额外模型调用并提高稳定性。

## 数据源与字段映射

| 平台 | OpenCLI 命令 | 标题字段 | 热度字段 |
| --- | --- | --- | --- |
| HackerNews | `opencli hackernews top` | `title` | `score` |
| 掘金 | `opencli juejin hot` | `title` | `hot_rank` |
| GitHub Trending | `opencli github-trending repos` | `repo` | `starsSince` |

不同平台的热度含义不同，不应直接视为同一种指标。

## 项目结构

    hotspot-monitor/
    ├── fetch.py                 # 抓取并写入 SQLite
    ├── analyze.py               # 分析最新批次并生成报告
    ├── app.py                   # Streamlit 两页看板
    ├── requirements.txt         # Python 依赖
    ├── .env.example             # 配置模板，不含真实密钥
    ├── analysis/
    │   └── latest.md            # 最新分析报告
    ├── scripts/
    │   └── run_pipeline.sh      # 定时任务包装脚本
    ├── skills/
    │   └── hotspot-monitor/
    │       └── SKILL.md         # Hermes 监控技能
    ├── notes/                   # 技术决策与公开抓取样例
    └── hotspots.db              # 本地数据库，不提交 Git

## 环境要求

- macOS；
- Python 3.14；
- Node.js 与 npm；
- OpenCLI；
- Hermes Agent；
- DeepSeek API Key；
- GLM API Key，仅免费调试时需要。

## 安装

在项目根目录执行：

    python3 -m venv venv
    source venv/bin/activate
    python -m pip install -r requirements.txt

安装并检查 OpenCLI：

    npm install -g @jackwener/opencli
    opencli doctor

Hermes Agent 按其官方文档安装，不需要重复安装项目 Python 依赖。

## 配置

复制配置模板：

    cp .env.example .env

编辑 `.env`，填入自己的密钥：

    AI_PROVIDER=deepseek

    GLM_API_KEY=your_glm_api_key
    GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
    GLM_MODEL=glm-4.7-flash

    DEEPSEEK_API_KEY=your_deepseek_api_key
    DEEPSEEK_BASE_URL=https://api.deepseek.com
    DEEPSEEK_MODEL=deepseek-flash

限制密钥文件权限：

    chmod 600 .env

`.env`、数据库和日志均已加入 `.gitignore`，不得提交真实密钥。

## 手动运行

抓取三个平台并写入数据库：

    python fetch.py

使用 DeepSeek 分析最新批次：

    python analyze.py

如需使用 GLM 免费调试，在 `.env` 中设置：

    AI_PROVIDER=glm

启动看板：

    python -m streamlit run app.py

停止看板时，在终端按 `Control + C`。

## Hermes 自然语言触发

先用 `hermes model` 配置 DeepSeek，然后安装项目 skill：

    mkdir -p "$HOME/.hermes/skills/course/hotspot-monitor"

    cp skills/hotspot-monitor/SKILL.md \
       "$HOME/.hermes/skills/course/hotspot-monitor/SKILL.md"

检查 skill：

    hermes skills list | grep hotspot-monitor

执行完整监控：

    hermes chat -q "/hotspot-monitor 帮我抓取最新热点，并生成今天的分析报告"

skill 只允许调用固定的 `fetch.py` 和 `analyze.py`，不允许模型生成任意 shell 命令。

## 定时执行

先手动验证：

    /bin/zsh scripts/run_pipeline.sh
    tail -n 35 logs/pipeline.log

正式每天 09:00 执行时，可添加 cron：

    0 9 * * * /bin/zsh /Users/keira/CODE_CODE/hotspot-monitor/scripts/run_pipeline.sh

cron 使用绝对路径，不依赖当前终端的虚拟环境。macOS 睡眠或合盖可能阻止任务按时执行。

不再使用定时任务时，应从 crontab 中移除对应条目，避免继续抓取和调用 API。

## 安全与容错

- 不使用 `sudo pip`；
- Python 依赖只安装在项目 `venv/`；
- 不提交 `.env`、数据库、日志或个人学习笔记；
- 单个平台抓取失败不会中断其他平台；
- 所有平台失败时，`fetch.py` 返回非零退出码；
- 模型调用失败不会覆盖上一次成功报告；
- 同一轮抓取共享一个 `fetched_at`，方便读取完整批次。

## 当前限制与后续优化

- 当前只实现三个无需登录的主力源；
- 知乎和 B 站保留为后续扩展；
- 暂不提供历史趋势图；
- 不同运行批次允许出现相同热点，用于保留历史记录；
- DeepSeek 报告风格可以进一步优化提示词，但不影响核心流程。