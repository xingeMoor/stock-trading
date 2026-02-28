"""
LLM 投资委员会
使用大模型作为最终决策者，综合所有分析师报告
"""
from typing import Dict, Any, List
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LLM_DECISION_CONFIG


def build_committee_prompt(symbol: str, reports: Dict[str, Dict], 
                           backtest_history: List[Dict],
                           market_data: Dict[str, Any]) -> str:
    """
    构建投资委员会决策提示词
    """
    prompt = f"""
# 🏢 量化交易公司 - 投资委员会决策

## 会议信息
- **股票代码**: {symbol}
- **会议时间**: 2026-02-27
- **主持人**: LLM 投资委员会

---

## 📊 各方分析师报告

### 1️⃣ 基本面分析师
**评级**: {reports.get('FundamentalAnalyst', {}).get('rating', 'N/A')}
**置信度**: {reports.get('FundamentalAnalyst', {}).get('confidence', 0):.1%}
**理由**: 
{chr(10).join('  - ' + r for r in reports.get('FundamentalAnalyst', {}).get('reasoning', []))}

### 2️⃣ 技术分析师
**评级**: {reports.get('TechnicalAnalyst', {}).get('rating', 'N/A')}
**置信度**: {reports.get('TechnicalAnalyst', {}).get('confidence', 0):.1%}
**技术指标**:
  - 当前价格：${market_data.get('technical_indicators', {}).get('current_price', 'N/A')}
  - RSI(14): {market_data.get('technical_indicators', {}).get('rsi_14', 'N/A')}
  - MACD: {market_data.get('technical_indicators', {}).get('macd', 'N/A')}
  - SMA50 vs SMA200: {market_data.get('technical_indicators', {}).get('sma_50', 0)} vs {market_data.get('technical_indicators', {}).get('sma_200', 0)}
**理由**: 
{chr(10).join('  - ' + r for r in reports.get('TechnicalAnalyst', {}).get('reasoning', []))}

### 3️⃣ 舆情分析师
**评级**: {reports.get('SentimentAnalyst', {}).get('rating', 'N/A')}
**置信度**: {reports.get('SentimentAnalyst', {}).get('confidence', 0):.1%}
**情绪评分**: {market_data.get('sentiment', {}).get('composite_score', 'N/A')}
**理由**: 
{chr(10).join('  - ' + r for r in reports.get('SentimentAnalyst', {}).get('reasoning', []))}

### 4️⃣ 风险管理师
**风险等级**: {reports.get('RiskManager', {}).get('risk_level', 'N/A')}
**建议仓位**: {reports.get('RiskManager', {}).get('position_limit', 0):.1%}
**止损价**: ${reports.get('RiskManager', {}).get('stop_loss', 'N/A')}
**止盈价**: ${reports.get('RiskManager', {}).get('take_profit', 'N/A')}
**理由**: 
{chr(10).join('  - ' + r for r in reports.get('RiskManager', {}).get('reasoning', []))}

### 5️⃣ 策略师
**建议**: {reports.get('Strategist', {}).get('action', 'N/A')}
**置信度**: {reports.get('Strategist', {}).get('confidence', 0):.1%}
**历史回测参考**:
{chr(10).join('  - ' + f"{r.get('period', 'N/A')}: 收益{r.get('total_return', 0):.1f}%, 回撤{r.get('max_drawdown', 0):.1f}%" for r in backtest_history[-3:])}
**理由**: 
{chr(10).join('  - ' + r for r in reports.get('Strategist', {}).get('reasoning', []))}

---

## 🎯 决策要求

请作为投资委员会主席，综合以上所有报告，做出最终投资决策。

### 输出格式 (严格 JSON):
```json
{{
    "final_action": "BUY/SELL/HOLD",
    "confidence": 0.0-1.0,
    "quantity_pct": 0.0-1.0,  // 建议仓位百分比
    "reasoning": "详细的决策理由，包括对各分析师意见的权衡",
    "key_factors": ["关键因素 1", "关键因素 2", ...],
    "risk_concerns": ["风险关注点 1", "风险关注点 2", ...],
    "stop_loss": 止损价格,
    "take_profit": 止盈价格,
    "time_horizon": "预期持仓时间 (如：1-3 个月)",
    "alternative_scenario": "如果判断错误，应对方案"
}}
```

### 决策原则:
1. **多方验证**: 至少 2 个分析师支持才行动
2. **风险优先**: 高风险时降低仓位
3. **历史参考**: 重视回测表现
4. **明确止损**: 每笔交易必须有止损计划
5. **置信度门槛**: 置信度<0.6 时建议 HOLD

---

请输出 JSON 格式的决策结果 (不要包含 Markdown 格式):
"""
    return prompt


def parse_committee_decision(response: str) -> Dict[str, Any]:
    """
    解析 LLM 决策响应
    """
    try:
        # 尝试直接解析
        decision = json.loads(response.strip())
        return validate_decision(decision)
    except json.JSONDecodeError:
        # 尝试提取 JSON
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                return validate_decision(decision)
            except:
                pass
        
        # 解析失败，返回默认
        return {
            'final_action': 'HOLD',
            'confidence': 0.5,
            'quantity_pct': 0,
            'reasoning': 'LLM 决策解析失败，默认观望',
            'key_factors': [],
            'risk_concerns': ['决策系统异常'],
            'stop_loss': 0,
            'take_profit': 0,
            'time_horizon': 'N/A',
            'alternative_scenario': '等待系统恢复'
        }


def validate_decision(decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证决策格式
    """
    required_fields = ['final_action', 'confidence', 'reasoning']
    for field in required_fields:
        if field not in decision:
            decision[field] = 'N/A' if field == 'final_action' else 0 if field == 'confidence' else ''
    
    # 验证 action
    if decision['final_action'] not in ['BUY', 'SELL', 'HOLD']:
        decision['final_action'] = 'HOLD'
    
    # 验证 confidence
    try:
        decision['confidence'] = float(decision['confidence'])
        decision['confidence'] = min(max(decision['confidence'], 0), 1)
    except:
        decision['confidence'] = 0.5
    
    return decision


async def llm_committee_decision(symbol: str, reports: Dict[str, Dict],
                                  backtest_history: List[Dict],
                                  market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM 投资委员会决策 (异步)
    """
    from llm_decision import make_llm_call
    
    # 构建提示词
    prompt = build_committee_prompt(symbol, reports, backtest_history, market_data)
    
    # 调用 LLM
    response = await make_llm_call(prompt)
    
    # 解析决策
    decision = parse_committee_decision(response)
    
    # 添加元数据
    decision['symbol'] = symbol
    decision['timestamp'] = __import__('datetime').datetime.now().isoformat()
    decision['decision_method'] = 'LLM_Committee'
    
    return decision


# 同步版本 (用于测试)
def llm_committee_decision_sync(symbol: str, reports: Dict[str, Dict],
                                 backtest_history: List[Dict],
                                 market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM 投资委员会决策 (同步版本)
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        llm_committee_decision(symbol, reports, backtest_history, market_data)
    )


if __name__ == "__main__":
    # 测试
    print("测试 LLM 投资委员会决策...")
    
    # 模拟数据
    test_reports = {
        'FundamentalAnalyst': {
            'rating': 'BUY',
            'confidence': 0.7,
            'reasoning': ['科技龙头', '基本面强劲']
        },
        'TechnicalAnalyst': {
            'rating': 'BUY',
            'confidence': 0.6,
            'reasoning': ['趋势向上', 'RSI 中性']
        },
        'SentimentAnalyst': {
            'rating': 'HOLD',
            'confidence': 0.5,
            'reasoning': ['情绪中性']
        },
        'RiskManager': {
            'risk_level': 'MEDIUM',
            'position_limit': 0.25,
            'reasoning': ['波动率正常']
        },
        'Strategist': {
            'action': 'BUY',
            'confidence': 0.65,
            'reasoning': ['多方共识']
        }
    }
    
    test_backtest = [
        {'period': '2025-06 to 2026-02', 'total_return': 68.85, 'max_drawdown': -7.45},
        {'period': '2024-01 to 2024-12', 'total_return': 63.92, 'max_drawdown': -9.07}
    ]
    
    test_market = {
        'technical_indicators': {
            'current_price': 175.0,
            'rsi_14': 45.0,
            'macd': 2.5,
            'sma_50': 165.0,
            'sma_200': 155.0
        },
        'sentiment': {
            'composite_score': 0.25
        }
    }
    
    # 构建提示词测试
    prompt = build_committee_prompt('GOOGL', test_reports, test_backtest, test_market)
    print("\n=== 提示词预览 (前 1000 字符) ===")
    print(prompt[:1000])
    print("\n... (省略) ...\n")
    print("✅ 提示词构建成功！")
