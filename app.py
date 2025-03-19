#!/usr/bin/env python
"""
LLM-Blender-Agent Gradio Web界面
"""
import os
import sys
import json
import logging
import threading
import time
import gradio as gr

from src.llm import LLMFactory
from src.blender import BlenderClient
from src.agent import BlenderAgent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = "config.json"

# 全局变量
blender_clients = {}  # 用于存储不同连接的Blender客户端
agents = {}  # 用于存储不同会话的Agent

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
        return ["claude"]
    
    llm_config = config.get("llm", {})
    models = []
    
    for model_type, model_config in llm_config.items():
        if model_type != "default_model" and isinstance(model_config, dict):
            models.append(model_type)
    
    return models or ["claude"]

def connect_to_blender(host, port, session_id):
    """
    连接到Blender MCP服务器
    
    Args:
        host: 服务器主机名
        port: 服务器端口号
        session_id: 会话ID
        
    Returns:
        连接状态信息
    """
    try:
        blender_client = BlenderClient(host, port)
        
        # 测试连接
        scene_info = blender_client.get_scene_info()
        if scene_info.get("status") == "error":
            return f"连接失败: {scene_info.get('message')}"
        
        # 存储客户端
        blender_clients[session_id] = blender_client
        
        return f"连接成功，场景: {scene_info.get('result', {}).get('name', '未知')}"
    
    except Exception as e:
        logger.error(f"连接Blender时出错: {str(e)}")
        return f"连接出错: {str(e)}"

def initialize_agent(session_id, model_type, temperature):
    """
    初始化Agent
    
    Args:
        session_id: 会话ID
        model_type: 模型类型
        temperature: 温度参数
        
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
        llm = LLMFactory.create_from_config_file(DEFAULT_CONFIG_PATH, model_type)
        
        # 创建Agent
        agent = BlenderAgent(llm, blender_clients[session_id])
        agents[session_id] = agent
        
        return f"初始化成功，使用模型: {model_type}"
    
    except Exception as e:
        logger.error(f"初始化Agent时出错: {str(e)}")
        return f"初始化出错: {str(e)}"

def process_message(message, session_id, history, temperature=0.7):
    """
    处理用户消息
    
    Args:
        message: 用户消息
        session_id: 会话ID
        history: 对话历史
        temperature: 温度参数
        
    Returns:
        更新后的对话历史
    """
    try:
        # 检查Agent是否已初始化
        if session_id not in agents:
            return history + [[message, "请先连接到Blender并初始化Agent"]]
        
        # 处理消息
        agent = agents[session_id]
        response = agent.chat(message, temperature=temperature)
        
        content = response.get("content", "")
        function_call = response.get("function_call")
        
        # 构建响应文本
        response_text = content or ""
        
        if function_call:
            if not response_text:
                response_text = f"执行了操作: {function_call['name']}"
        
        if not response_text:
            response_text = "[无响应]"
        
        return history + [[message, response_text]]
    
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        return history + [[message, f"处理出错: {str(e)}"]]

def create_ui():
    """创建Gradio UI界面"""
    # 加载配置
    config = load_config()
    available_models = get_available_models(config)
    
    # 生成唯一会话ID
    session_id = f"session_{int(time.time())}"
    
    with gr.Blocks(title="LLM-Blender-Agent") as app:
        gr.Markdown("## LLM-Blender-Agent")
        gr.Markdown("使用各种LLM的Function Call功能操作Blender")
        
        with gr.Tab("连接设置"):
            with gr.Row():
                with gr.Column():
                    blender_host = gr.Textbox(label="Blender主机", value="localhost")
                    blender_port = gr.Number(label="Blender端口", value=9876)
                    connect_btn = gr.Button("连接到Blender")
                    connection_status = gr.Textbox(label="连接状态", interactive=False)
                
                with gr.Column():
                    model_selector = gr.Dropdown(
                        label="选择LLM模型",
                        choices=available_models,
                        value=available_models[0] if available_models else "claude"
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
        
        with gr.Tab("对话"):
            chatbot = gr.Chatbot(label="Blender对话")
            message = gr.Textbox(label="消息", placeholder="输入指令...")
            submit_btn = gr.Button("发送")
            clear_btn = gr.Button("清空对话")
        
        # 连接按钮事件
        connect_btn.click(
            fn=lambda host, port: connect_to_blender(host, port, session_id),
            inputs=[blender_host, blender_port],
            outputs=connection_status
        )
        
        # 初始化按钮事件
        initialize_btn.click(
            fn=lambda model, temp: initialize_agent(session_id, model, temp),
            inputs=[model_selector, temperature],
            outputs=initialization_status
        )
        
        # 发送消息事件
        submit_btn.click(
            fn=lambda msg, history, temp: process_message(msg, session_id, history, temp),
            inputs=[message, chatbot, temperature],
            outputs=[chatbot],
            api_name="chat"
        ).then(
            fn=lambda: "",
            inputs=None,
            outputs=message
        )
        
        # 清空对话事件
        clear_btn.click(
            fn=lambda: [],
            inputs=None,
            outputs=chatbot
        )
        
        # 也可以通过按Enter键发送消息
        message.submit(
            fn=lambda msg, history, temp: process_message(msg, session_id, history, temp),
            inputs=[message, chatbot, temperature],
            outputs=[chatbot]
        ).then(
            fn=lambda: "",
            inputs=None,
            outputs=message
        )
    
    return app

def main():
    """主函数"""
    try:
        app = create_ui()
        app.launch(server_name="0.0.0.0", share=False)
    
    except Exception as e:
        logger.error(f"启动Gradio界面时出错: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 