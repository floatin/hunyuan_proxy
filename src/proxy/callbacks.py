"""
LiteLLM 回调实现模块

从原 proxy_handler.py 提取并重构的回调功能：
- HunyuanMessageFixer: 主要回调类
- ImageCache: 图片缓存管理
- 级联处理逻辑
"""

import os
import copy
import litellm
import hashlib
import time
import re
from collections import OrderedDict
from litellm.integrations.custom_logger import CustomLogger
from typing import Optional, List, Dict, Any, Tuple

# 级联处理配置
DEFAULT_CONFIG = {
    "vision_model": "hunyuan-vision-1.5-instruct",
    "text_model": "hunyuan-2.0-thinking-20251109",
    "api_key": os.getenv("API_KEY"),
    "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
    "cache_max_size": 1000,
    "cache_ttl": 3600,
    "enable_cache_logging": True,
}


class ImageCache:
    """高性能图片缓存类"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_cache_key(self, image_content) -> Optional[str]:
        """生成缓存键"""
        if not image_content:
            return None
            
        if isinstance(image_content, dict) and image_content.get("type") == "image_url":
            return self._generate_single_image_key(image_content)
        
        if isinstance(image_content, list):
            keys = []
            for img in image_content:
                key = self._generate_single_image_key(img)
                if key:
                    keys.append(key)
            return "|".join(keys) if keys else None
        
        return None
    
    def _generate_single_image_key(self, image_item: dict) -> Optional[str]:
        """为单张图片生成缓存键"""
        image_url = image_item.get("image_url", {})
        if isinstance(image_url, dict):
            url = image_url.get("url", "")
        else:
            url = str(image_url)
        
        if url.startswith("data:image/"):
            return self._generate_base64_key(url)
        elif url.startswith("http"):
            return self._generate_url_key(url)
        else:
            return f"img_unknown_{hash(url) % 1000000}"
    
    def _generate_base64_key(self, data_url: str) -> str:
        """为base64图片生成SHA256哈希键"""
        try:
            if "," in data_url:
                header, data_part = data_url.split(",", 1)
            else:
                data_part = data_url
            
            hash_obj = hashlib.sha256(data_part.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()
            return f"img_b64_{hash_hex}"
        except Exception:
            return f"img_b64_{hash(data_url) % 1000000}"
    
    def _generate_url_key(self, url: str) -> str:
        """为URL图片生成规范化键"""
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            parsed = urlparse(url)
            if parsed.query:
                params = parse_qs(parsed.query)
                normalized_query = urlencode(sorted(params.items()), doseq=True)
            else:
                normalized_query = ""
            
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
            return f"img_url_{hash(url) % 1000000}"
    
    def get(self, key: str) -> Optional[str]:
        """获取缓存项"""
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        entry = self.cache[key]
        if time.time() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            self.stats['misses'] += 1
            self.stats['evictions'] += 1
            return None
        
        self.cache.move_to_end(key)
        self.stats['hits'] += 1
        return entry['value']
    
    def set(self, key: str, value: str):
        """设置缓存项"""
        if key is None:
            return
            
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
    
    def get_stats(self) -> Dict[str, Any]:
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
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }


class HunyuanMessageFixer(CustomLogger):
    """
    LiteLLM 自定义回调：在请求发送到混元之前修正消息格式
    
    功能：
    1. 消息格式修正（确保以 user 或 tool 结尾）
    2. 级联处理（图片→文本）
    3. 参数清理
    4. 缓存管理
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        
        # 初始化图片缓存
        cache_max_size = self.config.get("cache_max_size", 1000)
        cache_ttl = self.config.get("cache_ttl", 3600)
        self.image_cache = ImageCache(max_size=cache_max_size, ttl=cache_ttl)
        self.enable_cache_logging = self.config.get("enable_cache_logging", True)
    
    def _contains_image(self, content) -> bool:
        """检测内容中是否包含图片"""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "image_url":
                        return True
                    image_url = item.get("image_url", {})
                    if isinstance(image_url, dict):
                        url = image_url.get("url", "")
                        if url.startswith("data:image/") or url.startswith("http"):
                            return True
        elif isinstance(content, str):
            if content.startswith("data:image/"):
                return True
        return False
    
    def _extract_images_from_content(self, content) -> Tuple[List[Dict], str]:
        """从内容中提取图片和文本"""
        images = []
        text_parts = []
        
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "image_url":
                        images.append(item)
                    elif item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
        elif isinstance(content, str):
            if content.startswith("data:image/"):
                images.append({"type": "image_url", "image_url": {"url": content}})
            else:
                text_parts.append(content)
        
        return images, " ".join(text_parts)
    
    def _has_images_in_messages(self, messages: List[Dict]) -> bool:
        """检查消息列表中是否包含图片"""
        for msg in messages:
            content = msg.get("content")
            if self._contains_image(content):
                return True
        return False
    
    async def _analyze_image_with_vision_model(self, image_content: List[Dict], context_text: str) -> str:
        """使用视觉模型分析图片（带缓存）"""
        try:
            # 生成缓存键
            cache_key = self.image_cache._generate_cache_key(image_content)
            if cache_key:
                cached_result = self.image_cache.get(cache_key)
                if cached_result:
                    print(f"[HunyuanCascade] 缓存命中，返回缓存的图片分析结果")
                    return cached_result
            
            # 构建视觉模型请求
            vision_messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"请详细描述这张图片的内容，包括所有可见的文字、代码、图表、界面元素等。用户的问题是：{context_text}"},
                        *image_content
                    ]
                }
            ]
            
            print(f"[HunyuanCascade] 调用视觉模型分析图片...")
            
            # 调用视觉模型
            response = await litellm.acompletion(
                model=f"openai/{self.config['vision_model']}",
                messages=vision_messages,
                api_key=self.config["api_key"],
                api_base=self.config["api_base"],
                max_tokens=2000,
            )
            
            # 处理响应
            description = str(response)
            print(f"[HunyuanCascade] 图片分析完成，描述长度: {len(description)}")
            
            # 存入缓存
            if cache_key:
                self.image_cache.set(cache_key, description)
                
            return description
            
        except Exception as e:
            print(f"[HunyuanCascade] 视觉模型调用失败: {e}")
            return f"[图片分析失败: {str(e)}]"
    
    async def _process_cascade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """级联处理：图片先由视觉模型分析，然后转为文本给文本模型处理"""
        messages = data.get("messages", [])
        processed_messages = []
        
        for msg in messages:
            content = msg.get("content")
            role = msg.get("role")
            
            if self._contains_image(content):
                # 提取图片和文本
                images, text = self._extract_images_from_content(content)
                
                if images:
                    # 调用视觉模型分析图片
                    description = await self._analyze_image_with_vision_model(images, text)
                    
                    # 用图片描述替换原内容
                    new_content = f"{text}\n\n[图片内容描述]:\n{description}"
                    
                    processed_messages.append({
                        **msg,
                        "content": new_content
                    })
                    print(f"[HunyuanCascade] 已将图片转换为文本描述")
                else:
                    processed_messages.append(msg)
            else:
                processed_messages.append(msg)
        
        data["messages"] = processed_messages
        
        # 强制使用文本模型（支持工具调用）
        original_model = data.get("model", "")
        data["model"] = self.config["text_model"]
        print(f"[HunyuanCascade] 模型切换: {original_model} -> {self.config['text_model']}")
        
        return data
    
    def _ensure_content_not_empty(self, msg: Dict) -> Dict:
        """确保消息的 content 不为空"""
        msg = copy.deepcopy(msg)
        content = msg.get("content")
        role = msg.get("role", "")
        
        # 检查 content 是否为空
        is_empty = False
        if content is None:
            is_empty = True
        elif isinstance(content, str) and not content.strip():
            is_empty = True
        elif isinstance(content, list) and len(content) == 0:
            is_empty = True
        
        if is_empty:
            if role == "assistant":
                if msg.get("tool_calls"):
                    tool_names = []
                    for tc in msg.get("tool_calls", []):
                        if isinstance(tc, dict) and "function" in tc:
                            tool_names.append(tc["function"].get("name", "unknown"))
                    msg["content"] = f"我将调用工具：{', '.join(tool_names)}"
                else:
                    msg["content"] = "好的，我来处理。"
            elif role == "user":
                msg["content"] = "请继续。"
            elif role == "system":
                msg["content"] = "你是一个有帮助的AI助手。"
            elif role == "tool":
                msg["content"] = "工具执行完成。"
            else:
                msg["content"] = "..."
            print(f"[HunyuanFixer] 修复空 content: role={role}")
        
        return msg
    
    def _fix_messages(self, messages: List[Dict]) -> List[Dict]:
        """修正消息列表，使其兼容混元大模型"""
        if not messages:
            return messages
        
        messages = copy.deepcopy(messages)
        
        # 打印调试信息
        roles = [m.get("role") for m in messages]
        print(f"[HunyuanFixer] 原始消息角色列表: {roles}")
        
        # 策略：保留工具调用链，在 tool→user 之间插入过渡 assistant 消息
        fixed_messages = []
        
        for i, msg in enumerate(messages):
            role = msg.get("role")
            
            # 确保消息 content 不为空
            msg = self._ensure_content_not_empty(msg)
            
            # 添加当前消息
            fixed_messages.append(msg)
            
            # 检查是否需要在 tool 和 user 之间插入 assistant
            if role == "tool" and i + 1 < len(messages):
                next_msg = messages[i + 1]
                if next_msg.get("role") == "user":
                    # 在 tool 和 user 之间插入一个过渡 assistant 消息
                    tool_content = msg.get("content", "")
                    if len(str(tool_content)) > 200:
                        summary = str(tool_content)[:200] + "..."
                    else:
                        summary = tool_content if tool_content else "工具执行完成"
                    
                    transition_msg = {
                        "role": "assistant",
                        "content": f"工具返回了结果。{str(summary)[:100]}"
                    }
                    fixed_messages.append(transition_msg)
                    print(f"[HunyuanFixer] 在 tool 和 user 之间插入 assistant 消息")
        
        # 确保消息以 user 或 tool 结尾
        if fixed_messages:
            last_role = fixed_messages[-1].get("role")
            print(f"[HunyuanFixer] 修正后最后一条消息角色: {last_role}")
            if last_role == "assistant":
                print(f"[HunyuanFixer] 添加 user 消息使序列以 user 结尾")
                fixed_messages.append({"role": "user", "content": "请继续。"})
        
        final_roles = [m.get("role") for m in fixed_messages]
        print(f"[HunyuanFixer] 最终消息角色列表: {final_roles}")
        
        return fixed_messages
    
    async def async_pre_call_hook(
        self,
        user_api_key_dict,
        cache,
        data: Dict[str, Any],
        call_type: str,
    ) -> Dict[str, Any]:
        """在 LLM 调用之前修改请求数据"""
        print(f"[HunyuanFixer] async_pre_call_hook 被调用, call_type={call_type}")
        
        # 只处理 chat completion 请求
        if call_type == "completion" or call_type == "acompletion":
            model_name = data.get("model", "")
            print(f"[HunyuanFixer] 请求模型: {model_name}")
            
            # 检查是否包含图片
            has_images = self._has_images_in_messages(data.get("messages", []))
            
            if has_images:
                print(f"[HunyuanCascade] 检测到图片内容，启动级联处理")
                # 级联处理：先用视觉模型分析图片，再用文本模型处理
                data = await self._process_cascade(data)
            
            # 修正消息（确保以 user 或 tool 结尾等）
            if "messages" in data:
                data["messages"] = self._fix_messages(data["messages"])
            
            # 移除混元不支持的参数
            unsupported_params = [
                "parallel_tool_calls",
                "reasoning_effort",
            ]
            for param in unsupported_params:
                if param in data:
                    print(f"[HunyuanFixer] 移除参数: {param}")
                    data.pop(param, None)
            
            # 清理 tools 参数中混元不支持的字段
            if "tools" in data:
                cleaned_tools = []
                for tool in data.get("tools", []):
                    if isinstance(tool, dict):
                        cleaned_tool = copy.deepcopy(tool)
                        if "function" in cleaned_tool and isinstance(cleaned_tool["function"], dict):
                            cleaned_tool["function"].pop("strict", None)
                        cleaned_tools.append(cleaned_tool)
                data["tools"] = cleaned_tools
                print(f"[HunyuanFixer] 清理 tools 参数，共 {len(cleaned_tools)} 个工具")
        
        return data
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = self.image_cache.get_stats()
        if self.enable_cache_logging:
            print(f"[CacheStats] 命中率: {stats['hit_rate']}%, 命中: {stats['hits']}, 未命中: {stats['misses']}, 大小: {stats['size']}/{stats['max_size']}")
        return stats
    
    def clear_image_cache(self):
        """清空图片缓存"""
        self.image_cache.clear()
        print(f"[HunyuanCascade] 图片缓存已清空")
