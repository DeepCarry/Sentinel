#!/bin/bash

# Sentinel 停止脚本
# 使用方法: ./stop.sh

YES=false
PORT_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes)
            YES=true
            shift
            ;;
        -p|--port)
            PORT_ONLY=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [-y|--yes] [-p|--port]"
            exit 1
            ;;
    esac
done

echo "正在查找 Sentinel 进程..."

# 查找所有相关的 Python 进程
PIDS_MAIN_PROD=$(pgrep -f "python.*main_prod.py" 2>/dev/null || true)
PIDS_PORT=$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)

if [ "$PORT_ONLY" = true ]; then
    PIDS="$PIDS_PORT"
else
    PIDS="$PIDS_MAIN_PROD"$'\n'"$PIDS_PORT"
fi

# 去重/去空
PIDS=$(echo "$PIDS" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')

if [ -z "$PIDS" ]; then
    echo "Sentinel 未在运行"
    exit 0
fi

echo "找到以下进程:"
ps -p $PIDS -o pid,etime,cmd 2>/dev/null || true

echo ""
if [ "$YES" != true ]; then
    # 非交互环境默认 YES（避免脚本卡住）
    if [ ! -t 0 ]; then
        YES=true
    else
        read -p "确认要停止这些进程吗? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            YES=true
        fi
    fi
fi

if [ "$YES" = true ]; then
    echo "正在停止进程..."
    kill $PIDS 2>/dev/null || true
    
    # 等待进程结束
    sleep 2
    
    # 如果还在运行，强制杀死（再次从端口确认，避免遗漏）
    REMAINING=$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)
    if [ ! -z "$REMAINING" ]; then
        echo "强制停止仍占用 8000 的进程: $REMAINING"
        kill -9 $REMAINING 2>/dev/null || true
    fi
    
    echo "✓ Sentinel 已停止"
else
    echo "已取消"
fi

