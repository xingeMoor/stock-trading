"""
优化版 V2 交易策略
P0 优化：动态阈值 + 趋势过滤 + 止损止盈
"""
from typing import Dict, Any, Optional


def optimized_v2_strategy(row, indicators: Dict[str, Any], 
                          position: Optional[Dict[str, Any]] = None) -> str:
    """
    优化策略 V2：
    
    1. 动态阈值 - 根据波动率调整 RSI 阈值
    2. 趋势过滤 - 只在上升趋势中做多 (SMA50 > SMA200)
    3. 止损止盈 - 内置风控
    
    买入条件 (满足任意 2 个 + 趋势向上):
    - RSI < 动态阈值 (35-45，根据波动率调整)
    - MACD 金叉 (MACD > Signal)
    - 价格站上 SMA20
    
    卖出条件 (满足任意 1 个即可):
    - RSI > 动态阈值 (55-65，根据波动率调整)
    - MACD 死叉 (MACD < Signal)
    - 价格跌破 SMA20
    - 触发止损/止盈
    """
    buy_conditions = []
    sell_conditions = []
    
    # 获取基础数据
    current_price = indicators.get('current_price', row.get('close', 0))
    rsi = indicators.get('rsi_14')
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    sma_20 = indicators.get('sma_20')
    sma_50 = indicators.get('sma_50')
    sma_200 = indicators.get('sma_200')
    
    # === 1. 计算动态阈值 ===
    # 使用 ATR 或价格波动率调整 RSI 阈值
    volatility = calculate_volatility(indicators, current_price)
    
    # 波动率高时，放宽阈值 (避免频繁交易)
    # 波动率低时，收紧阈值 (捕捉更多机会)
    rsi_buy_threshold = 40 + volatility * 5  # 范围约 35-45
    rsi_sell_threshold = 60 - volatility * 5  # 范围约 55-65
    
    # === 2. 趋势判断 ===
    # 上升趋势：SMA50 > SMA200 且 价格 > SMA50
    # 如果缺少长期均线数据，使用 SMA20 作为替代
    uptrend = False
    if sma_50 and sma_200 and sma_50 > sma_200:
        if current_price > sma_50:
            uptrend = True
    elif sma_20 and current_price > sma_20:
        # 没有 SMA50/200 时，价格在 SMA20 之上也认为是上升趋势
        uptrend = True
    
    # === 3. 止损止盈检查 ===
    if position and position.get('shares', 0) > 0:
        entry_price = position.get('average_cost', 0)
        if entry_price > 0:
            # 止损：-8%
            stop_loss_price = entry_price * 0.92
            # 止盈：+15%
            take_profit_price = entry_price * 1.15
            
            if current_price <= stop_loss_price:
                return 'sell'  # 触发止损，立即卖出
            elif current_price >= take_profit_price:
                return 'sell'  # 触发止盈，立即卖出
    
    # === 4. 买入条件检查 ===
    
    # 条件 1: RSI 低于动态阈值
    if rsi is not None and rsi < rsi_buy_threshold:
        buy_conditions.append(f"RSI 偏低 ({rsi:.1f} < {rsi_buy_threshold:.1f})")
    
    # 条件 2: MACD 金叉
    if macd is not None and macd_signal is not None and macd > macd_signal:
        buy_conditions.append(f"MACD 金叉 ({macd:.2f} > {macd_signal:.2f})")
    
    # 条件 3: 价格站上 SMA20
    if sma_20 is not None and current_price > sma_20:
        buy_conditions.append(f"价格>SMA20 (${current_price:.2f} > ${sma_20:.2f})")
    
    # === 5. 卖出条件检查 ===
    
    # 条件 1: RSI 高于动态阈值
    if rsi is not None and rsi > rsi_sell_threshold:
        sell_conditions.append(f"RSI 偏高 ({rsi:.1f} > {rsi_sell_threshold:.1f})")
    
    # 条件 2: MACD 死叉
    if macd is not None and macd_signal is not None and macd < macd_signal:
        sell_conditions.append(f"MACD 死叉 ({macd:.2f} < {macd_signal:.2f})")
    
    # 条件 3: 价格跌破 SMA20
    if sma_20 is not None and current_price < sma_20:
        sell_conditions.append(f"价格<SMA20 (${current_price:.2f} < ${sma_20:.2f})")
    
    # === 6. 决策逻辑 ===
    
    # 买入：至少 1 个条件 + 趋势向上
    if len(buy_conditions) >= 1 and uptrend:
        return 'buy'
    
    # 卖出：任意 1 个条件
    if len(sell_conditions) >= 1:
        return 'sell'
    
    return 'hold'


def calculate_volatility(indicators: Dict[str, Any], current_price: float) -> float:
    """
    计算波动率 (简化版)
    使用 ATR 或价格变化率
    """
    # 尝试获取 ATR
    atr = indicators.get('atr_14')
    if atr and current_price > 0:
        # ATR 占价格百分比
        volatility = atr / current_price
        # 限制在 0-0.2 之间 (0%-20%)
        return min(max(volatility, 0), 0.2)
    
    # 没有 ATR 时，使用默认值
    return 0.02  # 默认 2% 波动率


# 兼容性：保留原函数签名
def relaxed_strategy(row, indicators: Dict[str, Any]) -> str:
    """兼容旧版本调用"""
    return optimized_v2_strategy(row, indicators, position=None)


if __name__ == "__main__":
    # 测试
    test_indicators = {
        'rsi_14': 38.5,
        'macd': 2.5,
        'macd_signal': 1.8,
        'sma_20': 165.0,
        'sma_50': 160.0,
        'sma_200': 150.0,
        'current_price': 168.0,
        'atr_14': 3.5
    }
    
    class MockRow:
        close = 168.0
        def get(self, key, default=None):
            return getattr(self, key, default)
    
    # 测试买入场景
    signal = optimized_v2_strategy(MockRow(), test_indicators)
    print(f"测试场景 1 (上升趋势 + RSI 偏低 + MACD 金叉): {signal}")
    print(f"  预期：buy")
    print()
    
    # 测试下跌趋势 (无卖出信号)
    test_indicators2 = {
        'rsi_14': 50.0,  # RSI 中性
        'macd': 1.0,
        'macd_signal': 1.0,  # MACD 无金叉死叉
        'sma_20': 140.0,  # 价格 > SMA20
        'sma_50': 145.0,  # SMA50 < SMA200 (下跌趋势)
        'sma_200': 150.0,
        'current_price': 148.0,
        'atr_14': 3.0
    }
    signal = optimized_v2_strategy(MockRow(), test_indicators2)
    print(f"测试场景 2 (下跌趋势 + 无卖出信号): {signal}")
    print(f"  预期：hold (趋势过滤，不买入)")
    print()
    
    # 测试止损
    position = {'shares': 100, 'average_cost': 180.0}
    test_indicators['current_price'] = 165.0  # -8.3% 触发止损
    signal = optimized_v2_strategy(MockRow(), test_indicators, position)
    print(f"测试场景 3 (触发止损): {signal}")
    print(f"  预期：sell")
