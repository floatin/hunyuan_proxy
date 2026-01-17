#!/bin/bash

# SDD-Sync Script - 统一的Git操作封装工具
# 提供双仓(Gitea/GitHub)同步的标准化命令集
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
    echo "Usage: $0 {init|checkpoint|finalize|sync-main|push-main|start-change}"
    echo ""
    echo "Commands:"
    echo "  init           Initialize project with dual remotes"
    echo "  checkpoint     Create a checkpoint snapshot (local Gitea only)"
    echo "  finalize       Finalize change and push to GitHub"
    echo "  sync-main      Sync main branch after merge"
    echo "  push-main      Push approved code to main branch"
    echo "  start-change   Start new change, create feature branch"
}

# 统一推送函数（整合原sdd-push.sh功能）
push_changes() {
    local branch="$1"
    local type="$2"
    local message="$3"
    
    print_msg "Pushing changes to both remotes..." "$BLUE"
    
    git add -A
    git commit -m "$type:$message"
    git push origin "$branch"      # 本地 Gitea
    git push upstream "$branch"   # GitHub
    
    print_msg "Changes pushed successfully to both remotes" "$GREEN"
}

# 初始化项目
init_project() {
    print_msg "Initializing SDD project with dual remotes..." "$BLUE"
    
    # 双远端配置
    print_msg "Please ensure remotes are configured:" "$YELLOW"
    print_msg "  git remote add origin <local_gitea_url>" "$NC"
    print_msg "  git remote add upstream <github_url>" "$NC"
    
    print_msg "Project initialized successfully" "$GREEN"
}

# 创建检查点 - 仅在本地 Gitea (origin) 存档
checkpoint() {
    print_msg "Creating checkpoint (local Gitea only)..." "$BLUE"
    
    # 获取当前时间戳
    timestamp=$(date +"%Y%m%d-%H%M%S")
    tag_name="ckpt-${timestamp}"
    
    # 创建提交
    git add .
    git commit -m "Checkpoint: ${timestamp}" || print_msg "No changes to commit" "$YELLOW"
    
    # 创建标签
    git tag -a "$tag_name" -m "Checkpoint at ${timestamp}"
    print_msg "Created tag: $tag_name" "$GREEN"
    
    # 仅推送到 origin (本地 Gitea)，不推送到 upstream (GitHub)
    git push origin HEAD
    git push origin "$tag_name"
    
    print_msg "Checkpoint completed: $tag_name" "$GREEN"
    print_msg "Pushed to origin only (local Gitea) - NOT pushed to GitHub" "$YELLOW"
}

# 完成变更 - 同步至 GitHub
finalize() {
    print_msg "Finalizing change and pushing to GitHub..." "$BLUE"
    push_changes "HEAD" "feat" "Finalize change for PR"
    print_msg "Change finalized and pushed to upstream" "$GREEN"
}

# 同步主分支
sync_main() {
    print_msg "Syncing main branch after merge..." "$BLUE"
    git checkout main
    git pull upstream main
    git push origin main
    print_msg "Main branch synced successfully" "$GREEN"
}

# 主干提交
push_main() {
    local type="${2:-feat}"
    local message="${3:-Push to main branch}"
    print_msg "Pushing to main branch..." "$BLUE"
    push_changes "main" "$type" "$message"
}

# 开始新变更
start_change() {
    if [ $# -ne 1 ]; then
        print_msg "用法: $0 start-change <CHANGE_ID>" "$RED"
        print_msg "示例: $0 start-change ABC-123" "$NC"
        exit 1
    fi
    
    local CHANGE_ID="$1"
    print_msg "Starting new change: $CHANGE_ID" "$BLUE"
    
    git checkout main
    git pull upstream main
    git checkout -b "feature-${CHANGE_ID}"
    git push origin "feature-${CHANGE_ID}"
    git push upstream "feature-${CHANGE_ID}"
    
    print_msg "Created and pushed feature branch: feature-${CHANGE_ID}" "$GREEN"
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
    push-main)
        shift
        push_main "$@"
        ;;
    start-change)
        shift
        start_change "$@"
        ;;
    *)
        show_help
        exit 1
        ;;
esac