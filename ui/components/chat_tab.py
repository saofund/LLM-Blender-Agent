#!/usr/bin/env python
"""
聊天界面组件

本模块提供了聊天界面的创建和事件处理功能。聊天界面是LLM-Blender-Agent的核心交互界面，
包含了所有用户交互和显示元素。

主要组件：
1. 聊天区域 - 用户与LLM的对话历史显示
2. Blender连接控制 - 连接到Blender服务器的设置
3. LLM模型选择 - 选择和初始化不同的LLM模型
4. 高级设置 - 配置函数调用、场景信息和渲染选项
5. 场景信息和渲染结果显示 - 展示Blender的当前状态和渲染输出

交互逻辑：
1. 初始化 - 创建界面元素并设置初始状态
2. 连接Blender - 用户输入主机和端口，点击连接按钮建立与Blender的连接
3. 初始化Agent - 用户选择模型和温度，点击初始化按钮创建Agent
4. 消息处理 - 用户发送消息，系统调用process_message_stream处理
5. 函数选择 - 用户在高级设置中选择可用的函数，系统自动管理选择状态
6. 场景更新 - 自动或手动更新场景信息和渲染结果
7. 上下文管理 - 根据用户设置，将场景信息加入到LLM的上下文中

全局状态：
- session_id - 当前会话ID
- blender_clients - Blender客户端字典的引用
- agents - Agent字典的引用
"""
import gradio as gr
import ui.globals as globals
import os  # 添加os模块用于处理文件路径
from gradio_modal import Modal  # 导入Modal组件

from ui.utils.chat_utils import process_message_stream
from ui.utils.blender_utils import get_scene_info, render_scene_and_return_image, connect_to_blender
from ui.utils.llm_utils import load_config, get_available_models

# 创建全局状态更新函数
def update_status_after_message(history, scene_info, render_image):
    """
    消息处理后更新全局状态显示
    
    Args:
        history: 对话历史
        scene_info: 场景信息
        render_image: 渲染图像
        
    Returns:
        更新后的状态
    """
    # 确保全局变量已初始化
    if None in (globals.session_id, globals.blender_clients, globals.agents):
        # 如果全局变量未设置，直接返回无修改的输入
        return history, scene_info, render_image
    
    # 如果有history但是为空列表，直接返回
    if not history:
        return history, scene_info, render_image
    
    # 不再需要更新状态指示，所有状态信息直接显示在对话框中
    return history, scene_info, render_image

def create_chat_tab(session_id_param):
    """
    创建聊天界面
    
    这个函数创建了整个聊天界面，包括所有交互元素和事件处理。
    界面布局采用两列设计：
    - 左侧(scale=2)：主要交互区域，包含对话、输入、连接设置、模型选择和高级设置
    - 右侧(scale=1)：显示区域，包含场景信息、渲染结果和状态信息
    
    组件详细说明：
    1. 对话区域：
       - chatbot: 显示系统和用户之间的对话历史
       - message: 用户输入消息的文本框
       - submit_btn: 发送消息的按钮
    
    2. 连接设置：
       - blender_host: Blender服务器主机地址输入框，默认为localhost
       - blender_port: Blender服务器端口输入框，默认为9876
       - connect_btn: 连接到Blender服务器的按钮
    
    3. 模型选择：
       - model_selector: LLM模型下拉选择框，选项从配置中加载
       - initialize_btn: 初始化Agent的按钮
    
    4. 高级设置：
       - function_checkboxes: 可用函数多选框，控制LLM可以调用的函数
       - auto_update_info: 是否自动获取场景信息的开关
       - auto_render: 是否自动渲染的开关
       - include_in_context: 是否将场景信息加入LLM上下文的开关(默认选中)
    
    5. 显示区域：
       - scene_info: 显示Blender场景信息的文本框
       - render_image: 显示Blender渲染结果的图像框
       - connection_status: 显示Blender连接状态的文本框
       - initialization_status: 显示Agent初始化状态的文本框
    
    6. 功能按钮：
       - clear_btn: 清空对话历史的按钮
       - render_btn: 手动渲染场景的按钮
       - update_info_btn: 手动更新场景信息的按钮
    
    Args:
        session_id_param: 会话ID
        
    Returns:
        聊天界面组件，以及需要在其他地方使用的组件引用
    """
    # 从配置中获取可用模型
    config = load_config()
    available_models = get_available_models(config)
    
    # 步骤1和步骤2放在整行
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 步骤1: 连接到Blender")
            
            # 主机和端口放在同一行
            with gr.Row():
                blender_host = gr.Textbox(label="Blender主机", value="localhost", scale=3)
                blender_port = gr.Number(label="Blender端口", value=9876, scale=1)
            
            # 状态和按钮放在同一行，按钮在右侧
            with gr.Row():
                connection_status = gr.Textbox(label="连接状态", interactive=False, scale=3)
                
                # 使用列来垂直排列两个按钮
                with gr.Column(scale=1):
                    connect_btn = gr.Button("连接Blender", variant="primary")
                    help_btn = gr.Button("❓ 如何启动Blender 插件", variant="secondary",size="md")
            
            # 创建模态窗用于显示GIF，初始设置为不可见
            with Modal(visible=False) as addon_help_modal:
                gr.Markdown("## 如何启动Blender插件")
                gif_path = os.path.join("asserts", "guide", "how_to_start_addon.gif")
                gr.Image(value=gif_path, show_label=False)
                close_btn = gr.Button("关闭")
            
            # 设置帮助按钮点击事件，打开模态窗
            help_btn.click(lambda: Modal(visible=True), None, addon_help_modal)
            # 设置关闭按钮点击事件，关闭模态窗
            close_btn.click(lambda: Modal(visible=False), None, addon_help_modal)
        
        with gr.Column(scale=1):
            gr.Markdown("## 步骤2: 初始化LLM模型")
            model_selector = gr.Dropdown(
                label="选择LLM模型",
                choices=available_models,
                value="aimlapi" if "aimlapi" in available_models else available_models[0]
            )
            
            # 状态和按钮放在同一行，按钮在右侧
            with gr.Row():
                initialization_status = gr.Textbox(label="初始化状态", interactive=False, scale=3)
                initialize_btn = gr.Button("初始化Agent", variant="primary", scale=1)
    
    # 步骤3标题独占一行
    gr.Markdown("## 步骤3: 开始与Blender对话")
    
    # 聊天界面部分
    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Blender对话", 
                height=500,
                value=[
                    ["系统", "欢迎使用LLM-Blender-Agent！\n\n请先完成步骤1和步骤2，连接Blender并初始化模型，然后开始对话。"]
                ]
            )
            
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
                
                include_in_context = gr.Checkbox(
                    label="将场景信息和渲染结果加入LLM上下文",
                    value=True,  # 默认勾选
                    info="选中时，会将当前场景信息加入到LLM的上下文中，以便更好地理解场景状态"
                )
            
            clear_btn = gr.Button("清空对话")
        
        with gr.Column(scale=1):
            scene_info = gr.Textbox(label="场景信息", interactive=False, lines=10)
            render_image = gr.Image(label="渲染结果", interactive=False)
            
            with gr.Row():
                render_btn = gr.Button("手动渲染")
                update_info_btn = gr.Button("更新场景信息")
    
    # 清空对话事件
    def reset_chat():
        # 准备初始系统消息
        try:
            blender_connected = (globals.session_id in globals.blender_clients and 
                             globals.blender_clients[globals.session_id] is not None and
                             hasattr(globals.blender_clients[globals.session_id], 'is_connected') and
                             globals.blender_clients[globals.session_id].is_connected)
        except Exception:
            blender_connected = False
            
        try:
            agent_initialized = (globals.session_id in globals.agents and 
                             globals.agents[globals.session_id] is not None and
                             hasattr(globals.agents[globals.session_id], 'functions') and
                             len(globals.agents[globals.session_id].functions) > 0)
        except Exception:
            agent_initialized = False
        
        # 根据状态选择合适的消息
        if blender_connected and agent_initialized:
            system_message = "系统已初始化完成，可以开始对话！"
        elif blender_connected:
            system_message = "步骤1已完成，Blender已连接。请完成步骤2，初始化Agent以开始对话。"
        elif agent_initialized:
            system_message = "步骤2已完成，Agent已初始化。请先完成步骤1，连接Blender。"
        else:
            system_message = "欢迎使用LLM-Blender-Agent！\n\n请先完成步骤1和步骤2，连接Blender并初始化模型，然后开始对话。"
        
        return [
            [["系统", system_message]], 
            None, 
            None
        ]

    clear_btn.click(
        fn=reset_chat,
        inputs=None,
        outputs=[chatbot, scene_info, render_image]
    ).then(
        fn=update_status_after_message,
        inputs=[
            chatbot,
            scene_info,
            render_image
        ],
        outputs=[
            chatbot,
            scene_info,
            render_image
        ]
    )
    
    # 手动渲染按钮
    render_btn.click(
        fn=lambda: render_scene_and_return_image(globals.session_id, globals.blender_clients)[0],
        inputs=None,
        outputs=render_image
    )
    
    # 更新场景信息按钮
    update_info_btn.click(
        fn=lambda: get_scene_info(globals.session_id, globals.blender_clients)[0],
        inputs=None,
        outputs=scene_info
    )
    
    # 连接按钮事件
    connect_btn.click(
        fn=lambda host, port: connect_to_blender(host, port, globals.blender_clients, globals.session_id),
        inputs=[blender_host, blender_port],
        outputs=connection_status
    )
    
    # 初始化按钮事件
    def init_and_update_functions(model):
        from ui.utils.llm_utils import initialize_agent, format_functions_for_display
        
        # 使用默认温度0.7
        temp = 0.7
        result = initialize_agent(globals.session_id, model, temp)
        
        # 更新可用函数列表
        formatted_functions = ["all"] + format_functions_for_display(globals.session_id, globals.agents)
        
        return result, gr.update(choices=formatted_functions, value=["all"])
    
    initialize_btn.click(
        fn=init_and_update_functions,
        inputs=[model_selector],
        outputs=[initialization_status, function_checkboxes]
    )
    
    # 添加函数选择器的更新逻辑
    def update_function_selection(selected_functions):
        """
        更新函数选择状态
        
        该函数确保函数选择的逻辑合理：
        1. 当用户选择了具体函数（非"all"）时，自动取消"all"的选择
           - 这保证了要么使用全部函数，要么使用特定的函数子集
           - 防止出现选择了"all"又选择了具体函数的矛盾情况
        2. 当用户没有选择任何函数时，自动选择"all"
           - 确保始终有可用的函数供LLM调用
           - 避免因为没有可用函数而导致功能失效
        
        Args:
            selected_functions: 当前选中的函数列表
            
        Returns:
            更新后的函数选择列表
        """
        # 如果选择了特定函数(非all)，则从选择中移除"all"
        if "all" in selected_functions and len(selected_functions) > 1:
            selected_functions.remove("all")
        # 如果没有选择任何函数，自动选择"all"
        elif len(selected_functions) == 0:
            selected_functions = ["all"]
        return selected_functions
    
    # 函数选择变化时的事件
    function_checkboxes.change(
        fn=update_function_selection,
        inputs=[function_checkboxes],
        outputs=[function_checkboxes]
    )
    
    # 返回需要在其他地方使用的组件
    return {
        "chatbot": chatbot,
        "message": message,
        "submit_btn": submit_btn,
        "function_checkboxes": function_checkboxes,
        "auto_update_info": auto_update_info,
        "auto_render": auto_render,
        "include_in_context": include_in_context,
        "scene_info": scene_info,
        "render_image": render_image,
        "connect_btn": connect_btn, 
        "connection_status": connection_status,
        "model_selector": model_selector,
        "initialize_btn": initialize_btn,
        "initialization_status": initialization_status,
        "help_btn": help_btn,  # 添加帮助按钮
        "addon_help_modal": addon_help_modal  # 添加模态窗组件
    }

def setup_chat_handlers(chat_components, settings_components, session_id_param, connection_indicator=None):
    """
    设置聊天界面的事件处理器
    
    该函数设置了聊天界面中各组件的事件处理器，定义了用户交互时系统的响应方式。
    主要的事件处理逻辑包括：
    
    1. 消息处理流程：
       a. 用户点击发送按钮或按下Enter键
       b. 系统调用process_message_stream函数处理消息
       c. process_message_stream函数流程：
          - 获取用户输入消息
          - 根据include_in_context选项，决定是否将场景信息加入上下文
          - 根据function_checkboxes筛选可用的函数
          - 调用LLM生成回复和执行函数调用
          - 更新聊天历史、场景信息和渲染结果
       d. 调用update_status_after_message更新界面状态
       e. 清空消息输入框
    
    2. 参数说明：
       - message: 用户输入的消息
       - session_id: 当前会话ID
       - chatbot: 聊天历史组件
       - function_checkboxes: 选择的可用函数
       - auto_update_info: 是否自动更新场景信息
       - auto_render: 是否自动渲染
       - include_in_context: 是否将场景信息加入LLM上下文
       - blender_clients: Blender客户端字典
       - agents: Agent字典
    
    3. 返回值说明：
       - chatbot: 更新后的对话历史
       - scene_info: 更新后的场景信息
       - render_image: 更新后的渲染图像
    
    Args:
        chat_components: 聊天界面组件
        settings_components: 设置界面组件（现在与chat_components相同）
        session_id_param: 会话ID
        connection_indicator: 连接状态指示器（可选）
    """
    # 发送消息事件
    chat_components["submit_btn"].click(
        fn=process_message_stream,
        inputs=[
            chat_components["message"], 
            gr.State(globals.session_id), 
            chat_components["chatbot"], 
            chat_components["function_checkboxes"], 
            chat_components["auto_update_info"], 
            chat_components["auto_render"],
            chat_components["include_in_context"],
            gr.State(globals.blender_clients),
            gr.State(globals.agents),
            gr.State(0.7)  # 使用固定温度0.7
        ],
        outputs=[
            chat_components["chatbot"], 
            chat_components["scene_info"], 
            chat_components["render_image"]
        ]
    ).then(
        fn=update_status_after_message,
        inputs=[
            chat_components["chatbot"], 
            chat_components["scene_info"], 
            chat_components["render_image"]
        ],
        outputs=[
            chat_components["chatbot"], 
            chat_components["scene_info"], 
            chat_components["render_image"]
        ]
    ).then(
        fn=lambda: "",
        inputs=None,
        outputs=chat_components["message"]
    )
    
    # 也可以通过按Enter键发送消息
    chat_components["message"].submit(
        fn=process_message_stream,
        inputs=[
            chat_components["message"], 
            gr.State(globals.session_id), 
            chat_components["chatbot"], 
            chat_components["function_checkboxes"], 
            chat_components["auto_update_info"], 
            chat_components["auto_render"],
            chat_components["include_in_context"],
            gr.State(globals.blender_clients),
            gr.State(globals.agents),
            gr.State(0.7)  # 使用固定温度0.7
        ],
        outputs=[
            chat_components["chatbot"], 
            chat_components["scene_info"], 
            chat_components["render_image"]
        ]
    ).then(
        fn=update_status_after_message,
        inputs=[
            chat_components["chatbot"], 
            chat_components["scene_info"], 
            chat_components["render_image"]
        ],
        outputs=[
            chat_components["chatbot"], 
            chat_components["scene_info"], 
            chat_components["render_image"]
        ]
    ).then(
        fn=lambda: "",
        inputs=None,
        outputs=chat_components["message"]
    ) 