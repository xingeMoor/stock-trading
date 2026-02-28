"""
自适应策略 V3 (最终版)
多策略框架 + 最宽松股票筛选 + 动态止损止盈
"""
from typing import Dict, Any
from datetime import datetime


# 股票 - 策略映射
STOCK_STRATEGY_MAP = {
    'GOOGL': 'trend_following',
    'AAPL': 'trend_following',
    'MSFT': 'trend_following',
    'META': 'mean_reversion',
    'AMZN': 'mean_reversion',
    'NVDA': 'breakout',
    'AMD': 'breakout',
    'TSLA': 'breakout',
    'INTC': 'breakout',
    'NFLX': 'defensive'
}


def get_stock_type(symbol: str) -> str:
    strategy = STOCK_STRATEGY_MAP.get(symbol.upper(), 'trend_following')
    type_map = {
        'trend_following': 'TRENDING',
        'mean_reversion': 'RANGING',
        'breakout': 'VOLATILE',
        'defensive': 'DECLINING'
    }
    return type_map.get(strategy, 'TRENDING')


def screen_stock(symbol: str, indicators: Dict[str, Any]) -> bool:
    """股票筛选 (最宽松版)"""
    price = indicators.get('current_price', 0)
    sma_20 = indicators.get('sma_20')
    rsi = indicators.get('rsi_14', 50)
    
    if not (price > 0 and sma_20 and sma_20 > 0):
        return False
    
    # 满足任一条件即可
    if price > sma_20:
        return True
    if rsi > 50:
        return True
    
    return False


def trend_following_v3(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """趋势跟踪策略"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_20 = indicators.get('sma_20')
    sma_50 = indicators.get('sma_50')
    rsi = indicators.get('rsi_14')
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    
    buy_conditions = []
    sell_conditions = []
    
    # 买入条件
    if sma_50 and price > sma_50:
        buy_conditions.append("价格>SMA50")
    
    if rsi and 35 <= rsi <= 65:
        buy_conditions.append(f"RSI 适中 ({rsi:.1f})")
    
    if macd and macd_signal and macd > macd_signal:
        buy_conditions.append("MACD 金叉")
    elif macd and macd > 0:
        buy_conditions.append("MACD 为正")
    
    if sma_20 and price > sma_20:
        buy_conditions.append("价格>SMA20")
    
    # 卖出条件
    if sma_50 and price < sma_50:
        sell_conditions.append("价格跌破 SMA50")
    
    if rsi and rsi > 70:
        sell_conditions.append(f"RSI 超买 ({rsi:.1f})")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def mean_reversion_v3(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """均值回归策略"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_20 = indicators.get('sma_20')
    rsi = indicators.get('rsi_14')
    
    buy_conditions = []
    sell_conditions = []
    
    if rsi and rsi < 40:
        buy_conditions.append(f"RSI 偏低 ({rsi:.1f})")
    
    if sma_20 and price < sma_20 * 0.98:
        buy_conditions.append("价格接近 SMA20")
    
    if rsi and rsi > 60:
        sell_conditions.append(f"RSI 偏高 ({rsi:.1f})")
    
    if sma_20 and price > sma_20 * 1.02:
        sell_conditions.append("价格高于 SMA20")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def breakout_v3(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """突破策略"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_50 = indicators.get('sma_50')
    rsi = indicators.get('rsi_14')
    
    buy_conditions = []
    sell_conditions = []
    
    if sma_50 and price > sma_50:
        buy_conditions.append("价格>SMA50")
    
    if rsi and rsi > 50:
        buy_conditions.append("RSI 强势")
    
    if sma_50 and price < sma_50 * 0.95:
        sell_conditions.append("价格跌破 SMA50")
    
    if rsi and rsi < 40:
        sell_conditions.append("RSI 走弱")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def defensive_v3(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """防守策略"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_50 = indicators.get('sma_50')
    sma_200 = indicators.get('sma_200')
    rsi = indicators.get('rsi_14')
    
    buy_conditions = []
    sell_conditions = []
    
    # 只在超卖时买入
    if rsi and rsi < 35:
        buy_conditions.append(f"超卖 (RSI={rsi:.1f})")
    
    # 趋势转弱时卖出
    if sma_50 and sma_200 and sma_50 < sma_200:
        if rsi and rsi > 50:
            sell_conditions.append("RSI 回到中性")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


class AdaptiveStrategyCoordinatorV3:
    """自适应策略协调器"""
    
    def __init__(self):
        self.strategies = {
            'trend_following': trend_following_v3,
            'mean_reversion': mean_reversion_v3,
            'breakout': breakout_v3,
            'defensive': defensive_v3
        }
    
    def execute(self, symbol: str, row, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """执行自适应策略"""
        if not screen_stock(symbol, indicators):
            return {
                'action': 'hold',
                'strategy_used': 'screening',
                'reason': '股票不符合筛选标准',
                'confidence': 0.9,
                'timestamp': datetime.now().isoformat()
            }
        
        stock_type = get_stock_type(symbol)
        strategy_name = STOCK_STRATEGY_MAP.get(symbol.upper(), 'trend_following')
        strategy_func = self.strategies.get(strategy_name, trend_following_v3)
        
        action = strategy_func(row, indicators, symbol)
        confidence = 0.75 if action != 'hold' else 0.5
        reasoning = f"{symbol}: {stock_type} → {strategy_name} → {action}"
        
        return {
            'action': action,
            'strategy_used': strategy_name,
            'stock_type': stock_type,
            'confidence': confidence,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }


def adaptive_strategy_v3(row, indicators: Dict[str, Any], symbol: str) -> str:
    """统一接口 (供 backtest 调用)"""
    coordinator = AdaptiveStrategyCoordinatorV3()
    result = coordinator.execute(symbol, row, indicators)
    return result['action']


if __name__ == "__main__":
    print("="*70)
    print("🎯 自适应策略 V3 (最终版) - 测试")
    print("="*70)
    
    coordinator = AdaptiveStrategyCoordinatorV3()
    
    test_indicators = {
        'current_price': 175.0,
        'sma_20': 170.0,
        'sma_50': 165.0,
        'rsi_14': 45.0,
        'macd': 2.5,
        'macd_signal': 1.8,
        'volume': 1000000
    }
    
    class MockRow:
        close = 175.0
        def get(self, key, default=None):
            return getattr(self, key, default)
    
    for symbol in ['GOOGL', 'META', 'NVDA', 'NFLX']:
        result = coordinator.execute(symbol, MockRow(), test_indicators)
        print(f"{symbol}: {result['action']} ({result['strategy_used']})")
    
    print("\n✅ 自适应策略 V3 (最终版) 测试完成！")
