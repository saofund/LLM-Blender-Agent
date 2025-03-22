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
import base64
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
        return ["aimlapi"]
    
    llm_config = config.get("llm", {})
    models = []
    
    for model_type, model_config in llm_config.items():
        if model_type != "default_model" and isinstance(model_config, dict):
            models.append(model_type)
    
    return models or ["aimlapi"]

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

def get_available_functions(session_id):
    """
    获取可用的函数列表
    
    Args:
        session_id: 会话ID
        
    Returns:
        函数名称列表
    """
    if session_id not in agents:
        return []
    
    agent = agents[session_id]
    return [func["name"] for func in agent.functions]

def render_scene_and_return_image(session_id):
    """
    渲染当前场景并返回图像
    
    Args:
        session_id: 会话ID
        
    Returns:
        渲染后的图像路径或错误信息
    """
    if session_id not in blender_clients:
        return None, "请先连接到Blender"
    
    try:
        client = blender_clients[session_id]
        result = client.render_scene(auto_save=True, save_dir="renders")
        
        if result.get("status") == "success":
            # 获取保存的图像路径
            saved_path = result.get("result", {}).get("saved_to")
            if saved_path and os.path.exists(saved_path):
                return saved_path, None
            
            # 如果没有保存路径但有图像数据，则从图像数据创建临时文件
            image_data = result.get("result", {}).get("image_data")
            if image_data:
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image_bytes = base64.b64decode(image_data)
                with open(temp_file.name, "wb") as f:
                    f.write(image_bytes)
                return temp_file.name, None
            
        return None, f"渲染失败: {result.get('message', '未知错误')}"
    
    except Exception as e:
        logger.error(f"渲染场景时出错: {str(e)}")
        return None, f"渲染出错: {str(e)}"

def get_scene_info(session_id):
    """
    获取场景信息
    
    Args:
        session_id: 会话ID
        
    Returns:
        场景信息文本
    """
    if session_id not in blender_clients:
        return "请先连接到Blender"
    
    try:
        client = blender_clients[session_id]
        result = client.get_scene_info()
        
        if result.get("status") == "success":
            scene_data = result.get("result", {})
            info_text = f"场景名称: {scene_data.get('name', '未知')}\n"
            info_text += f"对象数量: {len(scene_data.get('objects', []))}\n\n"
            
            # 添加对象列表
            objects = scene_data.get("objects", [])
            if objects:
                info_text += "对象列表:\n"
                for obj in objects:
                    obj_type = obj.get("type", "未知")
                    obj_name = obj.get("name", "未知")
                    info_text += f"- {obj_name} ({obj_type})\n"
            
            return info_text
        else:
            return f"获取场景信息失败: {result.get('message', '未知错误')}"
    
    except Exception as e:
        logger.error(f"获取场景信息时出错: {str(e)}")
        return f"获取场景信息出错: {str(e)}"

def process_message_stream(message, session_id, history, selected_functions, auto_update_info, auto_render, temperature=0.7):
    """
    处理用户消息（流式响应）
    
    Args:
        message: 用户消息
        session_id: 会话ID
        history: 对话历史
        selected_functions: 选择的函数列表
        auto_update_info: 是否自动更新场景信息
        auto_render: 是否自动渲染
        temperature: 温度参数
        
    Returns:
        生成器，产生更新后的对话历史、场景信息和渲染图像
    """
    try:
        # 检查Agent是否已初始化
        if session_id not in agents:
            history.append([message, "请先连接到Blender并初始化Agent"])
            yield history, None, None
            return

        # 生成空白回复占位
        history.append([message, ""])
        yield history, None, None
        
        # 获取所选函数的子集
        agent = agents[session_id]
        if selected_functions and selected_functions != ["all"]:
            # 过滤函数
            allowed_functions = [func for func in agent.functions if func["name"] in selected_functions]
        else:
            # 使用全部函数
            allowed_functions = agent.functions
        
        # 流式处理消息
        response_text = ""
        full_response = {"content": "", "function_call": None}
        
        # 获取流式响应
        for chunk in agent.chat_stream(message, allowed_functions, temperature=temperature):
            content_chunk = chunk.get("content") or ""
            
            if content_chunk:
                response_text += content_chunk
                history[-1][1] = response_text
                yield history, None, None
            
            # 更新完整响应
            if "content" in chunk and chunk["content"] is not None:
                full_response["content"] = (full_response.get("content") or "") + (chunk.get("content") or "")
            if "function_call" in chunk and chunk["function_call"] is not None:
                full_response["function_call"] = chunk["function_call"]
        
        # 如果有函数调用，执行并更新响应
        if full_response.get("function_call"):
            function_result = agent._execute_function(full_response["function_call"])
            function_name = full_response["function_call"]["name"]
            
            # 添加函数执行结果到响应中
            if not response_text:
                response_text = f"执行了操作: {function_name}"
            
            response_text += f"\n\n函数执行结果: {json.dumps(function_result, ensure_ascii=False)}"
            history[-1][1] = response_text
            yield history, None, None
        
        # 如果需要更新场景信息
        scene_info = None
        if auto_update_info:
            scene_info = get_scene_info(session_id)
        
        # 如果需要自动渲染
        render_image = None
        render_error = None
        if auto_render:
            render_image, render_error = render_scene_and_return_image(session_id)
            if render_error:
                # 添加渲染错误信息到响应
                response_text += f"\n\n[渲染失败: {render_error}]"
                history[-1][1] = response_text
        
        yield history, scene_info, render_image
    
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        if len(history) > 0 and len(history[-1]) > 1:
            history[-1][1] += f"\n\n处理出错: {str(e)}"
        else:
            history.append([message, f"处理出错: {str(e)}"])
        yield history, None, None

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
        
        with gr.Tab("对话"):
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(label="Blender对话", height=600)
                    
                    with gr.Row():
                        message = gr.Textbox(label="消息", placeholder="输入指令...", scale=4)
                        submit_btn = gr.Button("发送", scale=1)
                    
                    with gr.Accordion("高级设置", open=False):
                        function_checkboxes = gr.CheckboxGroup(
                            label="选择可用的函数",
                            choices=["all"],
                            value=["all"]
                        )
                        with gr.Row():
                            auto_update_info = gr.Checkbox(label="自动获取场景信息", value=True)
                            auto_render = gr.Checkbox(label="自动渲染", value=True)
                    
                    clear_btn = gr.Button("清空对话")
                
                with gr.Column(scale=1):
                    scene_info = gr.Textbox(label="场景信息", interactive=False, lines=10)
                    render_image = gr.Image(label="渲染结果", interactive=False)
                    render_btn = gr.Button("手动渲染")
                    update_info_btn = gr.Button("更新场景信息")
        
        # 连接按钮事件
        connect_btn.click(
            fn=lambda host, port: connect_to_blender(host, port, session_id),
            inputs=[blender_host, blender_port],
            outputs=connection_status
        )
        
        # 初始化按钮事件
        def init_and_update_functions(model, temp):
            result = initialize_agent(session_id, model, temp)
            # 更新可用函数列表
            funcs = ["all"] + get_available_functions(session_id)
            return result, gr.update(choices=funcs, value=["all"])
        
        initialize_btn.click(
            fn=init_and_update_functions,
            inputs=[model_selector, temperature],
            outputs=[initialization_status, function_checkboxes]
        )
        
        # 发送消息事件
        submit_btn.click(
            fn=process_message_stream,
            inputs=[message, gr.State(session_id), chatbot, function_checkboxes, auto_update_info, auto_render, temperature],
            outputs=[chatbot, scene_info, render_image],
            api_name="chat"
        ).then(
            fn=lambda: "",
            inputs=None,
            outputs=message
        )
        
        # 清空对话事件
        clear_btn.click(
            fn=lambda: [[], None, None],
            inputs=None,
            outputs=[chatbot, scene_info, render_image]
        )
        
        # 手动渲染按钮
        render_btn.click(
            fn=lambda: render_scene_and_return_image(session_id)[0],
            inputs=None,
            outputs=render_image
        )
        
        # 更新场景信息按钮
        update_info_btn.click(
            fn=lambda: get_scene_info(session_id),
            inputs=None,
            outputs=scene_info
        )
        
        # 也可以通过按Enter键发送消息
        message.submit(
            fn=process_message_stream,
            inputs=[message, gr.State(session_id), chatbot, function_checkboxes, auto_update_info, auto_render, temperature],
            outputs=[chatbot, scene_info, render_image]
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