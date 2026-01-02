# LiteLLM Hunyuan Proxy

一个基于 LiteLLM 的代理服务，用于解决腾讯混元大模型与 OpenAI 兼容 API 之间的消息格式兼容性问题。

## 背景

在使用一些AI工具（如Roo Code）通过 OpenAI 兼容 API 调用腾讯混元大模型时，会遇到以下问题：

- **消息格式限制**：混元要求 `messages` 必须以 `user` 或 `tool` 角色结尾，但客户端（如 Roo Code）常常以 `assistant` 结尾
- **工具调用序列**：混元要求 `tool` 消息后如果紧跟 `user` 消息，中间需要有 `assistant` 消息作为过渡
- **不支持的参数**：混元不支持 `parallel_tool_calls`、`reasoning_effort` 等参数
- **工具定义字段**：混元不支持 `strict` 等 OpenAI 特有的工具定义字段

## 解决方案

本项目通过 LiteLLM 的 `CustomLogger` 回调机制，在请求发送到混元 API 之前自动修正消息格式：

1. **自动补全消息序列**：如果消息以 `assistant` 结尾，自动添加 `user` 消息
2. **插入过渡消息**：在 `tool` → `user` 之间自动插入 `assistant` 过渡消息
3. **移除不支持的参数**：自动移除 `parallel_tool_calls`、`reasoning_effort` 等参数
4. **清理工具定义**：移除 `function.strict` 等不支持的字段

## 安装

### 1. 创建虚拟环境

```bash
cd /path/to/litellm
python -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install litellm uvicorn
```

### 3. 配置 `config.yaml`

```yaml
model_list:
  - model_name: hunyuan-fixed
    litellm_params:
      model: openai/hunyuan-model
      api_key: your-api-key-here
      api_base: https://api.hunyuan.cloud.tencent.com/v1
      
litellm_settings:
  modify_params: true
  drop_params: true
```

## 使用方法

### 手动运行

```bash
source .venv/bin/activate
python proxy_handler.py
```

服务将在 `http://localhost:4000` 启动。



## 许可证

MIT License

