"""
健康检查端点模块

提供全面的健康检查功能：
- 组件状态监控
- 存活和就绪检查
- 依赖服务检查
- 健康状态报告
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    status: HealthStatus
    message: str
    timestamp: float
    duration: float
    details: Dict[str, Any] = None


class ComponentHealth:
    """组件健康状态基类"""
    
    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.timeout = timeout
        self.last_check = None
        self.last_result = None
        self.check_count = 0
        self.success_count = 0
    
    async def check(self) -> HealthCheckResult:
        """执行健康检查"""
        start_time = time.time()
        
        try:
            # 设置超时
            result = await asyncio.wait_for(self._do_check(), timeout=self.timeout)
            
            # 更新统计
            self.check_count += 1
            if result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                self.success_count += 1
            
            self.last_check = time.time()
            self.last_result = result
            
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            result = HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"健康检查超时 ({self.timeout}s)",
                timestamp=start_time,
                duration=duration
            )
            
            self.check_count += 1
            self.last_check = time.time()
            self.last_result = result
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"健康检查异常: {str(e)}",
                timestamp=start_time,
                duration=duration
            )
            
            self.check_count += 1
            self.last_check = time.time()
            self.last_result = result
            
            return result
    
    async def _do_check(self) -> HealthCheckResult:
        """子类实现具体的检查逻辑"""
        raise NotImplementedError("子类必须实现 _do_check 方法")
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.check_count == 0:
            return 0.0
        return self.success_count / self.check_count


class CallbackHealthCheck(ComponentHealth):
    """回调处理器健康检查"""
    
    def __init__(self, callback_handler):
        super().__init__("callback_handler")
        self.callback_handler = callback_handler
    
    async def _do_check(self) -> HealthCheckResult:
        """检查回调处理器状态"""
        if not self.callback_handler:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message="回调处理器未初始化",
                timestamp=time.time(),
                duration=0.0
            )
        
        try:
            # 测试缓存功能
            cache_stats = self.callback_handler.get_cache_stats()
            
            # 检查缓存是否正常工作
            if cache_stats is None:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.DEGRADED,
                    message="无法获取缓存统计",
                    timestamp=time.time(),
                    duration=0.0,
                    details={"cache_stats": None}
                )
            
            # 检查缓存命中率
            hit_rate = cache_stats.get("hit_rate", 0)
            if hit_rate < 10:  # 命中率低于10%认为有问题
                status = HealthStatus.DEGRADED
                message = f"缓存命中率较低: {hit_rate}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"回调处理器正常，缓存命中率: {hit_rate}%"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                timestamp=time.time(),
                duration=0.0,
                details=cache_stats
            )
            
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"回调处理器检查失败: {str(e)}",
                timestamp=time.time(),
                duration=0.0
            )


class ImageCacheHealthCheck(ComponentHealth):
    """图片缓存健康检查"""
    
    def __init__(self, image_cache):
        super().__init__("image_cache")
        self.image_cache = image_cache
    
    async def _do_check(self) -> HealthCheckResult:
        """检查图片缓存状态"""
        if not self.image_cache:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message="图片缓存未初始化",
                timestamp=time.time(),
                duration=0.0
            )
        
        try:
            # 测试缓存基本操作
            test_key = "health_check_test"
            test_value = f"test_value_{time.time()}"
            
            # 测试写入
            self.image_cache.set(test_key, test_value)
            
            # 测试读取
            retrieved_value = self.image_cache.get(test_key)
            
            # 测试删除
            self.image_cache.delete(test_key)
            
            # 验证结果
            if retrieved_value != test_value:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="缓存读写测试失败",
                    timestamp=time.time(),
                    duration=0.0
                )
            
            # 获取缓存统计
            stats = self.image_cache.get_stats()
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="图片缓存正常",
                timestamp=time.time(),
                duration=0.0,
                details=stats
            )
            
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"图片缓存检查失败: {str(e)}",
                timestamp=time.time(),
                duration=0.0
            )


class DatabaseHealthCheck(ComponentHealth):
    """数据库健康检查（示例）"""
    
    def __init__(self, connection_string: str):
        super().__init__("database")
        self.connection_string = connection_string
    
    async def _do_check(self) -> HealthCheckResult:
        """检查数据库连接"""
        # 这里是示例实现，实际应该连接数据库
        try:
            # 模拟数据库连接测试
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="数据库连接正常",
                timestamp=time.time(),
                duration=0.1
            )
            
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"数据库连接失败: {str(e)}",
                timestamp=time.time(),
                duration=0.0
            )


class ExternalServiceHealthCheck(ComponentHealth):
    """外部服务健康检查"""
    
    def __init__(self, name: str, url: str, timeout: float = 5.0):
        super().__init__(name, timeout)
        self.url = url
    
    async def _do_check(self) -> HealthCheckResult:
        """检查外部服务"""
        try:
            import aiohttp
            
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(self.url) as response:
                    duration = time.time() - start_time
                    
                    if response.status == 200:
                        return HealthCheckResult(
                            component=self.name,
                            status=HealthStatus.HEALTHY,
                            message=f"外部服务正常 (HTTP {response.status})",
                            timestamp=start_time,
                            duration=duration,
                            details={"status_code": response.status}
                        )
                    else:
                        return HealthCheckResult(
                            component=self.name,
                            status=HealthStatus.DEGRADED,
                            message=f"外部服务响应异常 (HTTP {response.status})",
                            timestamp=start_time,
                            duration=duration,
                            details={"status_code": response.status}
                        )
                        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"外部服务请求超时 ({self.timeout}s)",
                timestamp=time.time(),
                duration=self.timeout
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"外部服务检查失败: {str(e)}",
                timestamp=time.time(),
                duration=0.0
            )


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, ComponentHealth] = {}
        self.is_initialized = False
        self.check_interval = 30.0  # 默认30秒检查一次
        self.check_task: Optional[asyncio.Task] = None
        self.last_results: Dict[str, HealthCheckResult] = {}
    
    def register_check(self, name: str, check_func: Callable[[], ComponentHealth]):
        """注册健康检查"""
        if callable(check_func):
            # 如果是函数，调用它获取检查实例
            check_instance = check_func()
        else:
            # 如果已经是检查实例
            check_instance = check_func
        
        self.checks[name] = check_instance
        logger.info(f"注册健康检查: {name}")
    
    def register_component(self, name: str, component: ComponentHealth):
        """注册组件健康检查"""
        self.checks[name] = component
        logger.info(f"注册组件健康检查: {name}")
    
    async def initialize(self):
        """初始化健康检查器"""
        try:
            logger.info("初始化健康检查器...")
            
            # 启动定期检查任务
            self.check_task = asyncio.create_task(self._check_loop())
            
            self.is_initialized = True
            logger.info("健康检查器初始化完成")
            
        except Exception as e:
            logger.error(f"健康检查器初始化失败: {e}")
            raise
    
    async def run_checks(self) -> Dict[str, HealthCheckResult]:
        """运行所有健康检查"""
        results = {}
        
        # 并行执行所有检查
        tasks = []
        check_names = []
        
        for name, check in self.checks.items():
            task = asyncio.create_task(check.check())
            tasks.append(task)
            check_names.append(name)
        
        # 等待所有检查完成
        if tasks:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(completed_results):
                name = check_names[i]
                
                if isinstance(result, Exception):
                    # 处理异常
                    error_result = HealthCheckResult(
                        component=name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"检查执行异常: {str(result)}",
                        timestamp=time.time(),
                        duration=0.0
                    )
                    results[name] = error_result
                else:
                    results[name] = result
                    self.last_results[name] = result
        
        return results
    
    async def check_liveness(self) -> Dict[str, Any]:
        """存活检查 - 服务是否正在运行"""
        if not self.is_initialized:
            return {
                "status": "unhealthy",
                "message": "健康检查器未初始化"
            }
        
        # 简单的存活检查
        return {
            "status": "healthy",
            "message": "服务正在运行",
            "timestamp": time.time()
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """就绪检查 - 服务是否准备好接收请求"""
        if not self.is_initialized:
            return {
                "status": "unhealthy",
                "message": "健康检查器未初始化"
            }
        
        # 运行关键检查
        critical_checks = ["callback_handler", "image_cache"]
        results = await self.run_checks()
        
        # 检查关键组件
        failed_critical = []
        for check_name in critical_checks:
            if check_name in results:
                result = results[check_name]
                if result.status == HealthStatus.UNHEALTHY:
                    failed_critical.append(check_name)
        
        if failed_critical:
            return {
                "status": "unhealthy",
                "message": f"关键组件未就绪: {', '.join(failed_critical)}",
                "failed_components": failed_critical,
                "timestamp": time.time()
            }
        
        return {
            "status": "healthy",
            "message": "服务已就绪",
            "timestamp": time.time()
        }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """获取详细健康状态"""
        results = await self.run_checks()
        
        # 计算整体状态
        overall_status = HealthStatus.HEALTHY
        failed_components = []
        degraded_components = []
        
        for name, result in results.items():
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                failed_components.append(name)
            elif result.status == HealthStatus.DEGRADED:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                degraded_components.append(name)
        
        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "summary": {
                "total_checks": len(results),
                "healthy": len([r for r in results.values() if r.status == HealthStatus.HEALTHY]),
                "degraded": len(degraded_components),
                "unhealthy": len(failed_components)
            },
            "components": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "duration": result.duration,
                    "timestamp": result.timestamp,
                    "details": result.details
                }
                for name, result in results.items()
            },
            "failed_components": failed_components,
            "degraded_components": degraded_components
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取健康检查器状态"""
        return {
            "initialized": self.is_initialized,
            "registered_checks": len(self.checks),
            "check_interval": self.check_interval,
            "last_results": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "timestamp": result.timestamp
                }
                for name, result in self.last_results.items()
            }
        }
    
    async def _check_loop(self):
        """定期检查循环"""
        while self.is_initialized:
            try:
                # 运行检查
                await self.run_checks()
                
                # 等待下次检查
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环出错: {e}")
                await asyncio.sleep(5)  # 错误时短暂等待
    
    async def shutdown(self):
        """关闭健康检查器"""
        logger.info("正在关闭健康检查器...")
        
        self.is_initialized = False
        
        # 取消检查任务
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("健康检查器已关闭")
