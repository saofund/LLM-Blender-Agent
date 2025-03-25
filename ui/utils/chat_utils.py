#!/usr/bin/env python
"""
聊天处理工具函数
"""
import json
import logging
from typing import Dict, List, Any, Optional, Generator
import gradio as gr
from ui.utils.blender_utils import get_scene_info, render_scene_and_return_image
import time
from src.agent.agent import BlenderAgent
from ui.globals import agents

# 配置日志
logger = logging.getLogger(__name__)

"""
消息类型说明：

1. 普通文本消息
   - 用户或助手发送的纯文本消息
   - 结构: {'role': 'user'/'assistant', 'content': '文本内容', ...}

2. 图文消息
   - 用户上传的文件，如图片等
   - 结构: {'role': 'user', 'content': {'type': 'file', 'content': [文件路径列表], ...}, ...}

3. 工具消息
   - 助手使用工具返回的结果
   - 结构: {'role': 'assistant', 'content': {'type': 'tool', 'content': '工具内容', ...}, ...}

4. 组合消息
   - 包含多种内容类型的消息
   - 结构: {'role': 'user'/'assistant', 'content': [{消息1}, {消息2}, ...], ...}

5. 加载状态消息
   - 表示助手正在处理的消息
   - 结构: {'role': 'assistant', 'loading': True, 'status': 'pending', ...}

6. 思考类型消息
   - 显示助手正在思考或推理的过程
   - 结构: {'role': 'assistant', 'content': {'type': 'thinking', 'content': '思考内容'}, ...}
   - 可以包含状态如 'typing': True 表示正在输入思考内容

消息通用属性:
- role: 消息发送者角色 ('user' 或 'assistant')
- content: 消息内容，可以是字符串、字典或列表
- status: 消息状态 ('pending', 'done' 等)
- loading: 是否正在加载
- typing: 是否正在输入(思考)
- footer: 底部信息，如 'canceled' 表示已取消
- 以及其他UI相关属性(avatar, variant, shape等)
"""


def get_agent() -> Optional[BlenderAgent]:
    """获取当前使用的Agent实例"""
    import ui.globals as globals
    for session_id in globals.agents:
        return globals.agents[session_id]


def submit(input_value, chatbot_value):
    """处理聊天提交事件"""
    # 获取当前Agent
    agent = get_agent()
    if agent is None:
        logger.error("未找到可用的Agent实例")
        chatbot_value.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "content": input_value["text"]},
                    {"type": "file", "content": [file for file in input_value["files"]]},
                ],
            }
        )
        chatbot_value.append({
            "role": "assistant", 
            "content": "系统错误：未找到可用的Agent实例，请确认已正确配置Blender和LLM。",
            "status": "done"
        })
        yield gr.update(value=None), gr.update(value=chatbot_value)
        return

    # 添加用户消息到聊天界面
    chatbot_value.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "content": input_value["text"]},
                {"type": "file", "content": [file for file in input_value["files"]]},
            ],
        }
    )
    chatbot_value.append({"role": "assistant", "loading": True, "status": "pending"})
    
    # 更新UI，清空输入框并显示loading状态
    yield gr.update(value=None, loading=True), gr.update(value=chatbot_value)
    
    try:
        # 构建用户消息格式
        user_message = input_value["text"]
        
        # 如果有文件，添加到用户消息
        if input_value["files"]:
            user_message = [
                {"type": "text", "text": input_value["text"]},
                *[{"type": "image_url", "image_url": {"url": file}} for file in input_value["files"]]
            ]
        
        # 调用Agent进行流式聊天
        response_stream = agent.chat_stream(user_message=user_message, temperature=0.7)
        
        # 处理流式响应
        first_output = True
        current_function = None  # 记录当前正在执行的函数
        for chunk in response_stream:
            content_chunk = chunk.get("content")
            function_call = chunk.get("function_call")
            function_result = chunk.get("function_result")
            
            # 更新聊天内容
            if content_chunk:
                if "content" not in chatbot_value[-1] or chatbot_value[-1]["content"] is None:
                    chatbot_value[-1]["content"] = content_chunk
                else:
                    chatbot_value[-1]["content"] += content_chunk
                
            # 如果有函数调用，添加函数调用信息（仅当是新函数时）
            if function_call:
                function_name = function_call.get("name", "未知函数")
                # 检查是否是新的函数调用
                if function_name != current_function:
                    current_function = function_name
                    if "content" not in chatbot_value[-1] or chatbot_value[-1]["content"] is None:
                        chatbot_value[-1]["content"] = f"正在执行：{function_name}..."
                    else:
                        chatbot_value[-1]["content"] += f"\n正在执行：{function_name}..."
            
            # 如果有函数调用结果，添加函数调用结果到当前消息
            if function_result:
                # 在当前消息中添加函数调用结果
                if "content" not in chatbot_value[-1] or chatbot_value[-1]["content"] is None:
                    chatbot_value[-1]["content"] = json.dumps(function_result, ensure_ascii=False, indent=2)
                else:
                    chatbot_value[-1]["content"] += f"\n\n```json\n{json.dumps(function_result, ensure_ascii=False, indent=2)}\n```"
            
            # 第一次有内容输出时就取消loading状态
            if first_output and (content_chunk or function_call or function_result):
                chatbot_value[-1]["loading"] = False
                first_output = False
            
            # 更新UI
            yield gr.update(loading=False), gr.update(value=chatbot_value)
        
        # 完成对话，更新最后一条消息的状态
        chatbot_value[-1]["loading"] = False
        chatbot_value[-1]["status"] = "done"
        
    except Exception as e:
        logger.error(f"聊天过程中发生错误: {str(e)}")
        chatbot_value[-1]["loading"] = False
        chatbot_value[-1]["content"] = f"处理消息时发生错误: {str(e)}"
        chatbot_value[-1]["status"] = "done"
    
    # 更新UI，结束loading状态
    yield gr.update(loading=False), gr.update(value=chatbot_value)


def cancel(chatbot_value):
    """处理取消事件"""
    chatbot_value[-1]["loading"] = False
    chatbot_value[-1]["footer"] = "canceled"
    chatbot_value[-1]["status"] = "done"
    yield gr.update(loading=False), gr.update(value=chatbot_value)


def clear():
    """清空聊天历史"""
    # 如果存在Agent，也清空Agent的消息历史
    agent = get_agent()
    if agent:
        agent.messages = []
    
    yield gr.update(value=None)


def retry(chatbot_value):
    """重试事件"""
    agent = get_agent()
    if agent is None or not chatbot_value:
        yield gr.update(value=chatbot_value)
    
    # 找到最后一条用户消息
    user_messages = [msg for msg in chatbot_value if msg.get("role") == "user"]
    if not user_messages:
        yield gr.update(value=chatbot_value)
    
    last_user_message = user_messages[-1]
    
    # 从chatbot_value中移除最后一个助手消息
    assistant_indices = [i for i, msg in enumerate(chatbot_value) if msg.get("role") == "assistant"]
    if assistant_indices:
        chatbot_value.pop(assistant_indices[-1])
    
    # 添加新的助手消息（处理中状态）
    chatbot_value.append({"role": "assistant", "loading": True, "status": "pending"})
    
    # 先更新UI
    yield gr.update(loading=True), gr.update(value=chatbot_value)
    
    try:
        # 从Agent的消息历史中移除最后一个助手消息
        if agent.messages and agent.messages[-1]["role"] == "assistant":
            agent.messages.pop()
        
        # 提取用户消息内容
        if isinstance(last_user_message.get("content"), list):
            # 多模态消息
            text_content = next((item.get("content") for item in last_user_message["content"] 
                                if item.get("type") == "text"), "")
            file_content = [item.get("content") for item in last_user_message["content"] 
                           if item.get("type") == "file"]
            
            # 构建用户消息格式
            if file_content and file_content[0]:
                user_message = [
                    {"type": "text", "text": text_content},
                    *[{"type": "image_url", "image_url": {"url": file}} for file in file_content[0]]
                ]
            else:
                user_message = text_content
        else:
            # 纯文本消息
            user_message = last_user_message.get("content", "")
        
        # 调用Agent进行流式聊天
        response_stream = agent.chat_stream(user_message=user_message, temperature=0.7)
        
        # 处理流式响应
        first_output = True
        current_function = None  # 记录当前正在执行的函数
        for chunk in response_stream:
            content_chunk = chunk.get("content")
            function_call = chunk.get("function_call")
            function_result = chunk.get("function_result")
            
            # 更新聊天内容
            if content_chunk:
                if "content" not in chatbot_value[-1] or chatbot_value[-1]["content"] is None:
                    chatbot_value[-1]["content"] = content_chunk
                else:
                    chatbot_value[-1]["content"] += content_chunk
                
            # 如果有函数调用，添加函数调用信息（仅当是新函数时）
            if function_call:
                function_name = function_call.get("name", "未知函数")
                # 检查是否是新的函数调用
                if function_name != current_function:
                    current_function = function_name
                    if "content" not in chatbot_value[-1] or chatbot_value[-1]["content"] is None:
                        chatbot_value[-1]["content"] = f"正在执行：{function_name}..."
                    else:
                        chatbot_value[-1]["content"] += f"\n正在执行：{function_name}..."
            
            # 如果有函数调用结果，添加函数调用结果到当前消息
            if function_result:
                # 在当前消息中添加函数调用结果
                if "content" not in chatbot_value[-1] or chatbot_value[-1]["content"] is None:
                    chatbot_value[-1]["content"] = json.dumps(function_result, ensure_ascii=False, indent=2)
                else:
                    chatbot_value[-1]["content"] += f"\n\n```json\n{json.dumps(function_result, ensure_ascii=False, indent=2)}\n```"
            
            # 第一次有内容输出时就取消loading状态
            if first_output and (content_chunk or function_call or function_result):
                chatbot_value[-1]["loading"] = False
                first_output = False
            
            # 更新UI
            yield gr.update(loading=False), gr.update(value=chatbot_value)
        
        # 完成对话，更新最后一条消息的状态
        chatbot_value[-1]["loading"] = False
        chatbot_value[-1]["status"] = "done"
        
    except Exception as e:
        logger.error(f"重试过程中发生错误: {str(e)}")
        chatbot_value[-1]["loading"] = False
        chatbot_value[-1]["content"] = f"处理重试时发生错误: {str(e)}"
        chatbot_value[-1]["status"] = "done"
    
    # 更新UI，结束loading状态
    yield gr.update(loading=False), gr.update(value=chatbot_value)

