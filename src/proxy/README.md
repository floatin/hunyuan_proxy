# LiteLLM 混元代理主处理器模块

这个模块提供了完整的 LiteLLM 混元代理服务器功能，包括消息格式修正、级联处理、缓存管理、性能监控和健康检查。

## 🚀 快速开始

### 基本使用

```python
import asyncio
from src.proxy import create_proxy_server

async def main():
    # 创建并启动服务器
    server = create_proxy_server()
    await server.initialize()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### 自定义配置

```python
from src.proxy import ProxyServer

async def main():
    config = {
        "host": "0.0.0.0",
        "port": 4000,
        "vision_model": "hunyuan-vision-1.5-instruct",
        "text_model": "hunyuan-2.0-thinking-20251109",
        "api_key": "your-api-key",
        "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
        "cache_max_size": 2000,
        "cache_ttl": 7200,
        "enable_monitoring": True,
        "enable_health_check": True,
    }
    
    server = ProxyServer()
    server.config = config
    await server.initialize()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📁 模块结构

```
src/proxy/
├── __init__.py          # 模块入口点
├── handler.py           # 主代理处理器
├── callbacks.py         # LiteLLM 回调实现
├── server.py            # 服务器配置和启动
├── monitoring.py        # 性能监控集成
└── health.py            # 健康检查端点
```

## 🔧 核心功能

### 1. 消息格式修正 (callbacks.py)

- **HunyuanMessageFixer**: 主要回调类，确保消息格式兼容混元大模型
- **自动修正**: 确保消息以 user 或 tool 结尾
- **空内容处理**: 自动填充空的 content 字段
- **工具调用支持**: 保留完整的工具调用链

### 2. 级联处理 (callbacks.py)

- **图片检测**: 自动检测消息中的图片内容
- **视觉模型分析**: 使用混元视觉模型分析图片
- **缓存优化**: 智能缓存图片分析结果
- **模型切换**: 自动切换到支持工具调用的文本模型

### 3. 高性能缓存 (callbacks.py)

- **LRU缓存**: 基于 OrderedDict 的 LRU 缓存实现
- **TTL支持**: 可配置的缓存过期时间
- **统计信息**: 详细的缓存命中率统计
- **智能键生成**: 为不同类型的图片生成唯一缓存键

### 4. 请求处理管道 (handler.py)

- **模块化处理**: 将请求处理分解为多个阶段
- **错误处理**: 统一的错误处理和恢复机制
- **组件协调**: 协调所有组件的工作
- **状态管理**: 实时状态监控和管理

### 5. 服务器管理 (server.py)

- **FastAPI集成**: 基于 FastAPI 的高性能服务器
- **配置管理**: 灵活的配置加载和验证
- **中间件支持**: CORS、日志、错误处理中间件
- **优雅关闭**: 支持优雅的服务器关闭

### 6. 性能监控 (monitoring.py)

- **指标收集**: 全面的性能指标收集
- **实时监控**: 实时的性能监控和告警
- **告警系统**: 可配置的告警规则和通知
- **统计报告**: 详细的性能统计报告

### 7. 健康检查 (health.py)

- **组件监控**: 监控各个组件的健康状态
- **存活检查**: 简单的服务存活检查
- **就绪检查**: 详细的就绪状态检查
- **依赖检查**: 外部依赖服务的健康检查

## 📊 API 端点

### 主要端点

- `POST /v1/chat/completions` - LiteLLM 兼容的聊天完成
- `POST /v1/completions` - LiteLLM 兼容的文本完成
- `GET /health` - 健康检查
- `GET /status` - 详细状态信息
- `GET /` - 服务基本信息

### 管理端点

- `DELETE /cache` - 清空缓存
- `GET /cache/stats` - 获取缓存统计

## 🔍 监控和日志

### 性能指标

- 请求数量和成功率
- 响应时间统计
- 缓存命中率
- 错误率和异常统计
- 模型调用统计

### 健康检查

- 回调处理器状态
- 图片缓存状态
- 数据库连接状态
- 外部服务状态

### 日志记录

- 请求/响应日志
- 错误和异常日志
- 性能监控日志
- 缓存操作日志

## ⚙️ 配置选项

### 服务器配置

```python
{
    "host": "0.0.0.0",           # 服务器主机
    "port": 4000,                # 服务器端口
    "log_level": "info",         # 日志级别
    "enable_cors": True,         # 启用 CORS
    "cors_origins": ["*"],       # CORS 允许的源
}
```

### 模型配置

```python
{
    "vision_model": "hunyuan-vision-1.5-instruct",
    "text_model": "hunyuan-2.0-thinking-20251109",
    "api_key": "your-api-key",
    "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
}
```

### 缓存配置

```python
{
    "cache_max_size": 1000,      # 缓存最大条目数
    "cache_ttl": 3600,           # 缓存TTL（秒）
    "enable_cache_logging": True, # 启用缓存日志
}
```

### 监控配置

```python
{
    "enable_monitoring": True,   # 启用性能监控
    "enable_health_check": True, # 启用健康检查
    "alert_check_interval": 30,  # 告警检查间隔（秒）
    "max_metric_points": 10000,  # 最大指标点数
}
```

## 🚨 告警规则

### 默认告警

- **高错误率**: 错误率超过 10%
- **长响应时间**: P95 响应时间超过 5 秒
- **低缓存命中率**: 缓存命中率低于 50%

### 自定义告警

```python
from src.proxy.monitoring import AlertRule, AlertSeverity

rule = AlertRule(
    name="custom_alert",
    metric_name="custom_metric",
    condition="gt",
    threshold=100.0,
    severity=AlertSeverity.MEDIUM,
    message="自定义告警触发"
)

monitor.alert_manager.add_rule(rule)
```

## 🔧 扩展和自定义

### 添加自定义中间件

```python
from src.proxy.server import ProxyServer

server = ProxyServer()

@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    # 自定义处理逻辑
    response = await call_next(request)
    return response
```

### 添加自定义健康检查

```python
from src.proxy.health import ComponentHealth, HealthCheckResult, HealthStatus

class CustomHealthCheck(ComponentHealth):
    async def _do_check(self) -> HealthCheckResult:
        # 自定义检查逻辑
        return HealthCheckResult(
            component="custom",
            status=HealthStatus.HEALTHY,
            message="自定义组件正常",
            timestamp=time.time(),
            duration=0.0
        )

# 注册检查
server.health_checker.register_check("custom", CustomHealthCheck())
```

### 添加自定义监控指标

```python
from src.proxy.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()

# 记录自定义指标
monitor.metrics_collector.increment_counter("custom_counter")
monitor.metrics_collector.set_gauge("custom_gauge", 42.0)
monitor.metrics_collector.record_histogram("custom_histogram", 1.5)
```

## 🐛 故障排除

### 常见问题

1. **服务器启动失败**
   - 检查端口是否被占用
   - 验证配置文件格式
   - 确认 API 密钥正确

2. **缓存命中率低**
   - 检查缓存配置
   - 验证图片内容格式
   - 调整缓存大小和TTL

3. **健康检查失败**
   - 检查组件初始化状态
   - 验证外部依赖连接
   - 查看详细错误日志

### 调试模式

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 获取详细状态
status = server.handler.get_status()
print(status)
```

## 📈 性能优化

### 缓存优化

- 合理设置缓存大小和TTL
- 监控缓存命中率
- 定期清理过期缓存

### 并发优化

- 使用异步处理
- 配置合适的连接池
- 启用请求限流

### 监控优化

- 调整监控频率
- 优化指标存储
- 配置合适的告警阈值

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。
