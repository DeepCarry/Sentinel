#!/bin/bash

# Sentinel 后台启动脚本
# 使用方法: ./start.sh

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 未找到虚拟环境 .venv"
    exit 1
fi

# 激活虚拟环境并启动
source .venv/bin/activate

# 检查端口是否被占用（最常见的“启动多次/断点不命中”根因）
if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "错误: 端口 8000 已被占用，拒绝启动（避免启动多次/请求打到别的进程）。"
    echo ""
    echo "占用详情:"
    lsof -nP -iTCP:8000 -sTCP:LISTEN | sed 's/^/  /'
    echo ""
    echo "建议：先执行 ./stop.sh（或手动 kill 对应 PID），确认端口释放后再启动。"
    exit 1
fi

# 检查是否已经在运行（兜底）
if pgrep -f "python.*main_prod.py" > /dev/null; then
    echo "警告: Sentinel 已经在运行中 (main_prod.py)"
    echo "进程ID: $(pgrep -f 'python.*main_prod.py')"
    exit 1
fi

# 确保日志目录存在
mkdir -p logs

# 使用 nohup 在后台启动，输出重定向到日志文件
echo "正在启动 Sentinel..."
nohup .venv/bin/python main_prod.py > logs/startup.log 2>&1 &

# 获取进程ID
PID=$!
echo "Sentinel 已启动，进程ID: $PID"
echo "日志文件: logs/sentinel.log"
echo "启动日志: logs/startup.log"
echo ""
echo "使用以下命令查看状态:"
echo "  ./status.sh    - 查看运行状态"
echo "  ./logs.sh      - 查看实时日志"
echo "  ./stop.sh      - 停止服务"

# 等待一下，检查进程是否成功启动
sleep 2
if ps -p $PID > /dev/null; then
    echo "✓ 启动成功！"
    echo ""
    echo "🌍 Web 管理后台: http://localhost:8000"
    echo ""
else
    echo "✗ 启动失败，请查看 logs/startup.log 了解详情"
    exit 1
fi

