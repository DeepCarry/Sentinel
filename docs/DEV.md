# Sentinel (哨兵) 系统技术架构方案

**版本:** v1.2
**日期:** 2026-01-21

**关联文档:** PRD.md

---

## 1. 技术栈选型 (Tech Stack)

### 1.1 核心语言
* **Python 3.10+**: 选择 Python 是因其在数据抓取、文本处理和自动化任务领域的丰富生态。

### 1.2 关键组件

| 组件类型 | 选型 | 理由 |
| :--- | :--- | :--- |
| **网页爬虫 (Crawler)** | **Playwright** | 能够模拟真实浏览器行为 (Headless Chrome)，有效应对动态渲染 (SPA) 和反爬防护。支持 AICoin 和 BlockBeats 的抓取。 |
| **Web 框架 (Web Framework)** | **FastAPI** | [v1.1新增] 高性能、易用的 Python Web 框架，用于构建管理后台和 API。原生支持 Pydantic (与 SQLModel 完美契合)。 |
| **Web 服务器 (Server)** | **Uvicorn** | [v1.1新增] 用于运行 FastAPI 应用的 ASGI 服务器。 |
| **模板引擎 (Template)** | **Jinja2** | [v1.1新增] 用于服务端渲染管理后台的 HTML 页面，保持部署架构的轻量化（无需独立前端构建）。 |
| **任务调度 (Scheduler)** | **APScheduler** | 轻量级进程内调度器。支持 Cron 表达式和 Interval，易于集成在主进程中。 |
| **数据库 (Database)** | **SQLite + SQLModel** | 单文件存储，部署极简。SQLModel 结合了 Pydantic 和 SQLAlchemy，提供类型安全的数据库操作。 |
| **通知服务 (Notification)** | **Feishu (Lark) Webhook** | 飞书机器人接口友好，支持富文本卡片 (Interactive Cards)。 |

---

## 2. 系统架构设计 (Architecture)

### 2.1 逻辑流程图

```mermaid
graph TD
    subgraph Data Acquisition [数据采集层]
        A1[AICoin Source] -->|Playwright| B(Scraper Dispatcher)
        A2[BlockBeats Source] -->|Playwright/RSS| B
        B -->|Normalize| C[Raw News Object]
    end

    subgraph Processing [处理层]
        C --> D{去重检查 (Deduplication)}
        D -->|New Item| S1[Update Daily Stats]
        D -->|Exists| E[Discard]
        
        S1 --> F{关键词过滤 (Filtering)}
        F -->|Noise| E
        F -->|Match| G[Risk Tagging]
    end

    subgraph Storage [存储层]
        G --> H[(SQLite Database)]
        H -->|Table: news_flash| I[High Risk News]
        H -->|Table: daily_stats| S2[Scan Stats]
        H -->|Table: scan_record| S3[Scan History ID]
        H -->|Table: reports| R[Report Archives]
    end

    subgraph Notification [通知层]
        G --> J[Alert Manager]
        J -->|Format| K[Feishu Card]
        K -->|Webhook| L[Feishu App]
        N[Report Generator] -->|Send| L
    end

    subgraph Web Dashboard [管理后台 v1.1]
        User((Admin)) -->|Browser| W[FastAPI Server]
        W -->|Query News| H
        W -->|Query Stats| S2
        W -->|Render| UI[News List / Reports]
    end

    subgraph Scheduling [调度层]
        S[APScheduler] -->|Trigger| B
        S -->|Trigger| N
    end
```

### 2.2 目录结构规划

```
sentinel/
├── src/
│   ├── __init__.py
│   ├── config.py         # 配置文件 (URLs, Keys, Interval)
│   ├── models.py         # 数据库模型 (SQLModel)
│   ├── database.py       # 数据库连接与会话管理
│   │
│   ├── scrapers/         # [新增] 爬虫模块包
│   │   ├── __init__.py   # 包含 BaseScraper 基类
│   │   ├── aicoin.py     # AICoin 具体实现
│   │   └── blockbeats.py # BlockBeats 具体实现
│   │
│   ├── web/              # [新增] Web 后台模块
│   │   ├── __init__.py
│   │   ├── app.py        # FastAPI App 入口
│   │   ├── routes.py     # 路由定义
│   │   ├── templates/    # Jinja2 HTML 模板
│   │   ├── static/       # CSS/JS 静态资源
│   │   └── utils.py      # [新增] Web通用工具函数
│   │
│   ├── filter.py         # 过滤器逻辑
│   ├── notifier.py       # 消息通知模块
│   ├── report.py         # 报表生成模块
│   └── main.py           # 命令行入口 & 调度器启动
│
├── data/
│   └── sentinel.db       # SQLite 数据库
├── logs/
├── requirements.txt
├── .env
├── README.md
├── PRD.md
└── DEV.md
```

---

## 3. 关键模块详细设计

### 3.1 数据库设计 (Schema)

#### 表名: `news_flash` (高危快讯表)

| 字段名 | 类型 | 描述 | 更新点 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | 主键 | |
| `source` | String | **来源标识** (e.g., 'aicoin', 'blockbeats') | [v1.1新增] |
| `source_id` | String | 来源原始ID (或 Hash) | |
| `title` | String | 新闻标题 | |
| `content` | Text | 新闻正文 | |
| `url` | String | 原始链接 | |
| `pub_time` | DateTime | 发布时间 | |
| `created_at` | DateTime | 抓取入库时间 | |
| `updated_at` | DateTime | 系统更新时间 | [v1.1新增] |
| `tags` | String | 标签 (e.g., "安全,监管") | |
| `is_pushed` | Boolean | 是否已通过Webhook推送 | [v1.0保留] |
| `in_daily_report` | Boolean | 是否已计入日报 | [v1.0保留] |
| `in_weekly_report` | Boolean | 是否已计入周报 | [v1.0保留] |

#### 表名: `reports` (报表归档表) [v1.1新增]

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | Integer | 主键 |
| `type` | String | 报表类型 ('daily', 'weekly') |
| `period_start` | DateTime | 统计开始时间 |
| `period_end` | DateTime | 统计结束时间 |
| `content_html` | Text | 报表内容 (HTML格式，用于回显) |
| `created_at` | DateTime | 生成时间 |

#### 表名: `daily_stats` (每日统计表) [v1.1优化]

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | Integer | 主键 |
| `date` | Date | 统计日期 (unique) |
| `scanned_count` | Integer | 当日经过去重的原始抓取总数 |
| `updated_at` | DateTime | 最后更新时间 |

#### 表名: `scan_record` (扫描历史表) [v1.1优化]

> 用于全量去重，确保即使被丢弃的噪音数据也不会被重复计数。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | Integer | 主键 |
| `source_id` | String | 来源原始ID (索引) |
| `created_at` | DateTime | 扫描时间 |

### 3.2 爬虫扩展策略 (Scraper Strategy)

采用 **策略模式 (Strategy Pattern)** 组织爬虫：
1.  定义 `BaseScraper` 抽象基类，规范 `run()` 方法和返回数据结构。
2.  `AICoinScraper`: 继承基类，沿用 Playwright 逻辑。
3.  `BlockBeatsScraper`: 继承基类，针对 BlockBeats DOM 结构编写解析逻辑。
4.  **调度**: 调度器遍历所有注册的 Scraper 实例并发或串行执行。

### 3.3 管理后台设计 (Web Dashboard)

> v1.2 更新: 仪表盘增加“总抓取数 / 总匹配数”累计指标（分别来自 `scan_record` 与 `newsflash`），左侧导航调整为“舆情监控”分组，包含“快讯列表”和“报表归档”二级菜单。

基于 FastAPI + Jinja2 实现服务端渲染：
*   **GET /**: 仪表盘，显示**今日抓取数量**（读取 daily_stats）、最新几条高危预警。
*   **GET /news**: 快讯列表页。支持 Query 参数筛选 (`?source=blockbeats&tag=安全`)。
*   **GET /news/{id}**: 快讯详情页。
*   **GET /reports**: 历史日报/周报列表。
*   **GET /reports/{id}**: 渲染某份历史报表的 HTML。

### 3.4 调度策略 (Scheduling)

*   **配置化**: 在 `config.py` 中统一配置 `CRAWL_INTERVAL_MINUTES` (默认 5 分钟)。
*   **Web 服务共存**:
    *   方案 A: `main.py` 启动时，同时启动 APScheduler 和 Uvicorn Server (需注意多进程/线程模型)。
    *   方案 B (推荐): 使用 `FastAPI` 的 `lifespan` 事件在启动时初始化 Scheduler，确保并在同一个 Event Loop 或独立线程中运行。

---

## 4. 部署与环境

*   **新增依赖**: `fastapi`, `uvicorn`, `jinja2`, `python-multipart` (如果需要表单)。
*   **启动方式**: 统一通过 `python src/main.py` 启动 (内部调用 uvicorn.run) 或直接使用 `uvicorn src.web.app:app` (需处理 Scheduler 挂载)。

---

## 5. 开发步骤 (Milestones v1.1)

1.  **Refactor**: 重构项目目录，建立 `scrapers/` 和 `web/` 包结构。
2.  **Database**: 更新 `models.py`，添加 `source` 字段和 `Report` 模型；执行数据库迁移（或重建）。
3.  **Scraper**: 封装 `BaseScraper`，迁移 AICoin 逻辑，实现 BlockBeats 逻辑。
4.  **Web Backend**: 开发 FastAPI 应用，实现数据查询 API。
5.  **Web Frontend**: 使用 Jinja2 + 简单的 CSS 框架 (如 MVP.css 或 Bootstrap CDN) 开发列表和详情页面。
6.  **Report**: 更新报表生成逻辑，生成后同时存入 `reports` 表。
7.  **Integration**: 整合 Scheduler 与 Web Server 的启动流程。
8.  **Testing**: 验证多源抓取去重、Web 页面显示及历史报表查看。
9.  **Stats Optimization**: [v1.1优化] 实现 `DailyStats` 和 `ScanRecord` 逻辑，确保“今日抓取”数据准确且去重。
