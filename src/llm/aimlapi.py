"""
AIMLAPI 实现
"""
import json
import requests
from typing import Dict, List, Any, Optional
from .base import BaseLLM

class AIMLAPI_LLM(BaseLLM):
    """AIMLAPI接口实现"""
    
    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-20250219", **kwargs):
        """
        初始化AIMLAPI LLM接口
        
        Args:
            api_key: AIMLAPI API密钥
            model: 模型名称，默认为claude-3-7-sonnet-20250219
            **kwargs: 其他参数
        """
        super().__init__(api_key, model, **kwargs)
        self.api_url = "https://api.aimlapi.com/v1/chat/completions"
    
    def chat(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]],
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与AIMLAPI进行对话，支持function calling
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            AIMLAPI响应结果
        """
        formatted_functions = self.format_functions(functions)
        
        try:
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 设置请求体
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 512,
                "stream": False,
                "system": "你是一位专业的3D建模助手，可以通过自然语言指令控制Blender软件进行3D建模。"
            }
            
            # 添加工具（函数）
            if formatted_functions:
                payload["tools"] = formatted_functions
                payload["tool_choice"] = {"type": "auto"}
            
            # 发送请求
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()  # 确保请求成功
            
            # 解析响应
            return self.parse_response(response.json())
        
        except Exception as e:
            return {
                "content": f"与AIMLAPI通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将统一格式的函数定义转换为AIMLAPI的格式
        
        Args:
            functions: 统一格式的函数定义列表
            
        Returns:
            AIMLAPI格式的函数定义列表
        """
        aimlapi_tools = []
        for func in functions:
            aimlapi_tool = {
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": func.get("required", [])
                }
            }
            
            # 添加参数
            if "parameters" in func:
                for param_name, param_info in func["parameters"].items():
                    aimlapi_tool["input_schema"]["properties"][param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", "")
                    }
                    
                    # 处理枚举类型
                    if "enum" in param_info:
                        aimlapi_tool["input_schema"]["properties"][param_name]["enum"] = param_info["enum"]
            
            aimlapi_tools.append(aimlapi_tool)
            
        return aimlapi_tools
    
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        解析AIMLAPI的原始响应为统一格式
        
        Args:
            response: AIMLAPI的原始响应
            
        Returns:
            统一格式的响应，包含content和function_call等字段
        """
        result = {
            "content": None,
            "function_call": None
        }
        
        try:
            # 提取消息内容
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                message = choice.get("message", {})
                
                # 提取文本内容
                if "content" in message and message["content"]:
                    result["content"] = message["content"]
                
                # 提取工具调用
                if "tool_calls" in message and message["tool_calls"]:
                    tool_call = message["tool_calls"][0]  # 获取第一个工具调用
                    
                    # 解析参数JSON
                    arguments = {}
                    try:
                        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    result["function_call"] = {
                        "name": tool_call.get("function", {}).get("name", ""),
                        "arguments": arguments
                    }
        except Exception as e:
            result["content"] = f"解析AIMLAPI响应出错: {str(e)}"
            result["error"] = str(e)
        
        return result 

if __name__ == "__main__":
    """测试AIMLAPI连接"""
    import os
    import json
    
    # 读取配置文件
    try:
        # 获取项目根目录路径
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_file = os.path.join(project_root, "config.json")
        
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        # 获取AIMLAPI配置
        aimlapi_config = config.get("llm", {}).get("aimlapi", {})
        api_key = aimlapi_config.get("api_key", "")
        model = aimlapi_config.get("model", "claude-3-7-sonnet-20250219")
        
        if not api_key:
            print("错误: 配置文件中未找到有效的AIMLAPI API密钥")
            exit(1)
            
        # 创建AIMLAPI实例
        llm = AIMLAPI_LLM(api_key=api_key, model=model)
        
        # 测试简单对话
        messages = [
            {"role": "user", "content": "你好，请简单介绍一下你自己。"}
        ]
        
        # 定义一个简单的测试函数
        test_function = [{
            "name": "create_cube",
            "description": "在Blender中创建一个立方体",
            "parameters": {
                "size": {
                    "type": "number",
                    "description": "立方体的大小"
                },
                "location": {
                    "type": "array",
                    "description": "立方体的位置坐标 [x, y, z]"
                }
            },
            "required": ["size"]
        }]
        
        # 进行对话
        print("正在测试AIMLAPI连接...")
        response = llm.chat(messages=messages, functions=test_function)
        
        # 打印响应
        print("\n===== 响应内容 =====")
        if response.get("content"):
            print("文本响应:", response["content"])
        
        if response.get("function_call"):
            print("\n函数调用:")
            print(f"  函数名称: {response['function_call']['name']}")
            print(f"  函数参数: {json.dumps(response['function_call']['arguments'], ensure_ascii=False, indent=2)}")
            
        if response.get("error"):
            print("\n错误信息:", response["error"])
            
        print("\n测试完成")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}") 
