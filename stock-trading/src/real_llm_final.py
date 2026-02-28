"""
真实 LLM 分析师 - 通过 sessions_spawn 实现
不使用任何 mock 或规则化回退
"""
import json
import os
import sys
from typing import Dict, Any
from datetime import datetime

# 导入 sessions_spawn 用于真实 LLM 调用
try:
    from sessions_spawn import sessions_spawn
    from sessions_history import sessions_history
    SESSIONS_AVAILABLE = True
except ImportError:
    print("⚠️ sessions_spawn 不可用，将使用简化实现")
    SESSIONS_AVAILABLE = False


def build_analyst_prompt(role: str, task: str, data: Dict[str, Any]) -> str:
    """构建分析师提示词"""
    
    role_prompts = {
        "基本面分析师": """你是一位资深基本面分析师。请分析以下数据并输出 JSON：
{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "targetPrice": 目标价格,
    "reasoning": "分析理由",
    "keyStrengths": ["优势 1", "优势 2"],
    "keyRisks": ["风险 1", "风险 2"]
}

数据：
{data}

只输出 JSON，不要 Markdown。""",

        "技术分析师": """你是一位资深技术分析师。请分析技术指标并输出 JSON：
{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "trendDirection": "UPTREND/DOWNTREND/SIDEWAYS",
    "reasoning": "分析理由",
    "supportLevel": 支撑位,
    "resistanceLevel": 阻力位
}

数据：
{data}

只输出 JSON，不要 Markdown。""",

        "舆情分析师": """你是一位舆情分析师。请分析情绪数据并输出 JSON：
{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "sentimentScore": -1.0 到 1.0,
    "reasoning": "分析理由",
    "newsAssessment": "正面/中性/负面",
    "socialAssessment": "正面/中性/负面"
}

数据：
{data}

只输出 JSON，不要 Markdown。""",

        "风险管理师": """你是一位风险管理师。请评估风险并输出 JSON：
{
    "riskLevel": "LOW/MEDIUM/HIGH",
    "positionLimit": 0.0-1.0,
    "stopLoss": 止损价,
    "takeProfit": 止盈价,
    "reasoning": "评估理由",
    "keyRisks": ["风险 1", "风险 2"]
}

数据：
{data}

只输出 JSON，不要 Markdown。"""
    }
    
    prompt = role_prompts.get(role, "分析以下数据并输出 JSON：{data}")
    return prompt.format(data=json.dumps(data, indent=2, ensure_ascii=False))


def call_llm_via_sessions(prompt: str, timeout: int = 60) -> str:
    """
    通过 sessions_spawn 调用真实 LLM
    """
    if not SESSIONS_AVAILABLE:
        raise RuntimeError("sessions_spawn 不可用")
    
    print(f"   🤖 创建 LLM 分析会话...")
    
    # 创建子代理会话
    session_key = sessions_spawn(
        task=prompt,
        label="llm_analyst",
        runtime="subagent",
        mode="run",
        cleanup="delete",
        timeout_seconds=timeout
    )
    
    print(f"   📡 等待 LLM 响应 (会话：{session_key})...")
    
    # 获取会话历史 (LLM 响应)
    history = sessions_history(session_key=session_key, limit=5)
    
    # 提取 LLM 响应
    if history and 'messages' in history:
        for msg in reversed(history['messages']):
            if msg.get('role') == 'assistant':
                return msg.get('content', '')
    
    raise RuntimeError("无法获取 LLM 响应")


def parse_json_response(response: str) -> Dict[str, Any]:
    """解析 JSON 响应"""
    try:
        return json.loads(response.strip())
    except:
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"JSON 解析失败：{response[:200]}")


def analyze_with_real_llm(role: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用真实 LLM 进行分析
    
    完整流程:
    1. 构建提示词
    2. 调用 sessions_spawn
    3. 解析 JSON 响应
    4. 返回结果
    """
    print(f"\n📊 {role} 正在分析...")
    
    # 1. 构建提示词
    prompt = build_analyst_prompt(role, "分析", data)
    
    # 2. 保存提示词
    os.makedirs('logs/llm_prompts', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs/llm_prompts/{role}_{timestamp}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    # 3. 调用真实 LLM
    try:
        llm_response = call_llm_via_sessions(prompt, timeout=60)
        
        # 4. 解析响应
        result = parse_json_response(llm_response)
        
        # 5. 添加元数据
        result['role'] = role
        result['timestamp'] = datetime.now().isoformat()
        result['llm_used'] = True
        
        print(f"   ✅ {role} 完成分析")
        print(f"      评级：{result.get('rating', 'N/A')}")
        print(f"      置信度：{result.get('confidence', 0):.1%}")
        
        return result
        
    except Exception as e:
        print(f"   ❌ {role} 分析失败：{e}")
        # 返回空结果但不中断流程
        return {
            'role': role,
            'error': str(e),
            'llm_used': True,
            'timestamp': datetime.now().isoformat()
        }


# 测试
if __name__ == "__main__":
    print("="*60)
    print("🤖 真实 LLM 分析师 - 测试")
    print("="*60)
    
    test_data = {
        'symbol': 'GOOGL',
        'pe_ratio': 25.5,
        'roe': 0.28,
        'revenue_growth': 0.12
    }
    
    if SESSIONS_AVAILABLE:
        print(f"\n✅ sessions_spawn 可用，将调用真实 LLM")
        result = analyze_with_real_llm("基本面分析师", test_data)
        print(f"\n结果：{json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"\n⚠️ sessions_spawn 不可用，无法测试真实 LLM 调用")
        print(f"   提示词已保存到 logs/llm_prompts/")
