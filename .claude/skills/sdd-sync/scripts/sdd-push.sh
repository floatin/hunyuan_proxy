#!/bin/bash
# 核心同步逻辑：确保双仓一致性

# 检查参数数量
if [ $# -ne 3 ]; then
    echo "用法: $0 <branch> <type> <commit_message>"
    echo "示例: $0 main feat \"添加新功能\""
    exit 1
fi

branch="$1"
type="$2"
commit_message="$3"

# 执行推送操作
git add -A
git commit -m "$type:$commit_message"
git push github "$branch"
git push origin "$branch"
echo "已将代码分别提交到远端和本地的代码仓."
