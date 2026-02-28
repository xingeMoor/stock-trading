"""
自适应策略 V4 (优化版)
改进：放宽均值回归/防守策略触发条件 + 添加止盈逻辑
"""
from typing import Dict, Any
from datetime import datetime


# 扩展股票池 - 20 只股票
STOCK_STRATEGY_MAP = {
    # 原 10 只
    'GOOGL': 'trend_following',
    'AAPL': 'trend_following',
    'MSFT': 'trend_following',
    'META': 'mean_reversion',
    'AMZN': 'mean_reversion',
    'NVDA': 'breakout',
    'AMD': 'breakout',
    'TSLA': 'breakout',
    'INTC': 'breakout',
    'NFLX': 'defensive',
    # 新增 10 只
    'AVGO': 'trend_following',  # 博通 - 趋势型
    'ORCL': 'trend_following',  # 甲骨文 - 趋势型
    'CRM': 'trend_following',   # Salesforce - 趋势型
    'QCOM': 'breakout',         # 高通 - 波动型
    'TXN': 'mean_reversion',    # 德州仪器 - 震荡型
    'MU': 'breakout',           # 美光 - 波动型
    'AMAT': 'breakout',         # 应用材料 - 波动型
    'LRCX': 'breakout',         # 拉姆研究 - 波动型
    'KLAC': 'breakout',         # 科磊 - 波动型
    'SNPS': 'trend_following'   # 新思科技 - 趋势型
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
    if price > sma_20 * 0.95:  # 放宽到 95%
        return True
    if rsi > 45:  # 放宽到 45
        return True
    
    return False


def trend_following_v4(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """趋势跟踪策略 V4 - 添加止盈"""
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
    
    # 卖出条件 (添加止盈)
    if sma_50 and price < sma_50 * 0.97:  # 跌破 SMA50 3%
        sell_conditions.append("趋势转弱")
    
    if rsi and rsi > 75:  # 提高止盈阈值
        sell_conditions.append(f"RSI 超买 ({rsi:.1f}) - 止盈")
    
    # 止盈逻辑：从高点回撤 10%
    # (实际实现需要持仓成本数据，这里简化)
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def mean_reversion_v4(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """均值回归策略 V4 - 放宽触发条件"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_20 = indicators.get('sma_20')
    rsi = indicators.get('rsi_14')
    
    buy_conditions = []
    sell_conditions = []
    
    # 放宽买入条件 (RSI 40/60 → 45/55)
    if rsi and rsi < 45:
        buy_conditions.append(f"RSI 偏低 ({rsi:.1f})")
    
    if sma_20 and price < sma_20 * 0.99:  # 接近 SMA20 即可
        buy_conditions.append("价格接近 SMA20")
    
    if rsi and rsi > 55:  # 降低止盈阈值
        sell_conditions.append(f"RSI 偏高 ({rsi:.1f}) - 止盈")
    
    if sma_20 and price > sma_20 * 1.01:  # 高于 SMA20 1%
        sell_conditions.append("价格高于 SMA20 - 止盈")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def breakout_v4(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """突破策略 V4 - 添加止盈"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_50 = indicators.get('sma_50')
    rsi = indicators.get('rsi_14')
    
    buy_conditions = []
    sell_conditions = []
    
    # 买入条件
    if sma_50 and price > sma_50:
        buy_conditions.append("价格>SMA50")
    
    if rsi and rsi > 50:
        buy_conditions.append("RSI 强势")
    
    # 卖出条件 (添加止盈)
    if sma_50 and price < sma_50 * 0.95:
        sell_conditions.append("跌破 SMA50 - 止损")
    
    if rsi and rsi > 80:  # RSI 超买止盈
        sell_conditions.append(f"RSI 超买 ({rsi:.1f}) - 止盈")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


def defensive_v4(row, indicators: Dict[str, Any], symbol: str = 'UNKNOWN') -> str:
    """防守策略 V4 - 放宽触发条件"""
    price = indicators.get('current_price', row.get('close', 0))
    sma_50 = indicators.get('sma_50')
    sma_200 = indicators.get('sma_200')
    rsi = indicators.get('rsi_14')
    
    buy_conditions = []
    sell_conditions = []
    
    # 放宽买入条件 (RSI 35 → 40)
    if rsi and rsi < 40:
        buy_conditions.append(f"超卖 (RSI={rsi:.1f})")
    
    # 放宽卖出条件
    if sma_50 and sma_200 and sma_50 < sma_200:
        if rsi and rsi > 45:  # 降低阈值
            sell_conditions.append("RSI 回到中性 - 止盈")
    
    # 价格反弹止盈
    sma_20 = indicators.get('sma_20')
    if sma_20 and price > sma_20 * 1.02:
        sell_conditions.append("价格反弹 - 止盈")
    
    if len(buy_conditions) >= 1:
        return 'buy'
    elif len(sell_conditions) >= 1:
        return 'sell'
    else:
        return 'hold'


class AdaptiveStrategyCoordinatorV4:
    """自适应策略协调器 V4"""
    
    def __init__(self):
        self.strategies = {
            'trend_following': trend_following_v4,
            'mean_reversion': mean_reversion_v4,
            'breakout': breakout_v4,
            'defensive': defensive_v4
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
        strategy_func = self.strategies.get(strategy_name, trend_following_v4)
        
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


def adaptive_strategy_v4(row, indicators: Dict[str, Any], symbol: str) -> str:
    """统一接口 (供 backtest 调用)"""
    coordinator = AdaptiveStrategyCoordinatorV4()
    result = coordinator.execute(symbol, row, indicators)
    return result['action']


# 测试
if __name__ == "__main__":
    print("="*70)
    print("🎯 自适应策略 V4 (优化版) - 20 只股票测试")
    print("="*70)
    
    coordinator = AdaptiveStrategyCoordinatorV4()
    
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
    
    # 测试 20 只股票
    test_stocks = list(STOCK_STRATEGY_MAP.keys())
    
    print(f"\n测试 {len(test_stocks)} 只股票:\n")
    
    for symbol in test_stocks:
        result = coordinator.execute(symbol, MockRow(), test_indicators)
        status = "✅" if result['action'] != 'hold' else "⏸️"
        print(f"{status} {symbol:6}: {result['action']:4} ({result['strategy_used']:15})")
    
    print(f"\n✅ 自适应策略 V4 (优化版) 测试完成！")
