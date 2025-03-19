"""
Blender Agent类
"""
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union

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
            },
            {
                "name": "get_polyhaven_status",
                "description": "检查Poly Haven集成是否已启用",
                "parameters": {},
                "required": []
            },
            {
                "name": "get_polyhaven_categories",
                "description": "获取指定资源类型的分类列表",
                "parameters": {
                    "asset_type": {
                        "type": "string",
                        "description": "资源类型，可选值：hdris、textures、models、all",
                        "enum": ["hdris", "textures", "models", "all"]
                    }
                },
                "required": ["asset_type"]
            },
            {
                "name": "search_polyhaven_assets",
                "description": "搜索Poly Haven资源库",
                "parameters": {
                    "asset_type": {
                        "type": "string",
                        "description": "资源类型（可选）",
                        "enum": ["hdris", "textures", "models"]
                    },
                    "categories": {
                        "type": "array",
                        "description": "分类（可选）"
                    }
                },
                "required": []
            },
            {
                "name": "download_polyhaven_asset",
                "description": "下载并导入指定的Poly Haven资源",
                "parameters": {
                    "asset_id": {
                        "type": "string",
                        "description": "资源ID"
                    },
                    "asset_type": {
                        "type": "string",
                        "description": "资源类型",
                        "enum": ["hdris", "textures", "models"]
                    },
                    "resolution": {
                        "type": "string",
                        "description": "分辨率（可选，默认1k）",
                        "enum": ["1k", "2k", "4k", "8k"]
                    },
                    "file_format": {
                        "type": "string",
                        "description": "文件格式（可选，根据资源类型有不同默认值）"
                    }
                },
                "required": ["asset_id", "asset_type"]
            },
            {
                "name": "set_texture",
                "description": "将已下载的Poly Haven纹理应用到指定对象",
                "parameters": {
                    "object_name": {
                        "type": "string",
                        "description": "要应用纹理的对象名称"
                    },
                    "texture_id": {
                        "type": "string",
                        "description": "已下载纹理的ID"
                    }
                },
                "required": ["object_name", "texture_id"]
            },
            {
                "name": "get_hyper3d_status",
                "description": "检查Hyper3D Rodin集成是否已启用",
                "parameters": {},
                "required": []
            },
            {
                "name": "create_rodin_job",
                "description": "创建Hyper3D Rodin模型生成任务",
                "parameters": {
                    "text_prompt": {
                        "type": "string",
                        "description": "描述要生成模型的文本提示（可选）"
                    },
                    "images": {
                        "type": "array",
                        "description": "参考图像列表（可选）"
                    },
                    "bbox_condition": {
                        "type": "object",
                        "description": "边界框条件（可选）"
                    }
                },
                "required": []
            },
            {
                "name": "poll_rodin_job_status",
                "description": "获取当前Rodin任务的状态",
                "parameters": {
                    "job_id": {
                        "type": "string",
                        "description": "任务ID"
                    },
                    "mode": {
                        "type": "string",
                        "description": "模式，MAIN_SITE或FAL_AI",
                        "enum": ["MAIN_SITE", "FAL_AI"]
                    }
                },
                "required": ["job_id"]
            },
            {
                "name": "import_generated_asset",
                "description": "从Hyper3D Rodin导入生成的3D模型",
                "parameters": {
                    "job_id": {
                        "type": "string",
                        "description": "任务ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "资源名称"
                    },
                    "mode": {
                        "type": "string",
                        "description": "模式，MAIN_SITE或FAL_AI",
                        "enum": ["MAIN_SITE", "FAL_AI"]
                    }
                },
                "required": ["job_id", "name"]
            }
        ]
    
    def add_message(self, role: str, content: str):
        """
        添加消息到对话历史
        
        Args:
            role: 角色（user或assistant）
            content: 消息内容
        """
        self.messages.append({"role": role, "content": content})
    
    def chat(self, user_message: str, temperature: float = 0.7) -> Dict[str, Any]:
        """
        与LLM进行对话
        
        Args:
            user_message: 用户消息
            temperature: 温度参数
            
        Returns:
            LLM响应
        """
        # 添加用户消息到历史
        self.add_message("user", user_message)
        
        # 调用LLM
        response = self.llm.chat(
            messages=self.messages,
            functions=self.functions,
            temperature=temperature
        )
        
        # 处理响应
        content = response.get("content")
        function_call = response.get("function_call")
        
        if function_call:
            # 执行函数调用
            function_result = self._execute_function(function_call)
            
            # 将函数调用和结果添加到历史
            self.add_message("assistant", f"我将帮你执行以下操作: {function_call['name']}")
            self.add_message("user", f"函数 {function_call['name']} 的执行结果: {json.dumps(function_result, ensure_ascii=False)}")
            
            # 再次调用LLM，让它解释结果
            response = self.llm.chat(
                messages=self.messages,
                functions=self.functions,
                temperature=temperature
            )
            
            # 更新响应内容
            content = response.get("content")
        
        # 将助手响应添加到历史
        if content:
            self.add_message("assistant", content)
        
        return {
            "content": content,
            "function_call": function_call
        }
    
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