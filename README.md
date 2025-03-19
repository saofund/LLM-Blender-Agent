# LLM-Blender-Agent

This is a project that uses the Function Call capability of different Large Language Models (LLMs) to operate Blender. The project allows users to control Blender for 3D modeling using natural language through various LLM interfaces (such as Claude, Zhipu AI, DeepseekV3, etc.).

## Features

- Seamless switching between multiple LLM interfaces (Claude, Zhipu AI, DeepseekV3, etc.)
- Unified Function Call processing framework
- Two interaction modes: Command-line interface and Gradio Web UI
- Complete support for all features provided by the BlenderMCP plugin
- Easily extensible, supporting the addition of new LLM providers

## Installation Requirements

```bash
# Install dependencies
pip install -r requirements.txt
```

Additionally, you need to install the BlenderMCP plugin in Blender and start the MCP server.

## Usage

### Command-line Mode

```bash
# Start the command-line interface with a specific LLM
python cli.py --model claude  # or zhipu, deepseek, etc.

# View help
python cli.py --help
```

### Gradio Web UI Mode

```bash
# Start the Web UI
python app.py
```

Then visit http://localhost:7860 in your browser

## LLM Configuration

Set your API keys and model configurations in the `config.json` file:

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

## License

MIT License 