#!/usr/bin/env python
"""
LLM-Blender-Agent命令行接口
"""
import os
import sys
import json
import argparse
import logging

from src.llm import LLMFactory
from src.blender import BlenderClient
from src.agent import BlenderAgent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    
    # 命令行参数
    parser = argparse.ArgumentParser(description="LLM-Blender-Agent命令行接口")
    parser.add_argument("--model", type=str, default="aimlapi", help="要使用的LLM模型类型（claude, zhipu, deepseek）")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")
    parser.add_argument("--host", type=str, default="localhost", help="Blender MCP服务器主机名")
    parser.add_argument("--port", type=int, default=9876, help="Blender MCP服务器端口号")
    parser.add_argument("--temperature", type=float, default=0.7, help="LLM温度参数")
    args = parser.parse_args()
    
    try:
        # 加载配置
        if not os.path.exists(args.config):
            logger.error(f"配置文件不存在: {args.config}")
            sys.exit(1)
        
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 检查模型类型
        model_type = args.model or config.get("llm", {}).get("default_model", "claude")
        
        # 创建LLM实例
        logger.info(f"使用模型: {model_type}")
        llm = LLMFactory.create_from_config_file(args.config, model_type)
        
        # 设置Blender客户端
        blender_config = config.get("blender_mcp", {})
        host = args.host or blender_config.get("host", "localhost")
        port = args.port or blender_config.get("port", 9876)
        
        logger.info(f"连接到Blender MCP服务器: {host}:{port}")
        blender_client = BlenderClient(host, port)
        
        # 测试服务器连接
        scene_info = blender_client.get_scene_info()
        if scene_info.get("status") == "error":
            logger.error(f"无法连接到Blender MCP服务器: {scene_info.get('message')}")
            logger.error("请确保Blender正在运行，并且MCP插件已启动")
            sys.exit(1)
        
        logger.info("成功连接到Blender MCP服务器")
        
        # 创建Agent
        agent = BlenderAgent(llm, blender_client)
        
        # 欢迎信息
        print("\n=== LLM-Blender-Agent命令行接口 ===")
        print(f"使用模型: {model_type}")
        print(f"Blender MCP服务器: {host}:{port}")
        print("输入 'quit' 或 'exit' 退出")
        print("=" * 40 + "\n")
        
        # 交互循环
        while True:
            user_input = input("\n请输入指令: ")
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("退出程序...")
                break
            
            if not user_input.strip():
                continue
            
            # 处理用户输入
            print("\n正在处理...")
            response = agent.chat(user_input, temperature=args.temperature)
            
            # 显示响应
            content = response.get("content", "")
            
            if content:
                print("\n" + content)
            else:
                print("\n[无文本响应]")
    
    except KeyboardInterrupt:
        print("\n程序被中断")
    except Exception as e:
        logger.error(f"运行时错误: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 