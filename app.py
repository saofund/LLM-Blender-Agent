#!/usr/bin/env python
"""
LLM-Blender-Agent Gradio Web界面
"""
import sys
import logging

from ui.main import create_ui

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        app = create_ui()
        app.launch(server_name="0.0.0.0", share=False)
    
    except Exception as e:
        logger.error(f"启动Gradio界面时出错: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 