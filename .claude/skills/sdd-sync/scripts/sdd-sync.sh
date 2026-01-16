#!/bin/bash
# 核心同步逻辑：确保双仓一致性

# 检查参数数量
if [ $# -lt 1 ]; then
    echo "用法: $0 <command> [args...]"
    echo "可用命令:"
    echo "  start-change <CHANGE_ID>    - 开始新变更，创建feature分支"
    echo "  sync-main                    - 同步main分支"
    echo ""
    echo "示例:"
    echo "  $0 start-change ABC-123"
    echo "  $0 sync-main"
    exit 1
fi

command="$1"

case "$command" in
    "start-change")
        if [ $# -ne 2 ]; then
            echo "用法: $0 start-change <CHANGE_ID>"
            echo "示例: $0 start-change ABC-123"
            exit 1
        fi
        CHANGE_ID="$2"
        git checkout main
        git pull github main
        git checkout -b "feature-${CHANGE_ID}"
        git push origin "feature-${CHANGE_ID}"
        git push github "feature-${CHANGE_ID}"
        echo "已创建并推送feature分支: feature-${CHANGE_ID}"
        ;;
    "sync-main")
        git checkout main
        git pull github main
        git push origin main
        echo "Main branch synchronized across both remotes."
        ;;
    *)
        echo "未知命令: $command"
        echo "可用命令: start-change, sync-main"
        exit 1
        ;;
esac