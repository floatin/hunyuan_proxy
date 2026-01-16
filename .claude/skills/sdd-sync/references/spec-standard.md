# 规范驱动开发 (SDD) 标准协议

本文件定义了项目在代码实现前必须遵循的文档规范。所有开发活动必须以 Spec（技术规范）为起点。

## 1. Spec 的层级结构

### 1.1 项目全景规范 (Project Spec)
- **路径**: `spec/project_spec.md`
- **内容**: 项目目标、核心架构（技术栈）、全局约束、双仓配置信息。
- **触发**: 在项目初始化阶段 (`/init-project`) 创建。

### 1.2 需求变更规范 (Change Spec)
- **路径**: `spec/changes/${change_id}_spec.md`
- **内容**: 
  - **Context**: 为什么要做这个变更。
  - **Proposed Changes**: 具体的代码修改逻辑、新增 API、数据库 Schema 变更。
  - **Verification**: 如何验证变更是否成功。
- **触发**: 在功能开发启动阶段 (`/start-change`) 创建。

## 2. SDD 工作流生命周期

1. **OpenSpec**: 针对 `change_id` 生成或打开对应的变更规范。
2. **Review**: Claude 与用户对 Spec 达成一致（确认逻辑无误）。
3. **Implement**: 依据 Spec 进行编码，每一步都要引用 Spec 中的条目。
4. **Archive**: 需求完成后，将变更摘要同步回 `Project Spec`，并归档 `Change Spec`。

## 3. 规范质量检查清单 (Checklist)

在开始写代码前，Claude 必须自检 Spec 是否包含以下要素：
- [ ] **明确的范围**: 清楚定义了“做什么”和“不做什么”。
- [ ] **受影响的文件**: 列出所有需要新增或修改的文件路径。
- [ ] **破坏性变更**: 是否涉及数据库迁移或 API 兼容性问题？
- [ ] **Git 策略**: 是否已标记该 Change 的 Checkpoint 频率。

## 4. 与 Git 工作流的联动

- **禁止无 Spec 提交**: 所有的代码提交（除 Checkpoint 外）必须能溯源到 Spec 中的某个任务点。
- **双端对齐**: 在 `/finish-change` 时，必须确保 `spec/` 目录下的更新已同步推送到 `upstream`，以供团队评审。
