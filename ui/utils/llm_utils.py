#!/usr/bin/env python
"""
LLM交互工具函数
"""
import os
import json
import logging

# 默认配置文件路径
DEFAULT_CONFIG_PATH = "config.json"

# 配置日志
logger = logging.getLogger(__name__)

def load_config(config_path=DEFAULT_CONFIG_PATH):
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置信息
    """
    try:
        if not os.path.exists(config_path):
            logger.error(f"配置文件不存在: {config_path}")
            return None
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return config
    
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return None

def get_available_models(config):
    """
    获取可用的模型列表
    
    Args:
        config: 配置信息
        
    Returns:
        可用模型列表
    """
    if not config or "llm" not in config:
        return ["aimlapi"]
    
    llm_config = config.get("llm", {})
    models = []
    
    for model_type, model_config in llm_config.items():
        if model_type != "default_model" and isinstance(model_config, dict):
            models.append(model_type)
    
    return models or ["aimlapi"]

def initialize_agent(session_id, model_type, temperature, blender_clients, agents):
    """
    初始化Agent
    
    Args:
        session_id: 会话ID
        model_type: 模型类型
        temperature: 温度参数
        blender_clients: Blender客户端字典
        agents: Agent字典
        
    Returns:
        初始化状态信息
    """
    try:
        # 检查Blender客户端是否已连接
        if session_id not in blender_clients:
            return "请先连接到Blender"
        
        # 加载配置
        config = load_config()
        if not config:
            return "加载配置失败"
        
        # 创建LLM实例
        from src.llm import LLMFactory
        llm = LLMFactory.create_from_config_file(DEFAULT_CONFIG_PATH, model_type)
        
        # 创建Agent
        from src.agent import BlenderAgent
        agent = BlenderAgent(llm, blender_clients[session_id])
        agents[session_id] = agent
        
        return f"初始化成功，使用模型: {model_type}"
    
    except Exception as e:
        logger.error(f"初始化Agent时出错: {str(e)}")
        return f"初始化出错: {str(e)}"

def get_available_functions(session_id, agents):
    """
    获取可用的函数列表，包含函数名和描述
    
    Args:
        session_id: 会话ID
        agents: Agent字典
        
    Returns:
        函数信息列表 [(name, description), ...]
    """
    if session_id not in agents:
        return []
    
    agent = agents[session_id]
    return [(func["name"], func.get("description", "无描述")) for func in agent.functions]

def get_function_names(session_id, agents):
    """
    仅获取函数名列表
    
    Args:
        session_id: 会话ID
        agents: Agent字典
        
    Returns:
        函数名列表
    """
    if session_id not in agents:
        return []
    
    agent = agents[session_id]
    return [func["name"] for func in agent.functions]

def format_functions_for_display(session_id, agents):
    """
    格式化函数列表，用于显示
    
    Args:
        session_id: 会话ID
        agents: Agent字典
        
    Returns:
        格式化后的函数列表，每个元素包含函数名和说明
    """
    functions = get_available_functions(session_id, agents)
    return [f"{name} - {desc}" for name, desc in functions] 