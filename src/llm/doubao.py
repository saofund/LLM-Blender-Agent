"""
豆包API实现（火山方舟）
"""
import json
from typing import Dict, List, Any, Optional
from volcenginesdkarkruntime import Ark
from .base import BaseLLM

class DoubaoLLM(BaseLLM):
    """豆包API实现（基于火山方舟SDK）"""
    
    def __init__(self, api_key: str, model: str = "doubao-pro", **kwargs):
        """
        初始化豆包LLM接口
        
        Args:
            api_key: 豆包API密钥
            model: 豆包模型名称，默认为doubao-pro
            **kwargs: 其他参数，包括api_base等
        """
        super().__init__(api_key, model, **kwargs)
        self.client = Ark(api_key=api_key)
        
    def chat(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]],
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与豆包进行对话，支持function calling
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            豆包响应结果
        """
        formatted_functions = self.format_functions(functions)
        
        try:
            # 准备参数
            params = {
                "model": self.model,
                "messages": messages,  # 火山方舟的消息格式与我们的统一格式相同
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
                "content": f"与豆包API通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将统一格式的函数定义转换为豆包API的格式
        
        Args:
            functions: 统一格式的函数定义列表
            
        Returns:
            豆包API格式的函数定义列表
        """
        if not functions:
            return []
        
        # 豆包API的函数定义格式与OpenAI兼容
        formatted_functions = []
        for func in functions:
            formatted_function = {
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {})
                }
            }
            formatted_functions.append(formatted_function)
        
        return formatted_functions
    
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        解析豆包API的原始响应为统一格式
        
        Args:
            response: 豆包API的原始响应
            
        Returns:
            统一格式的响应，包含content和function_call等字段
        """
        result = {
            "content": None,
            "function_call": None,
        }
        
        try:
            # 获取消息内容
            choice = response.choices[0]
            message = choice.message
            
            if hasattr(message, "content") and message.content:
                result["content"] = message.content
                
            # 处理函数调用
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_call = message.tool_calls[0]
                if tool_call.type == "function":
                    result["function_call"] = {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                    
            return result
            
        except Exception as e:
            result["content"] = f"解析豆包API响应出错: {str(e)}"
            result["error"] = str(e)
            return result 