"""
Blender MCP客户端
"""
import json
import os
import socket
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import base64

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
        
        # 测试连接并设置连接状态
        try:
            scene_info = self.get_scene_info()
            self.is_connected = scene_info.get("status") != "error"
        except Exception:
            self.is_connected = False
    
    def close(self):
        """
        关闭客户端连接
        """
        # 由于使用的是无状态连接，实际上不需要特别的关闭逻辑
        # 但为了保持接口一致性，保留这个方法
        self.is_connected = False
    
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
        
        print(f"准备发送命令: {command_type}")
        
        try:
            # 创建socket连接
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # 设置超时时间为5秒,如果是生成3d模型，则设置为10秒
                if command_type == 'generate_3d_model':
                    sock.settimeout(30)
                else:
                    sock.settimeout(10)
                # print(f"尝试连接到 {self.host}:{self.port}...")
                sock.connect((self.host, self.port))
                # print("连接成功，发送数据...")
                # 发送命令
                command_data = json.dumps(command).encode('utf-8')
                sock.sendall(command_data)
                print(f"已发送数据: {len(command_data)} 字节")
                
                # 接收响应
                response_data = b''
                # print("等待服务器响应...")
                while True:
                    try:
                        data = sock.recv(8192)
                        if not data:
                            break
                        response_data += data
                        # print(f"收到数据: {len(data)} 字节")
                    except socket.timeout:
                        print("接收响应超时")
                        break
                
                # 解析响应
                if response_data:
                    try:
                        print(f"解析响应数据: {len(response_data)} 字节")
                        response = json.loads(response_data.decode('utf-8'))
                        return response
                    except json.JSONDecodeError as je:
                        print(f"JSON解析错误: {str(je)}")
                        return {"status": "error", "message": f"解析响应失败: {str(je)}"}
                else:
                    print("未收到响应数据")
                    return {"status": "error", "message": "没有收到响应"}
                
        except socket.timeout:
            print("连接超时")
            return {
                "status": "error",
                "message": "连接Blender MCP服务器超时"
            }
        except Exception as e:
            print(f"发生异常: {type(e).__name__}: {str(e)}")
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
    
    def generate_3d_model(self, text: Optional[str] = None, image_path: Optional[str] = None,
                        object_name: Optional[str] = None, octree_resolution: int = 256,
                        num_inference_steps: int = 20, guidance_scale: float = 5.5,
                        texture: bool = False) -> Dict[str, Any]:
        """
        调用Hunyuan3D-2生成3D模型

        Args:
            text: 文本提示，描述要生成的3D模型（如果提供了image_path，则text会被忽略）
            image_path: 图片路径，用于图像到3D生成（优先级高于text）
            object_name: 要应用纹理的现有模型名称
            octree_resolution: 3D生成的八叉树分辨率，默认为256
            num_inference_steps: 推理步骤数，默认为20
            guidance_scale: 引导比例，默认为5.5
            texture: 是否生成纹理，默认为False

        Returns:
            生成结果
        """
        params = {}
        
        if image_path:
            # 优先使用图片，如果有图片则忽略文本
            try:
                with open(image_path, "rb") as img_file:
                    image_data = img_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                params["image_data"] = image_base64
                print(f"使用图片进行3D生成: {image_path}")
            except Exception as e:
                print(f"读取图片文件失败: {str(e)}，尝试使用文本提示")
                # 图片读取失败时，检查是否有文本提示可用
                if text:
                    params["text"] = text
                else:
                    return {
                        "status": "error", 
                        "message": f"读取图片文件失败且没有提供文本提示: {str(e)}"
                    }
        elif text:
            # 没有图片时使用文本
            params["text"] = text
            print(f"使用文本进行3D生成: {text}")
        else:
            # 既没有图片也没有文本
            return {
                "status": "error",
                "message": "必须提供文本提示或图片路径"
            }
        
        if object_name:
            params["object_name"] = object_name
            
        params["octree_resolution"] = octree_resolution
        params["num_inference_steps"] = num_inference_steps
        params["guidance_scale"] = guidance_scale
        params["texture"] = texture
            
        return self.send_command("generate_3d_model", params)
    
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
    
    def render_scene(self, output_path: Optional[str] = None, 
                    resolution_x: Optional[int] = None, 
                    resolution_y: Optional[int] = None,
                    return_image: bool = True,
                    auto_save: bool = True,
                    save_dir: str = "renders") -> Dict[str, Any]:
        """
        渲染当前场景
        
        Args:
            output_path: 输出文件路径（可选）
            resolution_x: 渲染宽度（可选）
            resolution_y: 渲染高度（可选）
            return_image: 是否返回图像数据，默认为True
            auto_save: 是否自动保存图像数据到本地，默认为True
            save_dir: 自动保存时使用的目录，默认为"renders"
            
        Returns:
            渲染结果，如果return_image为True，则包含base64编码的图像数据
        """
        params = {}
        
        if output_path:
            params["output_path"] = output_path
            
        if resolution_x is not None:
            params["resolution_x"] = resolution_x
            
        if resolution_y is not None:
            params["resolution_y"] = resolution_y
            
        params["return_image"] = return_image
        
        response = self.send_command("render_scene", params)
        
        # 如果需要自动保存并且成功获取到图像数据
        if auto_save and return_image and response.get("status") == "success":
            result = response.get("result", {})
            if "image_data" in result:
                # 生成保存路径
                import os
                from datetime import datetime
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"render_{timestamp}.png"
                save_path = os.path.join(save_dir, filename)
                
                # 保存图像
                self.save_render_image(response, save_path)
                
                # 在结果中添加保存路径信息
                result["saved_to"] = save_path
        
        return response
    
    def save_render_image(self, render_result: Dict[str, Any], save_path: str, create_dirs: bool = True) -> bool:
        """
        将渲染结果中的图像数据保存到文件
        
        Args:
            render_result: render_scene方法返回的结果
            save_path: 保存图像的文件路径
            create_dirs: 是否自动创建目录，默认为True
            
        Returns:
            是否成功保存图像
        """
        try:
            # 检查结果是否包含图像数据
            if render_result.get("status") != "success":
                print(f"渲染结果状态不是success: {render_result.get('status')}")
                return False
                
            result = render_result.get("result", {})
            if "image_data" not in result:
                print("渲染结果中不包含图像数据")
                return False
            
            # 获取base64编码的图像数据
            image_data = result["image_data"]
            
            # 确保目标目录存在
            save_dir = os.path.dirname(save_path)
            if save_dir and not os.path.exists(save_dir) and create_dirs:
                os.makedirs(save_dir)
            
            # 将base64编码的图像数据解码并保存到文件
            with open(save_path, "wb") as img_file:
                img_data = base64.b64decode(image_data)
                img_file.write(img_data)
            
            print(f"图像已保存到: {os.path.abspath(save_path)}")
            return True
            
        except Exception as e:
            print(f"保存图像时出错: {str(e)}")
            return False

def main():
    """
    测试与Blender MCP服务器的连接
    """
    import sys
    import os
    from datetime import datetime
    
    # 创建客户端实例
    print("创建BlenderClient实例...")
    client = BlenderClient()
    
    # 尝试连接并获取场景信息
    print("尝试连接到Blender MCP服务器...")
    
    try:
        response = client.get_scene_info()
        
        # 输出连接结果
        if response.get("status") == "error":
            print(f"连接失败: {response.get('message')}")
        else:
            print("连接成功！")
            print(f"场景信息: {json.dumps(response, ensure_ascii=False, indent=2)}")
            
            # 尝试创建一个立方体
            print("\n创建一个立方体...")
            cube_response = client.create_object("CUBE", name="测试立方体", location=(0, 0, 3))
            print(f"创建结果: {json.dumps(cube_response, ensure_ascii=False, indent=2)}")
            
            # 设置红色材质
            print("\n为立方体设置红色材质...")
            material_response = client.set_material("测试立方体", 
                                                 material_name="测试红色材质", 
                                                 color=[1.0, 0.0, 0.0, 1.0])
            print(f"设置材质结果: {json.dumps(material_response, ensure_ascii=False, indent=2)}")
            
            # 渲染场景并保存图像
            print("\n渲染场景并保存图像...")
            render_response = client.render_scene(
                resolution_x=800, 
                resolution_y=600, 
                return_image=True,
                auto_save=True,
                save_dir="renders"
            )
            
            if render_response.get("status") == "success":
                result = render_response.get("result", {})
                if "image_data" in result:
                    print(f"成功获取渲染图像数据，长度: {len(result['image_data'])} 字节")
                    if "saved_to" in result:
                        print(f"图像已自动保存到: {result['saved_to']}")
                else:
                    print("渲染成功但未返回图像数据")
            else:
                print(f"渲染失败: {render_response.get('message')}")
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"发生未预期的异常: {type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 