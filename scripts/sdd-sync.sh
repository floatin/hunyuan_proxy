#!/bin/bash

# SDD-Sync Script
# 规范驱动开发 (SDD) 与双仓同步管家

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_msg() {
    echo -e "${2}${1}${NC}"
}

# 显示帮助信息
show_help() {
    echo "Usage: $0 {init|checkpoint|finalize|sync-main}"
    echo ""
    echo "Commands:"
    echo "  init        Initialize project with dual remotes"
    echo "  checkpoint  Create a checkpoint snapshot"
    echo "  finalize    Finalize change and prepare for PR"
    echo "  sync-main   Sync main branch after merge"
}

# 初始化项目
init_project() {
    print_msg "Initializing SDD project..." "$BLUE"
    # 这里可以添加初始化逻辑
    print_msg "Project initialized successfully" "$GREEN"
}

# 创建检查点
checkpoint() {
    print_msg "Creating checkpoint..." "$BLUE"
    
    # 获取当前时间戳
    timestamp=$(date +"%Y%m%d-%H%M%S")
    tag_name="ckpt-${timestamp}"
    
    # 创建提交
    git add .
    git commit -m "Checkpoint: ${timestamp}" || print_msg "No changes to commit" "$YELLOW"
    
    # 创建标签
    git tag -a "$tag_name" -m "Checkpoint at ${timestamp}"
    print_msg "Created tag: $tag_name" "$GREEN"
    
    # 仅推送到 origin (本地 Gitea)
    git push origin HEAD
    git push origin "$tag_name"
    
    print_msg "Checkpoint completed: $tag_name" "$GREEN"
    print_msg "Pushed to origin only (local Gitea)" "$YELLOW"
}

# 完成变更
finalize() {
    print_msg "Finalizing change..." "$BLUE"
    # 同步到 upstream (GitHub)
    git push upstream HEAD
    print_msg "Change finalized and pushed to upstream" "$GREEN"
}

# 同步主分支
sync_main() {
    print_msg "Syncing main branch..." "$BLUE"
    git checkout main
    git pull upstream main
    git push origin main
    print_msg "Main branch synced successfully" "$GREEN"
}

# 主逻辑
case "$1" in
    init)
        init_project
        ;;
    checkpoint)
        checkpoint
        ;;
    finalize)
        finalize
        ;;
    sync-main)
        sync_main
        ;;
    *)
        show_help
        exit 1
        ;;
esac