#!/usr/bin/env python3
"""
LiteLLM 混元代理使用示例

演示如何使用重构后的代理服务器模块
"""

import asyncio
import os
from src.proxy import ProxyServer, create_proxy_server


async def basic_example():
    """基本使用示例"""
    print("🚀 基本使用示例")
    
    # 使用便捷函数创建服务器
    server = create_proxy_server()
    
    try:
        # 初始化服务器
        await server.initialize()
        print("✅ 服务器初始化完成")
        
        # 获取状态
        status = server.handler.get_status()
        print(f"📊 服务器状态: {status['initialized']}")
        
        # 启动服务器（非阻塞模式，仅用于演示）
        print("🌐 服务器配置完成，可以启动")
        print(f"   - 主机: {server.config['host']}")
        print(f"   - 端口: {server.config['port']}")
        print(f"   - 视觉模型: {server.config['vision_model']}")
        print(f"   - 文本模型: {server.config['text_model']}")
        
    finally:
        # 清理资源
        if server.handler:
            await server.handler.shutdown()
        print("🧹 资源清理完成")


async def custom_config_example():
    """自定义配置示例"""
    print("\n⚙️ 自定义配置示例")
    
    # 创建自定义配置
    config = {
        "host": "127.0.0.1",
        "port": 8080,
        "vision_model": "hunyuan-vision-1.5-instruct",
        "text_model": "hunyuan-2.0-thinking-20251109",
        "api_key": os.getenv("API_KEY", "demo-key"),
        "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
        "cache_max_size": 500,
        "cache_ttl": 1800,
        "enable_monitoring": True,
        "enable_health_check": True,
        "log_level": "INFO",
    }
    
    server = ProxyServer()
    server.config = config
    
    try:
        await server.initialize()
        print("✅ 自定义配置服务器初始化完成")
        
        # 显示配置
        safe_config = server.get_config()
        print("📋 当前配置:")
        for key, value in safe_config.items():
            print(f"   - {key}: {value}")
        
        # 测试缓存功能
        if server.handler.callback_handler:
            cache_stats = server.handler.callback_handler.get_cache_stats()
            print(f"📈 缓存统计: {cache_stats}")
        
    finally:
        if server.handler:
            await server.handler.shutdown()


async def callback_example():
    """回调功能示例"""
    print("\n🔄 回调功能示例")
    
    from src.proxy.callbacks import HunyuanMessageFixer, ImageCache
    
    # 创建回调实例
    config = {
        "vision_model": "hunyuan-vision-1.5-instruct",
        "text_model": "hunyuan-2.0-thinking-20251109",
        "api_key": os.getenv("API_KEY", "demo-key"),
        "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
    }
    
    callback = HunyuanMessageFixer(config)
    
    # 测试缓存功能
    print("🗄️ 测试图片缓存功能:")
    cache = callback.image_cache
    
    # 测试缓存操作
    cache.set("test_key", "test_value")
    value = cache.get("test_key")
    print(f"   - 缓存写入/读取: {value == 'test_value'}")
    
    # 获取缓存统计
    stats = cache.get_stats()
    print(f"   - 缓存统计: {stats}")
    
    # 清理测试数据
    cache.delete("test_key")
    print("   - 测试数据清理完成")


async def monitoring_example():
    """监控功能示例"""
    print("\n📊 监控功能示例")
    
    from src.proxy.monitoring import PerformanceMonitor, AlertRule, AlertSeverity
    
    # 创建监控器
    monitor = PerformanceMonitor()
    
    try:
        await monitor.initialize()
        print("✅ 性能监控器初始化完成")
        
        # 模拟一些指标
        monitor.track_cache_operation("get", hit=True)
        monitor.track_cache_operation("get", hit=False)
        monitor.track_cache_operation("set", hit=None)
        
        monitor.track_model_call("hunyuan-vision", 1.2, True)
        monitor.track_model_call("hunyuan-text", 0.8, True)
        
        # 获取指标摘要
        summary = monitor.get_metrics_summary()
        print("📈 性能指标摘要:")
        print(f"   - 请求总数: {summary['requests']['total']}")
        print(f"   - 缓存命中率: {summary['cache']['hit_rate']:.2%}")
        print(f"   - 活跃告警: {summary['alerts']['active']}")
        
        # 添加自定义告警规则
        custom_rule = AlertRule(
            name="demo_alert",
            metric_name="cache_hit_rate",
            condition="lt",
            threshold=0.8,
            severity=AlertSeverity.LOW,
            message="演示告警：缓存命中率低于80%"
        )
        monitor.alert_manager.add_rule(custom_rule)
        print("🚨 添加自定义告警规则")
        
    finally:
        await monitor.shutdown()


async def health_check_example():
    """健康检查示例"""
    print("\n🏥 健康检查示例")
    
    from src.proxy.health import HealthChecker, ComponentHealth, HealthCheckResult, HealthStatus
    
    # 创建健康检查器
    health_checker = HealthChecker()
    
    try:
        await health_checker.initialize()
        print("✅ 健康检查器初始化完成")
        
        # 添加模拟组件检查
        class MockComponent(ComponentHealth):
            async def _do_check(self) -> HealthCheckResult:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.HEALTHY,
                    message="模拟组件正常",
                    timestamp=asyncio.get_event_loop().time(),
                    duration=0.1
                )
        
        health_checker.register_component("mock_component", MockComponent("mock_component"))
        
        # 运行健康检查
        results = await health_checker.run_checks()
        print("🔍 健康检查结果:")
        for name, result in results.items():
            print(f"   - {name}: {result.status.value} - {result.message}")
        
        # 获取详细健康状态
        detailed_health = await health_checker.get_detailed_health()
        print(f"📊 整体健康状态: {detailed_health['status']}")
        print(f"   - 健康组件: {detailed_health['summary']['healthy']}")
        print(f"   - 异常组件: {detailed_health['summary']['unhealthy']}")
        
    finally:
        await health_checker.shutdown()


async def request_processing_example():
    """请求处理示例"""
    print("\n⚡ 请求处理示例")
    
    from src.proxy.handler import HunyuanProxyHandler
    
    # 创建处理器
    config = {
        "vision_model": "hunyuan-vision-1.5-instruct",
        "text_model": "hunyuan-2.0-thinking-20251109",
        "api_key": os.getenv("API_KEY", "demo-key"),
        "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
        "enable_monitoring": True,
        "enable_health_check": True,
    }
    
    handler = HunyuanProxyHandler(config)
    
    try:
        await handler.initialize()
        print("✅ 请求处理器初始化完成")
        
        # 模拟请求处理
        test_request = {
            "request_id": "test-123",
            "model": "hunyuan-vision",
            "messages": [
                {"role": "user", "content": "你好，请介绍一下你自己。"}
            ],
            "max_tokens": 1000,
        }
        
        print("📨 处理测试请求:")
        print(f"   - 请求ID: {test_request['request_id']}")
        print(f"   - 模型: {test_request['model']}")
        print(f"   - 消息数量: {len(test_request['messages'])}")
        
        # 处理请求
        processed_data = await handler.process_request(test_request)
        print("✅ 请求处理完成")
        
        # 显示处理结果
        print("📤 处理后的数据:")
        print(f"   - 消息数量: {len(processed_data.get('messages', []))}")
        print(f"   - 最终模型: {processed_data.get('model', 'unknown')}")
        
    finally:
        await handler.shutdown()


async def main():
    """主函数 - 运行所有示例"""
    print("🎯 LiteLLM 混元代理模块使用示例\n")
    
    try:
        # 运行各种示例
        await basic_example()
        await custom_config_example()
        await callback_example()
        await monitoring_example()
        await health_check_example()
        await request_processing_example()
        
        print("\n🎉 所有示例运行完成！")
        print("\n📚 更多信息请查看:")
        print("   - src/proxy/README.md - 详细使用文档")
        print("   - MODULE_PLANNING.md - 模块规划文档")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
