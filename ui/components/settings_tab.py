#!/usr/bin/env python
"""
设置界面组件
"""
import gradio as gr

from ui.utils.blender_utils import connect_to_blender
from ui.utils.llm_utils import get_available_models, initialize_agent, format_functions_for_display

def create_settings_tab(session_id, blender_clients, agents, available_models):
    """
    创建连接设置界面
    
    Args:
        session_id: 会话ID
        blender_clients: Blender客户端字典
        agents: Agent字典
        available_models: 可用的模型列表
        
    Returns:
        设置界面组件，以及需要在其他地方使用的组件引用
    """
    with gr.Row():
        with gr.Column(scale=1):
            blender_host = gr.Textbox(label="Blender主机", value="localhost")
            blender_port = gr.Number(label="Blender端口", value=9876)
            connect_btn = gr.Button("连接到Blender")
            connection_status = gr.Textbox(label="连接状态", interactive=False)
        
        with gr.Column(scale=1):
            model_selector = gr.Dropdown(
                label="选择LLM模型",
                choices=available_models,
                value="aimlapi" if "aimlapi" in available_models else available_models[0]
            )
            temperature = gr.Slider(
                label="温度",
                minimum=0.0,
                maximum=1.0,
                value=0.7,
                step=0.1
            )
            initialize_btn = gr.Button("初始化Agent")
            initialization_status = gr.Textbox(label="初始化状态", interactive=False)
    
    # 连接按钮事件
    connect_btn.click(
        fn=lambda host, port: connect_to_blender(host, port, blender_clients, session_id),
        inputs=[blender_host, blender_port],
        outputs=connection_status
    )
    
    # 返回需要在其他地方使用的组件
    return {
        "model_selector": model_selector,
        "temperature": temperature,
        "initialize_btn": initialize_btn,
        "initialization_status": initialization_status
    } 