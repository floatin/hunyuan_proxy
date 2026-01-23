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
