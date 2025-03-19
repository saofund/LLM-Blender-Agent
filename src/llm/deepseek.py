"""
DeepSeek API实现
"""
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from .base import BaseLLM

class DeepSeekLLM(BaseLLM):
    """DeepSeek API实现（基于OpenAI兼容接口）"""
    
    def __init__(self, api_key: str, model: str = "deepseek-coder-v2", **kwargs):
        """
        初始化DeepSeek LLM接口
        
        Args:
            api_key: DeepSeek API密钥
            model: DeepSeek模型名称，默认为deepseek-coder-v2
            **kwargs: 其他参数，包括api_base等
        """
        super().__init__(api_key, model, **kwargs)
        api_base = kwargs.get("api_base", "https://api.deepseek.com/v1")
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        
    def chat(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]],
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与DeepSeek进行对话，支持function calling
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            DeepSeek响应结果
        """
        formatted_functions = self.format_functions(functions)
        
        try:
            # 准备参数
            params = {
                "model": self.model,
                "messages": messages,  # DeepSeek的消息格式与我们的统一格式相同
                "temperature": temperature,
                "max_tokens": max_tokens or 4096
            }
            
            # 添加工具（函数）
            if formatted_functions:
                params["tools"] = formatted_functions
                params["tool_choice"] = "auto"
                
            # 调用API
            response = self.client.chat.completions.create(**params)
            
            # 解析响应
            return self.parse_response(response)
        
        except Exception as e:
            return {
                "content": f"与DeepSeek API通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将统一格式的函数定义转换为DeepSeek的格式（兼容OpenAI格式）
        
        Args:
            functions: 统一格式的函数定义列表
            
        Returns:
            DeepSeek格式的函数定义列表
        """
        formatted_tools = []
        for func in functions:
            tool = {
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": func.get("required", [])
                    }
                }
            }
            
            # 添加参数
            if "parameters" in func:
                for param_name, param_info in func["parameters"].items():
                    tool["function"]["parameters"]["properties"][param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", "")
                    }
                    
                    # 处理枚举类型
                    if "enum" in param_info:
                        tool["function"]["parameters"]["properties"][param_name]["enum"] = param_info["enum"]
            
            formatted_tools.append(tool)
            
        return formatted_tools
    
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        解析DeepSeek的原始响应为统一格式
        
        Args:
            response: DeepSeek的原始响应
            
        Returns:
            统一格式的响应，包含content和function_call等字段
        """
        result = {
            "content": None,
            "function_call": None
        }
        
        # 获取消息内容
        message = response.choices[0].message
        
        # 处理文本内容
        if hasattr(message, "content") and message.content:
            result["content"] = message.content
        
        # 处理工具调用
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_call = message.tool_calls[0]  # 获取第一个工具调用
            if tool_call.type == "function":
                function_call = tool_call.function
                # 解析参数JSON
                arguments = json.loads(function_call.arguments) if isinstance(function_call.arguments, str) else function_call.arguments
                
                result["function_call"] = {
                    "name": function_call.name,
                    "arguments": arguments
                }
        
        return result 