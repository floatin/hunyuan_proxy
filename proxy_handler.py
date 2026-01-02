import json
import copy
import litellm
from litellm.integrations.custom_logger import CustomLogger

class HunyuanMessageFixer(CustomLogger):
    """
    LiteLLM 自定义回调：在请求发送到混元之前修正消息格式
    混元要求：messages 必须以 user 或 tool 结尾
    """
    
    def __init__(self):
        super().__init__()
    
    def _fix_messages(self, messages: list) -> list:
        """
        修正消息列表，使其兼容混元大模型
        
        混元约束：
        1. messages 必须以 user 或 tool 结尾
        2. tool 后面如果是 user，需要在中间插入 assistant 消息
        
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
            
            # 添加当前消息
            if role == "assistant":
                # 确保 assistant 消息有 content
                if not msg.get("content") or not msg.get("content").strip():
                    if msg.get("tool_calls"):
                        # 从 tool_calls 生成描述
                        tool_names = []
                        for tc in msg.get("tool_calls", []):
                            if isinstance(tc, dict) and "function" in tc:
                                tool_names.append(tc["function"].get("name", "unknown"))
                        msg["content"] = f"我将调用工具：{', '.join(tool_names)}"
                    else:
                        msg["content"] = "..."
                fixed_messages.append(msg)
            else:
                fixed_messages.append(msg)
            
            # 检查是否需要在 tool 和 user 之间插入 assistant
            if role == "tool" and i + 1 < len(messages):
                next_msg = messages[i + 1]
                if next_msg.get("role") == "user":
                    # 在 tool 和 user 之间插入一个过渡 assistant 消息
                    tool_content = msg.get("content", "")
                    # 生成简短的工具结果摘要
                    if len(tool_content) > 200:
                        summary = tool_content[:200] + "..."
                    else:
                        summary = tool_content if tool_content else "工具执行完成"
                    
                    transition_msg = {
                        "role": "assistant",
                        "content": f"工具返回了结果。{summary[:100]}"
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
            # 记录完整的原始请求（用于调试）
            print(f"[HunyuanFixer] ====== 原始请求 ======")
            print(f"[HunyuanFixer] messages 数量: {len(data.get('messages', []))}")
            for i, msg in enumerate(data.get("messages", [])):
                role = msg.get("role")
                content = msg.get("content")
                tool_calls = msg.get("tool_calls")
                tool_call_id = msg.get("tool_call_id")
                
                # 截断 content 用于日志
                content_preview = str(content)[:100] + "..." if content and len(str(content)) > 100 else content
                
                print(f"[HunyuanFixer] msg[{i}]: role={role}, content={content_preview}, tool_calls={bool(tool_calls)}, tool_call_id={tool_call_id}")
            print(f"[HunyuanFixer] ====== 原始请求结束 ======")
            
            # 修正消息
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


# 创建回调实例
hunyuan_fixer = HunyuanMessageFixer()

# 设置 litellm 参数
litellm.drop_params = True
litellm.callbacks = [hunyuan_fixer]

if __name__ == "__main__":
    import uvicorn
    from litellm.proxy.proxy_server import app
    
    # 加载配置
    from litellm.proxy.proxy_server import initialize
    import asyncio
    
    async def start_server():
        # 初始化 proxy 配置
        await initialize(config="config.yaml")
        
        # 运行服务器
        config = uvicorn.Config(app, host="0.0.0.0", port=4000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(start_server())
