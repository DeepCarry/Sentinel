# Sentinel (哨兵)

Sentinel 是一个垂直于区块链加密货币合规与安全领域的自动化情报监测系统。旨在帮助用户从海量公开快讯中自动筛选高价值信息，第一时间发现洗钱、被盗、监管政策变动等潜在风险信号，并提供实时预警、周期性报告及可视化管理。

## 快速开始

### 启动服务

```bash
./scripts/start.sh
```

### 查看状态

```bash
./scripts/status.sh
```

### 查看日志

```bash
# 查看最后 50 行日志
./scripts/logs.sh

# 实时跟踪日志
./scripts/logs.sh -f

# 只显示错误日志
./scripts/logs.sh -e
```

### 停止服务

```bash
./scripts/stop.sh
```

### Web 管理后台

服务启动后，访问 http://localhost:8000 查看管理后台。

- 仪表盘: 展示“今日抓取 / 今日匹配”和“总抓取数 / 总匹配数”等核心指标。
- 导航菜单: 通过“舆情监控”分组访问“快讯列表”和“报表归档”。

## 项目结构

```
Sentinel/
├── README.md              # 项目说明
├── requirements.txt       # Python 依赖
├── main.py               # 开发环境入口
├── main_prod.py          # 生产环境入口
├── docs/                 # 📚 文档目录
│   ├── DEV.md           # 开发文档
│   ├── PRD.md           # 产品需求文档
│   └── RUN.md           # 运行指南
├── scripts/              # 🔧 脚本目录
│   ├── start.sh         # 启动脚本
│   ├── stop.sh          # 停止脚本
│   ├── status.sh        # 状态检查脚本
│   └── logs.sh          # 日志查看脚本
├── tests/                # 🧪 测试目录
│   ├── test_aicoin.py
│   ├── test_blockbeats.py
│   ├── test_refactor.py
│   └── test_report.py
└── src/                  # 💻 源代码目录
    ├── config.py         # 配置管理
    ├── models.py         # 数据模型
    ├── database.py       # 数据库操作
    ├── filter.py         # 关键词过滤
    ├── notifier.py       # 消息通知
    ├── report.py         # 报表生成
    ├── scheduler_service.py  # 任务调度
    ├── scrapers/         # 爬虫模块
    │   ├── base.py
    │   ├── aicoin.py
    │   └── blockbeats.py
    └── web/              # Web 后台
        ├── app.py
        ├── routes.py
        ├── static/
        └── templates/
```

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_aicoin.py
```

## 文档

- [开发文档](docs/DEV.md) - 技术架构和开发指南
- [产品需求文档](docs/PRD.md) - 产品功能和需求说明
- [运行指南](docs/RUN.md) - 后台运行和故障排查

## 技术栈

- **Python 3.10+**
- **FastAPI** - Web 框架
- **SQLite + SQLModel** - 数据库
- **Playwright** - 网页爬虫
- **APScheduler** - 任务调度
- **Feishu Webhook** - 消息通知
