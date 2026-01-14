# Sentinel 后台运行指南

## 📋 快速开始

### 启动服务（后台运行）

```bash
./start.sh
```

服务将在后台运行，即使关闭终端或 Cursor IDE 也会继续运行。

## 🧩 断点调试（为什么点“筛选”不进断点？）

如果你是用 `uvicorn ... --reload` 或 `python main.py`（其中 `reload=True`）启动 Web 服务，Uvicorn 会启动 **reloader 进程 + server 子进程**。浏览器请求实际由 **server 子进程**处理；如果调试器没有 attach 到子进程，你在 `src/web/routes.py` 里打的断点就不会命中。

推荐做法：

- **方式 A（最稳）**：调试时先关闭 reload。直接用 Cursor/VSCode 的 Run and Debug 运行 `.vscode/launch.json` 里的 `Sentinel Web (FastAPI, no reload) - breakpoints stable`。
- **方式 B（仍想热重载）**：用 `.vscode/launch.json` 里的 `Sentinel Web (FastAPI, reload + subprocess) - breakpoints stable`（已开启 `subProcess: true`）。

注意：启动调试前，确保本机 8000 端口没有被其他 `uvicorn`/`main_prod.py` 占用（先停掉 `./start.sh` 或正在运行的 `uvicorn`）。

### 查看运行状态

```bash
./status.sh
```

这会显示：

- ✅ 进程是否运行
- ✅ 端口 8000 是否监听
- ✅ 日志文件状态
- ✅ HTTP 服务是否响应

### 查看日志

```bash
# 查看最后 50 行日志
./logs.sh

# 实时跟踪日志（类似 tail -f）
./logs.sh -f

# 查看最后 100 行
./logs.sh -n 100

# 只显示错误和警告
./logs.sh -e
```

### 停止服务

```bash
./stop.sh
```

## 📁 日志文件位置

- **应用日志**: `logs/sentinel.log` - 所有应用日志（自动轮转，最大 5MB，保留 3 个备份）
- **启动日志**: `logs/startup.log` - 启动时的标准输出和错误

## 🔍 手动检查方法

### 1. 检查进程是否运行

```bash
# 查找进程
pgrep -f "python.*main_prod.py"

# 查看进程详情
ps aux | grep "main_prod.py"
```

### 2. 检查端口是否监听

```bash
# macOS/Linux
lsof -i :8000

# 或使用 netstat
netstat -an | grep 8000
```

### 3. 测试 HTTP 服务

```bash
# 检查服务是否响应
curl http://localhost:8000/

# 或在浏览器打开
open http://localhost:8000
```

### 4. 查看日志文件

```bash
# 查看完整日志
cat logs/sentinel.log

# 查看最后 100 行
tail -n 100 logs/sentinel.log

# 实时跟踪日志
tail -f logs/sentinel.log

# 搜索错误
grep -i error logs/sentinel.log

# 搜索特定关键词
grep "关键词" logs/sentinel.log
```

## 🛠️ 故障排查

### 问题：服务启动失败

1. 查看启动日志：

   ```bash
   cat logs/startup.log
   ```
2. 检查虚拟环境是否正确：

   ```bash
   source .venv/bin/activate
   python --version
   ```
3. 检查依赖是否安装：

   ```bash
   pip list
   ```

### 问题：服务意外停止

1. 检查日志中的错误信息：

   ```bash
   ./logs.sh -e
   ```
2. 检查系统资源：

   ```bash
   # 查看内存使用
   free -h  # Linux
   vm_stat  # macOS

   # 查看磁盘空间
   df -h
   ```

### 问题：端口被占用

如果端口 8000 已被占用，可以：

1. 查找占用端口的进程：

   ```bash
   lsof -i :8000
   ```
2. 修改端口（编辑 `main_prod.py`）：

   ```python
   uvicorn.run(..., port=8001)  # 改为其他端口
   ```

## 📊 监控建议

### 定期检查

建议定期运行 `./status.sh` 检查服务状态，或设置定时任务：

```bash
# 添加到 crontab（每小时检查一次）
0 * * * * cd /path/to/sentinel && ./status.sh >> logs/status_check.log 2>&1
```

### 日志轮转

日志文件会自动轮转：

- 单个日志文件最大 5MB
- 保留最近 3 个备份文件
- 备份文件名：`sentinel.log.1`, `sentinel.log.2`, `sentinel.log.3`

## 🔄 重启服务

```bash
./stop.sh
sleep 2
./start.sh
```

## 💡 提示

- 使用 `screen` 或 `tmux` 可以更方便地管理后台进程
- 生产环境建议使用 `systemd` 或 `supervisor` 进行进程管理
- 定期备份 `data/sentinel.db` 数据库文件
