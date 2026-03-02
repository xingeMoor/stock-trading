#!/usr/bin/env python3
"""
BettaFish 简化版 - 快速测试阿里云百炼 API
"""
import requests
import json

# 配置
API_KEY = "sk-sp-a184e2d7f771427a9b0c3c869992ff5a"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-plus"

def test_api():
    """测试阿里云百炼 API"""
    print("=" * 60)
    print("🧪 测试阿里云百炼 API")
    print("=" * 60)
    print()
    
    url = f"{BASE_URL}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "分析当前中东局势（美国以色列伊朗）对美股和 A 股的潜在影响，简要说明"
            }
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        print(f"请求 URL: {url}")
        print(f"模型：{MODEL}")
        print(f"问题：分析中东局势对市场的影响")
        print()
        print("正在调用 API...")
        print()
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            print("✅ API 调用成功！")
            print()
            print("=" * 60)
            print("📊 分析结果:")
            print("=" * 60)
            print(content)
            print()
            print("=" * 60)
            print("✅ 阿里云百炼 API 配置正确，可以正常使用！")
            print("=" * 60)
            
            return True
        else:
            print(f"❌ API 调用失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发生错误：{e}")
        return False

if __name__ == '__main__':
    test_api()
