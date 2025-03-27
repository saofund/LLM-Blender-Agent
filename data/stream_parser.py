#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试流式输出解析处理脚本
"""

import json
import os

class StreamParser:
    """
    解析流式输出数据的类
    支持解析普通文本输出和函数调用
    完全模仿aimlapi.py中的方法和agent.py的输出格式
    """
    
    def __init__(self):
        """初始化解析器"""
        self.accumulated_content = ""  # 累积的文本内容
        self.function_call = None  # 函数调用信息
        self.current_function_args_str = ""  # 当前函数调用参数字符串（用于累积分段传输的参数）
    
    def process_line(self, line):
        """
        处理单行流式输出数据
        
        Args:
            line: 流式输出的单行数据，格式为 data: {...}
            
        Returns:
            dict: 包含处理结果的字典，可能包含文本内容或函数调用
        """
        result = {
            "content": None,
            "function_call": None,
            "is_done": False
        }
        
        # 检查流是否结束
        if line.strip() == "data: [DONE]":
            result["is_done"] = True
            return result
            
        # 删除"data: "前缀并解析JSON
        if line.startswith("data: "):
            json_str = line[6:]
            try:
                chunk = json.loads(json_str)
                
                # 解析块内容
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    choice = chunk["choices"][0]
                    delta = choice.get("delta", {})
                    
                    # 处理文本内容更新
                    if "content" in delta and delta["content"] is not None:
                        content_chunk = delta["content"]
                        self.accumulated_content += content_chunk
                        result["content"] = content_chunk
                    
                    # 处理函数调用 - 模仿aimlapi.py中的处理方式
                    if "tool_calls" in delta and delta["tool_calls"]:
                        tool_call = delta["tool_calls"][0]
                        
                        # 初始化函数调用信息，完全模仿aimlapi.py中的结构
                        if self.function_call is None and tool_call.get("function", {}):
                            self.function_call = {
                                "name": tool_call.get("function", {}).get("name", ""),
                                "arguments": {}
                            }
                        
                        # 处理函数名称
                        if "function" in tool_call and "name" in tool_call["function"]:
                            self.function_call["name"] = tool_call["function"]["name"]
                        
                        # 处理函数参数，参数可能是分段传输的
                        if "function" in tool_call and "arguments" in tool_call["function"]:
                            # 累积函数参数字符串 - 关键改进
                            args_str = tool_call["function"]["arguments"]
                            self.current_function_args_str += args_str
                            
                            # 尝试解析完整的JSON
                            try:
                                # 首先验证我们有一个可能完整的JSON字符串
                                args_str_clean = self.current_function_args_str.strip()
                                if args_str_clean and (
                                    args_str_clean[0] == "{" and 
                                    args_str_clean[-1] == "}"
                                ):
                                    try:
                                        # 尝试解析累积的参数
                                        args = json.loads(args_str_clean)
                                        self.function_call["arguments"] = args
                                    except json.JSONDecodeError:
                                        # 如果无法解析，继续累积
                                        pass
                            except Exception:
                                # 捕获所有异常，确保处理继续
                                pass
                        
                        # 始终返回当前的函数调用信息，即使参数可能尚未完全解析
                        result["function_call"] = self.function_call
            
            except json.JSONDecodeError:
                print(f"无法解析JSON: {json_str}")
            except Exception as e:
                print(f"处理流数据时出错: {str(e)}")
        
        return result
    
    def get_final_result(self):
        """
        获取最终处理结果
        
        Returns:
            dict: 包含最终处理结果的字典，模仿agent.py中的响应格式
        """
        # 尝试最后一次解析函数参数 - 确保我们有最终完整的参数
        if self.function_call and self.current_function_args_str and not self.function_call.get("arguments"):
            try:
                # 最后尝试解析函数参数
                args_str_clean = self.current_function_args_str.strip()
                if args_str_clean and args_str_clean[0] == "{" and args_str_clean[-1] == "}":
                    args = json.loads(args_str_clean)
                    self.function_call["arguments"] = args
            except:
                # 如果仍然无法解析，提供空对象作为参数
                self.function_call["arguments"] = {}
                print("警告: 无法解析完整的函数参数，将使用空对象")
        
        # 构建最终结果，格式与agent.py中的响应格式完全一致
        result = {
            "content": self.accumulated_content if self.accumulated_content else None,
            "function_call": self.function_call
        }
        
        return result


def process_stream_file(file_path):
    """
    处理流式输出数据文件
    
    Args:
        file_path: 流式输出数据文件路径
    """
    parser = StreamParser()
    
    print("开始处理流式输出数据文件...\n")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            result = parser.process_line(line)
            
            # 打印处理结果
            if result["is_done"]:
                print("流式输出结束")
            elif result["content"]:
                print(f"收到文本内容: '{result['content']}'")
            elif result["function_call"]:
                func_call = result["function_call"]
                if func_call["name"]:
                    print(f"发现函数调用: {func_call['name']}")
                    if func_call.get("arguments"):
                        print(f"函数参数: {json.dumps(func_call['arguments'], ensure_ascii=False)}")
                    else:
                        print(f"正在累积函数参数...")
    
    # 打印最终结果
    final_result = parser.get_final_result()
    print("\n最终处理结果:")
    if final_result["content"]:
        print(f"完整文本内容: '{final_result['content']}'")
    
    if final_result["function_call"]:
        print("完整函数调用:")
        print(f"  函数名称: {final_result['function_call']['name']}")
        print(f"  函数参数: {json.dumps(final_result['function_call'].get('arguments', {}), ensure_ascii=False, indent=2)}")


def simulate_chat_stream(stream_data_file, output_file=None):
    """
    模拟agent.py中的chat_stream方法处理流式输出数据
    
    Args:
        stream_data_file: 流式输出数据文件路径
        output_file: 可选的输出文件路径，用于保存处理结果
    """
    parser = StreamParser()
    results = []
    
    print("模拟chat_stream方法处理流式输出...\n")
    
    with open(stream_data_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # 处理流式数据
            result = parser.process_line(line)
            
            # 格式化为chat_stream方法返回的格式
            stream_response = {}
            if result["content"]:
                stream_response["content"] = result["content"]
                stream_response["function_call"] = None
                print(f"文本输出: '{result['content']}'")
            
            if result["function_call"]:
                stream_response["content"] = None
                stream_response["function_call"] = result["function_call"]
                print(f"函数调用: {result['function_call']['name']}")
                if result["function_call"].get("arguments"):
                    print(f"函数参数: {json.dumps(result['function_call']['arguments'], ensure_ascii=False)}")
            
            if result["is_done"]:
                print("流式输出结束")
                break
                
            # 有内容才添加到结果
            if stream_response:
                results.append(stream_response)
    
    # 获取最终结果
    final_result = parser.get_final_result()
    
    # 输出最终结果
    print("\n最终整合结果:")
    if final_result["content"]:
        print(f"文本内容: '{final_result['content']}'")
    
    if final_result["function_call"]:
        print(f"函数调用: {final_result['function_call']['name']}")
        print(f"函数参数: {json.dumps(final_result['function_call'].get('arguments', {}), ensure_ascii=False, indent=2)}")
    
    # 保存结果到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            json.dump(results, out_file, ensure_ascii=False, indent=2)
        print(f"\n处理结果已保存到: {output_file}")
    
    return results


if __name__ == "__main__":
    """测试流式输出数据解析"""
    
    # 测试文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    stream_samples_dir = os.path.join(current_dir, "stream_samples")
    
    # 确保样本目录存在
    if not os.path.exists(stream_samples_dir):
        os.makedirs(stream_samples_dir)
        print(f"创建了样本目录: {stream_samples_dir}")
    
    test_file = os.path.join(stream_samples_dir, "test_stream.jsonl")
    
    if os.path.exists(test_file):
        print(f"1. 使用基本处理方法")
        process_stream_file(test_file)
        
        print("\n\n2. 使用模拟chat_stream方法")
        output_file = os.path.join(stream_samples_dir, "processed_results.json")
        simulate_chat_stream(test_file, output_file)
    else:
        print(f"错误: 测试文件不存在, 路径: {test_file}")
        print(f"请确保在 {stream_samples_dir} 目录中有 test_stream.jsonl 文件") 