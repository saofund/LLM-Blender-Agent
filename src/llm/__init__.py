"""
LLM模块初始化文件和工厂类
"""
import json
import os
from typing import Dict, Any, Optional

from .base import BaseLLM
from .claude import ClaudeLLM
from .zhipu import ZhipuLLM
from .deepseek import DeepSeekLLM

# 支持的LLM模型
LLM_MODELS = {
    "claude": ClaudeLLM,
    "zhipu": ZhipuLLM,
    "deepseek": DeepSeekLLM
}

class LLMFactory:
    """LLM工厂类，用于创建LLM实例"""
    
    @staticmethod
    def create_llm(model_type: str, config: Dict[str, Any]) -> Optional[BaseLLM]:
        """
        根据配置创建LLM实例
        
        Args:
            model_type: 模型类型，如"claude"、"zhipu"、"deepseek"
            config: 配置参数
            
        Returns:
            LLM实例
        """
        if model_type not in LLM_MODELS:
            raise ValueError(f"不支持的LLM类型: {model_type}，支持的类型有: {', '.join(LLM_MODELS.keys())}")
            
        llm_class = LLM_MODELS[model_type]
        api_key = config.get("api_key", "")
        model = config.get("model", "")
        
        # 额外参数
        kwargs = {k: v for k, v in config.items() if k not in ["api_key", "model"]}
        
        return llm_class(api_key=api_key, model=model, **kwargs)
    
    @staticmethod
    def create_from_config_file(config_file: str = "config.json", model_type: Optional[str] = None) -> BaseLLM:
        """
        从配置文件创建LLM实例
        
        Args:
            config_file: 配置文件路径
            model_type: 指定模型类型，如果为None则使用配置中的默认模型
            
        Returns:
            LLM实例
        """
        # 读取配置文件
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
            
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        # 获取LLM配置
        llm_config = config.get("llm", {})
        
        # 确定要使用的模型类型
        if model_type is None:
            model_type = llm_config.get("default_model", "claude")
            
        if model_type not in llm_config:
            raise ValueError(f"配置文件中未找到模型类型: {model_type}")
            
        # 创建LLM实例
        model_config = llm_config.get(model_type, {})
        return LLMFactory.create_llm(model_type, model_config) 