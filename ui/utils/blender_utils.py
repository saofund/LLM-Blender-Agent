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
    连接到Blender服务器
    
    Args:
        host: 主机地址
        port: 端口号
        blender_clients: 已废弃，保留参数仅用于兼容性，实际使用全局变量
        session_id: 会话ID
        
    Returns:
        连接状态信息
    """
    try:
        # 导入全局变量
        import ui.globals as globals
        
        # 尝试导入BlenderClient
        from src.blender import BlenderClient
        
        # 清理之前的连接（如果有）
        if session_id in globals.blender_clients and globals.blender_clients[session_id] is not None:
            try:
                # 尝试关闭之前的连接
                globals.blender_clients[session_id].close()
            except Exception:
                pass
        
        # 创建新的客户端连接
        client = BlenderClient(host, int(port))
        
        # 检查连接
        if client.is_connected:
            globals.blender_clients[session_id] = client
            
            # 如果Agent已经初始化，更新其Blender客户端
            if session_id in globals.agents and globals.agents[session_id] is not None:
                try:
                    globals.agents[session_id].update_blender_client(client)
                    return f"成功连接到Blender服务器: {host}:{port}，并已更新Agent中的Blender客户端"
                except AttributeError:
                    return f"成功连接到Blender服务器: {host}:{port}，但无法更新Agent（缺少update_blender_client方法）"
                except Exception as e:
                    return f"成功连接到Blender服务器: {host}:{port}，但更新Agent时出错: {str(e)}"
            
            return f"成功连接到Blender服务器: {host}:{port}"
        else:
            return "连接失败，请检查Blender服务器是否启动，或检查地址和端口是否正确"
    
    except Exception as e:
        logger.error(f"连接Blender时出错: {str(e)}")
        return f"连接出错: {str(e)}"

def render_scene_and_return_image(session_id, blender_clients):
    """
    渲染当前场景并返回图像
    
    Args:
        session_id: 会话ID
        blender_clients: 已废弃，保留参数仅用于兼容性，实际使用全局变量
        
    Returns:
        渲染后的图像路径和渲染状态信息
    """
    # 导入全局变量
    import ui.globals as globals
    
    if session_id not in globals.blender_clients:
        return None, "Blender未连接，无法进行渲染"
    
    try:
        client = globals.blender_clients[session_id]
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
        blender_clients: 已废弃，保留参数仅用于兼容性，实际使用全局变量
        
    Returns:
        场景信息文本和原始数据对象
    """
    # 导入全局变量
    import ui.globals as globals
    
    if session_id not in globals.blender_clients:
        return "Blender未连接，无法获取场景信息", None
    
    try:
        client = globals.blender_clients[session_id]
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