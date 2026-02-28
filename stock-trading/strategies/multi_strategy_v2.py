"""
多策略框架 V2
修复版：添加数据完整性检查，确保指标有效后再交易
"""
from typing import Dict, Any, Tuple
from datetime import datetime


def has_complete_indicators(indicators: Dict[str, Any]) -> bool:
    """
    检查指标数据是否完整
    
    需要至少 50 天数据才能计算 SMA50
    """
    required_fields = ['current_price', 'sma_20', 'sma_50']
    
    for field in required_fields:
        value = indicators.get(field)
        if value is None or (isinstance(value, float) and str(value) == 'nan'):
            return False
    
    return True


def trend_following_strategy_v2(row, indicators: Dict[str, Any]) -> str:
    """
    趋势跟踪策略 V2
    添加数据完整性检查
    """
    # 检查数据完整性
    if not has_complete_indicators(indicators):
        return 'hold'  # 数据不全，保持观望
    
    buy_conditions = []
    sell_conditions = []
    
    price = indicators.get('current_price', row.get('close', 0))
    sma_20 = indicators.get('sma_20')
    sma_50 = indicators.get('sma_50')
    sma_200 = indicators.get('sma_200')
    rsi = indicators.get('rsi_14')
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    
    # 趋势判断
    strong_uptrend = (sma_50 and sma_200 and 
                      sma_50 > sma_200 and 
                      price > sma_50)
    
    # 买入条件
    if strong_uptrend:
        if rsi and 30 <= rsi <= 65:
            buy_conditions.append(f"RSI 适中 ({rsi:.1f})")
        
        if macd and macd_signal and macd > macd_signal:
            buy_conditions.append("MACD 金叉")
        elif macd and macd > 0:
            buy_conditions.append("MACD 为正")
        
        if sma_20 and price > sma_20:
            buy_conditions.append("价格>SMA20")
    
    # 卖出条件
    if sma_50 and sma_200 and sma_50 < sma_200:
        sell_conditions.append("趋势反转")
    
    if sma_50 and price < sma_50:
        sell_conditions.append("价格跌破 SMA50")
    
    if rsi and rsi > 70:
        sell_conditions.append(f"RSI 超买 ({rsi:.1f})")
    
    # 决策
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def mean_reversion_strategy_v2(row, indicators: Dict[str, Any]) -> str:
    """均值回归策略 V2"""
    if not has_complete_indicators(indicators):
        return 'hold'
    
    buy_conditions = []
    sell_conditions = []
    
    price = indicators.get('current_price', row.get('close', 0))
    sma_20 = indicators.get('sma_20')
    rsi = indicators.get('rsi_14')
    
    # 买入 (超卖)
    if rsi and rsi < 30:
        buy_conditions.append(f"RSI 超卖 ({rsi:.1f})")
    
    if sma_20 and price < sma_20 * 0.95:
        buy_conditions.append("价格低于 SMA20")
    
    # 卖出 (超买)
    if rsi and rsi > 70:
        sell_conditions.append(f"RSI 超买 ({rsi:.1f})")
    
    if sma_20 and price > sma_20 * 1.05:
        sell_conditions.append("价格高于 SMA20")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def breakout_strategy_v2(row, indicators: Dict[str, Any]) -> str:
    """突破策略 V2"""
    if not has_complete_indicators(indicators):
        return 'hold'
    
    buy_conditions = []
    sell_conditions = []
    
    price = indicators.get('current_price', row.get('close', 0))
    sma_50 = indicators.get('sma_50')
    rsi = indicators.get('rsi_14')
    volume = indicators.get('volume', 0)
    avg_volume = indicators.get('avg_volume_20', 0)
    
    # 买入 (突破)
    if sma_50 and price > sma_50 * 1.05:
        buy_conditions.append("突破 SMA50")
        
        if avg_volume and volume > avg_volume * 1.5:
            buy_conditions.append("成交量放大")
    
    if rsi and rsi > 60:
        buy_conditions.append("RSI 强势")
    
    # 卖出
    if sma_50 and price < sma_50 * 0.95:
        sell_conditions.append("跌破 SMA50")
    
    if rsi and rsi < 40:
        sell_conditions.append("RSI 走弱")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def defensive_strategy_v2(row, indicators: Dict[str, Any]) -> str:
    """防守策略 V2"""
    if not has_complete_indicators(indicators):
        return 'hold'
    
    buy_conditions = []
    sell_conditions = []
    
    price = indicators.get('current_price', row.get('close', 0))
    sma_50 = indicators.get('sma_50')
    sma_200 = indicators.get('sma_200')
    rsi = indicators.get('rsi_14')
    
    # 下跌趋势判断
    downtrend = (sma_50 and sma_200 and 
                 sma_50 < sma_200 and 
                 price < sma_50)
    
    if downtrend:
        # 只在极度超卖时短线买入
        if rsi and rsi < 25:
            buy_conditions.append(f"极度超卖 (RSI={rsi:.1f})")
        
        # 快速卖出
        sma_20 = indicators.get('sma_20')
        if sma_20 and price > sma_20:
            sell_conditions.append("反弹到 SMA20")
        
        if rsi and rsi > 50:
            sell_conditions.append("RSI 回到中性")
    else:
        return 'hold'  # 不是下跌趋势，观望
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def identify_market_regime_v2(indicators: Dict[str, Any]) -> str:
    """市场状态识别 V2"""
    price = indicators.get('current_price', 0)
    sma_20 = indicators.get('sma_20', 0)
    sma_50 = indicators.get('sma_50', 0)
    sma_200 = indicators.get('sma_200', 0)
    atr = indicators.get('atr_14', 0)
    rsi = indicators.get('rsi_14', 50)
    
    volatility = atr / price if price > 0 and atr else 0.02
    
    # 优先使用 SMA50/SMA200
    if sma_50 and sma_200:
        if sma_50 > sma_200 and price > sma_50:
            return 'VOLATILE_BULL' if volatility >= 0.03 else 'BULL_MARK'
        elif sma_50 < sma_200 and price < sma_50:
            return 'BEAR_MARK'
        else:
            return 'RANGING'
    # 回退到 SMA20
    elif sma_20:
        if price > sma_20 * 1.05:
            return 'BULL_MARK'
        elif price < sma_20 * 0.95:
            return 'BEAR_MARK'
        else:
            return 'RANGING'
    # 最后回退到 RSI
    elif rsi:
        if rsi > 60:
            return 'BULL_MARK'
        elif rsi < 40:
            return 'BEAR_MARK'
        else:
            return 'RANGING'
    else:
        return 'RANGING'


class MultiStrategyCoordinatorV2:
    """多策略协调器 V2"""
    
    def __init__(self):
        self.strategies = {
            'trend_following': trend_following_strategy_v2,
            'mean_reversion': mean_reversion_strategy_v2,
            'breakout': breakout_strategy_v2,
            'defensive': defensive_strategy_v2
        }
    
    def select_strategy(self, symbol: str, market_regime: str, stock_type: str) -> str:
        """选择策略"""
        matrix = {
            ('BULL_MARK', 'TRENDING'): 'trend_following',
            ('BULL_MARK', 'VOLATILE'): 'breakout',
            ('RANGING', 'RANGING'): 'mean_reversion',
            ('RANGING', 'TRENDING'): 'trend_following',
            ('BEAR_MARK', 'DECLINING'): 'defensive',
            ('BEAR_MARK', 'TRENDING'): 'defensive',
            ('VOLATILE_BULL', 'VOLATILE'): 'breakout',
        }
        return matrix.get((market_regime, stock_type), 'trend_following')
    
    def execute(self, symbol: str, row, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """执行多策略决策"""
        # 1. 识别市场状态
        market_regime = identify_market_regime_v2(indicators)
        
        # 2. 分类股票特性
        stock_profiles = {
            'GOOGL': 'TRENDING', 'AAPL': 'TRENDING', 'MSFT': 'TRENDING',
            'META': 'RANGING', 'AMZN': 'RANGING',
            'NVDA': 'VOLATILE', 'AMD': 'VOLATILE', 'INTC': 'VOLATILE', 'TSLA': 'VOLATILE',
            'NFLX': 'DECLINING'
        }
        stock_type = stock_profiles.get(symbol.upper(), 'RANGING')
        
        # 3. 选择策略
        strategy_name = self.select_strategy(symbol, market_regime, stock_type)
        strategy_func = self.strategies.get(strategy_name, trend_following_strategy_v2)
        
        # 4. 执行策略
        action = strategy_func(row, indicators)
        
        # 5. 计算置信度
        confidence = 0.8 if action != 'hold' else 0.5
        
        # 6. 生成理由
        reasoning = f"{symbol}: {market_regime} + {stock_type} → {strategy_name} → {action}"
        
        return {
            'action': action,
            'strategy_used': strategy_name,
            'market_regime': market_regime,
            'stock_type': stock_type,
            'confidence': confidence,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }


# 测试
if __name__ == "__main__":
    print("="*70)
    print("🎯 多策略框架 V2 - 测试")
    print("="*70)
    
    coordinator = MultiStrategyCoordinatorV2()
    
    # 测试数据 (完整指标)
    test_indicators = {
        'current_price': 175.0,
        'sma_20': 170.0,
        'sma_50': 165.0,
        'sma_200': 155.0,
        'rsi_14': 45.0,
        'macd': 2.5,
        'macd_signal': 1.8,
        'atr_14': 3.5,
        'volume': 1000000,
        'avg_volume_20': 800000
    }
    
    # 测试数据 (不完整指标)
    incomplete_indicators = {
        'current_price': 170.0,
        'sma_20': 168.0,
        'sma_50': None,  # 数据不全
        'sma_200': None,
        'rsi_14': 50.0
    }
    
    class MockRow:
        close = 175.0
        def get(self, key, default=None):
            return getattr(self, key, default)
    
    print("\n【测试 1】完整指标数据")
    result = coordinator.execute('GOOGL', MockRow(), test_indicators)
    print(f"  决策：{result['action']}")
    print(f"  策略：{result['strategy_used']}")
    print(f"  市场：{result['market_regime']}")
    
    print("\n【测试 2】不完整指标数据")
    result = coordinator.execute('GOOGL', MockRow(), incomplete_indicators)
    print(f"  决策：{result['action']}")
    print(f"  策略：{result['strategy_used']}")
    print(f"  市场：{result['market_regime']}")
    
    print("\n✅ 多策略框架 V2 测试完成！")
