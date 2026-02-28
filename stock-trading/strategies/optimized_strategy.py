"""
优化版交易策略
基于回测结果调整参数，针对 META 等强势股票优化
"""
from typing import Dict, Any


def optimized_strategy(row, indicators: Dict[str, Any]) -> str:
    """
    优化策略：
    1. 增加趋势过滤 (SMA50)
    2. 调整 RSI 阈值
    3. MACD 需要确认
    """
    buy_conditions = []
    sell_conditions = []
    
    # 获取指标
    rsi = indicators.get('rsi_14')
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    sma_20 = indicators.get('sma_20')
    sma_50 = indicators.get('sma_50')
    current_price = indicators.get('current_price', row.get('close', 0))
    
    # === 买入条件 ===
    
    # 1. 趋势过滤：价格在 SMA50 之上 (只做强势股)
    trend_bullish = sma_50 and current_price > sma_50
    
    # 2. RSI 不过热 (< 60，避免追高)
    rsi_ok = rsi and rsi < 60
    
    # 3. MACD 金叉或柱状图上升
    macd_bullish = macd and macd_signal and macd > macd_signal
    
    # 4. 价格站上 SMA20
    price_above_sma20 = sma_20 and current_price > sma_20
    
    if trend_bullish:
        buy_conditions.append("趋势向上 (价格>SMA50)")
    if rsi_ok:
        buy_conditions.append(f"RSI 合理 ({rsi:.1f})")
    if macd_bullish:
        buy_conditions.append("MACD 金叉")
    if price_above_sma20:
        buy_conditions.append("价格>SMA20")
    
    # 买入：趋势向上 + 至少 2 个其他条件
    if trend_bullish and len([c for c in buy_conditions[1:] if c]) >= 2:
        return 'buy'
    
    # === 卖出条件 ===
    
    # 1. RSI 过热 (> 65)
    if rsi and rsi > 65:
        sell_conditions.append(f"RSI 偏高 ({rsi:.1f})")
    
    # 2. MACD 死叉
    if macd and macd_signal and macd < macd_signal:
        sell_conditions.append("MACD 死叉")
    
    # 3. 价格跌破 SMA20
    if sma_20 and current_price < sma_20:
        sell_conditions.append("价格<SMA20")
    
    # 4. 价格跌破 SMA50 (趋势反转)
    if sma_50 and current_price < sma_50:
        sell_conditions.append("趋势反转 (价格<SMA50)")
    
    # 卖出：至少 2 个条件
    if len(sell_conditions) >= 2:
        return 'sell'
    
    return 'hold'


if __name__ == "__main__":
    # 测试
    test_indicators = {
        'rsi_14': 55,
        'macd': 2.0,
        'macd_signal': 1.5,
        'sma_20': 450,
        'sma_50': 430,
        'current_price': 460
    }
    
    class MockRow:
        close = 460
    
    signal = optimized_strategy(MockRow(), test_indicators)
    print(f"测试信号：{signal}")
    print(f"条件：趋势向上，RSI=55，MACD 金叉，价格>SMA20")
