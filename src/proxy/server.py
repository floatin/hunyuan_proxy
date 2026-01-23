"""
服务器配置和启动模块

管理代理服务器的生命周期：
- 配置加载和验证
- 服务器启动和关闭
- 路由注册
- 中间件设置
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .handler import HunyuanProxyHandler
from .health import HealthChecker
from .monitoring import PerformanceMonitor

logger = logging.getLogger(__name__)


class ProxyServer:
    """代理服务器主类"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.handler: Optional[HunyuanProxyHandler] = None
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self.is_running = False
        
        # 默认配置
        self.default_config = {
            "host": "0.0.0.0",
            "port": 4000,
            "log_level": "info",
            "vision_model": "hunyuan-vision-1.5-instruct",
            "text_model": "hunyuan-2.0-thinking-20251109",
            "api_key": os.getenv("API_KEY"),
            "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
            "cache_max_size": 1000,
            "cache_ttl": 3600,
            "enable_monitoring": True,
            "enable_health_check": True,
            "enable_cors": True,
            "cors_origins": ["*"],
        }
    
    async def load_config(self, config_path: Optional[str] = None):
        """加载和验证配置"""
        config_file = config_path or self.config_path
        
        if config_file and os.path.exists(config_file):
            logger.info(f"从文件加载配置: {config_file}")
            # 这里可以添加 YAML/JSON 配置文件解析
            # 暂时使用环境变量和默认配置
            pass
        
        # 合并配置
        self.config = {**self.default_config}
        
        # 从环境变量覆盖配置
        env_mappings = {
            "PROXY_HOST": "host",
            "PROXY_PORT": "port", 
            "PROXY_LOG_LEVEL": "log_level",
            "API_KEY": "api_key",
            "VISION_MODEL": "vision_model",
            "TEXT_MODEL": "text_model",
            "API_BASE": "api_base",
        }
        
        for env_key, config_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value:
                # 类型转换
                if config_key in ["port"]:
                    self.config[config_key] = int(env_value)
                elif config_key in ["enable_monitoring", "enable_health_check", "enable_cors"]:
                    self.config[config_key] = env_value.lower() in ["true", "1", "yes"]
                else:
                    self.config[config_key] = env_value
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"配置加载完成: {self.config}")
    
    def _validate_config(self):
        """验证配置完整性"""
        required_fields = ["api_key", "api_base"]
        
        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"缺少必需配置: {field}")
        
        # 验证端口范围
        port = self.config.get("port", 4000)
        if not (1 <= port <= 65535):
            raise ValueError(f"端口 {port} 不在有效范围内 (1-65535)")
    
    async def initialize(self):
        """初始化服务器组件"""
        try:
            logger.info("初始化代理服务器...")
            
            # 加载配置
            await self.load_config()
            
            # 创建 FastAPI 应用
            self.app = FastAPI(
                title="LiteLLM 混元代理服务器",
                description="为混元大模型提供 LiteLLM 兼容的代理服务",
                version="1.0.0"
            )
            
            # 初始化处理器
            self.handler = HunyuanProxyHandler(self.config)
            await self.handler.initialize()
            
            # 设置路由
            self.register_routes()
            
            # 设置中间件
            self.setup_middleware()
            
            logger.info("代理服务器初始化完成")
            
        except Exception as e:
            logger.error(f"服务器初始化失败: {e}")
            raise
    
    def register_routes(self):
        """注册API路由"""
        
        @self.app.get("/")
        async def root():
            """根路径 - 服务信息"""
            return {
                "service": "LiteLLM 混元代理服务器",
                "version": "1.0.0",
                "status": "running" if self.is_running else "stopped"
            }
        
        @self.app.get("/health")
        async def health_check():
            """健康检查端点"""
            if self.handler:
                status = self.handler.get_status()
                return {
                    "status": "healthy" if status.get("initialized", False) else "unhealthy",
                    "details": status
                }
            return {"status": "unhealthy", "message": "处理器未初始化"}
        
        @self.app.get("/status")
        async def get_status():
            """获取详细状态"""
            if self.handler:
                return self.handler.get_status()
            return {"error": "处理器未初始化"}
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: Request):
            """LiteLLM 兼容的聊天完成端点"""
            try:
                # 获取请求数据
                request_data = await request.json()
                
                # 添加请求信息
                request_data["client_ip"] = request.client.host
                request_data["user_agent"] = request.headers.get("user-agent", "")
                
                # 处理请求
                processed_data = await self.handler.process_request(request_data)
                
                # 返回处理后的数据
                # 注意：这里应该调用实际的 LiteLLM API
                # 暂时返回处理后的数据用于演示
                return {
                    "id": f"chatcmpl-{request_data.get('request_id', 'unknown')}",
                    "object": "chat.completion",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": processed_data.get("model", "unknown"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "这是处理后的响应（演示）"
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150
                    }
                }
                
            except Exception as e:
                logger.error(f"聊天完成请求处理失败: {e}")
                return {
                    "error": {
                        "message": str(e),
                        "type": "api_error",
                        "code": 500
                    }
                }
        
        @self.app.post("/v1/completions")
        async def completions(request: Request):
            """LiteLLM 兼容的文本完成端点"""
            # 类似 chat_completions 的处理逻辑
            return await chat_completions(request)
        
        @self.app.delete("/cache")
        async def clear_cache():
            """清空缓存"""
            if self.handler and self.handler.callback_handler:
                self.handler.callback_handler.clear_image_cache()
                return {"message": "缓存已清空"}
            return {"error": "处理器未初始化"}
        
        @self.app.get("/cache/stats")
        async def get_cache_stats():
            """获取缓存统计"""
            if self.handler and self.handler.callback_handler:
                return self.handler.callback_handler.get_cache_stats()
            return {"error": "处理器未初始化"}
    
    def setup_middleware(self):
        """设置中间件"""
        
        # CORS 中间件
        if self.config.get("enable_cors", True):
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.get("cors_origins", ["*"]),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # 请求日志中间件
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = asyncio.get_event_loop().time()
            
            # 记录请求
            logger.info(f"请求开始: {request.method} {request.url}")
            
            # 处理请求
            response = await call_next(request)
            
            # 记录响应
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"请求完成: {request.method} {request.url} - 状态: {response.status_code} - 耗时: {duration:.3f}s")
            
            return response
        
        # 错误处理中间件
        @self.app.middleware("http")
        async def error_handler(request: Request, call_next):
            try:
                return await call_next(request)
            except Exception as e:
                logger.error(f"未处理的错误: {e}")
                return Response(
                    content={"error": {"message": "内部服务器错误", "type": "internal_error"}},
                    status_code=500,
                    media_type="application/json"
                )
    
    async def start(self, host: Optional[str] = None, port: Optional[int] = None):
        """启动服务器"""
        if self.is_running:
            logger.warning("服务器已在运行")
            return
        
        try:
            # 使用参数或配置中的值
            server_host = host or self.config.get("host", "0.0.0.0")
            server_port = port or self.config.get("port", 4000)
            
            logger.info(f"启动服务器: {server_host}:{server_port}")
            
            # 配置 uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=server_host,
                port=server_port,
                log_level=self.config.get("log_level", "info"),
                access_log=True
            )
            
            # 创建服务器实例
            self.server = uvicorn.Server(config)
            
            # 启动服务器
            self.is_running = True
            await self.server.serve()
            
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """优雅关闭服务器"""
        if not self.is_running:
            logger.warning("服务器未在运行")
            return
        
        try:
            logger.info("正在关闭服务器...")
            
            # 关闭 uvicorn 服务器
            if self.server:
                self.server.should_exit = True
                await self.server.shutdown()
            
            # 关闭处理器
            if self.handler:
                await self.handler.shutdown()
            
            self.is_running = False
            logger.info("服务器已关闭")
            
        except Exception as e:
            logger.error(f"关闭服务器时出错: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置（隐藏敏感信息）"""
        safe_config = self.config.copy()
        
        # 隐藏敏感信息
        sensitive_fields = ["api_key"]
        for field in sensitive_fields:
            if field in safe_config:
                safe_config[field] = "***"
        
        return safe_config


# 便捷函数
async def create_and_start_server(config_path: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None):
    """创建并启动服务器的便捷函数"""
    server = ProxyServer(config_path)
    await server.initialize()
    await server.start(host, port)


if __name__ == "__main__":
    # 直接运行时的启动逻辑
    async def main():
        server = ProxyServer()
        await server.initialize()
        await server.start()
    
    asyncio.run(main())
