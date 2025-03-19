"""
Claude API实现
"""
import json
from typing import Dict, List, Any, Optional
import anthropic
from .base import BaseLLM

class ClaudeLLM(BaseLLM):
    """Claude API实现"""
    
    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-20250219", **kwargs):
        """
        初始化Claude LLM接口
        
        Args:
            api_key: Claude API密钥
            model: Claude模型名称，默认为claude-3-opus-20240229
            **kwargs: 其他参数
        """
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.Anthropic(api_key=api_key)
        
    def chat(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]],
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与Claude进行对话，支持function calling
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            Claude响应结果
        """
        formatted_functions = self.format_functions(functions)
        
        try:
            # 转换消息格式
            anthropic_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                content = msg["content"]
                anthropic_messages.append({"role": role, "content": content})
            
            # 设置参数
            params = {
                "model": self.model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
                "system": "你是一位专业的3D建模助手，可以通过自然语言指令控制Blender软件进行3D建模。"
            }
            
            # 添加工具（函数）
            if formatted_functions:
                params["tools"] = formatted_functions
                
            # 调用API
            response = self.client.messages.create(**params)
            
            # 解析响应
            return self.parse_response(response)
        
        except Exception as e:
            return {
                "content": f"与Claude API通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将统一格式的函数定义转换为Claude的格式
        
        Args:
            functions: 统一格式的函数定义列表
            
        Returns:
            Claude格式的函数定义列表
        """
        claude_tools = []
        for func in functions:
            claude_tool = {
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": func.get("required", [])
                }
            }
            
            # 添加参数
            if "parameters" in func:
                for param_name, param_info in func["parameters"].items():
                    claude_tool["input_schema"]["properties"][param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", "")
                    }
                    
                    # 处理枚举类型
                    if "enum" in param_info:
                        claude_tool["input_schema"]["properties"][param_name]["enum"] = param_info["enum"]
            
            claude_tools.append(claude_tool)
            
        return claude_tools
    
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        解析Claude的原始响应为统一格式
        
        Args:
            response: Claude的原始响应
            
        Returns:
            统一格式的响应，包含content和function_call等字段
        """
        result = {
            "content": None,
            "function_call": None
        }
        
        # 处理纯文本内容
        text_blocks = []
        for content_block in response.content:
            if content_block.type == "text":
                text_blocks.append(content_block.text)
        
        if text_blocks:
            result["content"] = "\n".join(text_blocks)
        
        # 处理工具调用
        if hasattr(response, "tool_use") and response.tool_use:
            tool_use = response.tool_use[0]  # 获取第一个工具调用
            result["function_call"] = {
                "name": tool_use.name,
                "arguments": tool_use.input
            }
        
        return result 