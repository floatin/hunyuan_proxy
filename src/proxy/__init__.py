"""
LiteLLM 混元代理主处理器模块

提供完整的代理服务器功能，包括：
- 消息格式修正
- 级联处理（图片→文本）
- 缓存管理
- 性能监控
- 健康检查
"""

from .handler import HunyuanProxyHandler
from .callbacks import HunyuanMessageFixer, ImageCache
from .server import ProxyServer

# 版本信息
__version__ = "1.0.0"

# 便捷工厂函数
def create_proxy_server(config_path: str = None) -> ProxyServer:
    """创建并配置代理服务器实例"""
    return ProxyServer(config_path)

def setup_callbacks(config: dict = None) -> HunyuanMessageFixer:
    """设置并返回回调实例"""
    return HunyuanMessageFixer(config or {})

# 导出的公共接口
__all__ = [
    "HunyuanProxyHandler",
    "HunyuanMessageFixer", 
    "ImageCache",
    "ProxyServer",
    "create_proxy_server",
    "setup_callbacks",
]
