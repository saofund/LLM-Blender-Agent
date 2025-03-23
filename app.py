#!/usr/bin/env python
"""
LLM-Blender-Agent应用程序入口
"""
import os
import sys
import traceback
import logging

import gradio as gr

from ui.main import create_ui

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        app = create_ui()
        app.launch(
            server_name="127.0.0.1", 
            server_port=7860,
            inbrowser=True
        )
    except Exception as e:
        logger.error(f"启动Gradio界面时出错: {str(e)}")
        # 打印完整堆栈跟踪以便调试
        print("\n\n===== 错误详情 =====")
        traceback.print_exc()
        print("\n如果您看到'update_status_after_message'未定义的错误，请确保已正确更新所有代码。")

def fail_safe_main():
    """提供后备的UI，防止主UI无法启动"""
    try:
        # 尝试主启动流程
        main()
    except Exception as e:
        # 如果主UI无法启动，则显示一个简单的错误信息界面
        logger.error(f"启动应用失败，显示后备界面: {str(e)}")
        with gr.Blocks(title="LLM-Blender-Agent (错误模式)") as app:
            gr.Markdown("## LLM-Blender-Agent 启动错误")
            gr.Markdown(f"""
            应用程序启动时发生错误:
            
            ```
            {traceback.format_exc()}
            ```
            
            请检查日志和控制台输出以获取更多信息。
            """)
            
            with gr.Row():
                restart_btn = gr.Button("重启应用")
                
            def restart():
                # 重启应用程序
                os.execv(sys.executable, ['python'] + sys.argv)
                
            restart_btn.click(fn=restart)
            
        app.launch(
            server_name="127.0.0.1", 
            server_port=7860,
            inbrowser=True
        )

if __name__ == "__main__":
    fail_safe_main() 