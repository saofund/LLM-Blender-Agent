#!/usr/bin/env python
"""
聊天界面组件
"""
import gradio as gr

from ui.utils.chat_utils import process_message_stream
from ui.utils.blender_utils import get_scene_info, render_scene_and_return_image

def create_chat_tab(session_id, blender_clients, agents):
    """
    创建聊天界面
    
    Args:
        session_id: 会话ID
        blender_clients: Blender客户端字典
        agents: Agent字典
        
    Returns:
        聊天界面组件，以及需要在其他地方使用的组件引用
    """
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
                
                include_in_context = gr.Checkbox(
                    label="将场景信息和渲染结果加入LLM上下文",
                    value=False,
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
    clear_btn.click(
        fn=lambda: [[], None, None],
        inputs=None,
        outputs=[chatbot, scene_info, render_image]
    )
    
    # 手动渲染按钮
    render_btn.click(
        fn=lambda: render_scene_and_return_image(session_id, blender_clients)[0],
        inputs=None,
        outputs=render_image
    )
    
    # 更新场景信息按钮
    update_info_btn.click(
        fn=lambda: get_scene_info(session_id, blender_clients)[0],
        inputs=None,
        outputs=scene_info
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
        "render_image": render_image
    }

def setup_chat_handlers(chat_components, settings_components, session_id, blender_clients, agents):
    """
    设置聊天界面的事件处理器
    
    Args:
        chat_components: 聊天界面组件
        settings_components: 设置界面组件
        session_id: 会话ID
        blender_clients: Blender客户端字典
        agents: Agent字典
    """
    # 发送消息事件
    chat_components["submit_btn"].click(
        fn=process_message_stream,
        inputs=[
            chat_components["message"], 
            gr.State(session_id), 
            chat_components["chatbot"], 
            chat_components["function_checkboxes"], 
            chat_components["auto_update_info"], 
            chat_components["auto_render"],
            chat_components["include_in_context"],
            gr.State(blender_clients),
            gr.State(agents),
            settings_components["temperature"]
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
            gr.State(session_id), 
            chat_components["chatbot"], 
            chat_components["function_checkboxes"], 
            chat_components["auto_update_info"], 
            chat_components["auto_render"],
            chat_components["include_in_context"],
            gr.State(blender_clients),
            gr.State(agents),
            settings_components["temperature"]
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