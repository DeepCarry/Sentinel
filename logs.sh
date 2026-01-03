#!/bin/bash

# Sentinel 日志查看脚本
# 使用方法: 
#   ./logs.sh          - 查看最后50行日志
#   ./logs.sh -f       - 实时跟踪日志（类似 tail -f）
#   ./logs.sh -n 100   - 查看最后100行
#   ./logs.sh -e       - 只显示错误日志

LOG_FILE="logs/sentinel.log"

# 检查日志文件是否存在
if [ ! -f "$LOG_FILE" ]; then
    echo "错误: 日志文件不存在: $LOG_FILE"
    exit 1
fi

# 解析参数
FOLLOW=false
LINES=50
ERROR_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -e|--error)
            ERROR_ONLY=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [-f|--follow] [-n|--lines N] [-e|--error]"
            exit 1
            ;;
    esac
done

if [ "$FOLLOW" = true ]; then
    # 实时跟踪日志
    echo "正在实时跟踪日志 (按 Ctrl+C 退出)..."
    echo "=========================================="
    tail -f "$LOG_FILE"
elif [ "$ERROR_ONLY" = true ]; then
    # 只显示错误和警告
    echo "显示错误和警告日志:"
    echo "=========================================="
    grep -E "\[(ERROR|WARNING|CRITICAL)\]" "$LOG_FILE" | tail -n "$LINES"
else
    # 显示最后N行
    echo "最后 $LINES 行日志:"
    echo "=========================================="
    tail -n "$LINES" "$LOG_FILE"
fi

