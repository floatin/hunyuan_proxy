"""混元消息修正回调模块"""

import os
import copy
import litellm
import time
from litellm.integrations.custom_logger import CustomLogger
from dotenv import load_dotenv

from .cache import ImageCache

load_dotenv()

# 配置
CASCADE_CONFIG = {
    "vision_model": "hunyuan-vision-1.5-instruct",
    "text_model": "hunyuan-2.0-thinking-20251109",
    "api_key": os.getenv("API_KEY"),
    "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
    "cache_max_size": 1000,
    "cache_ttl": 3600,
    "enable_cache_logging": True,
}

class HunyuanMessageFixer(CustomLogger):
    """LiteLLM 自定义回调：消息格式修正 + 级联处理"""
    
    def __init__(self):
        super().__init__()
        # 初始化图片缓存，使用配置参数
        cache_max_size = CASCADE_CONFIG.get("cache_max_size", 1000)
        cache_ttl = CASCADE_CONFIG.get("cache_ttl", 3600)
        self.image_cache = ImageCache(max_size=cache_max_size, ttl=cache_ttl)
        self.enable_cache_logging = CASCADE_CONFIG.get("enable_cache_logging", True)
    
    def _contains_image(self, content) -> bool:
        """检测内容中是否包含图片"""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "image_url":
                        return True
                    # 检查 image_url 中的 url
                    image_url = item.get("image_url", {})
                    if isinstance(image_url, dict):
                        url = image_url.get("url", "")
                        if url.startswith("data:image/") or url.startswith("http"):
                            return True
        elif isinstance(content, str):
            if content.startswith("data:image/"):
                return True
        return False
    
    def _extract_images_from_content(self, content) -> tuple:
        """
        从内容中提取图片和文本
        返回: (图片列表, 纯文本内容)
        """
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
    
    def _has_images_in_messages(self, messages: list) -> bool:
        """检查消息列表中是否包含图片"""
        for msg in messages:
            content = msg.get("content")
            if self._contains_image(content):
                return True
        return False
    
    async def _analyze_image_with_vision_model(self, image_content: list, context_text: str) -> str:
        """
        使用视觉模型分析图片（带缓存）
        返回图片的文本描述
        """
        try:
            # 生成缓存键
            cache_key = self.image_cache.generate_cache_key(image_content)
            if cache_key:
                # 检查缓存
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
                model=f"openai/{CASCADE_CONFIG['vision_model']}",
                messages=vision_messages,
                api_key=CASCADE_CONFIG["api_key"],
                api_base=CASCADE_CONFIG["api_base"],
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
    
    def clear_image_cache(self):
        """清空图片缓存"""
        self.image_cache.clear()
        print(f"[HunyuanCascade] 图片缓存已清空")
    
    def get_cache_stats(self):
        """获取缓存统计信息"""
        stats = self.image_cache.get_stats()
        if self.enable_cache_logging:
            print(f"[CacheStats] 命中率: {stats['hit_rate']}%, 命中: {stats['hits']}, 未命中: {stats['misses']}, 大小: {stats['size']}/{stats['max_size']}")
        return stats
    
    def delete_cache_entry(self, cache_key):
        """删除特定缓存项"""
        success = self.image_cache.delete(cache_key)
        if success:
            print(f"[HunyuanCascade] 缓存项已删除: {cache_key}")
        else:
            print(f"[HunyuanCascade] 缓存项不存在: {cache_key}")
        return success
    
    async def _process_cascade(self, data: dict) -> dict:
        """
        级联处理：图片先由视觉模型分析，然后转为文本给文本模型处理（带缓存）
        """
        messages = data.get("messages", [])
        processed_messages = []
        
        for msg in messages:
            content = msg.get("content")
            role = msg.get("role")
            
            if self._contains_image(content):
                # 提取图片和文本
                images, text = self._extract_images_from_content(content)
                
                if images:
                    # 为批量图片生成缓存键（包含上下文信息）
                    cache_key = self.image_cache.generate_cache_key(images)
                    if cache_key:
                        # 在缓存键中包含上下文摘要以确保准确性
                        context_hash = hash(text) % 1000000
                        full_cache_key = f"{cache_key}_ctx_{context_hash}"
                        
                        # 检查缓存
                        cached_result = self.image_cache.get(full_cache_key)
                        if cached_result:
                            print(f"[HunyuanCascade] 级联处理缓存命中")
                            description = cached_result
                        else:
                            # 调用视觉模型分析图片
                            description = await self._analyze_image_with_vision_model(images, text)
                            # 存入缓存
                            self.image_cache.set(full_cache_key, description)
                    else:
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
        data["model"] = CASCADE_CONFIG["text_model"]
        print(f"[HunyuanCascade] 模型切换: {original_model} -> {CASCADE_CONFIG['text_model']}")
        
        return data
    
    def _ensure_content_not_empty(self, msg: dict) -> dict:
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
                    # 从 tool_calls 生成描述
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
    
    def _fix_messages(self, messages: list) -> list:
        """
        修正消息列表，使其兼容混元大模型
        
        混元约束：
        1. messages 必须以 user 或 tool 结尾
        2. tool 后面如果是 user，需要在中间插入 assistant 消息
        3. 所有消息的 content 不能为空
        
        解决方案：保留完整的工具调用链，只在 tool→user 之间插入 assistant 消息
        """
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
                    # 生成简短的工具结果摘要
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
        data: dict,
        call_type: str,
    ):
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
            
            # 记录完整的原始请求（用于调试）
            print(f"[HunyuanFixer] ====== 处理后请求 ======")
            print(f"[HunyuanFixer] messages 数量: {len(data.get('messages', []))}")
            for i, msg in enumerate(data.get("messages", [])):
                role = msg.get("role")
                content = msg.get("content")
                tool_calls = msg.get("tool_calls")
                tool_call_id = msg.get("tool_call_id")
                
                # 截断 content 用于日志
                content_str = str(content) if content else ""
                content_preview = content_str[:100] + "..." if len(content_str) > 100 else content_str
                
                print(f"[HunyuanFixer] msg[{i}]: role={role}, content={content_preview}, tool_calls={bool(tool_calls)}, tool_call_id={tool_call_id}")
            print(f"[HunyuanFixer] ====== 处理后请求结束 ======")
            
            # 修正消息（确保以 user 或 tool 结尾等）
            if "messages" in data:
                data["messages"] = self._fix_messages(data["messages"])
            
            # 移除混元不支持的参数
            unsupported_params = [
                "parallel_tool_calls",  # 混元不支持并行工具调用
                "reasoning_effort",     # 混元不支持
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
                        # 移除 function 中的 strict 字段
                        if "function" in cleaned_tool and isinstance(cleaned_tool["function"], dict):
                            cleaned_tool["function"].pop("strict", None)
                        cleaned_tools.append(cleaned_tool)
                data["tools"] = cleaned_tools
                print(f"[HunyuanFixer] 清理 tools 参数，共 {len(cleaned_tools)} 个工具")
        
        return data
