#!/usr/bin/env python3
"""
Q 脑系统 - 阿里云百炼 API 配置
"""

# 阿里云百炼 API 配置
DASHSCOPE_API_KEY = "sk-sp-a184e2d7f771427a9b0c3c869992ff5a"
DASHSCOPE_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"

# 推荐模型配置
MODEL_CONFIG = {
    "default": "qwen-plus",
    "chat": "qwen-plus",
    "analysis": "qwen-max",
    "vision": "qwen-vl-max",
    "code": "qwen-plus"
}

# API 调用参数
API_CONFIG = {
    "timeout": 30,
    "max_tokens": 4096,
    "temperature": 0.7,
    "top_p": 0.8
}

def get_api_key():
    """获取 API Key"""
    return DASHSCOPE_API_KEY

def get_base_url():
    """获取 Base URL"""
    return DASHSCOPE_BASE_URL

def get_model(task_type="default"):
    """根据任务类型获取模型"""
    return MODEL_CONFIG.get(task_type, MODEL_CONFIG["default"])
