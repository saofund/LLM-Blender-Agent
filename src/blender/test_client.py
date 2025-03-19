"""
Blender MCP 客户端测试程序
"""
import os
import sys
import json
import time
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

def test_basic_operations(client: BlenderClient) -> None:
    """测试基本操作功能"""
    # 测试获取场景信息
    print_response("获取场景信息", client.get_scene_info())
    pause()
    
    # 测试创建一个立方体
    print_response("创建立方体", 
                  client.create_object("CUBE", name="测试立方体", 
                                     location=(0, 0, 3), 
                                     scale=(1.5, 1.5, 1.5)))
    pause()
    
    # 测试创建一个球体
    print_response("创建球体", 
                  client.create_object("SPHERE", name="测试球体", 
                                     location=(3, 0, 3), 
                                     scale=(1.2, 1.2, 1.2)))
    pause()
    
    # 测试获取特定对象信息
    print_response("获取立方体信息", client.get_object_info("测试立方体"))
    pause()
    
    # 测试修改对象
    print_response("修改球体位置",
                  client.modify_object("测试球体", location=(3, 3, 3), 
                                      rotation=(0.5, 0.5, 0)))
    pause()
    
    # 测试设置材质
    print_response("为立方体设置红色材质",
                  client.set_material("测试立方体", 
                                     material_name="红色材质", 
                                     color=[1.0, 0.0, 0.0, 1.0]))
    pause()
    
    # 测试删除对象
    print_response("删除球体", client.delete_object("测试球体"))
    pause()

def test_python_code_execution(client: BlenderClient) -> None:
    """测试Python代码执行"""
    # 创建一个新的球体并设置材质
    code = """
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
    
    print_response("执行Python代码创建球体", client.execute_code(code))
    pause()

def test_polyhaven_integration(client: BlenderClient) -> None:
    """测试Poly Haven集成"""
    # 检查Poly Haven状态
    ph_status = client.get_polyhaven_status()
    print_response("Poly Haven状态", ph_status)
    
    if ph_status.get("status") != "success" or not ph_status.get("result", {}).get("enabled", False):
        print("Poly Haven未启用，跳过测试")
        return
    
    pause()
    
    # 获取HDRI分类
    print_response("获取HDRI分类", client.get_polyhaven_categories("hdris"))
    pause()
    
    # 搜索HDRI资源
    print_response("搜索HDRI资源", client.search_polyhaven_assets("hdris"))
    pause()
    
    # 如果有搜索结果，尝试下载一个HDRI
    search_result = client.search_polyhaven_assets("hdris")
    if search_result.get("status") == "success" and search_result.get("result"):
        hdris = search_result.get("result")
        if hdris and len(hdris) > 0:
            hdri_id = list(hdris.keys())[0]  # 获取第一个HDRI的ID
            print(f"尝试下载HDRI: {hdri_id}")
            print_response("下载HDRI资源", 
                          client.download_polyhaven_asset(hdri_id, "hdris", resolution="1k"))
            pause()

def test_hyper3d_integration(client: BlenderClient) -> None:
    """测试Hyper3D Rodin集成"""
    # 检查Hyper3D状态
    h3d_status = client.get_hyper3d_status()
    print_response("Hyper3D状态", h3d_status)
    
    if h3d_status.get("status") != "success" or not h3d_status.get("result", {}).get("enabled", False):
        print("Hyper3D未启用，跳过测试")
        return
    
    pause()
    
    # 创建一个模型生成任务 (这里只测试API调用，可能需要API密钥)
    print_response("创建Rodin模型生成任务", 
                  client.create_rodin_job(text_prompt="一个低多边形风格的猫"))
    pause()

def test_rendering(client: BlenderClient) -> None:
    """测试场景渲染"""
    # 创建一个测试场景
    print("创建测试渲染场景...")
    
    # 创建一个平面作为地面
    # print_response("创建地面平面", 
    #               client.create_object("PLANE", name="渲染测试_地面", 
    #                                  location=(0, 0, 0), 
    #                                  scale=(5, 5, 1)))
    
    # # 创建一个立方体
    # print_response("创建测试立方体", 
    #               client.create_object("CUBE", name="渲染测试_立方体", 
    #                                  location=(0, 0, 1)))
    
    # # 创建一个球体
    # print_response("创建测试球体", 
    #               client.create_object("SPHERE", name="渲染测试_球体", 
    #                                  location=(2, 2, 1), 
    #                                  scale=(0.8, 0.8, 0.8)))
    
    # # 创建一个光源
    # print_response("创建光源", 
    #               client.create_object("LIGHT", name="渲染测试_光源", 
    #                                  location=(3, -3, 5)))
    
    # # 为物体添加材质
    # print_response("为立方体设置红色材质",
    #               client.set_material("渲染测试_立方体", 
    #                                  material_name="渲染测试_红色材质", 
    #                                  color=[1.0, 0.0, 0.0, 1.0]))
    
    # print_response("为球体设置蓝色材质",
    #               client.set_material("渲染测试_球体", 
    #                                  material_name="渲染测试_蓝色材质", 
    #                                  color=[0.0, 0.0, 1.0, 1.0]))
    
    # 渲染场景并返回图像
    print("渲染场景并获取图像数据...")
    render_result = client.render_scene(
        resolution_x=800, 
        resolution_y=600, 
        return_image=True,
        auto_save=True,
        save_dir="renders"
    )
    print_response("渲染结果", render_result)
    
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
    print("渲染场景到文件...")
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

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Blender MCP 客户端测试")
    parser.add_argument("--host", default="localhost", help="Blender MCP 服务器主机名")
    parser.add_argument("--port", type=int, default=9876, help="Blender MCP 服务器端口号")
    parser.add_argument("--test", default="render", 
                      choices=["all", "basic", "code", "polyhaven", "hyper3d", "render"], 
                      help="要运行的测试")
    
    args = parser.parse_args()
    
    print(f"连接到 Blender MCP 服务器 {args.host}:{args.port}")
    client = BlenderClient(args.host, args.port)
    
    try:
        if args.test in ["all", "basic"]:
            test_basic_operations(client)
        
        if args.test in ["all", "code"]:
            test_python_code_execution(client)
        
        if args.test in ["all", "polyhaven"]:
            test_polyhaven_integration(client)
        
        if args.test in ["all", "hyper3d"]:
            test_hyper3d_integration(client)
            
        if args.test in ["all", "render"]:
            test_rendering(client)
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 