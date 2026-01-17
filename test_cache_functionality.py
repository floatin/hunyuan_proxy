#!/usr/bin/env python3
"""
测试图片缓存功能的简单脚本
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from proxy_handler import ImageCache, HunyuanMessageFixer

def test_cache_key_generation():
    """测试缓存键生成"""
    print("=== 测试缓存键生成 ===")
    cache = ImageCache()
    
    # 测试base64图片
    base64_img = {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"}
    }
    key1 = cache._generate_single_image_key(base64_img)
    print(f"Base64图片键: {key1}")
    
    # 测试URL图片
    url_img = {
        "type": "image_url", 
        "image_url": {"url": "https://example.com/image.png?param1=value1&param2=value2"}
    }
    key2 = cache._generate_single_image_key(url_img)
    print(f"URL图片键: {key2}")
    
    # 测试图片列表
    img_list = [base64_img, url_img]
    list_key = cache._generate_cache_key(img_list)
    print(f"图片列表键: {list_key}")
    
    print("✅ 缓存键生成测试完成\n")

def test_cache_operations():
    """测试缓存基本操作"""
    print("=== 测试缓存基本操作 ===")
    cache = ImageCache(max_size=2, ttl=10)  # 小容量用于测试
    
    # 测试设置和获取
    test_key = "test_key_123"
    test_value = "这是测试的描述内容"
    
    cache.set(test_key, test_value)
    retrieved = cache.get(test_key)
    print(f"设置并获取缓存: {retrieved == test_value}")
    
    # 测试缓存命中率统计
    stats_before = cache.get_stats()
    print(f"初始统计: {stats_before}")
    
    # 测试缓存未命中
    missed = cache.get("non_existent_key")
    print(f"缓存未命中返回: {missed}")
    
    stats_after = cache.get_stats()
    print(f"操作后统计: {stats_after}")
    
    # 测试LRU淘汰
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # 应该淘汰key1
    
    print(f"淘汰后key1存在: {cache.get('key1') is not None}")
    print(f"淘汰后key2存在: {cache.get('key2') is not None}")
    print(f"淘汰后key3存在: {cache.get('key3') is not None}")
    
    print("✅ 缓存基本操作测试完成\n")

def test_hunyuan_message_fixer():
    """测试HunyuanMessageFixer的缓存功能"""
    print("=== 测试HunyuanMessageFixer缓存功能 ===")
    fixer = HunyuanMessageFixer()
    
    # 检查缓存是否正确初始化
    print(f"缓存实例: {fixer.image_cache is not None}")
    print(f"缓存配置 - 最大大小: {fixer.image_cache.max_size}")
    print(f"缓存配置 - TTL: {fixer.image_cache.ttl}")
    
    # 测试缓存统计接口
    stats = fixer.get_cache_stats()
    print(f"初始缓存统计: {stats}")
    
    # 测试缓存清理接口
    fixer.clear_image_cache()
    print("✅ 已清空缓存")
    
    stats_after_clear = fixer.get_cache_stats()
    print(f"清空后缓存统计: {stats_after_clear}")
    
    print("✅ HunyuanMessageFixer缓存功能测试完成\n")

def main():
    """运行所有测试"""
    print("开始测试图片缓存功能...\n")
    
    try:
        test_cache_key_generation()
        test_cache_operations()
        test_hunyuan_message_fixer()
        
        print("🎉 所有测试完成！缓存功能基本实现。")
        print("\n注意: 完整测试需要视觉模型API调用，此处仅测试基础功能。")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()