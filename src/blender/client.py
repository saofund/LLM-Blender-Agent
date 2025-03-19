"""
Blender MCP客户端
"""
import json
import socket
from typing import Dict, Any, List, Optional, Union, Tuple

class BlenderClient:
    """
    Blender MCP客户端，用于与Blender MCP插件通信
    """
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        """
        初始化Blender客户端
        
        Args:
            host: Blender MCP服务器主机名，默认为localhost
            port: Blender MCP服务器端口号，默认为9876
        """
        self.host = host
        self.port = port
    
    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发送命令到Blender MCP服务器
        
        Args:
            command_type: 命令类型
            params: 命令参数
            
        Returns:
            服务器响应
        """
        if params is None:
            params = {}
            
        # 构建命令
        command = {
            "type": command_type,
            "params": params
        }
        
        try:
            # 创建socket连接
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                
                # 发送命令
                sock.sendall(json.dumps(command).encode('utf-8'))
                
                # 接收响应
                response_data = b''
                while True:
                    data = sock.recv(8192)
                    if not data:
                        break
                    response_data += data
                
                # 解析响应
                if response_data:
                    response = json.loads(response_data.decode('utf-8'))
                    return response
                else:
                    return {"status": "error", "message": "没有收到响应"}
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"连接Blender MCP服务器失败: {str(e)}"
            }
    
    # 以下是Blender MCP API的封装
    
    def get_scene_info(self) -> Dict[str, Any]:
        """
        获取场景信息
        
        Returns:
            场景信息
        """
        return self.send_command("get_scene_info")
    
    def create_object(self, obj_type: str, name: Optional[str] = None,
                    location: Tuple[float, float, float] = (0, 0, 0),
                    rotation: Tuple[float, float, float] = (0, 0, 0),
                    scale: Tuple[float, float, float] = (1, 1, 1),
                    **kwargs) -> Dict[str, Any]:
        """
        创建对象
        
        Args:
            obj_type: 对象类型，如CUBE、SPHERE等
            name: 对象名称
            location: 位置坐标
            rotation: 旋转角度
            scale: 缩放比例
            **kwargs: 其他特定参数
            
        Returns:
            创建结果
        """
        params = {
            "type": obj_type,
            "location": location,
            "rotation": rotation,
            "scale": scale
        }
        
        if name:
            params["name"] = name
            
        # 添加其他参数
        params.update(kwargs)
        
        return self.send_command("create_object", params)
    
    def modify_object(self, name: str,
                    location: Optional[Tuple[float, float, float]] = None,
                    rotation: Optional[Tuple[float, float, float]] = None,
                    scale: Optional[Tuple[float, float, float]] = None,
                    visible: Optional[bool] = None) -> Dict[str, Any]:
        """
        修改对象
        
        Args:
            name: 对象名称
            location: 新位置
            rotation: 新旋转
            scale: 新缩放
            visible: 可见性
            
        Returns:
            修改结果
        """
        params = {"name": name}
        
        if location is not None:
            params["location"] = location
            
        if rotation is not None:
            params["rotation"] = rotation
            
        if scale is not None:
            params["scale"] = scale
            
        if visible is not None:
            params["visible"] = visible
            
        return self.send_command("modify_object", params)
    
    def delete_object(self, name: str) -> Dict[str, Any]:
        """
        删除对象
        
        Args:
            name: 对象名称
            
        Returns:
            删除结果
        """
        return self.send_command("delete_object", {"name": name})
    
    def get_object_info(self, name: str) -> Dict[str, Any]:
        """
        获取对象信息
        
        Args:
            name: 对象名称
            
        Returns:
            对象信息
        """
        return self.send_command("get_object_info", {"name": name})
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """
        执行Python代码
        
        Args:
            code: Python代码
            
        Returns:
            执行结果
        """
        return self.send_command("execute_code", {"code": code})
    
    def set_material(self, object_name: str, material_name: Optional[str] = None,
                    create_if_missing: bool = True,
                    color: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        设置材质
        
        Args:
            object_name: 对象名称
            material_name: 材质名称
            create_if_missing: 如果材质不存在是否创建
            color: RGBA颜色值
            
        Returns:
            设置结果
        """
        params = {"object_name": object_name}
        
        if material_name:
            params["material_name"] = material_name
            
        params["create_if_missing"] = create_if_missing
        
        if color:
            params["color"] = color
            
        return self.send_command("set_material", params)
    
    # Poly Haven集成相关方法
    
    def get_polyhaven_status(self) -> Dict[str, Any]:
        """
        获取Poly Haven状态
        
        Returns:
            Poly Haven状态
        """
        return self.send_command("get_polyhaven_status")
    
    def get_polyhaven_categories(self, asset_type: str) -> Dict[str, Any]:
        """
        获取Poly Haven资源分类
        
        Args:
            asset_type: 资源类型，如hdris、textures、models、all
            
        Returns:
            分类列表
        """
        return self.send_command("get_polyhaven_categories", {"asset_type": asset_type})
    
    def search_polyhaven_assets(self, asset_type: Optional[str] = None,
                               categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        搜索Poly Haven资源
        
        Args:
            asset_type: 资源类型
            categories: 分类
            
        Returns:
            搜索结果
        """
        params = {}
        
        if asset_type:
            params["asset_type"] = asset_type
            
        if categories:
            params["categories"] = categories
            
        return self.send_command("search_polyhaven_assets", params)
    
    def download_polyhaven_asset(self, asset_id: str, asset_type: str,
                                resolution: str = "1k",
                                file_format: Optional[str] = None) -> Dict[str, Any]:
        """
        下载Poly Haven资源
        
        Args:
            asset_id: 资源ID
            asset_type: 资源类型
            resolution: 分辨率
            file_format: 文件格式
            
        Returns:
            下载结果
        """
        params = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "resolution": resolution
        }
        
        if file_format:
            params["file_format"] = file_format
            
        return self.send_command("download_polyhaven_asset", params)
    
    def set_texture(self, object_name: str, texture_id: str) -> Dict[str, Any]:
        """
        应用纹理
        
        Args:
            object_name: 对象名称
            texture_id: 纹理ID
            
        Returns:
            应用结果
        """
        return self.send_command("set_texture", {
            "object_name": object_name,
            "texture_id": texture_id
        })
    
    # Hyper3D Rodin集成相关方法
    
    def get_hyper3d_status(self) -> Dict[str, Any]:
        """
        获取Hyper3D状态
        
        Returns:
            Hyper3D状态
        """
        return self.send_command("get_hyper3d_status")
    
    def create_rodin_job(self, text_prompt: Optional[str] = None,
                        images: Optional[List[Tuple[str, str]]] = None,
                        bbox_condition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建Rodin模型生成任务
        
        Args:
            text_prompt: 文本提示
            images: 参考图像列表
            bbox_condition: 边界框条件
            
        Returns:
            任务创建结果
        """
        params = {}
        
        if text_prompt:
            params["text_prompt"] = text_prompt
            
        if images:
            params["images"] = images
            
        if bbox_condition:
            params["bbox_condition"] = bbox_condition
            
        return self.send_command("create_rodin_job", params)
    
    def poll_rodin_job_status(self, job_id: str, mode: str = "MAIN_SITE") -> Dict[str, Any]:
        """
        查询Rodin任务状态
        
        Args:
            job_id: 任务ID
            mode: 模式，MAIN_SITE或FAL_AI
            
        Returns:
            任务状态
        """
        params = {}
        
        if mode == "MAIN_SITE":
            params["subscription_key"] = job_id
        else:
            params["request_id"] = job_id
            
        return self.send_command("poll_rodin_job_status", params)
    
    def import_generated_asset(self, job_id: str, name: str, mode: str = "MAIN_SITE") -> Dict[str, Any]:
        """
        导入生成的资源
        
        Args:
            job_id: 任务ID
            name: 资源名称
            mode: 模式，MAIN_SITE或FAL_AI
            
        Returns:
            导入结果
        """
        params = {"name": name}
        
        if mode == "MAIN_SITE":
            params["task_uuid"] = job_id
        else:
            params["request_id"] = job_id
            
        return self.send_command("import_generated_asset", params) 