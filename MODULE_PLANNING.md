# LiteLLM 混元代理处理器重构计划（精简版）

## 重构目标

在保持现有功能完全不变的前提下，将单体 `proxy_handler.py` 拆分为结构化模块，提高可维护性和可测试性。

## 目录结构

```
hunyuan_adapter/
├── __init__.py    # 入口 + 导出 + 便捷函数
├── cache.py       # ImageCache 图片缓存类
└── fixer.py       # CASCADE_CONFIG 配置 + HunyuanMessageFixer 回调类

proxy_handler.py   # 保留作为入口脚本，导入新模块
```

## 现有功能分析

### 核心功能（必须保留）

| 功能 | 原代码位置 | 目标文件 |
|------|-----------|---------|
| ImageCache 类 | 14-177 行 | cache.py |
| CASCADE_CONFIG 配置 | 179-188 行 | fixer.py |
| HunyuanMessageFixer 类 | 190-559 行 | fixer.py |
| litellm 回调注册 | 562-569 行 | __init__.py |
| 服务器启动逻辑 | 571-588 行 | proxy_handler.py（保留） |

## 模块详细规划

### 1. cache.py - 图片缓存

**来源**：proxy_handler.py 第 14-177 行（约 160 行）

**内容**：
```python
"""图片缓存模块"""

import hashlib
import time
from collections import OrderedDict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class ImageCache:
    """LRU 图片缓存，支持 TTL 过期"""
    
    def __init__(self, max_size=1000, ttl=3600):
        ...
    
    def generate_cache_key(self, image_content):
        """生成缓存键（原 _generate_cache_key）"""
        
    def get(self, key): ...
    def set(self, key, value): ...
    def delete(self, key): ...
    def clear(self): ...
    def get_stats(self): ...
```

### 2. fixer.py - 核心回调

**来源**：proxy_handler.py 第 1-13 行（导入）+ 179-559 行（配置和类，约 380 行）

**内容**：
```python
"""混元消息修正回调模块"""

import os
import copy
import litellm
import time
from litellm.integrations.custom_logger import CustomLogger
from dotenv import load_dotenv

from .cache import ImageCache

load_dotenv()

# 配置
CASCADE_CONFIG = {
    "vision_model": "hunyuan-vision-1.5-instruct",
    "text_model": "hunyuan-2.0-thinking-20251109",
    "api_key": os.getenv("API_KEY"),
    "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
    "cache_max_size": 1000,
    "cache_ttl": 3600,
    "enable_cache_logging": True,
}

class HunyuanMessageFixer(CustomLogger):
    """LiteLLM 自定义回调：消息格式修正 + 级联处理"""
    
    def __init__(self):
        super().__init__()
        self.image_cache = ImageCache(...)
        ...
    
    # 所有原有方法保持不变
    async def async_pre_call_hook(self, ...): ...
    def _contains_image(self, content): ...
    def _extract_images_from_content(self, content): ...
    async def _analyze_image_with_vision_model(self, ...): ...
    async def _process_cascade(self, data): ...
    def _fix_messages(self, messages): ...
    def _ensure_content_not_empty(self, msg): ...
    def clear_image_cache(self): ...
    def get_cache_stats(self): ...
    def delete_cache_entry(self, cache_key): ...
```

### 3. __init__.py - 模块入口

**内容**：
```python
"""
混元适配器模块

为 LiteLLM Proxy 提供混元大模型的兼容性支持
"""

import litellm
from .cache import ImageCache
from .fixer import HunyuanMessageFixer, CASCADE_CONFIG

__version__ = "1.0.0"

# 全局实例
_fixer_instance = None

def setup_callbacks():
    """设置并返回回调实例"""
    global _fixer_instance
    
    if _fixer_instance is None:
        _fixer_instance = HunyuanMessageFixer()
    
    if _fixer_instance not in litellm.callbacks:
        litellm.callbacks.append(_fixer_instance)
    
    litellm.drop_params = True
    return _fixer_instance

def get_fixer():
    """获取当前回调实例"""
    return _fixer_instance

# 向后兼容
hunyuan_fixer = None  # 在 setup_callbacks() 调用后更新

__all__ = [
    "HunyuanMessageFixer",
    "ImageCache",
    "CASCADE_CONFIG",
    "setup_callbacks",
    "get_fixer",
    "hunyuan_fixer",
]
```

### 4. proxy_handler.py - 入口脚本（更新）

**内容**：
```python
"""入口脚本 - 保持向后兼容"""

from hunyuan_adapter import setup_callbacks, hunyuan_fixer, CASCADE_CONFIG

# 设置回调
fixer = setup_callbacks()

if __name__ == "__main__":
    import uvicorn
    import asyncio
    from litellm.proxy.proxy_server import app, initialize
    
    async def start_server():
        await initialize(config="config.yaml")
        config = uvicorn.Config(app, host="0.0.0.0", port=4000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(start_server())
```

## 重构步骤

### Phase 1：创建模块结构
1. 创建 `hunyuan_adapter/` 目录
2. 提取 ImageCache 到 `cache.py`
3. 提取配置和 HunyuanMessageFixer 到 `fixer.py`
4. 创建 `__init__.py`

### Phase 2：更新入口
5. 更新 `proxy_handler.py` 改为导入新模块
6. 验证功能正常

### Phase 3：清理（可选）
7. 添加类型注解
8. 移除未使用的导入（如 `re`）

## 验收标准

- 功能完全等价，所有原有行为保持不变
- 总代码行数增加不超过 30 行
- 所有原有接口保持兼容
- `python proxy_handler.py` 仍可正常启动服务器

## 使用方式

```python
# 方式1：直接运行（与原来相同）
python proxy_handler.py

# 方式2：作为模块导入
from hunyuan_adapter import setup_callbacks
fixer = setup_callbacks()

# 方式3：单独使用组件
from hunyuan_adapter import ImageCache, HunyuanMessageFixer
```

## 风险控制

- 保留原 `proxy_handler.py` 备份
- 每个阶段完成后进行功能验证
- 保留原有的 print 调试语句，降低改动风险
