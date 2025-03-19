"""
LLM基础接口类定义
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

class BaseLLM(ABC):
    """大语言模型基础接口类"""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """
        初始化LLM接口
        
        Args:
            api_key: API密钥
            model: 模型名称
            **kwargs: 其他参数
        """
        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs
        
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]],
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与LLM进行对话，支持function calling
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            LLM响应结果
        """
        pass
    
    @abstractmethod
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将统一格式的函数定义转换为特定LLM的格式
        
        Args:
            functions: 统一格式的函数定义列表
            
        Returns:
            特定LLM格式的函数定义列表
        """
        pass
    
    @abstractmethod
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        解析LLM的原始响应为统一格式
        
        Args:
            response: LLM的原始响应
            
        Returns:
            统一格式的响应，包含content和function_call等字段
        """
        pass 