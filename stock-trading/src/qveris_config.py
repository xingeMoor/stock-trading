"""
QVeris AI 配置和工具
API文档: https://www.qveris.ai/
"""
import os
from typing import Dict, Any, Optional

# API配置
QVERIS_API_KEY = "sk-4Gy1CrU_gGuj-dGt0gCo_YYhjo88eHQ43HP9JrThkX4"
QVERIS_BASE_URL = "https://qveris.ai/api/v1"

class QVerisClient:
    """QVeris AI 客户端"""
    
    def __init__(self, api_key: str = QVERIS_API_KEY):
        self.api_key = api_key
        self.base_url = QVERIS_BASE_URL
        
    def chat(self, message: str, model: str = "gpt-4") -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            message: 用户消息
            model: 模型名称
        """
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": message}]
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    def list_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        try:
            import requests
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}


def test_qveris():
    """测试 QVeris API"""
    print("🧪 测试 QVeris AI API\n")
    
    client = QVerisClient()
    
    # 测试1: 列出模型
    print("1️⃣  获取模型列表...")
    models = client.list_models()
    if "error" not in models:
        print(f"   ✅ 成功")
        print(f"   📋 模型: {models.get('data', [])[:3]}")
    else:
        print(f"   ⚠️  {models.get('error')}")
    
    # 测试2: 简单对话
    print("\n2️⃣  测试对话...")
    response = client.chat("Hello, what is your name?")
    if "error" not in response:
        print(f"   ✅ 成功")
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"   💬 回复: {content[:100]}...")
    else:
        print(f"   ⚠️  {response.get('error')}")


if __name__ == "__main__":
    test_qveris()
