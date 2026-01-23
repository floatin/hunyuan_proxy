"""
性能监控集成模块

提供全面的性能监控功能：
- 指标收集和存储
- 实时监控
- 告警机制
- 统计报告
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    message: str
    enabled: bool = True


@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    metric_value: float
    resolved: bool = False


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.timers: Dict[str, List[float]] = defaultdict(list)
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """增加计数器"""
        key = self._make_key(name, tags)
        self.counters[key] += value
        logger.debug(f"计数器增加: {key} += {value}")
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表盘值"""
        key = self._make_key(name, tags)
        self.gauges[key] = value
        logger.debug(f"仪表盘设置: {key} = {value}")
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图数据"""
        key = self._make_key(name, tags)
        point = MetricPoint(timestamp=time.time(), value=value, tags=tags or {})
        self.histograms[key].append(point)
        logger.debug(f"直方图记录: {key} = {value}")
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """记录计时器"""
        key = self._make_key(name, tags)
        self.timers[key].append(duration)
        
        # 保留最近的记录
        if len(self.timers[key]) > 1000:
            self.timers[key] = self.timers[key][-1000:]
        
        logger.debug(f"计时器记录: {key} = {duration:.3f}s")
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """生成指标键"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def get_metric(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """获取指标值"""
        key = self._make_key(name, tags)
        
        if key in self.counters:
            return self.counters[key]
        elif key in self.gauges:
            return self.gauges[key]
        elif key in self.timers and self.timers[key]:
            return sum(self.timers[key]) / len(self.timers[key])
        
        return None
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """获取直方图统计"""
        key = self._make_key(name, tags)
        
        if key not in self.histograms or not self.histograms[key]:
            return {}
        
        values = [point.value for point in self.histograms[key]]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_callbacks: List[Callable] = []
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.name] = rule
        logger.info(f"添加告警规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"移除告警规则: {rule_name}")
    
    def add_notification_callback(self, callback: Callable[[Alert], None]):
        """添加通知回调"""
        self.notification_callbacks.append(callback)
    
    async def check_rules(self, metrics_collector: MetricsCollector):
        """检查告警规则"""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                # 获取指标值
                metric_value = metrics_collector.get_metric(rule.metric_name)
                if metric_value is None:
                    continue
                
                # 检查条件
                should_alert = self._evaluate_condition(metric_value, rule.condition, rule.threshold)
                
                if should_alert:
                    await self._trigger_alert(rule, metric_value)
                else:
                    await self._resolve_alert(rule_name, metric_value)
                    
            except Exception as e:
                logger.error(f"检查告警规则 {rule_name} 时出错: {e}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """评估告警条件"""
        conditions = {
            "gt": value > threshold,
            "gte": value >= threshold,
            "lt": value < threshold,
            "lte": value <= threshold,
            "eq": value == threshold,
        }
        
        return conditions.get(condition, False)
    
    async def _trigger_alert(self, rule: AlertRule, metric_value: float):
        """触发告警"""
        if rule.name in self.active_alerts:
            return  # 告警已激活
        
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=rule.message,
            timestamp=time.time(),
            metric_value=metric_value
        )
        
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"触发告警: {rule.name} - {rule.message}")
        
        # 发送通知
        for callback in self.notification_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"发送告警通知时出错: {e}")
    
    async def _resolve_alert(self, rule_name: str, metric_value: float):
        """解决告警"""
        if rule_name not in self.active_alerts:
            return
        
        alert = self.active_alerts[rule_name]
        alert.resolved = True
        alert.metric_value = metric_value
        
        del self.active_alerts[rule_name]
        
        logger.info(f"告警已解决: {rule_name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics_collector = MetricsCollector(
            max_points=self.config.get("max_metric_points", 10000)
        )
        self.alert_manager = AlertManager()
        self.is_initialized = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 默认告警规则
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                metric_name="error_rate",
                condition="gt",
                threshold=0.1,  # 10%
                severity=AlertSeverity.HIGH,
                message="错误率过高"
            ),
            AlertRule(
                name="high_response_time",
                metric_name="response_time_p95",
                condition="gt",
                threshold=5.0,  # 5秒
                severity=AlertSeverity.MEDIUM,
                message="响应时间过长"
            ),
            AlertRule(
                name="low_cache_hit_rate",
                metric_name="cache_hit_rate",
                condition="lt",
                threshold=0.5,  # 50%
                severity=AlertSeverity.LOW,
                message="缓存命中率过低"
            ),
        ]
        
        for rule in default_rules:
            self.alert_manager.add_rule(rule)
    
    async def initialize(self):
        """初始化监控器"""
        try:
            logger.info("初始化性能监控器...")
            
            # 启动监控任务
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
            self.is_initialized = True
            logger.info("性能监控器初始化完成")
            
        except Exception as e:
            logger.error(f"性能监控器初始化失败: {e}")
            raise
    
    async def track_request_start(self, request_id: str, start_time: float):
        """跟踪请求开始"""
        self.metrics_collector.increment_counter("requests_total")
        logger.debug(f"开始跟踪请求: {request_id}")
    
    async def track_request_end(self, request_id: str, status: str, duration: float):
        """跟踪请求结束"""
        # 记录响应时间
        self.metrics_collector.record_timer("response_time", duration)
        
        # 记录状态
        self.metrics_collector.increment_counter(f"requests_{status}")
        
        if status == "error":
            self.metrics_collector.increment_counter("errors_total")
        
        # 计算错误率
        total_requests = self.metrics_collector.get_metric("requests_total")
        total_errors = self.metrics_collector.get_metric("errors_total")
        
        if total_requests > 0:
            error_rate = total_errors / total_requests
            self.metrics_collector.set_gauge("error_rate", error_rate)
        
        logger.debug(f"请求跟踪完成: {request_id} - {status} - {duration:.3f}s")
    
    def track_cache_operation(self, operation: str, hit: bool = None):
        """跟踪缓存操作"""
        self.metrics_collector.increment_counter(f"cache_{operation}")
        
        if hit is not None:
            if hit:
                self.metrics_collector.increment_counter("cache_hits")
            else:
                self.metrics_collector.increment_counter("cache_misses")
            
            # 计算命中率
            hits = self.metrics_collector.get_metric("cache_hits")
            misses = self.metrics_collector.get_metric("cache_misses")
            total = hits + misses
            
            if total > 0:
                hit_rate = hits / total
                self.metrics_collector.set_gauge("cache_hit_rate", hit_rate)
    
    def track_model_call(self, model_name: str, duration: float, success: bool):
        """跟踪模型调用"""
        tags = {"model": model_name}
        
        self.metrics_collector.record_timer("model_call_duration", duration, tags)
        self.metrics_collector.increment_counter("model_calls_total", tags=tags)
        
        if success:
            self.metrics_collector.increment_counter("model_calls_success", tags=tags)
        else:
            self.metrics_collector.increment_counter("model_calls_error", tags=tags)
    
    async def _monitor_loop(self):
        """监控循环"""
        check_interval = self.config.get("alert_check_interval", 30)  # 30秒
        
        while self.is_initialized:
            try:
                # 检查告警规则
                await self.alert_manager.check_rules(self.metrics_collector)
                
                # 等待下次检查
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(5)  # 错误时短暂等待
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {
            "requests": {
                "total": self.metrics_collector.get_metric("requests_total"),
                "success": self.metrics_collector.get_metric("requests_success"),
                "error": self.metrics_collector.get_metric("requests_error"),
                "error_rate": self.metrics_collector.get_metric("error_rate"),
            },
            "response_time": self.metrics_collector.get_histogram_stats("response_time"),
            "cache": {
                "hits": self.metrics_collector.get_metric("cache_hits"),
                "misses": self.metrics_collector.get_metric("cache_misses"),
                "hit_rate": self.metrics_collector.get_metric("cache_hit_rate"),
            },
            "alerts": {
                "active": len(self.alert_manager.get_active_alerts()),
                "total": len(self.alert_manager.get_alert_history()),
            }
        }
        
        return summary
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控器状态"""
        return {
            "initialized": self.is_initialized,
            "metrics_count": len(self.metrics_collector.counters) + len(self.metrics_collector.gauges),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "alert_rules": len(self.alert_manager.rules),
        }
    
    async def shutdown(self):
        """关闭监控器"""
        logger.info("正在关闭性能监控器...")
        
        self.is_initialized = False
        
        # 取消监控任务
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("性能监控器已关闭")
