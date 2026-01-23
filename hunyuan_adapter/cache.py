"""图片缓存模块"""

import hashlib
import time
from collections import OrderedDict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class ImageCache:
    """LRU 图片缓存，支持 TTL 过期"""
    
    def __init__(self, max_size=1000, ttl=3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def generate_cache_key(self, image_content):
        """生成缓存键（原 _generate_cache_key）"""
        return self._generate_cache_key(image_content)
    
    def _generate_cache_key(self, image_content):
        """生成缓存键"""
        if not image_content:
            return None
            
        # 处理单个图片内容
        if isinstance(image_content, dict) and image_content.get("type") == "image_url":
            return self._generate_single_image_key(image_content)
        
        # 处理图片列表
        if isinstance(image_content, list):
            keys = []
            for img in image_content:
                key = self._generate_single_image_key(img)
                if key:
                    keys.append(key)
            return "|".join(keys) if keys else None
        
        return None
    
    def _generate_single_image_key(self, image_item):
        """为单张图片生成缓存键"""
        image_url = image_item.get("image_url", {})
        if isinstance(image_url, dict):
            url = image_url.get("url", "")
        else:
            url = str(image_url)
        
        if url.startswith("data:image/"):
            # Base64图片：提取数据部分并计算SHA256
            return self._generate_base64_key(url)
        elif url.startswith("http"):
            # URL图片：规范化URL
            return self._generate_url_key(url)
        else:
            # 其他情况
            return f"img_unknown_{hash(url) % 1000000}"
    
    def _generate_base64_key(self, data_url):
        """为base64图片生成SHA256哈希键"""
        try:
            # 提取base64数据部分
            if "," in data_url:
                header, data_part = data_url.split(",", 1)
            else:
                data_part = data_url
            
            # 计算SHA256哈希
            hash_obj = hashlib.sha256(data_part.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()
            return f"img_b64_{hash_hex}"
        except Exception:
            # 如果解析失败，使用备用方案
            return f"img_b64_{hash(data_url) % 1000000}"
    
    def _generate_url_key(self, url):
        """为URL图片生成规范化键"""
        try:
            parsed = urlparse(url)
            # 规范化查询参数（排序）
            if parsed.query:
                params = parse_qs(parsed.query)
                normalized_query = urlencode(sorted(params.items()), doseq=True)
            else:
                normalized_query = ""
            
            # 重建规范化URL
            normalized_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                normalized_query,
                parsed.fragment
            ))
            
            return f"img_url_{hash(normalized_url) % 1000000}"
        except Exception:
            # 如果解析失败，使用简单哈希
            return f"img_url_{hash(url) % 1000000}"
    
    def get(self, key):
        """获取缓存项"""
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        entry = self.cache[key]
        # 检查TTL
        if time.time() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            self.stats['misses'] += 1
            self.stats['evictions'] += 1
            return None
        
        # 移动到末尾（LRU）
        self.cache.move_to_end(key)
        self.stats['hits'] += 1
        return entry['value']
    
    def set(self, key, value):
        """设置缓存项"""
        if key is None:
            return
            
        # 如果缓存已满，移除最老的条目
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.stats['evictions'] += 1
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        self.cache.move_to_end(key)
        self.stats['size'] = len(self.cache)
    
    def delete(self, key):
        """删除特定缓存项"""
        if key in self.cache:
            del self.cache[key]
            self.stats['size'] = len(self.cache)
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def get_stats(self):
        """获取缓存统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate': round(hit_rate, 2),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl
        }
