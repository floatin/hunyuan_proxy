---
name: sdd-sync
description: 规范驱动开发 (SDD) 与双仓 (Gitea/GitHub) 同步管家。当用户需要初始化项目、开始新功能开发、进行高频本地存档 (Checkpoint)、或在 GitHub 合并后同步本地状态时，此技能提供严格的 Git 工作流指导。它确保 Spec 领先于代码，且 GitHub 历史记录保持整洁。
---

# SDD-Sync

## Getting Started
在执行任何操作前，请先通过对话确认：
1. `change_id` (如: `feat-login-logic`)
2. `origin` (指向本地 Gitea) 与 `upstream` (指向 GitHub) 是否已配置。
（更多初始化细节请参考 [references/git-flow.md#1-基础配置与仓库初始化-initialization]）

## Core Workflows

### 1. 项目初始化 [/init-project]
- **目标**: 建立双远端基准。
- **操作**:
    1. 引导编写 `spec/project_spec.md`。 (详见 [references/spec-standard.md#1-1-项目全景规范-project-spec])
    2. 执行 `scripts/sdd-sync.sh init`。 (该步骤的 Git 操作逻辑参见 [references/git-flow.md#1-基础配置与仓库初始化-initialization])

### 2. 需求启动 [/start-change]
- **目标**: 开启隔离的特性分支并同步基准。
- **操作**:
    1. 确保 `main` 与 `upstream` 对齐。
    2. 基于 `upstream/main` 创建 `feature-${change_id}`。
    3. 调用 `openspec` 创建 Change Spec。 (详见 [references/spec-standard.md#1-2-需求变更规范-change-spec])
    4. 执行双端推送。
    (完整需求启动流程请参考 [references/git-flow.md#2-需求启动流-change-start])

### 3. 循环存档 [/save]
- **目标**: 在本地 Gitea 进行细粒度快照，不污染 GitHub。
- **操作**:
    1. 运行 `scripts/sdd-sync.sh checkpoint`。
    2. 生成含时间戳的 `ckpt-` 标签。 (标签命名规范详见 [assets/commit-templates.md#tagging-rule])
    3. 仅推送至 `origin`。
    (更详细的存档策略和意义请参考 [references/git-flow.md#3-循环开发与高频存档-iterative-checkpoint])

### 4. 需求完结与合并 [/finish-change]
- **目标**: 整理代码并提交 PR 准备。
- **操作**:
    1. 运行 `scripts/sdd-sync.sh finalize` 同步至 `upstream`。
    2. 提示用户在 GitHub UI 提交 Merge Request。 (提交信息模板请参考 [assets/commit-templates.md#commit-message-template])
    (合并前检查和 GitHub 侧操作请参考 [references/git-flow.md#4-集成与双端对齐-integration-sync] 中的"步骤 2：GitHub 侧合并 (Manual)" )

### 5. 主干对齐 [/sync-main]
- **目标**: MR 合并后，清理本地环境并对齐双端。
- **操作**:
    1. 执行 `scripts/sdd-sync.sh sync-main`。
    (对齐操作详情请参考 [references/git-flow.md#4-集成与双端对齐-integration-sync] 中的"步骤 3：本地同步与对齐")

### 6. 主干提交 [/push-main]

- **目标**: 将已审核通过的代码推送到主干分支。
- **操作**:
    1. 执行 `scripts/sdd-push.sh push-main`。

## Extended Capabilities
- **详细工作流原理**: 见 [references/git-flow.md#1-基础配置与仓库初始化-initialization]
- **提交信息模板**: 见 [assets/commit-templates.md#commit-message-template]
- **回退机制**: 见 [references/git-flow.md#6-异常处理-error-handling]
