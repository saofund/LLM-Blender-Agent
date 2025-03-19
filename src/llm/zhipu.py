"""
智谱AI API实现
"""
import json
from typing import Dict, List, Any, Optional
import zhipuai
from .base import BaseLLM

class ZhipuLLM(BaseLLM):
    """智谱AI API实现"""
    
    def __init__(self, api_key: str, model: str = "glm-4", **kwargs):
        """
        初始化智谱AI LLM接口
        
        Args:
            api_key: 智谱AI API密钥
            model: 智谱AI模型名称，默认为glm-4
            **kwargs: 其他参数
        """
        super().__init__(api_key, model, **kwargs)
        zhipuai.api_key = api_key
        self.client = zhipuai.ZhipuAI()
        
    def chat(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]],
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与智谱AI进行对话，支持function calling
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            智谱AI响应结果
        """
        formatted_functions = self.format_functions(functions)
        
        try:
            # 准备参数
            params = {
                "model": self.model,
                "messages": messages,  # 智谱AI的消息格式与我们的统一格式相同
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
                "content": f"与智谱AI API通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将统一格式的函数定义转换为智谱AI的格式
        
        Args:
            functions: 统一格式的函数定义列表
            
        Returns:
            智谱AI格式的函数定义列表
        """
        # 智谱AI的工具格式与OpenAI兼容
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
        解析智谱AI的原始响应为统一格式
        
        Args:
            response: 智谱AI的原始响应
            
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