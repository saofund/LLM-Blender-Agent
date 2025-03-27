import bpy
import mathutils
import json
import threading
import socket
import time
import requests
import tempfile
import traceback
import os
import shutil
import base64
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty, FloatProperty

bl_info = {
    "name": "LLM Blender Agent",
    "author": "SAOFUND",
    "version": (0, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderMCP / Hunyuan3D-2",
    "description": "Connect Blender to Claude via MCP and generate/texture 3D models with Hunyuan3D-2",
    "category": "Interface",
}

# Hunyuan3D Properties
class Hunyuan3DProperties(bpy.types.PropertyGroup):
    prompt: StringProperty(
        name="Text Prompt",
        description="Describe what you want to generate",
        default=""
    )
    api_url: StringProperty(
        name="API URL",
        description="URL of the Text-to-3D API service",
        default="http://192.168.111.3:9875"
    )
    is_processing: BoolProperty(
        name="Processing",
        default=False
    )
    job_id: StringProperty(
        name="Job ID",
        default=""
    )
    status_message: StringProperty(
        name="Status Message",
        default=""
    )
    # 添加图片路径属性
    image_path: StringProperty(
        name="Image",
        description="Select an image to upload",
        subtype='FILE_PATH'
    )
    # 修改后的 octree_resolution 属性
    octree_resolution: IntProperty(
        name="Octree Resolution",
        description="Octree resolution for the 3D generation",
        default=256,
        min=128,
        max=512,
    )
    num_inference_steps: IntProperty(
        name="Number of Inference Steps",
        description="Number of inference steps for the 3D generation",
        default=20,
        min=20,
        max=50
    )
    guidance_scale: FloatProperty(
        name="Guidance Scale",
        description="Guidance scale for the 3D generation",
        default=5.5,
        min=1.0,
        max=10.0
    )
    # 添加 texture 属性
    texture: BoolProperty(
        name="Generate Texture",
        description="Whether to generate texture for the 3D model",
        default=False
    )

class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
    
    def start(self):
        if self.running:
            print("Server is already running")
            return
            
        self.running = True
        
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            
            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            print(f"BlenderMCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            
    def stop(self):
        self.running = False
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Wait for thread to finish
        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None
        
        print("BlenderMCP server stopped")
    
    def _server_loop(self):
        """Main server loop in a separate thread"""
        print("Server thread started")
        self.socket.settimeout(1.0)  # Timeout to allow for stopping
        
        while self.running:
            try:
                # Accept new connection
                try:
                    client, address = self.socket.accept()
                    print(f"Connected to client: {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Just check running condition
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {str(e)}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error in server loop: {str(e)}")
                if not self.running:
                    break
                time.sleep(0.5)
        
        print("Server thread stopped")
    
    def _handle_client(self, client):
        """Handle connected client"""
        print("Client handler started")
        client.settimeout(None)  # No timeout
        buffer = b''
        
        try:
            while self.running:
                # Receive data
                try:
                    data = client.recv(8192)
                    if not data:
                        print("Client disconnected")
                        break
                    
                    buffer += data
                    try:
                        # Try to parse command
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b''
                        
                        # Execute command in Blender's main thread
                        def execute_wrapper():
                            try:
                                response = self.execute_command(command)
                                response_json = json.dumps(response)
                                try:
                                    client.sendall(response_json.encode('utf-8'))
                                except:
                                    print("Failed to send response - client disconnected")
                            except Exception as e:
                                print(f"Error executing command: {str(e)}")
                                traceback.print_exc()
                                try:
                                    error_response = {
                                        "status": "error",
                                        "message": str(e)
                                    }
                                    client.sendall(json.dumps(error_response).encode('utf-8'))
                                except:
                                    pass
                            return None
                        
                        # Schedule execution in main thread
                        bpy.app.timers.register(execute_wrapper, first_interval=0.0)
                    except json.JSONDecodeError:
                        # Incomplete data, wait for more
                        pass
                except Exception as e:
                    print(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            print(f"Error in client handler: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            print("Client handler stopped")

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})
            
            # Ensure we're in the right context
            if cmd_type in ["create_object", "modify_object", "delete_object"]:
                override = bpy.context.copy()
                override['area'] = [area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'][0]
                with bpy.context.temp_override(**override):
                    return self._execute_command_internal(command)
            else:
                return self._execute_command_internal(command)
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})
        
        # Base handlers that are always available
        handlers = {
            "get_scene_info": self.get_scene_info,
            "create_object": self.create_object,
            "modify_object": self.modify_object,
            "delete_object": self.delete_object,
            "get_object_info": self.get_object_info,
            "execute_code": self.execute_code,
            "set_material": self.set_material,
            "render_scene": self.render_scene,
            "generate_3d_model": self.generate_3d_model,
        }
        
        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    def get_simple_info(self):
        """Get basic Blender information"""
        return {
            "blender_version": ".".join(str(v) for v in bpy.app.version),
            "scene_name": bpy.context.scene.name,
            "object_count": len(bpy.context.scene.objects)
        }
    
    def get_scene_info(self):
        """Get information about the current Blender scene"""
        try:
            print("Getting scene info...")
            # Simplify the scene info to reduce data size
            scene_info = {
                "name": bpy.context.scene.name,
                "object_count": len(bpy.context.scene.objects),
                "objects": [],
                "materials_count": len(bpy.data.materials),
            }
            
            # Collect minimal object information (limit to first 10 objects)
            for i, obj in enumerate(bpy.context.scene.objects):
                if i >= 10:  # Reduced from 20 to 10
                    break
                    
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    # Only include basic location data
                    "location": [round(float(obj.location.x), 2), 
                                round(float(obj.location.y), 2), 
                                round(float(obj.location.z), 2)],
                }
                scene_info["objects"].append(obj_info)
            
            print(f"Scene info collected: {len(scene_info['objects'])} objects")
            return scene_info
        except Exception as e:
            print(f"Error in get_scene_info: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    @staticmethod
    def _get_aabb(obj):
        """ Returns the world-space axis-aligned bounding box (AABB) of an object. """
        if obj.type != 'MESH':
            raise TypeError("Object must be a mesh")

        # Get the bounding box corners in local space
        local_bbox_corners = [mathutils.Vector(corner) for corner in obj.bound_box]

        # Convert to world coordinates
        world_bbox_corners = [obj.matrix_world @ corner for corner in local_bbox_corners]

        # Compute axis-aligned min/max coordinates
        min_corner = mathutils.Vector(map(min, zip(*world_bbox_corners)))
        max_corner = mathutils.Vector(map(max, zip(*world_bbox_corners)))

        return [
            [*min_corner], [*max_corner]
        ]

    def create_object(self, type="CUBE", name=None, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1),
                    align="WORLD", major_segments=48, minor_segments=12, mode="MAJOR_MINOR",
                    major_radius=1.0, minor_radius=0.25, abso_major_rad=1.25, abso_minor_rad=0.75, generate_uvs=True):
        """Create a new object in the scene"""
        try:
            # Deselect all objects first
            bpy.ops.object.select_all(action='DESELECT')
            
            # Create the object based on type
            if type == "CUBE":
                bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation, scale=scale)
            elif type == "SPHERE":
                bpy.ops.mesh.primitive_uv_sphere_add(location=location, rotation=rotation, scale=scale)
            elif type == "CYLINDER":
                bpy.ops.mesh.primitive_cylinder_add(location=location, rotation=rotation, scale=scale)
            elif type == "PLANE":
                bpy.ops.mesh.primitive_plane_add(location=location, rotation=rotation, scale=scale)
            elif type == "CONE":
                bpy.ops.mesh.primitive_cone_add(location=location, rotation=rotation, scale=scale)
            elif type == "TORUS":
                bpy.ops.mesh.primitive_torus_add(
                    align=align,
                    location=location,
                    rotation=rotation,
                    major_segments=major_segments,
                    minor_segments=minor_segments,
                    mode=mode,
                    major_radius=major_radius,
                    minor_radius=minor_radius,
                    abso_major_rad=abso_major_rad,
                    abso_minor_rad=abso_minor_rad,
                    generate_uvs=generate_uvs
                )
            elif type == "EMPTY":
                bpy.ops.object.empty_add(location=location, rotation=rotation, scale=scale)
            elif type == "CAMERA":
                bpy.ops.object.camera_add(location=location, rotation=rotation)
            elif type == "LIGHT":
                bpy.ops.object.light_add(type='POINT', location=location, rotation=rotation, scale=scale)
            else:
                raise ValueError(f"Unsupported object type: {type}")
            
            # Force update the view layer
            bpy.context.view_layer.update()
            
            # Get the active object (which should be our newly created object)
            obj = bpy.context.view_layer.objects.active
            
            # If we don't have an active object, something went wrong
            if obj is None:
                raise RuntimeError("Failed to create object - no active object")
            
            # Make sure it's selected
            obj.select_set(True)
            
            # Rename if name is provided
            if name:
                obj.name = name
                if obj.data:
                    obj.data.name = name
            
            # Return the object info
            result = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            }
            
            if obj.type == "MESH":
                bounding_box = self._get_aabb(obj)
                result["world_bounding_box"] = bounding_box
            
            return result
        except Exception as e:
            print(f"Error in create_object: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

    def modify_object(self, name, location=None, rotation=None, scale=None, visible=None):
        """Modify an existing object in the scene"""
        # Find the object by name
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Modify properties as requested
        if location is not None:
            obj.location = location
        
        if rotation is not None:
            obj.rotation_euler = rotation
        
        if scale is not None:
            obj.scale = scale
        
        if visible is not None:
            obj.hide_viewport = not visible
            obj.hide_render = not visible
        
        result = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
        }

        if obj.type == "MESH":
            bounding_box = self._get_aabb(obj)
            result["world_bounding_box"] = bounding_box

        return result

    def delete_object(self, name):
        """Delete an object from the scene"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Store the name to return
        obj_name = obj.name
        
        # Select and delete the object
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        
        return {"deleted": obj_name}
    
    def get_object_info(self, name):
        """Get detailed information about a specific object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Basic object info
        obj_info = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
            "materials": [],
        }

        if obj.type == "MESH":
            bounding_box = self._get_aabb(obj)
            obj_info["world_bounding_box"] = bounding_box
        
        # Add material slots
        for slot in obj.material_slots:
            if slot.material:
                obj_info["materials"].append(slot.material.name)
        
        # Add mesh data if applicable
        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            obj_info["mesh"] = {
                "vertices": len(mesh.vertices),
                "edges": len(mesh.edges),
                "polygons": len(mesh.polygons),
            }
        
        return obj_info
    
    def execute_code(self, code):
        """Execute arbitrary Blender Python code"""
        # This is powerful but potentially dangerous - use with caution
        try:
            # Create a local namespace for execution
            namespace = {"bpy": bpy}
            exec(code, namespace)
            return {"executed": True}
        except Exception as e:
            raise Exception(f"Code execution error: {str(e)}")
    
    def set_material(self, object_name, material_name=None, create_if_missing=True, color=None):
        """Set or create a material for an object"""
        try:
            # Get the object
            obj = bpy.data.objects.get(object_name)
            if not obj:
                raise ValueError(f"Object not found: {object_name}")
            
            # Make sure object can accept materials
            if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                raise ValueError(f"Object {object_name} cannot accept materials")
            
            # Create or get material
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat and create_if_missing:
                    mat = bpy.data.materials.new(name=material_name)
                    print(f"Created new material: {material_name}")
            else:
                # Generate unique material name if none provided
                mat_name = f"{object_name}_material"
                mat = bpy.data.materials.get(mat_name)
                if not mat:
                    mat = bpy.data.materials.new(name=mat_name)
                material_name = mat_name
                print(f"Using material: {mat_name}")
            
            # Set up material nodes if needed
            if mat:
                if not mat.use_nodes:
                    mat.use_nodes = True
                
                # Get or create Principled BSDF
                principled = mat.node_tree.nodes.get('Principled BSDF')
                if not principled:
                    principled = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    # Get or create Material Output
                    output = mat.node_tree.nodes.get('Material Output')
                    if not output:
                        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                    # Link if not already linked
                    if not principled.outputs[0].links:
                        mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
                
                # Set color if provided
                if color and len(color) >= 3:
                    principled.inputs['Base Color'].default_value = (
                        color[0],
                        color[1],
                        color[2],
                        1.0 if len(color) < 4 else color[3]
                    )
                    print(f"Set material color to {color}")
            
            # Assign material to object if not already assigned
            if mat:
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    # Only modify first material slot
                    obj.data.materials[0] = mat
                
                print(f"Assigned material {mat.name} to object {object_name}")
                
                return {
                    "status": "success",
                    "object": object_name,
                    "material": mat.name,
                    "color": color if color else None
                }
            else:
                raise ValueError(f"Failed to create or find material: {material_name}")
            
        except Exception as e:
            print(f"Error in set_material: {str(e)}")
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "object": object_name,
                "material": material_name if 'material_name' in locals() else None
            }
    
    def render_scene(self, output_path=None, resolution_x=None, resolution_y=None, return_image=False):
        """Render the current scene"""
        if resolution_x is not None:
            bpy.context.scene.render.resolution_x = resolution_x
        
        if resolution_y is not None:
            bpy.context.scene.render.resolution_y = resolution_y
        
        # 创建临时文件路径用于保存渲染结果
        temp_path = None
        if return_image or not output_path:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                temp_path = tmp_file.name
        
        # 设置输出路径
        render_path = output_path if output_path else temp_path
        bpy.context.scene.render.filepath = render_path
        
        # 渲染场景
        bpy.ops.render.render(write_still=True)
        
        result = {
            "rendered": True,
            "output_path": output_path if output_path else "[temp file]",
            "resolution": [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y],
        }
        
        # 如果需要返回图像数据
        if return_image and os.path.exists(render_path):
            try:
                # 读取渲染后的图像文件
                with open(render_path, 'rb') as img_file:
                    img_data = img_file.read()
                
                # 将图像编码为base64字符串
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                result["image_data"] = img_base64
                
                # 如果使用了临时文件且不需要保留，则删除该文件
                if temp_path and not output_path:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            except Exception as e:
                print(f"读取渲染图像文件错误: {str(e)}")
                result["image_error"] = str(e)
        
        return result

    def generate_3d_model(self, text=None, image_data=None, object_name=None, 
                         api_url="http://192.168.111.3:9875", octree_resolution=256, 
                         num_inference_steps=20, guidance_scale=10, texture=False):
        """Generate 3D model using Hunyuan3D API
        
        Args:
            text (str): Text prompt for generation
            image_data (str): Base64 encoded image data
            object_name (str): Name of object to apply texture to (optional)
            api_url (str): Hunyuan3D API URL
            octree_resolution (int): Resolution for generation
            num_inference_steps (int): Number of steps
            guidance_scale (float): Guidance scale
            texture (bool): Generate with texture
            
        Returns:
            dict: Result information
        """
        try:
            # 检查参数
            if not text and not image_data:
                raise ValueError("必须提供文本提示或图像数据")
            
            # 优先使用用户在界面上设置的API URL
            if hasattr(bpy.context.scene, "gen_3d_props") and bpy.context.scene.gen_3d_props.api_url:
                api_url = bpy.context.scene.gen_3d_props.api_url
            
            # 准备API请求
            base_url = api_url.rstrip('/')
            request_data = {
                "octree_resolution": octree_resolution,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "texture": texture
            }
            
            # 添加文本或图像数据
            if text:
                request_data["text"] = text
            
            if image_data:
                request_data["image"] = image_data
            
            # 处理选定的对象（如果有）
            selected_mesh = None
            selected_mesh_base64 = None
            
            if object_name:
                selected_mesh = bpy.data.objects.get(object_name)
                if not selected_mesh or selected_mesh.type != 'MESH':
                    raise ValueError(f"对象 '{object_name}' 不存在或不是网格对象")
                
                # 导出对象为GLB
                temp_glb_file = tempfile.NamedTemporaryFile(delete=False, suffix=".glb")
                temp_glb_file.close()
                
                # 保存当前选择
                current_selection = bpy.context.selected_objects.copy()
                active_obj = bpy.context.view_layer.objects.active
                
                # 取消全部选择并选中目标对象
                bpy.ops.object.select_all(action='DESELECT')
                selected_mesh.select_set(True)
                bpy.context.view_layer.objects.active = selected_mesh
                
                # 导出
                bpy.ops.export_scene.gltf(filepath=temp_glb_file.name, 
                                          use_selection=True, 
                                          export_format='GLB')
                
                # 恢复选择
                bpy.ops.object.select_all(action='DESELECT')
                for obj in current_selection:
                    obj.select_set(True)
                if active_obj:
                    bpy.context.view_layer.objects.active = active_obj
                
                # 读取并编码GLB数据
                with open(temp_glb_file.name, "rb") as file:
                    mesh_data = file.read()
                selected_mesh_base64 = base64.b64encode(mesh_data).decode()
                os.unlink(temp_glb_file.name)
                
                # 添加到请求
                request_data["mesh"] = selected_mesh_base64
            
            # 创建一个线程来执行API请求
            def api_request_thread():
                try:
                    print(f"发送Hunyuan3D请求: {base_url}/generate")
                    
                    # 创建一个事件对象用于线程通信
                    request_completed = threading.Event()
                    response_data = [None]  # 使用列表存储响应，便于在内部函数中修改
                    
                    # 内部函数：执行实际的API请求
                    def make_request():
                        try:
                            response = requests.post(
                                f"{base_url}/generate",
                                json=request_data,
                                timeout=55  # 设置请求超时为55秒，留5秒处理时间
                            )
                            
                            if response.status_code != 200:
                                print(f"生成失败: {response.text}")
                                response_data[0] = None
                            else:
                                response_data[0] = response
                                
                            # 标记请求已完成
                            request_completed.set()
                        except Exception as e:
                            print(f"API请求异常: {str(e)}")
                            request_completed.set()
                    
                    # 启动请求线程
                    request_thread = threading.Thread(target=make_request)
                    request_thread.daemon = True
                    request_thread.start()
                    
                    # 等待请求完成或超时(60秒)
                    request_completed.wait(60)
                    
                    # 检查请求是否完成并处理结果
                    if not request_completed.is_set() or response_data[0] is None:
                        print("API请求超时或失败，1分钟强制返回")
                        # 在主线程中调用函数通知用户
                        def timeout_handler():
                            # 更新UI状态
                            if hasattr(bpy.context.scene, "gen_3d_props"):
                                props = bpy.context.scene.gen_3d_props
                                props.is_processing = False
                                props.status_message = "生成请求超时或失败，请稍后再试"
                            print("API请求已超时，请稍后再试")
                            return None
                        
                        bpy.app.timers.register(timeout_handler)
                        return
                    
                    # 处理成功的响应
                    response = response_data[0]
                    
                    # 保存为临时GLB文件
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".glb")
                    temp_file.write(response.content)
                    temp_file.close()
                    
                    # 在主线程中导入模型
                    def import_handler():
                        # 导入GLB
                        bpy.ops.import_scene.gltf(filepath=temp_file.name)
                        os.unlink(temp_file.name)
                        
                        # 获取新导入的对象
                        new_obj = None
                        for obj in bpy.context.selected_objects:
                            if obj.type == 'MESH':
                                new_obj = obj
                                break
                        
                        # 应用位置、旋转和缩放
                        if new_obj and selected_mesh and texture:
                            new_obj.location = selected_mesh.location
                            new_obj.rotation_euler = selected_mesh.rotation_euler
                            new_obj.scale = selected_mesh.scale
                            
                            # 隐藏原始对象
                            selected_mesh.hide_set(True)
                            selected_mesh.hide_render = True
                        
                        return None
                    
                    # 注册导入操作
                    bpy.app.timers.register(import_handler)
                    
                except Exception as e:
                    print(f"API请求线程错误: {str(e)}")
                    traceback.print_exc()
            
            # 启动线程
            thread = threading.Thread(target=api_request_thread)
            thread.daemon = True
            thread.start()
            
            # 返回立即响应
            result = {
                "status": "generating",
                "message": "3D模型生成中...",
                "params": {
                    "text": text,
                    "has_image": image_data is not None,
                    "object_name": object_name,
                    "texture": texture,
                    "octree_resolution": octree_resolution
                }
            }
            
            return result
            
        except Exception as e:
            print(f"生成3D模型错误: {str(e)}")
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "params": {
                    "text": text,
                    "has_image": image_data is not None,
                    "object_name": object_name
                }
            }

# Blender UI Panel
class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # MCP 服务器部分
        box = layout.box()
        row = box.row()
        row.label(text="MCP 服务器")
        
        box.prop(scene, "blendermcp_port")
        
        if not scene.blendermcp_server_running:
            box.operator("blendermcp.start_server", text="启动MCP服务器")
        else:
            box.operator("blendermcp.stop_server", text="停止MCP服务器")
            box.label(text=f"运行于端口 {scene.blendermcp_port}")
            
        # Hunyuan3D 折叠部分会作为子面板显示

# Operator to start the server
class BLENDERMCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Connect to Claude"
    bl_description = "Start the BlenderMCP server to connect with Claude"
    
    def execute(self, context):
        scene = context.scene
        
        # Create a new server instance
        if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
            bpy.types.blendermcp_server = BlenderMCPServer(port=scene.blendermcp_port)
        
        # Start the server
        bpy.types.blendermcp_server.start()
        scene.blendermcp_server_running = True
        
        return {'FINISHED'}

# Operator to stop the server
class BLENDERMCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop the connection to Claude"
    bl_description = "Stop the connection to Claude"
    
    def execute(self, context):
        scene = context.scene
        
        # Stop the server if it exists
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server
        
        scene.blendermcp_server_running = False
        
        return {'FINISHED'}

# Hunyuan3D Operator and Panel
class Hunyuan3DOperator(bpy.types.Operator):
    bl_idname = "object.generate_3d"
    bl_label = "Generate 3D Model"
    bl_description = "Generate a 3D model from text description, an image or a selected mesh"

    job_id = ''
    prompt = ""
    api_url = ""
    image_path = ""
    octree_resolution = 256
    num_inference_steps = 20
    guidance_scale = 5.5
    texture = False  # 新增属性
    selected_mesh_base64 = ""
    selected_mesh = None  # 新增属性，用于存储选中的 mesh

    thread = None
    task_finished = False

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        if self.task_finished:
            print("Threaded task completed")
            self.task_finished = False
            props = context.scene.gen_3d_props
            props.is_processing = False

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # 启动线程
        props = context.scene.gen_3d_props
        self.prompt = props.prompt
        self.api_url = props.api_url
        self.image_path = props.image_path
        self.octree_resolution = props.octree_resolution
        self.num_inference_steps = props.num_inference_steps
        self.guidance_scale = props.guidance_scale
        self.texture = props.texture  # 获取 texture 属性的值

        if self.prompt == "" and self.image_path == "":
            self.report({'WARNING'}, "Please enter some text or select an image first.")
            return {'FINISHED'}

        # 保存选中的 mesh 对象引用
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                self.selected_mesh = obj
                break

        if self.selected_mesh:
            temp_glb_file = tempfile.NamedTemporaryFile(delete=False, suffix=".glb")
            temp_glb_file.close()
            bpy.ops.export_scene.gltf(filepath=temp_glb_file.name, use_selection=True)
            with open(temp_glb_file.name, "rb") as file:
                mesh_data = file.read()
            mesh_b64_str = base64.b64encode(mesh_data).decode()
            os.unlink(temp_glb_file.name)
            self.selected_mesh_base64 = mesh_b64_str

        props.is_processing = True

        # 将相对路径转换为相对于 Blender 文件所在目录的绝对路径
        blend_file_dir = os.path.dirname(bpy.data.filepath)
        self.report({'INFO'}, f"blend_file_dir {blend_file_dir}")
        self.report({'INFO'}, f"image_path {self.image_path}")
        if self.image_path.startswith('//'):
            self.image_path = self.image_path[2:]
            self.image_path = os.path.join(blend_file_dir, self.image_path)

        if self.selected_mesh and self.texture:
            props.status_message = "Texturing Selected Mesh...\n" \
                                   "This may take several minutes depending \n on your GPU power."
        else:
            mesh_type = 'Textured Mesh' if self.texture else 'White Mesh'
            prompt_type = 'Text Prompt' if self.prompt else 'Image'
            props.status_message = f"Generating {mesh_type} with {prompt_type}...\n" \
                                   "This may take several minutes depending \n on your GPU power."

        self.thread = threading.Thread(target=self.generate_model)
        self.thread.start()

        wm = context.window_manager
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def generate_model(self):
        self.report({'INFO'}, f"Generation Start")
        base_url = self.api_url.rstrip('/')

        try:
            if self.selected_mesh_base64 and self.texture:
                # Texturing the selected mesh
                if self.image_path and os.path.exists(self.image_path):
                    self.report({'INFO'}, f"Post Texturing with Image")
                    # 打开图片文件并以二进制模式读取
                    with open(self.image_path, "rb") as file:
                        # 读取文件内容
                        image_data = file.read()
                    # 对图片数据进行 Base64 编码
                    img_b64_str = base64.b64encode(image_data).decode()
                    response = requests.post(
                        f"{base_url}/generate",
                        json={
                            "mesh": self.selected_mesh_base64,
                            "image": img_b64_str,
                            "octree_resolution": self.octree_resolution,
                            "num_inference_steps": self.num_inference_steps,
                            "guidance_scale": self.guidance_scale,
                            "texture": self.texture  # 传递 texture 参数
                        },
                    )
                else:
                    self.report({'INFO'}, f"Post Texturing with Text")
                    response = requests.post(
                        f"{base_url}/generate",
                        json={
                            "mesh": self.selected_mesh_base64,
                            "text": self.prompt,
                            "octree_resolution": self.octree_resolution,
                            "num_inference_steps": self.num_inference_steps,
                            "guidance_scale": self.guidance_scale,
                            "texture": self.texture  # 传递 texture 参数
                        },
                    )
            else:
                if self.image_path:
                    if not os.path.exists(self.image_path):
                        self.report({'ERROR'}, f"Image path does not exist {self.image_path}")
                        raise Exception(f'Image path does not exist {self.image_path}')
                    self.report({'INFO'}, f"Post Start Image to 3D")
                    # 打开图片文件并以二进制模式读取
                    with open(self.image_path, "rb") as file:
                        # 读取文件内容
                        image_data = file.read()
                    # 对图片数据进行 Base64 编码
                    img_b64_str = base64.b64encode(image_data).decode()
                    response = requests.post(
                        f"{base_url}/generate",
                        json={
                            "image": img_b64_str,
                            "octree_resolution": self.octree_resolution,
                            "num_inference_steps": self.num_inference_steps,
                            "guidance_scale": self.guidance_scale,
                            "texture": self.texture  # 传递 texture 参数
                        },
                    )
                else:
                    self.report({'INFO'}, f"Post Start Text to 3D")
                    response = requests.post(
                        f"{base_url}/generate",
                        json={
                            "text": self.prompt,
                            "octree_resolution": self.octree_resolution,
                            "num_inference_steps": self.num_inference_steps,
                            "guidance_scale": self.guidance_scale,
                            "texture": self.texture  # 传递 texture 参数
                        },
                    )
            self.report({'INFO'}, f"Post Done")

            if response.status_code != 200:
                self.report({'ERROR'}, f"Generation failed: {response.text}")
                return

            # Decode base64 and save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".glb")
            temp_file.write(response.content)
            temp_file.close()

            # Import the GLB file in the main thread
            def import_handler():
                bpy.ops.import_scene.gltf(filepath=temp_file.name)
                os.unlink(temp_file.name)

                # 获取新导入的 mesh
                new_obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None
                if new_obj and self.selected_mesh and self.texture:
                    # 应用选中 mesh 的位置、旋转和缩放
                    new_obj.location = self.selected_mesh.location
                    new_obj.rotation_euler = self.selected_mesh.rotation_euler
                    new_obj.scale = self.selected_mesh.scale

                    # 隐藏原来的 mesh
                    self.selected_mesh.hide_set(True)
                    self.selected_mesh.hide_render = True

                return None

            bpy.app.timers.register(import_handler)

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")

        finally:
            self.task_finished = True
            self.selected_mesh_base64 = ""


class Hunyuan3DPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'
    bl_label = 'Hunyuan3D-2 3D Generator'
    bl_idname = "BLENDERMCP_PT_Hunyuan3D"
    bl_parent_id = "BLENDERMCP_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.gen_3d_props

        layout.prop(props, "api_url")
        layout.prop(props, "prompt")
        # 添加图片选择器
        layout.prop(props, "image_path")
        # 添加新属性的 UI 元素
        layout.prop(props, "octree_resolution")
        layout.prop(props, "num_inference_steps")
        layout.prop(props, "guidance_scale")
        # 添加 texture 属性的 UI 元素
        layout.prop(props, "texture")

        row = layout.row()
        row.enabled = not props.is_processing
        row.operator("object.generate_3d")

        if props.is_processing:
            if props.status_message:
                for line in props.status_message.split("\n"):
                    layout.label(text=line)
            else:
                layout.label(text="Processing...")

# Registration functions
def register():
    bpy.types.Scene.blendermcp_port = IntProperty(
        name="Port",
        description="Port for the BlenderMCP server",
        default=9876,
        min=1024,
        max=65535
    )
    
    bpy.types.Scene.blendermcp_server_running = bpy.props.BoolProperty(
        name="Server Running",
        default=False
    )
    
    bpy.utils.register_class(BLENDERMCP_PT_Panel)
    bpy.utils.register_class(BLENDERMCP_OT_StartServer)
    bpy.utils.register_class(BLENDERMCP_OT_StopServer)
    
    # 注册 Hunyuan3D 相关类
    bpy.utils.register_class(Hunyuan3DProperties)
    bpy.utils.register_class(Hunyuan3DOperator)
    bpy.utils.register_class(Hunyuan3DPanel)
    
    # 添加 Hunyuan3D 属性组到场景
    bpy.types.Scene.gen_3d_props = bpy.props.PointerProperty(type=Hunyuan3DProperties)
    
    print("BlenderMCP addon registered")

def unregister():
    # Stop the server if it's running
    if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
        bpy.types.blendermcp_server.stop()
        del bpy.types.blendermcp_server
    
    bpy.utils.unregister_class(BLENDERMCP_PT_Panel)
    bpy.utils.unregister_class(BLENDERMCP_OT_StartServer)
    bpy.utils.unregister_class(BLENDERMCP_OT_StopServer)
    
    # 注销 Hunyuan3D 相关类
    bpy.utils.unregister_class(Hunyuan3DOperator)
    bpy.utils.unregister_class(Hunyuan3DPanel)
    bpy.utils.unregister_class(Hunyuan3DProperties)
    
    del bpy.types.Scene.blendermcp_port
    del bpy.types.Scene.blendermcp_server_running
    del bpy.types.Scene.gen_3d_props

    print("BlenderMCP addon unregistered")

if __name__ == "__main__":
    register()
