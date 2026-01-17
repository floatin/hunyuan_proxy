---
name: sdd-sync
description: SDD-Sync 是一个专注于 Git 操作封装的工具，提供双仓(Gitea/GitHub)同步的标准化命令集。它通过严格的 Git 工作流确保代码管理的整洁性和一致性。
---

# SDD-Sync

## 核心功能

### 1. 项目初始化 [/init-project]
- **目标**: 建立双远端(Gitea/GitHub)基准
- **操作**: 执行 `scripts/sdd-sync.sh init`

### 2. 循环存档 [/save]
- **目标**: 在本地 Gitea 进行细粒度快照
- **操作**: 执行 `scripts/sdd-sync.sh checkpoint`

### 3. 需求完结 [/finish-change]
- **目标**: 同步至 GitHub 准备 PR
- **操作**: 执行 `scripts/sdd-sync.sh finalize`

### 4. 主干对齐 [/sync-main]
- **目标**: MR 合并后对齐双端
- **操作**: 执行 `scripts/sdd-sync.sh sync-main`

### 5. 主干提交 [/push-main]
- **目标**: 推送已审核代码到主干
- **操作**: 执行 `scripts/sdd-sync.sh push-main`

## Git 工作流规范

### 双远端配置
- **Origin (Local)**: 指向本地 Gitea 实例，用于高频备份、checkpoint 存储
- **Upstream (Cloud)**: 指向 GitHub，用于存放正式版本、团队协作和 CI/CD

### 分支命名规范
- 格式：`feature-${change_id}`
- 示例：`feature-user-auth`

### 分支保留策略
- **原因**: 后续集成测试、线上补丁修复、审计需要
- **状态**: `feature-${change_id}` 分支在本地与双端均不执行删除

### 异常处理
- **代码冲突**: 停止合并，人工解决冲突后执行 `git add .` 和 `git commit`
- **回退到 Checkpoint**: 使用标签列表和重置命令回退

## 脚本接口
```bash
scripts/sdd-sync.sh {init|checkpoint|finalize|sync-main|push-main}
```
