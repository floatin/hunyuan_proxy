非常抱歉，为了严格遵循“渐进式披露”原则，我确实应该把最详尽、最具有确定性的 Git 操作逻辑沉淀到 `references/git-flow.md` 中。

# references/git-flow.md

## 1. 基础配置与仓库初始化 (Initialization)

### 双远端配置标准
- **Origin (Local)**: 指向本地 Gitea 实例。用于高频备份、checkpoint 存储。
- **Upstream (Cloud)**: 指向 GitHub。用于存放正式版本、进行团队协作和触发 CI/CD。

### 初始化命令序列
```bash
# 1. 建立基础
git init
git remote add origin <local_gitea_url>
git remote add upstream <github_url>

# 2. 初始推送
git branch -M main
git add .
git commit -m "initial: project setup with spec"
git push origin main
git push upstream main
```

## 2. 需求启动流 (Change Start)

### 分支命名规范
- 格式：`feature-${change_id}`
- 示例：`feature-user-auth`

### 启动序列
```bash
# 确保本地 main 是最新的
git checkout main
git pull upstream main

# 创建并发布特性分支
git checkout -b feature-${change_id}
git push origin feature-${change_id}
git push upstream feature-${change_id}
```

## 3. 循环开发与高频存档 (Iterative Checkpoint)

在此阶段，**只与 Origin 同步**，确保 Upstream 的 Git 历史记录整洁。

### Checkpoint 操作
```bash
# 提交到本地分支
git add .
git commit -m "ckpt(${change_id}): <description>"

# 打标签 (含时间戳)
TAG_NAME="ckpt-${change_id}-$(date +%Y%m%d%H%M)"
git tag $TAG_NAME

# 仅推送到本地仓
git push origin feature-${change_id} --tags
```

## 4. 集成与双端对齐 (Integration & Sync)

### 步骤 1：全量推送至特性分支
在合并前，确保 Upstream 的特性分支也有最新的代码：
```bash
git push upstream feature-${change_id}
```

### 步骤 2：GitHub 侧合并 (Manual)
提示用户在 GitHub UI 执行以下操作：
1. 发起 `feature-${change_id}` -> `main` 的 PR。
2. 通过审核并点击 **Merge**。

### 步骤 3：本地同步与对齐
```bash
# 切换回主分支并合并特性分支 (本地合并)
git checkout main
git merge feature-${change_id}

# 从远程拉取最新 main (确保包含远程 MR 的合并元数据)
git pull upstream main

# 将对齐后的最新 main 推送回本地 Gitea
git push origin main
```

## 5. 分支与标签维护 (Maintenance)

### 分支保留策略 (Non-Deletion Policy)
- **原因**：后续集成测试、线上补丁修复、审计需要。
- **状态**：`feature-${change_id}` 分支在本地与双端均**不执行删除**。

### 标签清理 (Optional)
若本地 Checkpoint 标签过多，可执行局部清理，但建议保留重要里程碑：
- 删除本地标签：`git tag -d <tag_name>`
- 同步删除远程标签：`git push origin --delete <tag_name>`

## 6. 异常处理 (Error Handling)

### 代码冲突 (Merge Conflicts)
1. 停止合并操作。
2. 提醒用户人工介入解决冲突。
3. 解决后执行 `git add .` 和 `git commit`。

### 回退到 Checkpoint
1. `git tag -l "ckpt-${change_id}*"` (列出所有相关标签)。
2. `git reset --hard <selected_tag>`。
3. `git clean -fd` (清理未追踪文件，谨慎执行)。

