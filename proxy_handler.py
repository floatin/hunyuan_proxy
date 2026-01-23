"""独立入口 - 使用重构后的 hunyuan_adapter 模块

用法：
    python main.py
"""

import uvicorn
import asyncio
from litellm.proxy.proxy_server import app, initialize

from hunyuan_adapter import setup_callbacks

# 设置回调
fixer = setup_callbacks()


async def start_server():
    """启动代理服务器"""
    # 初始化 proxy 配置
    await initialize(config="config.yaml")
    
    # 运行服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=4000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(start_server())
