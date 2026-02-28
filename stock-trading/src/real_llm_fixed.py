"""
真实 LLM 分析师 - 修复版
修复 JSON 格式问题
"""
import json
import os
from datetime import datetime
from typing import Dict, Any


def build_analyst_prompt(role: str, data: Dict[str, Any]) -> str:
    """构建分析师提示词 - 修复 JSON 转义"""
    
    role_prompts = {
        "基本面分析师": """你是一位资深基本面分析师。请分析以下数据并输出 JSON：

数据：
{data}

输出 JSON 格式 (使用双花括号转义)：
{{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "targetPrice": 目标价格，
    "reasoning": "分析理由",
    "keyStrengths": ["优势 1", "优势 2"],
    "keyRisks": ["风险 1", "风险 2"]
}}

只输出 JSON，不要 Markdown。""",

        "技术分析师": """你是一位资深技术分析师。请分析技术指标并输出 JSON：

数据：
{data}

输出 JSON 格式：
{{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "trendDirection": "UPTREND/DOWNTREND/SIDEWAYS",
    "reasoning": "分析理由",
    "supportLevel": 支撑位，
    "resistanceLevel": 阻力位
}}

只输出 JSON，不要 Markdown。"""
    }
    
    prompt = role_prompts.get(role, "分析以下数据并输出 JSON：{{}}")
    return prompt.format(data=json.dumps(data, indent=2, ensure_ascii=False))


# 测试
if __name__ == "__main__":
    print("测试 LLM 提示词构建...")
    
    test_data = {
        'symbol': 'GOOGL',
        'pe_ratio': 25.5,
        'roe': 0.28
    }
    
    prompt = build_analyst_prompt("基本面分析师", test_data)
    
    print(f"提示词长度：{len(prompt)}")
    print(f"\n前 500 字符:\n{prompt[:500]}")
    
    # 保存
    os.makedirs('logs/llm_prompts', exist_ok=True)
    with open('logs/llm_prompts/fixed_prompt.txt', 'w') as f:
        f.write(prompt)
    
    print(f"\n✅ 提示词已保存到 logs/llm_prompts/fixed_prompt.txt")
