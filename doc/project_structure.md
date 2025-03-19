# 项目结构

```
LLM-Blender-Agent/
│
├── doc/                        # 文档目录
│   └── BlenderMCP_API_Doc.md   # Blender MCP API文档
│
├── src/                        # 源代码目录
│   ├── __init__.py             # 项目主模块初始化文件
│   │
│   ├── agent/                  # Agent模块
│   │   ├── __init__.py         # Agent模块初始化文件
│   │   └── agent.py            # Blender Agent类
│   │
│   ├── blender/                # Blender模块
│   │   ├── __init__.py         # Blender模块初始化文件
│   │   └── client.py           # Blender MCP客户端
│   │
│   └── llm/                    # LLM模块
│       ├── __init__.py         # LLM模块初始化文件和工厂类
│       ├── base.py             # LLM基础接口类
│       ├── claude.py           # Claude API实现
│       ├── zhipu.py            # 智谱AI API实现
│       └── deepseek.py         # DeepSeek API实现
│
├── addon.py                    # Blender MCP插件
├── app.py                      # Gradio Web UI界面
├── cli.py                      # 命令行接口
├── config.json                 # 配置文件
├── requirements.txt            # 依赖列表
├── .env.template               # 环境变量模板
└── README.md                   # 项目说明
``` 