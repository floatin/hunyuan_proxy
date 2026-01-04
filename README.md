# LiteLLM Hunyuan Proxy

一个基于 LiteLLM 的代理服务，用于解决腾讯混元大模型与 OpenAI 兼容 API 之间的消息格式兼容性问题。

## 背景

在使用一些AI工具（如Roo Code）通过 OpenAI 兼容 API 调用腾讯混元大模型时，会遇到以下问题：

- **消息格式限制**：混元要求 `messages` 必须以 `user` 或 `tool` 角色结尾，但客户端（如 Roo Code）常常以 `assistant` 结尾
- **工具调用序列**：混元要求 `tool` 消息后如果紧跟 `user` 消息，中间需要有 `assistant` 消息作为过渡
- **不支持的参数**：混元不支持 `parallel_tool_calls`、`reasoning_effort` 等参数
- **工具定义字段**：混元不支持 `strict` 等 OpenAI 特有的工具定义字段
- **模型能力限制**：`hunyuan-2.0-instruct` 支持工具调用但不支持图片；`hunyuan-vision` 支持图片但不支持工具调用

## 解决方案

本项目通过 LiteLLM 的 `CustomLogger` 回调机制，在请求发送到混元 API 之前自动修正消息格式：

### 消息格式修正

1. **自动补全消息序列**：如果消息以 `assistant` 结尾，自动添加 `user` 消息
2. **插入过渡消息**：在 `tool` → `user` 之间自动插入 `assistant` 过渡消息
3. **移除不支持的参数**：自动移除 `parallel_tool_calls`、`reasoning_effort` 等参数
4. **清理工具定义**：移除 `function.strict` 等不支持的字段

### 级联处理（图片 + 工具调用）

为了同时支持图片分析和工具调用，本项目实现了**级联处理机制**：

```
用户请求（可能包含图片）
         ↓
    检测是否有图片
         ↓
    ┌────┴────┐
    ↓         ↓
  有图片    无图片
    ↓         ↓
调用 vision   直接使用
模型分析图片   text 模型
    ↓
将图片转为
文本描述
    ↓
使用 text 模型
处理（带工具调用）
    ↓
  返回结果
```

**工作原理**：
1. 检测请求中是否包含图片（支持 base64 和 URL 格式）
2. 如果包含图片，先调用 `hunyuan-vision-1.5-instruct` 分析图片内容
3. 将图片分析结果转换为文本描述
4. 使用 `hunyuan-2.0-instruct-20251111` 处理请求（支持工具调用）

这样就实现了**既能分析图片，又能使用工具**的完整能力。

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
      
# 核心设置：开启自动消息修复
litellm_settings:
  modify_params: true
  drop_params: true
```

### 4. 配置级联处理

在 `proxy_handler.py` 中修改 `CASCADE_CONFIG`：

```python
CASCADE_CONFIG = {
    "vision_model": "hunyuan-vision-1.5-instruct",  # 视觉模型
    "text_model": "hunyuan-2.0-instruct-20251111",   # 文本模型（支持工具调用）
    "api_key": "your-api-key-here",
    "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
}
```

## 使用方法

### 手动运行

```bash
source .venv/bin/activate
python proxy_handler.py
```

服务将在 `http://localhost:4000` 启动。

### 使用 Supervisor 管理

创建 supervisor 配置文件 `/etc/supervisor/conf.d/litellm-proxy.conf`：

```ini
[program:litellm-proxy]
command=/path/to/.venv/bin/python /path/to/proxy_handler.py
directory=/path/to/litellm
autostart=true
autorestart=true
stdout_logfile=/path/to/logs/litellm-proxy.log
stderr_logfile=/path/to/logs/litellm-proxy-error.log
```

然后：

```bash
supervisorctl reread
supervisorctl update
supervisorctl start litellm-proxy
```

## 在 Roo Code 中使用

在 Roo Code 的 API 配置中设置：

- **Base URL**: `http://localhost:4000/v1`
- **API Key**: 任意值（或与 config.yaml 中配置的一致）
- **Model**: 配置文件中定义的模型名称

## 支持的功能

| 功能 | 状态 |
|------|------|
| 消息格式自动修正 | ✅ |
| 工具调用（Function Calling） | ✅ |
| 图片分析 | ✅ |
| 图片 + 工具调用（级联模式） | ✅ |
| 流式输出 | ✅ |

## 日志

日志文件位置：`logs/litellm-proxy.log`

查看实时日志：

```bash
tail -f logs/litellm-proxy.log
```

## License

MIT
