#!/bin/bash

# Sentinel 状态检查脚本
# 使用方法: ./status.sh

echo "=== Sentinel 运行状态 ==="
echo ""

# 1. 检查进程
echo "📌 进程状态:"
PIDS_MAIN_PROD=$(pgrep -f "python.*main_prod.py" 2>/dev/null || true)
PIDS_UVICORN=$(pgrep -f "uvicorn.*src\\.web\\.app:app" 2>/dev/null || true)
PIDS=$(echo "$PIDS_MAIN_PROD"$'\n'"$PIDS_UVICORN" | sed '/^$/d' | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')
if [ -z "$PIDS" ]; then
    echo "  ✗ 未运行"
    PROCESS_RUNNING=false
else
    echo "  ✓ 正在运行"
    PROCESS_RUNNING=true
    echo "  进程ID: $PIDS"
    echo ""
    echo "  进程详情:"
    ps -p $PIDS -o pid,etime,%cpu,%mem,cmd 2>/dev/null | tail -n +2 | sed 's/^/    /'
fi

echo ""

# 2. 检查端口
echo "📌 端口状态 (8000):"
LISTENERS=$(lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null || true)
if [ ! -z "$LISTENERS" ]; then
    echo "  ✓ 端口 8000 正在监听"
    echo ""
    echo "  端口详情:"
    echo "$LISTENERS" | tail -n +2 | sed 's/^/    /'
    PORT_LISTENING=true

    # 多实例提示：出现多行 listener 时，调试断点很容易“不命中”
    LISTENER_COUNT=$(echo "$LISTENERS" | tail -n +2 | wc -l | tr -d ' ')
    if [ "$LISTENER_COUNT" -gt 1 ]; then
        echo ""
        echo "  ⚠ 检测到多个进程同时监听 8000（$LISTENER_COUNT 个）。"
        echo "    这会导致 Postman/浏览器请求随机命中其中一个进程，出现“断点不命中”。"
        echo "    建议先执行: ./scripts/stop.sh --yes"
    fi
else
    echo "  ✗ 端口 8000 未监听"
    PORT_LISTENING=false
fi

echo ""

# 3. 检查日志文件
echo "📌 日志文件:"
# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
LOG_FILE="$SCRIPT_DIR/logs/sentinel.log"
LEGACY_LOG_FILE="$SCRIPT_DIR/logs/startup.log"
if [ ! -f "$LOG_FILE" ] && [ -f "$LEGACY_LOG_FILE" ]; then
    LOG_FILE="$LEGACY_LOG_FILE"
fi
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(ls -lh "$LOG_FILE" | awk '{print $5}')
    LOG_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
    LAST_LOG_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LOG_FILE" 2>/dev/null || stat -c "%y" "$LOG_FILE" 2>/dev/null | cut -d'.' -f1)
    
    echo "  ✓ 日志文件存在"
    echo "    路径: $LOG_FILE"
    echo "    大小: $LOG_SIZE"
    echo "    行数: $LOG_LINES"
    echo "    最后修改: $LAST_LOG_TIME"
    
    # 检查最近的日志时间（判断是否在活跃写入）
    if [ "$PROCESS_RUNNING" = true ]; then
        RECENT_LOG=$(tail -n 1 "$LOG_FILE" 2>/dev/null | grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
        if [ ! -z "$RECENT_LOG" ]; then
            echo "    最新日志时间: $RECENT_LOG"
        fi
    fi
else
    echo "  ✗ 日志文件不存在"
fi

echo ""

# 4. 检查 HTTP 服务
echo "📌 HTTP 服务:"
if [ "$PORT_LISTENING" = true ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "307" ]; then
        echo "  ✓ HTTP 服务响应正常 (状态码: $HTTP_CODE)"
    else
        echo "  ⚠ HTTP 服务无响应 (状态码: $HTTP_CODE)"
    fi
else
    echo "  ✗ HTTP 服务不可用"
fi

echo ""

# 5. 总结
echo "=== 总结 ==="
if [ "$PROCESS_RUNNING" = true ] && [ "$PORT_LISTENING" = true ]; then
    echo "✓ Sentinel 运行正常"
    exit 0
else
    echo "✗ Sentinel 运行异常"
    exit 1
fi

