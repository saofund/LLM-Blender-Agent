"""
AIMLAPI 实现
"""
import json
import requests
import os
import sys
import base64
from typing import Dict, List, Any, Optional, Union, Iterator

# 处理导入路径
if __name__ == "__main__":
    # 获取项目根目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # 将项目根目录添加到Python路径
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from src.llm.base import BaseLLM
else:
    # 作为模块导入时使用相对导入
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
    
    def chat(self, messages: List[Dict[str, Any]], functions: List[Dict[str, Any]] = None,
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        与AIMLAPI进行对话，支持function calling和本地图片输入
        
        Args:
            messages: 对话历史消息列表，每条消息可以包含文本内容或图片内容
                格式：
                - 纯文本消息: {"role": "user", "content": "文本内容"}
                - 带图片消息: {"role": "user", "content": [
                    {"type": "text", "text": "文本内容"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "BASE64编码的图片"}}
                  ]}
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            AIMLAPI响应结果
        """
        # 处理消息格式，转换为AIMLAPI支持的格式
        formatted_messages = self.format_messages(messages)
        formatted_functions = self.format_functions(functions or [])
        
        try:
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 设置请求体
            payload = {
                "model": self.model,
                "messages": formatted_messages,
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
            # 打印请求体以便调试
            if 'payload' in locals():
                try:
                    print("请求体:", json.dumps(payload, indent=2, ensure_ascii=False))
                except:
                    print("无法打印请求体")
            
            return {
                "content": f"与AIMLAPI通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def chat_stream(self, messages: List[Dict[str, Any]], functions: List[Dict[str, Any]] = None,
                  temperature: float = 0.7, max_tokens: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """
        与AIMLAPI进行流式对话，支持function calling和本地图片输入
        
        Args:
            messages: 对话历史消息列表
            functions: 函数定义列表
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            生成器，产生AIMLAPI的流式响应块
        """
        # 处理消息格式，转换为AIMLAPI支持的格式
        formatted_messages = self.format_messages(messages)
        formatted_functions = self.format_functions(functions or [])
        
        try:
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 设置请求体
            payload = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 512,
                "stream": True,
                "system": "你是一位专业的3D建模助手，可以通过自然语言指令控制Blender软件进行3D建模。"
            }
            
            # 添加工具（函数）
            if formatted_functions:
                payload["tools"] = formatted_functions
                payload["tool_choice"] = {"type": "auto"}
            
            # 发送流式请求
            response = requests.post(self.api_url, headers=headers, json=payload, stream=True)
            response.raise_for_status()  # 确保请求成功
            
            # 处理流式响应
            accumulated_content = ""
            function_call = None
            
            for line in response.iter_lines():
                if line:
                    # 删除"data: "前缀并解析JSON
                    line_text = line.decode("utf-8")
                    if line_text.startswith("data: "):
                        json_str = line_text[6:]
                        if json_str == "[DONE]":
                            break
                            
                        try:
                            chunk = json.loads(json_str)
                            
                            # 解析块内容
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                choice = chunk["choices"][0]
                                delta = choice.get("delta", {})
                                
                                # 处理内容更新
                                if "content" in delta and delta["content"]:
                                    content_chunk = delta["content"]
                                    accumulated_content += content_chunk
                                    yield {"content": content_chunk, "function_call": None}
                                
                                # 处理函数调用
                                if "tool_calls" in delta and delta["tool_calls"]:
                                    tool_call = delta["tool_calls"][0]
                                    
                                    # 初始化函数调用信息
                                    if function_call is None:
                                        function_call = {
                                            "name": tool_call.get("function", {}).get("name", ""),
                                            "arguments": {}
                                        }
                                    
                                    # 更新函数名称
                                    if "function" in tool_call and "name" in tool_call["function"]:
                                        function_call["name"] = tool_call["function"]["name"]
                                    
                                    # 更新函数参数
                                    if "function" in tool_call and "arguments" in tool_call["function"]:
                                        # 处理参数 - 可能是部分JSON字符串
                                        args_str = tool_call["function"]["arguments"]
                                        try:
                                            # 尝试解析完整的JSON
                                            args = json.loads(args_str)
                                            function_call["arguments"] = args
                                        except json.JSONDecodeError:
                                            # 如果无法解析，则等待更多块
                                            pass
                                    
                                    # 当函数调用完整时，返回
                                    if function_call["name"] and hasattr(function_call, "arguments"):
                                        yield {"content": None, "function_call": function_call}
                        except json.JSONDecodeError:
                            print(f"无法解析JSON: {json_str}")
            
            # 如果我们收到完整的函数调用，但尚未解析参数
            if function_call and not function_call.get("arguments"):
                # 尝试从收集的部分数据中构建完整的函数调用
                try:
                    # 这里可能需要添加额外的逻辑来处理部分函数调用
                    yield {"content": None, "function_call": function_call}
                except:
                    pass
        
        except Exception as e:
            # 打印请求体以便调试
            if 'payload' in locals():
                try:
                    print("请求体:", json.dumps(payload, indent=2, ensure_ascii=False))
                except:
                    print("无法打印请求体")
            
            yield {
                "content": f"与AIMLAPI通信出错: {str(e)}",
                "function_call": None,
                "error": str(e)
            }
    
    def format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将消息列表转换为AIMLAPI支持的格式，支持文本和本地图片内容
        
        Args:
            messages: 消息列表
            
        Returns:
            AIMLAPI格式的消息列表
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # 标准格式的消息（纯文本）
            if isinstance(content, str):
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
            
            # 包含图片的消息（列表格式）
            elif isinstance(content, list):
                formatted_content = []
                
                for item in content:
                    if item.get("type") == "text":
                        formatted_content.append({
                            "type": "text",
                            "text": item.get("text", "")
                        })
                    elif item.get("type") == "image":
                        # 直接使用source格式的处理 - 仅支持base64格式
                        if "source" in item:
                            source = item["source"]
                            if isinstance(source, dict) and source.get("type") == "base64" and "data" in source and "media_type" in source:
                                formatted_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": source["media_type"],
                                        "data": source["data"]
                                    }
                                })
                        # 兼容旧格式的代码处理 - image_data
                        elif "image_data" in item:
                            media_type = item["image_data"].get("media_type", "image/jpeg")
                            data = item["image_data"].get("data", "")
                            if data:
                                formatted_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": data
                                    }
                                })
                
                # 添加消息，只有在有内容时才添加
                if formatted_content:
                    formatted_messages.append({
                        "role": role,
                        "content": formatted_content
                    })
                else:
                    # 如果所有图片格式都无效，至少添加一个纯文本消息
                    formatted_messages.append({
                        "role": role,
                        "content": "查看图片"
                    })
        
        return formatted_messages
    
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
    
    def image_chat(self, text: str, images: List[Union[str, Dict[str, str]]], 
                  temperature: float = 0.7, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        简化的图片对话方法，仅支持本地图片输入
        
        Args:
            text: 提问的文本
            images: 图片列表，可以是以下格式：
                - 图片路径字符串列表
                - 字典列表，支持"path"键
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            AIMLAPI响应结果
        """
        content = [{"type": "text", "text": text}]
        
        # 处理图片
        for img in images:
            # 图片是字符串，应该是本地路径
            if isinstance(img, str):
                # 本地路径
                if os.path.exists(img):
                    image_base64 = self.encode_image(img)
                    media_type = self.get_media_type(img)
                    content.append({
                        "type": "image", 
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64
                        }
                    })
                else:
                    raise FileNotFoundError(f"图片文件不存在: {img}")
            
            # 图片是字典，可能包含path
            elif isinstance(img, dict) and "path" in img:
                if os.path.exists(img["path"]):
                    image_base64 = self.encode_image(img["path"])
                    media_type = self.get_media_type(img["path"])
                    content.append({
                        "type": "image", 
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64
                        }
                    })
                else:
                    raise FileNotFoundError(f"图片文件不存在: {img['path']}")
        
        # 构建消息
        messages = [{"role": "user", "content": content}]
        
        # 调用chat方法
        return self.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
    
    @staticmethod
    def encode_image(image_path: str) -> str:
        """
        从文件路径读取图片并转换为base64编码
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的图片数据
        """
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    
    @staticmethod
    def get_media_type(image_path: str) -> str:
        """
        根据图片文件名后缀获取媒体类型
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            媒体类型
        """
        ext = os.path.splitext(image_path)[1].lower()
        if ext == ".jpg" or ext == ".jpeg":
            return "image/jpeg"
        elif ext == ".png":
            return "image/png"
        elif ext == ".gif":
            return "image/gif"
        elif ext == ".webp":
            return "image/webp"
        else:
            # 默认为JPEG
            return "image/jpeg" 

if __name__ == "__main__":
    """测试AIMLAPI连接"""
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
        
        # ============= 测试文本对话 =============
        print("\n===== 测试文本对话 =====")
        text_messages = [
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
        print("正在测试AIMLAPI文本对话...")
        text_response = llm.chat(messages=text_messages, functions=test_function)
        print("\n文本响应:", text_response.get("content"))
        
        # ============= 测试本地图片输入 =============
        print("\n\n===== 测试本地图片输入 =====")
        # 设置测试图片路径为asserts/test_image.jpg
        test_image_path = os.path.join(project_root, "asserts", "test_image.jpg")
                
        if os.path.exists(test_image_path):
            print(f"找到测试图片: {test_image_path}")
            
            # 原始方式测试
            print("原始方式测试本地图片输入...")
            # 读取并编码图片
            image_base64 = llm.encode_image(test_image_path)
            media_type = llm.get_media_type(test_image_path)
            
            # 构建消息
            image_base64_messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这张图片是什么，请详细描述一下。"},
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_base64}}
                    ]
                }
            ]
            
            image_base64_response = llm.chat(messages=image_base64_messages)
            print("\n原始方式本地图片响应:", image_base64_response.get("content"))
            
            # 简化方式测试
            print("\n简化方式测试本地图片输入...")
            simple_local_response = llm.image_chat(
                text="这张图片是什么，请详细描述一下。",
                images=[test_image_path]
            )
            print("\n简化方式本地图片响应:", simple_local_response.get("content"))
        else:
            print(f"本地图片测试跳过: 找不到测试图片，路径: {test_image_path}")
            print("请确认asserts目录中有test_image.jpg文件")
        
        print("\n测试完成")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}") 
