"""
Blender Agent类
"""
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Generator, Iterator

from ..llm.base import BaseLLM
from ..blender.client import BlenderClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BlenderAgent:
    """
    Blender代理，负责处理用户请求，与LLM交互，并执行Function Call
    """
    
    def __init__(self, llm: BaseLLM, blender_client: BlenderClient):
        """
        初始化Blender代理
        
        Args:
            llm: 大语言模型接口
            blender_client: Blender客户端
        """
        self.llm = llm
        self.blender_client = blender_client
        self.messages = []  # 对话历史
        self._init_functions()
    
    def _init_functions(self):
        """初始化可用的函数列表"""
        # 这里定义了所有可用的函数，对应于BlenderClient中的方法
        self.functions = [
            {
                "name": "get_scene_info",
                "description": "获取当前场景信息，包括场景名称、对象数量等基本信息",
                "parameters": {},
                "required": []
            },
            {
                "name": "create_object",
                "description": "在场景中创建指定类型的新对象",
                "parameters": {
                    "type": {
                        "type": "string",
                        "description": "对象类型，可选值：CUBE、SPHERE、CYLINDER、PLANE、CONE、TORUS、EMPTY、CAMERA、LIGHT",
                        "enum": ["CUBE", "SPHERE", "CYLINDER", "PLANE", "CONE", "TORUS", "EMPTY", "CAMERA", "LIGHT"]
                    },
                    "name": {
                        "type": "string",
                        "description": "对象名称（可选）"
                    },
                    "location": {
                        "type": "array",
                        "description": "位置坐标 [x, y, z]（可选，默认 [0, 0, 0]）"
                    },
                    "rotation": {
                        "type": "array",
                        "description": "旋转角度 [x, y, z]（可选，默认 [0, 0, 0]）"
                    },
                    "scale": {
                        "type": "array",
                        "description": "缩放比例 [x, y, z]（可选，默认 [1, 1, 1]）"
                    }
                },
                "required": ["type"]
            },
            {
                "name": "modify_object",
                "description": "修改场景中现有对象的属性",
                "parameters": {
                    "name": {
                        "type": "string",
                        "description": "对象名称"
                    },
                    "location": {
                        "type": "array",
                        "description": "新位置 [x, y, z]（可选）"
                    },
                    "rotation": {
                        "type": "array",
                        "description": "新旋转 [x, y, z]（可选）"
                    },
                    "scale": {
                        "type": "array",
                        "description": "新缩放 [x, y, z]（可选）"
                    },
                    "visible": {
                        "type": "boolean",
                        "description": "可见性（可选）"
                    }
                },
                "required": ["name"]
            },
            {
                "name": "delete_object",
                "description": "从场景中删除指定对象",
                "parameters": {
                    "name": {
                        "type": "string",
                        "description": "要删除的对象名称"
                    }
                },
                "required": ["name"]
            },
            {
                "name": "get_object_info",
                "description": "获取指定对象的详细信息，包括位置、旋转、缩放、材质等",
                "parameters": {
                    "name": {
                        "type": "string",
                        "description": "对象名称"
                    }
                },
                "required": ["name"]
            },
            {
                "name": "execute_code",
                "description": "在Blender环境中执行任意Python代码（高级功能，谨慎使用）",
                "parameters": {
                    "code": {
                        "type": "string",
                        "description": "要执行的Python代码"
                    }
                },
                "required": ["code"]
            },
            {
                "name": "set_material",
                "description": "为指定对象创建或应用材质",
                "parameters": {
                    "object_name": {
                        "type": "string",
                        "description": "要应用材质的对象名称"
                    },
                    "material_name": {
                        "type": "string",
                        "description": "材质名称（可选，如果未提供将创建一个默认名称）"
                    },
                    "create_if_missing": {
                        "type": "boolean",
                        "description": "如果材质不存在是否创建（可选，默认true）"
                    },
                    "color": {
                        "type": "array",
                        "description": "RGBA颜色值 [r, g, b, a]（可选）"
                    }
                },
                "required": ["object_name"]
            }
        ]
    
    def add_message(self, role: str, content: Union[str, List[Dict[str, Any]]]):
        """
        添加消息到对话历史
        
        Args:
            role: 角色（user或assistant）
            content: 消息内容，可以是字符串或包含多种内容类型（如文本、图像）的列表
                     格式遵循OpenAI标准，例如：
                     [
                         {"type": "text", "text": "文本内容"},
                         {"type": "image_url", "image_url": {"url": "图片URL"}}
                     ]
        """
        self.messages.append({"role": role, "content": content})
    
    def chat_stream(self, user_message: Union[str, List[Dict[str, Any]]], functions: List[Dict[str, Any]] = None, 
                    temperature: float = 0.7) -> Iterator[Dict[str, Any]]:
        """
        与LLM进行流式对话
        
        Args:
            user_message: 用户消息，可以是字符串或包含多模态内容的列表
            functions: 可用的函数列表，如果为None则使用所有函数
            temperature: 温度参数
            
        Returns:
            生成器，产生LLM的流式响应
        """
        # 使用指定的函数列表或默认的所有函数
        functions_to_use = functions if functions is not None else self.functions
        
        # 添加用户消息到历史
        self.add_message("user", user_message)
        
        # 检查LLM是否支持流式响应
        if hasattr(self.llm, 'chat_stream'):
            # 调用LLM的流式接口
            response_stream = self.llm.chat_stream(
                messages=self.messages,
                functions=functions_to_use,
                temperature=temperature
            )
            
            # 累积响应内容
            accumulated_content = ""
            function_call = None
            
            # 处理流式响应
            for chunk in response_stream:
                content_chunk = chunk.get("content")
                function_call_chunk = chunk.get("function_call")
                
                # 更新累积内容
                if content_chunk:
                    accumulated_content += content_chunk
                
                # 更新函数调用信息
                if function_call_chunk:
                    function_call = function_call_chunk
                
                # 返回本次响应块
                yield chunk
            
            # 完整的响应内容
            full_response = {
                "content": accumulated_content,
                "function_call": function_call
            }
            
            # 将完整响应添加到历史
            if full_response["content"]:
                self.add_message("assistant", full_response["content"])
            elif full_response["function_call"]:
                self.add_message("assistant", f"我将帮你执行以下操作: {full_response['function_call']['name']}")
            
            # 如果存在函数调用，执行它并将结果添加到历史
            if function_call:
                function_result = self._execute_function(function_call)
                
                # 将函数执行结果添加到历史
                self.add_message("user", f"函数 {function_call['name']} 的执行结果: {json.dumps(function_result, ensure_ascii=False)}")
                
                # 返回一个包含函数执行结果的响应块
                yield {
                    "content": None, 
                    "function_call": function_call,
                    "function_result": function_result
                }
        
        else:
            # 如果LLM不支持流式响应，则使用普通chat接口并模拟流式返回
            response = self.llm.chat(
                messages=self.messages,
                functions=functions_to_use,
                temperature=temperature
            )
            
            content = response.get("content", "")
            function_call = response.get("function_call")
            
            # 将响应添加到历史
            if content:
                self.add_message("assistant", content)
                
                # 模拟流式返回，一次性返回全部内容
                yield {"content": content, "function_call": None}
            
            if function_call:
                self.add_message("assistant", f"我将帮你执行以下操作: {function_call['name']}")
                
                # 返回函数调用信息
                yield {"content": None, "function_call": function_call}
                
                # 执行函数并返回结果
                function_result = self._execute_function(function_call)
                self.add_message("user", f"函数 {function_call['name']} 的执行结果: {json.dumps(function_result, ensure_ascii=False)}")
                
                # 添加函数执行结果到响应
                yield {"content": None, "function_call": function_call, "function_result": function_result}
    
    def _execute_function(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行函数调用
        
        Args:
            function_call: 函数调用信息，包含name和arguments字段
            
        Returns:
            函数执行结果
        """
        try:
            function_name = function_call["name"]
            arguments = function_call["arguments"]
            
            # 检查Blender客户端是否存在
            if self.blender_client is None:
                return {
                    "status": "error",
                    "message": "Blender未连接，无法执行操作。请先在「连接设置」中连接到Blender。"
                }
            
            # 检查函数是否存在
            if not hasattr(self.blender_client, function_name):
                return {
                    "status": "error",
                    "message": f"函数 {function_name} 不存在"
                }
            
            # 获取函数
            func = getattr(self.blender_client, function_name)
            
            # 执行函数
            logger.info(f"执行函数: {function_name}，参数: {arguments}")
            result = func(**arguments)
            logger.info(f"函数执行结果: {result}")
            
            return result
        
        except Exception as e:
            logger.error(f"执行函数 {function_call.get('name', '未知')} 时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"执行函数时出错: {str(e)}"
            }

    def update_blender_client(self, blender_client: BlenderClient):
        """
        更新Blender客户端引用
        
        在UI中先初始化Agent后连接Blender时，需要调用此方法更新Agent中的
        Blender客户端引用，以便Agent能够与新连接的Blender进行交互。
        
        Args:
            blender_client: 新的Blender客户端
            
        Returns:
            None
        """
        self.blender_client = blender_client
        logger.info("已更新Agent中的Blender客户端引用") 