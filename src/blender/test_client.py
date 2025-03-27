"""
Blender MCP 客户端测试程序
"""
import os
import sys
import json
import time
import base64
import tempfile
import argparse
import traceback
from typing import Dict, Any, List, Optional

# 导入 BlenderClient 类
from client import BlenderClient

def print_response(description: str, response: Dict[str, Any]) -> None:
    """打印响应结果"""
    print("\n" + "=" * 60)
    print(f"【{description}】")
    print("=" * 60)
    
    if response.get("status") == "error":
        print(f"错误: {response.get('message')}")
    else:
        print(f"状态: {response.get('status')}")
        result = response.get("result")
        if result:
            print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print("没有返回结果数据")
    
    print("=" * 60)

def pause():
    """暂停并等待用户按Enter键继续"""
    input("\n按Enter键继续...\n")

def test_get_scene_info(client: BlenderClient) -> None:
    """测试获取场景信息"""
    print_response("获取场景信息", client.get_scene_info())
    pause()

def test_create_object(client: BlenderClient) -> None:
    """测试创建对象"""
    # 测试创建立方体
    print_response("创建立方体", 
                  client.create_object("CUBE", name="测试立方体", 
                                     location=(0, 0, 3), 
                                     scale=(1.5, 1.5, 1.5)))
    pause()
    
    # 测试创建球体
    print_response("创建球体", 
                  client.create_object("SPHERE", name="测试球体", 
                                     location=(3, 0, 3), 
                                     scale=(1.2, 1.2, 1.2)))
    pause()

def test_get_object_info(client: BlenderClient) -> None:
    """测试获取对象信息"""
    # 创建一个测试对象
    client.create_object("CUBE", name="测试对象信息立方体", location=(0, 0, 0))
    
    # 获取对象信息
    print_response("获取对象信息", client.get_object_info("测试对象信息立方体"))
    pause()
    

def test_modify_object(client: BlenderClient) -> None:
    """测试修改对象"""
    # 创建一个测试对象
    client.create_object("CUBE", name="测试修改对象", location=(0, 0, 0))
    
    # 修改位置
    print_response("修改对象位置",
                  client.modify_object("测试修改对象", location=(2, 2, 2)))
    pause()
    
    # 修改旋转
    print_response("修改对象旋转",
                  client.modify_object("测试修改对象", rotation=(0.5, 0.5, 0.5)))
    pause()
    
    # 修改缩放
    print_response("修改对象缩放",
                  client.modify_object("测试修改对象", scale=(2.0, 2.0, 2.0)))
    pause()
    
    # 修改可见性
    print_response("修改对象可见性",
                  client.modify_object("测试修改对象", visible=False))
    pause()
    
    # 重新显示对象
    print_response("重新显示对象",
                  client.modify_object("测试修改对象", visible=True))
    pause()
    
    # 同时修改多个属性
    print_response("同时修改多个属性",
                  client.modify_object("测试修改对象", 
                                      location=(0, 0, 0),
                                      rotation=(0, 0, 0),
                                      scale=(1, 1, 1)))
    pause()

def test_delete_object(client: BlenderClient) -> None:
    """测试删除对象"""
    # 创建一个测试对象
    client.create_object("CUBE", name="测试删除对象", location=(0, 0, 0))
    
    # 删除对象
    print_response("删除对象", client.delete_object("测试删除对象"))
    pause()
    
    # 测试删除不存在的对象
    print_response("删除不存在的对象", client.delete_object("不存在的对象"))
    pause()

def test_set_material(client: BlenderClient) -> None:
    """测试设置材质"""
    # 创建一个测试对象
    client.create_object("CUBE", name="测试材质对象", location=(0, 0, 0))
    
    # 设置红色材质
    print_response("设置红色材质",
                  client.set_material("测试材质对象", 
                                     material_name="红色材质", 
                                     color=[1.0, 0.0, 0.0, 1.0]))
    pause()
    
    # 设置绿色材质
    print_response("设置绿色材质",
                  client.set_material("测试材质对象", 
                                     material_name="绿色材质", 
                                     color=[0.0, 1.0, 0.0, 1.0]))
    pause()
    
    # 设置蓝色材质（半透明）
    print_response("设置蓝色半透明材质",
                  client.set_material("测试材质对象", 
                                     material_name="蓝色半透明材质", 
                                     color=[0.0, 0.0, 1.0, 0.5]))
    pause()

def test_execute_code(client: BlenderClient) -> None:
    """测试Python代码执行"""
    # 简单代码测试
    simple_code = """
import bpy
result = {"current_scene": bpy.context.scene.name}
"""
    print_response("执行简单代码", client.execute_code(simple_code))
    pause()
    
    # 创建对象的代码
    create_object_code = """
import bpy

# 创建一个新的球体
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, -3, 3))
sphere = bpy.context.active_object
sphere.name = "代码创建的球体"

# 创建蓝色材质
if "蓝色材质" not in bpy.data.materials:
    mat = bpy.data.materials.new("蓝色材质")
    mat.diffuse_color = (0, 0, 1, 1)
else:
    mat = bpy.data.materials["蓝色材质"]

# 应用材质
if sphere.data.materials:
    sphere.data.materials[0] = mat
else:
    sphere.data.materials.append(mat)

# 返回结果
result = {
    "name": sphere.name,
    "location": list(sphere.location),
    "material": mat.name
}
"""
    print_response("执行创建对象代码", client.execute_code(create_object_code))
    pause()
    
    # 测试复杂操作
    complex_code = """
import bpy
import bmesh
import math

# 创建一个自定义网格
mesh = bpy.data.meshes.new("CustomMesh")
obj = bpy.data.objects.new("自定义网格对象", mesh)

# 链接到场景
bpy.context.collection.objects.link(obj)

# 创建一个bmesh来编辑网格
bm = bmesh.new()

# 添加一个金字塔
h = 2.0  # 高度
v1 = bm.verts.new((-1, -1, 0))
v2 = bm.verts.new((1, -1, 0))
v3 = bm.verts.new((1, 1, 0))
v4 = bm.verts.new((-1, 1, 0))
v5 = bm.verts.new((0, 0, h))

# 创建面
bm.faces.new((v1, v2, v5))
bm.faces.new((v2, v3, v5))
bm.faces.new((v3, v4, v5))
bm.faces.new((v4, v1, v5))
bm.faces.new((v1, v4, v3, v2))

# 更新网格
bm.to_mesh(mesh)
bm.free()

# 设置对象位置
obj.location = (5, 0, 0)

# 创建材质
mat = bpy.data.materials.new("自定义材质")
mat.diffuse_color = (0.8, 0.2, 0.8, 1.0)  # 紫色
obj.data.materials.append(mat)

result = {
    "object_name": obj.name,
    "vertices": len(obj.data.vertices),
    "faces": len(obj.data.polygons),
    "location": list(obj.location)
}
"""
    print_response("执行复杂自定义网格代码", client.execute_code(complex_code))
    pause()

def test_render_scene(client: BlenderClient) -> None:
    """测试场景渲染"""
    # 创建一些测试对象
    client.create_object("CUBE", name="渲染测试立方体", 
                        location=(0, 0, 0), 
                        scale=(1, 1, 1))
    client.set_material("渲染测试立方体", 
                       material_name="红色材质", 
                       color=[1.0, 0.0, 0.0, 1.0])
                       
    client.create_object("SPHERE", name="渲染测试球体", 
                        location=(3, 0, 0), 
                        scale=(1, 1, 1))
    client.set_material("渲染测试球体", 
                       material_name="绿色材质", 
                       color=[0.0, 1.0, 0.0, 1.0])
    
    # 默认参数渲染（返回图像数据）
    print("默认参数渲染（返回图像数据）...")
    render_result = client.render_scene()
    print_response("默认参数渲染结果", render_result)
    pause()
    
    # 指定分辨率渲染
    print("指定分辨率渲染...")
    render_result = client.render_scene(
        resolution_x=800, 
        resolution_y=600, 
        return_image=True,
        auto_save=True,
        save_dir="renders"
    )
    print_response("指定分辨率渲染结果", render_result)
    
    # 检查是否成功获取图像数据
    result = render_result.get("result", {})
    if "image_data" in result:
        image_data = result["image_data"]
        print(f"成功获取图像数据，长度: {len(image_data)} 字节")
        print("图像数据前100个字符: " + image_data[:100] + "...")
        
        if "saved_to" in result:
            print(f"图像已自动保存到: {result['saved_to']}")
    else:
        print("未能获取图像数据")
    
    pause()
    
    # 渲染到文件
    print("渲染到指定文件...")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        output_path = tmp_file.name
    
    render_file_result = client.render_scene(
        output_path=output_path, 
        resolution_x=800, 
        resolution_y=600, 
        return_image=False,
        auto_save=False
    )
    print_response("渲染到文件结果", render_file_result)
    
    if os.path.exists(output_path):
        print(f"成功渲染到文件: {output_path}")
        file_size = os.path.getsize(output_path)
        print(f"文件大小: {file_size} 字节")
    else:
        print(f"未能找到渲染输出文件: {output_path}")
    
    pause()

def test_save_render_image(client: BlenderClient) -> None:
    """测试保存渲染图像"""
    # 先渲染一个图像
    render_result = client.render_scene(
        resolution_x=800, 
        resolution_y=600, 
        return_image=True,
        auto_save=False
    )
    
    if render_result.get("status") == "success" and "image_data" in render_result.get("result", {}):
        # 创建临时文件名
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            save_path = tmp_file.name
        
        # 测试保存图像
        print(f"尝试保存图像到: {save_path}")
        success = client.save_render_image(render_result, save_path)
        
        if success:
            print(f"图像成功保存到: {save_path}")
            file_size = os.path.getsize(save_path)
            print(f"文件大小: {file_size} 字节")
        else:
            print("保存图像失败")
    else:
        print("渲染失败或未返回图像数据，无法测试保存图像功能")
    
    pause()

def test_generate_3d_model(client: BlenderClient) -> None:
    """测试生成3D模型"""
    # 使用文本提示生成3D模型
    print_response("使用文本提示生成3D模型", 
                  client.generate_3d_model(
                      text="一个红色的苹果",
                      object_name=None,
                      octree_resolution=128,
                      num_inference_steps=20,
                      guidance_scale=5.5,
                      texture=True
                  ))
    pause()
    
    # 如果有图片文件，测试使用图片生成3D模型
    test_image_path = "test_image.jpg"
    if os.path.exists(test_image_path):
        print_response("使用图片生成3D模型", 
                      client.generate_3d_model(
                          image_path=test_image_path,
                          object_name=None,
                          octree_resolution=128,
                          num_inference_steps=20,
                          guidance_scale=5.5,
                          texture=True
                      ))
        pause()
    else:
        print(f"找不到测试图片文件: {test_image_path}，跳过图片生成测试")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Blender MCP 客户端测试")
    parser.add_argument("--host", default="localhost", help="Blender MCP 服务器主机名")
    parser.add_argument("--port", type=int, default=9876, help="Blender MCP 服务器端口号")
    parser.add_argument("--test", default="all", 
                      choices=["all", "scene_info", "create_object", "object_info", 
                               "modify_object", "delete_object", "set_material", 
                               "execute_code", "render_scene", "save_render_image",
                               "generate_3d_model"], 
                      help="要运行的测试")
    
    args = parser.parse_args()
    
    print(f"连接到 Blender MCP 服务器 {args.host}:{args.port}")
    client = BlenderClient(args.host, args.port)
    
    try:
        # 根据参数选择要运行的测试
        if args.test in ["all", "scene_info"]:
            print("\n运行测试: 获取场景信息")
            test_get_scene_info(client)
        
        if args.test in ["all", "create_object"]:
            print("\n运行测试: 创建对象")
            test_create_object(client)
            
        if args.test in ["all", "object_info"]:
            print("\n运行测试: 获取对象信息")
            test_get_object_info(client)
            
        if args.test in ["all", "modify_object"]:
            print("\n运行测试: 修改对象")
            test_modify_object(client)
            
        if args.test in ["all", "delete_object"]:
            print("\n运行测试: 删除对象")
            test_delete_object(client)
            
        if args.test in ["all", "set_material"]:
            print("\n运行测试: 设置材质")
            test_set_material(client)
            
        if args.test in ["all", "execute_code"]:
            print("\n运行测试: 执行Python代码")
            test_execute_code(client)
            
        if args.test in ["all", "render_scene"]:
            print("\n运行测试: 渲染场景")
            test_render_scene(client)
            
        if args.test in ["all", "save_render_image"]:
            print("\n运行测试: 保存渲染图像")
            test_save_render_image(client)
            
        if args.test in ["all", "generate_3d_model"]:
            print("\n运行测试: 生成3D模型")
            test_generate_3d_model(client)
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 