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
    # 缓存配置
    "cache_max_size": 1000,      # 缓存最大条目数
    "cache_ttl": 3600,           # 缓存TTL（秒）
    "enable_cache_logging": True, # 启用缓存日志
}
```

### 5. 缓存功能配置（可选）

系统已内置智能图片缓存机制，无需额外配置即可使用：

**缓存特性：**
- 🚀 **性能提升**：相同图片只调用一次视觉模型
- 💰 **成本优化**：减少重复的API调用费用
- 📈 **命中率统计**：自动监控缓存效果
- ⏱️ **自动过期**：TTL机制保证数据新鲜度

**缓存键生成策略：**
- **Base64图片**：提取数据部分计算SHA256哈希
- **URL图片**：规范化URL（排序查询参数）
- **批量图片**：组合多个图片键，包含上下文哈希

**配置参数说明：**
- `cache_max_size`: 缓存最大条目数（默认1000）
- `cache_ttl`: 缓存生存时间（秒，默认3600=1小时）
- `enable_cache_logging`: 启用详细缓存日志（默认True）

**缓存管理接口：**
```python
# 清空缓存
hunyuan_fixer.clear_image_cache()

# 获取缓存统计
stats = hunyuan_fixer.get_cache_stats()
print(f"命中率: {stats['hit_rate']}%")

# 删除特定缓存项
hunyuan_fixer.delete_cache_entry(cache_key)
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
| 图片理解缓存 | ✅ |

## 缓存行为说明

### 工作原理
1. **缓存键生成**：基于图片内容生成唯一哈希键
2. **缓存检查**：处理图片前先查询缓存
3. **缓存命中**：直接返回已分析的结果
4. **缓存未命中**：调用视觉模型并缓存结果
5. **自动清理**：LRU策略 + TTL过期机制

### 已知限制
- **内存缓存**：进程重启后缓存丢失
- **上下文忽略**：相同图片在不同上下文中可能返回相同描述
- **内存占用**：约2MB/1000条缓存记录
- **单实例**：多实例部署需要额外同步机制

### 最佳实践
- **合理设置TTL**：根据业务需求调整缓存时间
- **监控命中率**：关注缓存效果，调整容量配置
- **内存控制**：避免过大缓存影响系统性能
- **定期清理**：必要时手动清理过期缓存

### 性能指标
- **预期命中率**：>80%（重复图片场景）
- **响应时间改善**：缓存命中时减少90%+延迟
- **API成本节约**：相同图片只调用一次视觉模型
- **内存开销**：<2MB（默认配置）

## 日志

日志文件位置：`logs/litellm-proxy.log`

查看实时日志：

```bash
tail -f logs/litellm-proxy.log
```

## License

MIT
