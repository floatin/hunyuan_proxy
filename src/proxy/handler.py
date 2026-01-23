"""
主代理处理器模块

协调所有组件的核心业务逻辑：
- 请求处理流程管理
- 回调链管理
- 错误处理和恢复
- 组件状态管理
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from .callbacks import HunyuanMessageFixer
from .monitoring import PerformanceMonitor
from .health import HealthChecker

logger = logging.getLogger(__name__)


class HunyuanProxyHandler:
    """主代理处理器 - 协调所有组件"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.callback_handler: Optional[HunyuanMessageFixer] = None
        self.monitor: Optional[PerformanceMonitor] = None
        self.health_checker: Optional[HealthChecker] = None
        self.is_initialized = False
        self.request_pipeline = RequestPipeline()
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志配置"""
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def initialize(self):
        """初始化所有组件"""
        try:
            logger.info("初始化代理处理器...")
            
            # 初始化回调处理器
            self.callback_handler = HunyuanMessageFixer(self.config)
            logger.info("回调处理器初始化完成")
            
            # 初始化性能监控
            if self.config.get("enable_monitoring", True):
                self.monitor = PerformanceMonitor(self.config.get("monitoring_config", {}))
                await self.monitor.initialize()
                logger.info("性能监控初始化完成")
            
            # 初始化健康检查
            if self.config.get("enable_health_check", True):
                self.health_checker = HealthChecker()
                self._register_health_checks()
                await self.health_checker.initialize()
                logger.info("健康检查初始化完成")
            
            # 设置请求处理管道
            self._setup_request_pipeline()
            
            self.is_initialized = True
            logger.info("代理处理器初始化完成")
            
        except Exception as e:
            logger.error(f"代理处理器初始化失败: {e}")
            raise
    
    def _setup_request_pipeline(self):
        """设置请求处理管道"""
        # 添加处理阶段
        self.request_pipeline.add_stage("validation", self._validate_request)
        self.request_pipeline.add_stage("preprocessing", self._preprocess_request)
        self.request_pipeline.add_stage("callback", self._apply_callbacks)
        self.request_pipeline.add_stage("postprocessing", self._postprocess_request)
    
    def _register_health_checks(self):
        """注册健康检查"""
        if self.health_checker:
            # 注册回调处理器健康检查
            self.health_checker.register_check(
                "callback_handler",
                self._check_callback_handler_health
            )
            
            # 注册缓存健康检查
            self.health_checker.register_check(
                "image_cache",
                self._check_image_cache_health
            )
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理传入请求的主入口"""
        if not self.is_initialized:
            raise RuntimeError("处理器未初始化")
        
        request_id = request_data.get("request_id", "unknown")
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"开始处理请求 {request_id}")
            
            # 开始性能监控
            if self.monitor:
                await self.monitor.track_request_start(request_id, start_time)
            
            # 执行请求处理管道
            processed_data = await self.request_pipeline.execute(request_data)
            
            # 记录成功
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"请求 {request_id} 处理完成，耗时: {duration:.3f}s")
            
            # 更新性能监控
            if self.monitor:
                await self.monitor.track_request_end(request_id, "success", duration)
            
            return processed_data
            
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(f"请求 {request_id} 处理失败: {e}")
            
            # 更新性能监控
            if self.monitor:
                await self.monitor.track_request_end(request_id, "error", duration)
            
            # 错误处理
            return await self.handle_error(e, {"request_id": request_id, "data": request_data})
    
    async def _validate_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证请求数据"""
        required_fields = ["messages"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必需字段: {field}")
        
        # 验证消息格式
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("messages 必须是列表")
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"消息 {i} 必须是字典")
            if "role" not in msg:
                raise ValueError(f"消息 {i} 缺少 role 字段")
        
        return data
    
    async def _preprocess_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """预处理请求数据"""
        # 添加请求时间戳
        data["timestamp"] = asyncio.get_event_loop().time()
        
        # 添加请求ID（如果没有）
        if "request_id" not in data:
            import uuid
            data["request_id"] = str(uuid.uuid4())
        
        return data
    
    async def _apply_callbacks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用回调处理"""
        if self.callback_handler:
            # 模拟 LiteLLM 回调调用
            call_type = "acompletion"
            processed_data = await self.callback_handler.async_pre_call_hook(
                user_api_key_dict={},
                cache={},
                data=data,
                call_type=call_type
            )
            return processed_data
        
        return data
    
    async def _postprocess_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """后处理请求数据"""
        # 添加处理完成时间戳
        data["processed_at"] = asyncio.get_event_loop().time()
        
        return data
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """统一错误处理"""
        error_type = type(error).__name__
        error_message = str(error)
        
        logger.error(f"处理错误: {error_type}: {error_message}")
        
        # 根据错误类型进行不同处理
        if isinstance(error, ValueError):
            # 客户端错误
            return {
                "error": {
                    "type": "validation_error",
                    "message": error_message,
                    "code": 400
                },
                "request_id": context.get("request_id")
            }
        elif isinstance(error, RuntimeError):
            # 服务器错误
            return {
                "error": {
                    "type": "server_error", 
                    "message": "内部服务器错误",
                    "code": 500
                },
                "request_id": context.get("request_id")
            }
        else:
            # 未知错误
            return {
                "error": {
                    "type": "unknown_error",
                    "message": "未知错误",
                    "code": 500
                },
                "request_id": context.get("request_id")
            }
    
    def get_status(self) -> Dict[str, Any]:
        """获取处理器状态"""
        status = {
            "initialized": self.is_initialized,
            "config": {
                "vision_model": self.config.get("vision_model"),
                "text_model": self.config.get("text_model"),
                "enable_monitoring": self.config.get("enable_monitoring"),
                "enable_health_check": self.config.get("enable_health_check")
            }
        }
        
        # 添加缓存统计
        if self.callback_handler:
            status["cache_stats"] = self.callback_handler.get_cache_stats()
        
        # 添加性能监控状态
        if self.monitor:
            status["monitoring"] = self.monitor.get_status()
        
        # 添加健康检查状态
        if self.health_checker:
            status["health"] = self.health_checker.get_status()
        
        return status
    
    async def _check_callback_handler_health(self) -> bool:
        """检查回调处理器健康状态"""
        if not self.callback_handler:
            return False
        
        try:
            # 测试缓存功能
            stats = self.callback_handler.get_cache_stats()
            return stats is not None
        except Exception:
            return False
    
    async def _check_image_cache_health(self) -> bool:
        """检查图片缓存健康状态"""
        if not self.callback_handler or not self.callback_handler.image_cache:
            return False
        
        try:
            # 测试缓存基本操作
            cache = self.callback_handler.image_cache
            test_key = "health_check_test"
            cache.set(test_key, "test_value")
            value = cache.get(test_key)
            cache.delete(test_key)
            return value == "test_value"
        except Exception:
            return False
    
    async def shutdown(self):
        """关闭处理器"""
        logger.info("正在关闭代理处理器...")
        
        try:
            # 关闭性能监控
            if self.monitor:
                await self.monitor.shutdown()
            
            # 关闭健康检查
            if self.health_checker:
                await self.health_checker.shutdown()
            
            # 清理回调处理器
            if self.callback_handler:
                self.callback_handler.clear_image_cache()
            
            self.is_initialized = False
            logger.info("代理处理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭处理器时出错: {e}")


class RequestPipeline:
    """请求处理管道"""
    
    def __init__(self):
        self.stages: Dict[str, Callable] = {}
    
    def add_stage(self, name: str, stage_func: Callable):
        """添加处理阶段"""
        self.stages[name] = stage_func
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行处理管道"""
        current_data = data
        
        for stage_name, stage_func in self.stages.items():
            try:
                current_data = await stage_func(current_data)
            except Exception as e:
                logger.error(f"管道阶段 {stage_name} 执行失败: {e}")
                raise
        
        return current_data
