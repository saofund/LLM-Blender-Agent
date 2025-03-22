#!/usr/bin/env python
"""
LLM-Blender-Agent UI主入口
"""
import time
import gradio as gr

from ui.utils.llm_utils import load_config, get_available_models, initialize_agent, format_functions_for_display
from ui.components.settings_tab import create_settings_tab
from ui.components.chat_tab import create_chat_tab, setup_chat_handlers

def create_ui():
    """
    创建Gradio UI界面
    
    Returns:
        Gradio应用
    """
    # 全局变量
    blender_clients = {}  # 用于存储不同连接的Blender客户端
    agents = {}  # 用于存储不同会话的Agent
    
    # 加载配置
    config = load_config()
    available_models = get_available_models(config)
    
    # 生成唯一会话ID
    session_id = f"session_{int(time.time())}"
    
    with gr.Blocks(title="LLM-Blender-Agent") as app:
        gr.Markdown("## LLM-Blender-Agent")
        gr.Markdown("使用各种LLM的Function Call功能操作Blender")
        
        with gr.Tab("连接设置"):
            settings_components = create_settings_tab(session_id, blender_clients, agents, available_models)
        
        with gr.Tab("对话"):
            chat_components = create_chat_tab(session_id, blender_clients, agents)
        
        # 设置函数选择框的更新
        def init_and_update_functions(model, temp):
            result = initialize_agent(session_id, model, temp, blender_clients, agents)
            
            # 更新可用函数列表
            formatted_functions = ["all"] + format_functions_for_display(session_id, agents)
            
            return result, gr.update(choices=formatted_functions, value=["all"])
        
        # 初始化按钮事件
        settings_components["initialize_btn"].click(
            fn=init_and_update_functions,
            inputs=[settings_components["model_selector"], settings_components["temperature"]],
            outputs=[settings_components["initialization_status"], chat_components["function_checkboxes"]]
        )
        
        # 设置聊天处理器
        setup_chat_handlers(chat_components, settings_components, session_id, blender_clients, agents)
    
    return app 