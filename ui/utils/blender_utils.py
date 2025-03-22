#!/usr/bin/env python
"""
Blender通信工具函数
"""
import os
import json
import base64
import logging
import tempfile

# 配置日志
logger = logging.getLogger(__name__)

def connect_to_blender(host, port, blender_clients, session_id):
    """
    连接到Blender MCP服务器
    
    Args:
        host: 服务器主机名
        port: 服务器端口号
        blender_clients: 客户端字典
        session_id: 会话ID
        
    Returns:
        连接状态信息
    """
    try:
        from src.blender import BlenderClient
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

def render_scene_and_return_image(session_id, blender_clients):
    """
    渲染当前场景并返回图像
    
    Args:
        session_id: 会话ID
        blender_clients: 客户端字典
        
    Returns:
        渲染后的图像路径和渲染状态信息
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
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image_bytes = base64.b64decode(image_data)
                with open(temp_file.name, "wb") as f:
                    f.write(image_bytes)
                return temp_file.name, None
            
        return None, f"渲染失败: {result.get('message', '未知错误')}"
    
    except Exception as e:
        logger.error(f"渲染场景时出错: {str(e)}")
        return None, f"渲染出错: {str(e)}"

def get_scene_info(session_id, blender_clients):
    """
    获取场景信息
    
    Args:
        session_id: 会话ID
        blender_clients: 客户端字典
        
    Returns:
        场景信息文本和原始数据对象
    """
    if session_id not in blender_clients:
        return "请先连接到Blender", None
    
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
            
            return info_text, scene_data
        else:
            return f"获取场景信息失败: {result.get('message', '未知错误')}", None
    
    except Exception as e:
        logger.error(f"获取场景信息时出错: {str(e)}")
        return f"获取场景信息出错: {str(e)}", None 