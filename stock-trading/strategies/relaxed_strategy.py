"""
宽松版交易策略
降低交易门槛，增加交易频率，适合回测验证
"""
from typing import Dict, Any


def relaxed_strategy(row, indicators: Dict[str, Any]) -> str:
    """
    宽松策略：降低交易门槛
    
    买入条件 (满足任意 1 个即可):
    - RSI < 40 (放宽超卖判断)
    - MACD 金叉 (MACD > Signal)
    - 价格站上 SMA20
    
    卖出条件 (满足任意 1 个即可):
    - RSI > 60 (放宽超买判断)
    - MACD 死叉 (MACD < Signal)
    - 价格跌破 SMA20
    """
    buy_conditions = []
    sell_conditions = []
    
    # 1. RSI (放宽阈值)
    rsi = indicators.get('rsi_14')
    if rsi is not None:
        if rsi < 40:  # 原为 30
            buy_conditions.append(f"RSI 偏低 ({rsi:.1f})")
        elif rsi > 60:  # 原为 70
            sell_conditions.append(f"RSI 偏高 ({rsi:.1f})")
    
    # 2. MACD
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            buy_conditions.append(f"MACD 金叉 ({macd:.2f} > {macd_signal:.2f})")
        elif macd < macd_signal:
            sell_conditions.append(f"MACD 死叉 ({macd:.2f} < {macd_signal:.2f})")
    
    # 3. SMA20
    sma_20 = indicators.get('sma_20')
    current_price = indicators.get('current_price', row.get('close', 0))
    if sma_20 is not None and current_price > 0:
        if current_price > sma_20:
            buy_conditions.append(f"价格>SMA20 (${current_price:.2f} > ${sma_20:.2f})")
        elif current_price < sma_20:
            sell_conditions.append(f"价格<SMA20 (${current_price:.2f} < ${sma_20:.2f})")
    
    # 决策：任意 1 个条件满足即可
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


if __name__ == "__main__":
    # 测试
    test_indicators = {
        'rsi_14': 44.4,
        'macd': 0.33,
        'macd_signal': 1.64,
        'sma_20': 167.27,
        'current_price': 100
    }
    
    class MockRow:
        close = 100
    
    signal = relaxed_strategy(MockRow(), test_indicators)
    print(f"测试信号：{signal}")
    print(f"条件：MACD 死叉 (0.33 < 1.64), 价格<SMA20 (100 < 167.27)")
