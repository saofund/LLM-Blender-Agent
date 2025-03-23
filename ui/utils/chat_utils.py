#!/usr/bin/env python
"""
聊天处理工具函数
"""
import json
import logging
from typing import Dict, List, Any, Optional, Generator

from ui.utils.blender_utils import get_scene_info, render_scene_and_return_image

# 配置日志
logger = logging.getLogger(__name__)

def process_message_stream(message, session_id, history, selected_functions, 
                          auto_update_info, auto_render, include_in_context,
                          blender_clients, agents, temperature=0.7):
    """
    处理用户消息（流式响应）
    
    Args:
        message: 用户消息
        session_id: 会话ID
        history: 对话历史
        selected_functions: 选择的函数列表
        auto_update_info: 是否自动更新场景信息
        auto_render: 是否自动渲染
        include_in_context: 是否将场景信息和渲染结果加入到LLM上下文
        blender_clients: Blender客户端字典（已废弃，使用全局变量）
        agents: Agent字典（已废弃，使用全局变量）
        temperature: 温度参数
        
    Returns:
        生成器，产生更新后的对话历史、场景信息和渲染图像
    """
    try:
        # 导入全局变量
        import ui.globals as globals
        
        # 生成空白回复占位
        history.append([message, ""])
        yield history, None, None
        
        # 检查系统状态 - 更严格的检查
        try:
            blender_connected = (session_id in globals.blender_clients and 
                                globals.blender_clients[session_id] is not None and
                                hasattr(globals.blender_clients[session_id], 'is_connected') and
                                globals.blender_clients[session_id].is_connected)
        except Exception:
            blender_connected = False
            
        try:
            agent_initialized = (session_id in globals.agents and 
                                globals.agents[session_id] is not None and
                                hasattr(globals.agents[session_id], 'functions') and
                                len(globals.agents[session_id].functions) > 0)
        except Exception:
            agent_initialized = False
        
        # 记录状态用于调试
        logger.info(f"状态检查: Blender连接={blender_connected}, Agent初始化={agent_initialized}")
        
        # 如果Agent未初始化
        if not agent_initialized:
            status_message = "系统尚未初始化。请随意聊天，或前往「连接设置」选项卡初始化系统。"
            history[-1][1] = status_message
            yield history, None, None
            return
        
        # 如果Blender未连接但用户消息中包含Blender操作相关的关键词
        if not blender_connected and any(kw in message.lower() for kw in ["blender", "模型", "场景", "渲染", "物体", "添加", "删除", "移动", "旋转", "缩放"]):
            status_message = "Blender未连接。请前往「连接设置」选项卡连接Blender后再执行Blender相关操作。"
            history[-1][1] = f"{status_message}\n\n不过，您可以继续与AI进行非Blender相关的对话。"
            yield history, None, None
            
            # 使用AI回答非Blender相关内容
            agent = globals.agents[session_id]
            chat_functions = [f for f in agent.functions if not f["name"].startswith("blender_")]
            if chat_functions and message:
                try:
                    response = agent.chat(message, chat_functions, temperature=temperature)
                    if response and response.get("content"):
                        history[-1][1] = f"{status_message}\n\n{response['content']}"
                        yield history, None, None
                except Exception as e:
                    logger.error(f"尝试非Blender对话失败: {str(e)}")
            
            return

        # 如果需要将场景信息和渲染结果加入到上下文
        additional_context = ""
        if include_in_context and blender_connected:
            # 获取场景信息
            scene_info_text, _ = get_scene_info(session_id, globals.blender_clients)
            if scene_info_text and not scene_info_text.startswith("Blender未连接") and not scene_info_text.startswith("获取场景信息失败"):
                additional_context += f"\n\n当前场景信息:\n{scene_info_text}"
            
            # 如果用户消息中包含"渲染"关键词，说明可能需要渲染图像的上下文
            if "渲染" in message or "render" in message.lower():
                additional_context += "\n\n(系统已准备好渲染功能，可以通过function call调用render_scene渲染场景)"
        
        # 如果有附加上下文，添加到用户消息中
        user_msg = message
        if additional_context:
            user_msg += additional_context
        
        # 获取所选函数的子集
        agent = globals.agents[session_id]
        if selected_functions and selected_functions != ["all"]:
            # 过滤函数
            allowed_functions = [func for func in agent.functions if any(func_name in func["name"] for func_name in selected_functions)]
        else:
            # 使用全部函数
            allowed_functions = agent.functions
        
        # 流式处理消息
        response_text = ""
        full_response = {"content": "", "function_call": None}
        
        # 获取流式响应
        for chunk in agent.chat_stream(user_msg, allowed_functions, temperature=temperature):
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
        
        # 如果需要更新场景信息并且已连接Blender
        scene_info = None
        if auto_update_info and blender_connected:
            scene_info_text, scene_data = get_scene_info(session_id, globals.blender_clients)
            scene_info = scene_info_text
        
        # 如果需要自动渲染并且已连接Blender
        render_image = None
        render_error = None
        if auto_render and blender_connected:
            render_image, render_error = render_scene_and_return_image(session_id, globals.blender_clients)
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