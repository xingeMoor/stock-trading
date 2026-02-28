"""
OpenClaw LLM 集成
通过 OpenClaw 会话系统调用 LLM，而不是直接 HTTP 请求
"""
import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class OpenClawLLMClient:
    """
    OpenClaw LLM 客户端
    通过子进程调用 OpenClaw 来获取 LLM 响应
    """
    
    def __init__(self, model: str = "bailian/qwen3.5-plus-2026-02-15"):
        self.model = model
        print(f"🤖 OpenClaw LLM 客户端初始化")
        print(f"   模型：{model}")
    
    def analyze(self, role: str, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 进行分析
        
        由于 OpenClaw 限制，这里使用规则化分析 + LLM 提示词模板
        实际 LLM 调用需要通过 OpenClaw 会话系统
        """
        print(f"\n📊 {role} 正在分析...")
        
        # 构建分析提示词 (用于后续 LLM 调用)
        prompt = self._build_prompt(role, task, data)
        
        # 当前使用规则化分析 (临时)
        # 实际应该调用 OpenClaw 会话获取 LLM 响应
        result = self._rule_based_analysis(role, data)
        
        # 保存提示词到文件 (供后续 LLM 调用使用)
        self._save_prompt_for_llm(role, prompt)
        
        print(f"   ✅ {role} 完成分析")
        print(f"      评级：{result.get('rating', 'N/A')}")
        
        return result
    
    def _build_prompt(self, role: str, task: str, data: Dict[str, Any]) -> str:
        """构建 LLM 提示词"""
        return f"""你是一位{role}。

任务：{task}

数据：
{json.dumps(data, indent=2, ensure_ascii=False)}

请输出 JSON 格式的分析结果。"""
    
    def _rule_based_analysis(self, role: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        规则化分析 (临时实现)
        """
        if role == "基本面分析师":
            return self._fundamental_analysis(data)
        elif role == "技术分析师":
            return self._technical_analysis(data)
        elif role == "舆情分析师":
            return self._sentiment_analysis(data)
        elif role == "风险管理师":
            return self._risk_assessment(data)
        else:
            return self._generic_analysis(data)
    
    def _fundamental_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """基本面分析"""
        ratios = data.get('financialRatios', {})
        pe = ratios.get('valuationRatios', {}).get('peRatio', 30)
        roe = ratios.get('profitabilityRatios', {}).get('returnOnEquity', 0.2)
        growth = ratios.get('growthRatios', {}).get('revenueGrowth', 0.1)
        
        score = 0
        if pe < 25: score += 1
        if pe < 20: score += 1
        if roe > 0.25: score += 1
        if growth > 0.15: score += 1
        
        rating = 'BUY' if score >= 3 else 'HOLD' if score >= 1 else 'SELL'
        confidence = 0.5 + score * 0.1
        
        return {
            'role': 'Fundamental Analyst',
            'rating': rating,
            'confidence': min(confidence, 0.9),
            'reasoning': [
                f"P/E={pe}，估值{'合理' if 20<=pe<=30 else '偏低' if pe<20 else '偏高'}",
                f"ROE={roe:.1%}，盈利能力{'强' if roe>0.25 else '中等'}",
                f"营收增长={growth:.1%}，成长性{'高' if growth>0.15 else '中等'}"
            ]
        }
    
    def _technical_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """技术分析"""
        indicators = data.get('technical_indicators', {})
        sma_50 = indicators.get('sma_50', 0)
        sma_200 = indicators.get('sma_200', 0)
        rsi = indicators.get('rsi_14', 50)
        price = indicators.get('current_price', 0)
        
        uptrend = sma_50 > sma_200 if sma_50 and sma_200 else False
        above_sma50 = price > sma_50 if sma_50 else False
        oversold = rsi < 30 if rsi else False
        overbought = rsi > 70 if rsi else False
        
        if uptrend and above_sma50 and not overbought:
            rating = 'BUY'
            confidence = 0.7
        elif overbought:
            rating = 'SELL'
            confidence = 0.6
        elif oversold and uptrend:
            rating = 'BUY'
            confidence = 0.65
        else:
            rating = 'HOLD'
            confidence = 0.5
        
        return {
            'role': 'Technical Analyst',
            'rating': rating,
            'confidence': confidence,
            'reasoning': [
                f"趋势：{'上升' if uptrend else '下降' if sma_50 and sma_200 and sma_50<sma_200 else '横盘'}",
                f"RSI={rsi:.1f}，{'超卖' if oversold else '超买' if overbought else '中性'}",
                f"价格{'在' if above_sma50 else '低于'}SMA50 上方"
            ]
        }
    
    def _sentiment_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """舆情分析"""
        sentiment = data.get('sentiment', {})
        score = sentiment.get('composite_score', 0)
        
        if score > 0.3:
            rating = 'BUY'
            confidence = 0.6 + score * 0.4
        elif score < -0.3:
            rating = 'SELL'
            confidence = 0.6 + abs(score) * 0.4
        else:
            rating = 'HOLD'
            confidence = 0.5
        
        return {
            'role': 'Sentiment Analyst',
            'rating': rating,
            'confidence': min(confidence, 0.9),
            'reasoning': [
                f"综合情绪评分={score:.2f}，{'正面' if score>0.3 else '负面' if score<-0.3 else '中性'}"
            ]
        }
    
    def _risk_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """风险评估"""
        macro = data.get('macroConditions', {})
        regime = macro.get('marketRegime', 'MODERATE_GROWTH')
        
        if regime in ['RECESSION', 'BEAR_MARK']:
            risk_level = 'HIGH'
            position_limit = 0.15
        elif regime == 'BULL_MARK':
            risk_level = 'LOW'
            position_limit = 0.40
        else:
            risk_level = 'MEDIUM'
            position_limit = 0.25
        
        current_price = data.get('technical_indicators', {}).get('current_price', 100)
        
        return {
            'role': 'Risk Manager',
            'risk_level': risk_level,
            'position_limit': position_limit,
            'stop_loss': current_price * 0.92,
            'take_profit': current_price * 1.15,
            'reasoning': [
                f"市场状态：{regime}",
                f"建议仓位：{position_limit:.1%}"
            ]
        }
    
    def _generic_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """通用分析"""
        return {
            'role': 'Analyst',
            'rating': 'HOLD',
            'confidence': 0.5,
            'reasoning': ['通用分析，需要更多数据']
        }
    
    def _save_prompt_for_llm(self, role: str, prompt: str):
        """保存提示词到文件，供后续 LLM 调用"""
        os.makedirs('logs/llm_prompts', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"logs/llm_prompts/{role}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        print(f"   💾 提示词已保存：{filename}")


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("🤖 OpenClaw LLM 集成 - 测试")
    print("="*60)
    
    client = OpenClawLLMClient()
    
    # 测试数据
    test_data = {
        'symbol': 'GOOGL',
        'financialRatios': {
            'valuationRatios': {'peRatio': 25.5},
            'profitabilityRatios': {'returnOnEquity': 0.28},
            'growthRatios': {'revenueGrowth': 0.12}
        },
        'technical_indicators': {
            'current_price': 175.0,
            'sma_50': 165.0,
            'sma_200': 155.0,
            'rsi_14': 45.0
        },
        'sentiment': {'composite_score': 0.25},
        'macroConditions': {'marketRegime': 'MODERATE_GROWTH'}
    }
    
    # 测试各角色分析
    print(f"\n【测试 1】基本面分析师")
    fundamental = client.analyze("基本面分析师", "分析公司财务状况", test_data)
    print(f"结果：{json.dumps(fundamental, indent=2, ensure_ascii=False)}")
    
    print(f"\n【测试 2】技术分析师")
    technical = client.analyze("技术分析师", "分析技术指标", test_data)
    print(f"结果：{json.dumps(technical, indent=2, ensure_ascii=False)}")
    
    print(f"\n【测试 3】舆情分析师")
    sentiment = client.analyze("舆情分析师", "分析市场情绪", test_data)
    print(f"结果：{json.dumps(sentiment, indent=2, ensure_ascii=False)}")
    
    print(f"\n【测试 4】风险管理师")
    risk = client.analyze("风险管理师", "评估投资风险", test_data)
    print(f"结果：{json.dumps(risk, indent=2, ensure_ascii=False)}")
    
    print(f"\n{'='*60}")
    print("✅ OpenClaw LLM 集成测试完成！")
    print(f"\n📝 提示词已保存到 logs/llm_prompts/ 目录")
    print(f"💡 后续可以通过 OpenClaw 会话系统调用真实 LLM")
