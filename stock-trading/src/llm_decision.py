"""
LLM 交易决策模块
基于综合数据 (技术指标 + 舆情 + 基本面) 生成交易决策
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .config import LLM_DECISION_CONFIG, BACKTEST_CONFIG


def build_decision_prompt(symbol: str, data: Dict[str, Any]) -> str:
    """
    构建 LLM 决策提示词
    """
    prompt = f"""
# 股票交易决策分析

## 股票信息
- 代码：{symbol}
- 当前价格：${data.get('current_price', 'N/A')}
- 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 技术指标
"""
    
    indicators = data.get('technical_indicators', {})
    if indicators:
        prompt += f"""
- SMA(20): ${indicators.get('sma_20', 'N/A')}
- EMA(20): ${indicators.get('ema_20', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A')}
- RSI(14): {indicators.get('rsi_14', 'N/A')}
- Stochastic K: {indicators.get('stoch_k', 'N/A')}
- Stochastic D: {indicators.get('stoch_d', 'N/A')}
- CCI: {indicators.get('cci', 'N/A')}
- ADX: {indicators.get('adx', 'N/A')}
- Williams %R: {indicators.get('williams_r', 'N/A')}
"""
    
    sentiment = data.get('sentiment', {})
    prompt += f"""
## 舆情情绪
- 综合评分：{sentiment.get('composite_score', 'N/A')} ({sentiment.get('sentiment_level', 'N/A')})
- 新闻情绪：{sentiment.get('components', {}).get('news', {}).get('score', 'N/A')}
- 社交情绪：{sentiment.get('components', {}).get('social', {}).get('score', 'N/A')}
- 分析师评级：{sentiment.get('components', {}).get('analyst', {}).get('rating', 'N/A')}
"""
    
    portfolio = data.get('portfolio', {})
    prompt += f"""
## 当前持仓
- 持仓数量：{portfolio.get('current_position', 0)} 股
- 平均成本：${portfolio.get('average_cost', 'N/A')}
- 可用资金：${portfolio.get('available_capital', 'N/A')}
"""
    
    prompt += """
## 决策要求

请基于以上数据进行综合分析，给出明确的交易决策。

### 输出格式 (严格 JSON):
{
    "action": "buy/sell/hold",
    "quantity": 具体股数 (整数),
    "confidence": 置信度 (0-1 之间的小数),
    "reasoning": "详细的分析理由，包括技术指标、舆情情绪的综合判断",
    "stop_loss": 止损价格 (数字),
    "take_profit": 止盈价格 (数字),
    "time_horizon": "预期持仓时间",
    "risk_level": "low/medium/high"
}

### 决策原则:
1. 技术指标多重确认时才行动 (至少 2 个指标支持)
2. 舆情情绪作为辅助判断，不单独作为决策依据
3. RSI < 30 考虑买入，RSI > 70 考虑卖出
4. MACD 金叉 (MACD > Signal) 看涨，死叉看跌
5. 价格站上 SMA20 看涨，跌破看跌
6. 置信度低于 0.6 时建议 hold
7. 考虑当前持仓情况，避免过度集中

请输出 JSON 格式的决策结果:
"""
    
    return prompt


def parse_llm_response(response: str) -> Dict[str, Any]:
    """
    解析 LLM 响应，提取决策 JSON
    """
    try:
        # 尝试直接解析
        decision = json.loads(response.strip())
        return validate_decision(decision)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 块
    import re
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            decision = json.loads(json_match.group())
            return validate_decision(decision)
        except json.JSONDecodeError:
            pass
    
    # 解析失败，返回默认 hold 决策
    return {
        "action": "hold",
        "quantity": 0,
        "confidence": 0.5,
        "reasoning": "无法解析 LLM 响应，默认持有",
        "stop_loss": 0,
        "take_profit": 0,
        "time_horizon": "N/A",
        "risk_level": "low"
    }


def validate_decision(decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并补全决策数据
    """
    # 验证 action
    valid_actions = ["buy", "sell", "hold"]
    if decision.get('action') not in valid_actions:
        decision['action'] = 'hold'
    
    # 验证 quantity
    quantity = decision.get('quantity', 0)
    if not isinstance(quantity, int) or quantity < 0:
        decision['quantity'] = 0
    
    # 验证 confidence
    confidence = decision.get('confidence', 0.5)
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        decision['confidence'] = 0.5
    
    # 验证必填字段
    if 'reasoning' not in decision:
        decision['reasoning'] = "无详细理由"
    
    if 'stop_loss' not in decision:
        decision['stop_loss'] = 0
    
    if 'take_profit' not in decision:
        decision['take_profit'] = 0
    
    if 'time_horizon' not in decision:
        decision['time_horizon'] = "N/A"
    
    if 'risk_level' not in decision:
        decision['risk_level'] = "medium"
    
    return decision


def calculate_quantity(action: str, current_price: float, 
                       available_capital: float, 
                       current_position: int) -> int:
    """
    计算交易数量
    """
    if action == 'hold':
        return 0
    
    if action == 'sell':
        return current_position
    
    # 买入：根据可用资金和仓位比例计算
    position_pct = LLM_DECISION_CONFIG.get('default_quantity_pct', 0.5)
    buy_capital = available_capital * position_pct
    
    # 考虑手续费
    commission_rate = BACKTEST_CONFIG.get('commission_rate', 0.001)
    effective_price = current_price * (1 + commission_rate)
    
    quantity = int(buy_capital / effective_price)
    
    # 确保至少 1 股 (如果资金足够)
    if quantity == 0 and buy_capital >= effective_price:
        quantity = 1
    
    return quantity


def make_trading_decision(symbol: str, data: Dict[str, Any], 
                          llm_response: Optional[str] = None) -> Dict[str, Any]:
    """
    生成交易决策
    
    Args:
        symbol: 股票代码
        data: 完整数据包 (技术指标、舆情、持仓等)
        llm_response: 可选的 LLM 响应 (如果已预先调用)
    
    Returns:
        决策字典
    """
    # 如果有预提供的 LLM 响应，直接解析
    if llm_response:
        decision = parse_llm_response(llm_response)
    else:
        # 构建提示词 (实际使用时需要调用 LLM API)
        prompt = build_decision_prompt(symbol, data)
        
        # 这里返回提示词，实际调用由上层处理
        # 因为 LLM 调用需要通过 OpenClaw 的消息系统
        return {
            "symbol": symbol,
            "prompt": prompt,
            "status": "awaiting_llm",
            "message": "请调用 LLM API 获取决策，使用上述 prompt"
        }
    
    # 计算具体交易数量
    current_price = data.get('current_price', 0)
    portfolio = data.get('portfolio', {})
    available_capital = portfolio.get('available_capital', 0)
    current_position = portfolio.get('current_position', 0)
    
    quantity = calculate_quantity(
        decision['action'],
        current_price,
        available_capital,
        current_position
    )
    
    # 如果置信度低于阈值，强制 hold
    min_confidence = LLM_DECISION_CONFIG.get('min_confidence', 0.6)
    if decision['confidence'] < min_confidence and decision['action'] != 'hold':
        decision['action'] = 'hold'
        decision['quantity'] = 0
        decision['reasoning'] = f"置信度 {decision['confidence']:.2f} 低于阈值 {min_confidence}，建议持有观望"
    
    # 添加元数据
    decision['symbol'] = symbol
    decision['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    decision['current_price'] = current_price
    
    return decision


def make_llm_decision_via_openclaw(symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    通过 OpenClaw 会话调用 LLM 获取决策
    这是一个示例函数，实际使用需要集成到 OpenClaw 系统中
    """
    prompt = build_decision_prompt(symbol, data)
    
    # 在实际 OpenClaw 环境中，这里会调用 sessions_send 或其他方式
    # 将 prompt 发送给 LLM 并获取响应
    # 由于这是 skill 模块，我们返回 prompt 供上层调用
    
    return {
        "symbol": symbol,
        "prompt": prompt,
        "status": "ready_for_llm",
        "data_summary": {
            "price": data.get('current_price'),
            "rsi": data.get('technical_indicators', {}).get('rsi_14'),
            "sentiment": data.get('sentiment', {}).get('composite_score')
        }
    }


if __name__ == "__main__":
    # 测试数据
    test_data = {
        "current_price": 185.50,
        "technical_indicators": {
            "sma_20": 182.30,
            "ema_20": 183.10,
            "macd": 2.02,
            "macd_signal": 0.84,
            "macd_histogram": 1.18,
            "rsi_14": 45.2,
            "stoch_k": 65.3,
            "stoch_d": 58.7,
            "cci": 85.2,
            "adx": 28.5,
            "williams_r": -35.6
        },
        "sentiment": {
            "composite_score": 0.58,
            "sentiment_level": "Positive",
            "components": {
                "news": {"score": 0.65, "count": 8},
                "social": {"score": 0.42, "mentions": 15},
                "analyst": {"score": 0.5, "rating": "Buy"}
            }
        },
        "portfolio": {
            "current_position": 100,
            "average_cost": 178.20,
            "available_capital": 50000
        }
    }
    
    # 构建提示词
    prompt = build_decision_prompt("AAPL", test_data)
    print("=== LLM 决策提示词 ===")
    print(prompt)
    print("\n=== 请将此提示词发送给 LLM 获取决策 ===")
