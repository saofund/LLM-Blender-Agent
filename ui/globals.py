#!/usr/bin/env python
"""
全局变量模块，用于在不同模块之间共享状态
"""

# 全局字典，用于存储会话相关的数据
blender_clients = {}  # 用于存储不同连接的Blender客户端
agents = {}  # 用于存储不同会话的Agent
session_id = None  # 当前会话ID 