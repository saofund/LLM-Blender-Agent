# LLM-Blender-Agent

这是一个使用不同大语言模型(LLM)的Function Call功能来操作Blender的项目。该项目允许用户通过各种LLM接口（如Claude、智谱AI、DeepseekV3等）使用自然语言操控Blender进行3D建模。

## 功能特点

- 支持多种LLM接口的无缝切换（Claude、智谱AI、DeepseekV3等）
- 统一的Function Call处理框架
- 命令行界面和Gradio Web UI两种交互方式
- 完整支持BlenderMCP插件提供的所有功能
- 易于扩展，支持添加新的LLM提供商

## 安装要求

```bash
# 安装依赖
pip install -r requirements.txt
```

此外，您需要在Blender中安装BlenderMCP插件，并启动MCP服务器。

## 使用方法

### 命令行模式

```bash
# 使用特定LLM启动命令行界面
python cli.py --model claude  # 或 zhipu、deepseek 等

# 查看帮助
python cli.py --help
```

### Gradio Web UI模式

```bash
# 启动Web UI
python app.py
```

然后在浏览器中访问 http://localhost:7860

## LLM配置

在 `config.json` 文件中设置您的API密钥和模型配置：

```json
{
  "claude": {
    "api_key": "YOUR_CLAUDE_API_KEY",
    "model": "claude-3-opus-20240229"
  },
  "zhipu": {
    "api_key": "YOUR_ZHIPU_API_KEY",
    "model": "glm-4"
  },
  "deepseek": {
    "api_key": "YOUR_DEEPSEEK_API_KEY",
    "model": "deepseek-v3"
  }
}
```

## 许可证

MIT License 