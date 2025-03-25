#!/usr/bin/env python
"""
LLM-Blender-Agent UI主入口

UI组件说明：
1. 连接步骤区域 - 分为两行的布局设计
   - 第一行: 步骤1和步骤2并排显示，贯穿整个界面宽度
     * 步骤1: 连接到Blender - 输入主机、端口并连接
     * 步骤2: 初始化LLM模型 - 选择模型并初始化
   - 第二行: 步骤3占据左侧区域
     * 步骤3: 开始对话 - 与LLM交互的主要界面
2. 聊天界面 - 与LLM交互
   - 对话框 - 显示用户与LLM的对话历史
   - 输入框和发送按钮 - 用于发送消息
3. 高级设置 - 配置可用函数、场景信息和渲染选项
4. 场景信息和渲染结果 - 在右侧区域显示Blender状态

数据流和交互逻辑：
1. 用户按照界面引导完成步骤1和步骤2
   a. 连接到Blender服务器
   b. 选择LLM模型并初始化Agent
2. 完成初始设置后，用户开始步骤3
   a. 用户发送消息，系统调用LLM处理消息
   b. LLM通过函数调用与Blender交互，执行操作
   c. 操作结果和对话内容更新到UI上
"""
import time
import gradio as gr

from ui.components.chat_tab import create_chat_tab
import ui.globals as globals

def create_ui():
    """
    创建Gradio UI界面
    
    主要组件和功能：
    1. 聊天界面 - 由create_chat_tab函数创建，包含所有交互元素
    2. 聊天处理器 - 由setup_chat_handlers设置，处理各种事件和消息
    
    数据管理：
    - blender_clients: 存储Blender客户端连接
    - agents: 存储LLM Agent实例
    - session_id: 唯一会话标识符，用于关联客户端和Agent
    
    Returns:
        Gradio应用实例
    """
    # 初始化全局变量
    globals.blender_clients = {}  # 用于存储不同连接的Blender客户端
    globals.agents = {}  # 用于存储不同会话的Agent
    
    # 生成唯一会话ID，用于标识当前会话
    session_id = f"session_{int(time.time())}"
    globals.session_id = session_id
    
    with gr.Blocks(title="LLM-Blender-Agent") as app:
        # 标题和说明
        gr.Markdown("## LLM-Blender-Agent")
        gr.Markdown("使用各种LLM的Function Call功能操作Blender")
        
        # 创建聊天界面组件
        # 返回的chat_components包含所有UI元素的引用，用于后续事件处理
        chat_components = create_chat_tab(session_id)
      
    
    return app 