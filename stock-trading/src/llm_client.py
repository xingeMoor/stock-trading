"""
LLM 客户端
集成真实的 LLM API 调用 (OpenAI 兼容格式)
"""
import os
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime


class LLMClient:
    """
    LLM 客户端
    支持多种模型：Qwen、OpenAI 等
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: str = "qwen3.5-plus-2026-02-15"):
        """
        初始化 LLM 客户端
        
        Args:
            api_key: API Key (默认从环境变量读取)
            base_url: API 基础 URL (默认使用阿里云 dashscope)
            model: 模型名称
        """
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY', 
                                           'sk-sp-a184e2d7f771427a9b0c3c869992ff5a')
        self.base_url = base_url or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        self.model = model
        
        print(f"🤖 LLM 客户端初始化完成")
        print(f"   模型：{model}")
        print(f"   API: {self.base_url}")
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: int = 2000,
             **kwargs) -> Dict[str, Any]:
        """
        聊天补全 API
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度 (0-1)
            max_tokens: 最大 token 数
        
        Returns:
            LLM 响应
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        try:
            print(f"   📡 调用 LLM API...")
            print(f"      消息数：{len(messages)}")
            print(f"      输入长度：{sum(len(m.get('content', '')) for m in messages)} 字符")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            print(f"   ✅ LLM 响应成功")
            print(f"      输出长度：{len(result.get('choices', [{}])[0].get('message', {}).get('content', ''))} 字符")
            print(f"      Token 使用：{result.get('usage', {})}")
            
            return {
                'success': True,
                'content': result['choices'][0]['message']['content'],
                'usage': result.get('usage', {}),
                'raw': result
            }
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ LLM API 调用失败：{e}")
            return {
                'success': False,
                'error': str(e),
                'content': ''
            }
    
    def chat_with_json_output(self, system_prompt: str, 
                               user_prompt: str,
                               temperature: float = 0.3) -> Dict[str, Any]:
        """
        聊天并强制 JSON 输出
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度 (建议 0.3 以下保证 JSON 格式)
        
        Returns:
            解析后的 JSON 数据
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.chat(messages, temperature=temperature)
        
        if not response['success']:
            return {
                'success': False,
                'error': response.get('error', 'Unknown error'),
                'data': {}
            }
        
        # 解析 JSON
        content = response['content']
        parsed_data = self._parse_json_content(content)
        
        return {
            'success': True,
            'data': parsed_data,
            'raw_content': content,
            'usage': response.get('usage', {})
        }
    
    def _parse_json_content(self, content: str) -> Dict[str, Any]:
        """
        解析 JSON 内容
        """
        try:
            # 尝试直接解析
            return json.loads(content.strip())
        except json.JSONDecodeError:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # 解析失败
            print(f"   ⚠️ JSON 解析失败，返回空字典")
            return {}
    
    def analyze_with_role(self, role: str, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用指定角色进行分析
        
        Args:
            role: 角色名称 (如 "基本面分析师", "技术分析师")
            task: 任务描述
            data: 分析数据
        
        Returns:
            分析结果
        """
        system_prompt = f"""你是一位专业的{role}。
你的任务是：{task}
请输出 JSON 格式的分析结果，不要包含 Markdown 格式。"""
        
        user_prompt = f"""请分析以下数据：

{json.dumps(data, indent=2, ensure_ascii=False)}

请输出 JSON 格式的分析结果。"""
        
        return self.chat_with_json_output(system_prompt, user_prompt)


# ============================================================================
# 便捷函数
# ============================================================================

def get_llm_client(model: str = "qwen3.5-plus-2026-02-15") -> LLMClient:
    """获取 LLM 客户端实例"""
    return LLMClient(model=model)


def llm_analyze(role: str, task: str, data: Dict[str, Any], 
                model: str = "qwen3.5-plus-2026-02-15") -> Dict[str, Any]:
    """
    快速调用 LLM 分析
    
    Args:
        role: 角色名称
        task: 任务描述
        data: 分析数据
        model: 模型名称
    
    Returns:
        分析结果
    """
    client = get_llm_client(model)
    return client.analyze_with_role(role, task, data)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("🤖 LLM 客户端 - 测试")
    print("="*60)
    
    # 创建客户端
    client = LLMClient()
    
    # 测试 1: 简单对话
    print(f"\n【测试 1】简单对话")
    response = client.chat([
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ])
    
    if response['success']:
        print(f"✅ 响应：{response['content'][:100]}...")
    
    # 测试 2: JSON 输出
    print(f"\n【测试 2】JSON 格式输出")
    response = client.chat_with_json_output(
        system_prompt="你是一位股票分析师。请输出 JSON 格式的分析结果。",
        user_prompt="""
请分析以下股票数据：
- 代码：GOOGL
- 当前价格：$175
- P/E: 25.5
- RSI: 45

请给出评级 (BUY/HOLD/SELL) 和理由。
"""
    )
    
    if response['success']:
        print(f"✅ 分析结果：{json.dumps(response['data'], indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ 失败：{response['error']}")
    
    # 测试 3: 角色扮演分析
    print(f"\n【测试 3】角色扮演 - 基本面分析师")
    test_data = {
        'symbol': 'GOOGL',
        'pe_ratio': 25.5,
        'roe': 0.28,
        'revenue_growth': 0.12,
        'net_margin': 0.22
    }
    
    result = client.analyze_with_role(
        role="基本面分析师",
        task="分析公司财务状况，给出评级和目标价",
        data=test_data
    )
    
    if result['success']:
        print(f"✅ 分析完成：{json.dumps(result['data'], indent=2, ensure_ascii=False)[:500]}...")
    
    print(f"\n{'='*60}")
    print("✅ LLM 客户端测试完成！")
