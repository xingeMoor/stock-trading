"""
默认交易策略
基于多指标确认的经典策略模板
"""
from typing import Dict, Any, Callable


def default_strategy(row: Any, indicators: Dict[str, Any]) -> str:
    """
    默认策略：多指标确认
    
    买入条件 (至少 2 个满足):
    - RSI < 30 (超卖)
    - MACD 金叉 (MACD > Signal)
    - 价格站上 SMA20
    
    卖出条件 (至少 2 个满足):
    - RSI > 70 (超买)
    - MACD 死叉 (MACD < Signal)
    - 价格跌破 SMA20
    
    Returns:
        'buy' / 'sell' / 'hold'
    """
    buy_conditions = []
    sell_conditions = []
    
    # === 技术指标判断 ===
    
    # 1. RSI
    rsi = indicators.get('rsi_14')
    if rsi is not None:
        if rsi < 30:
            buy_conditions.append(f"RSI 超卖 ({rsi:.1f})")
        elif rsi > 70:
            sell_conditions.append(f"RSI 超买 ({rsi:.1f})")
    
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
            buy_conditions.append(f"价格站上 SMA20 (${current_price:.2f} > ${sma_20:.2f})")
        elif current_price < sma_20:
            sell_conditions.append(f"价格跌破 SMA20 (${current_price:.2f} < ${sma_20:.2f})")
    
    # 4. 随机指标 (Stochastic)
    stoch_k = indicators.get('stoch_k')
    stoch_d = indicators.get('stoch_d')
    if stoch_k is not None and stoch_d is not None:
        if stoch_k < 20 and stoch_k > stoch_d:
            buy_conditions.append(f"Stochastic 超卖金叉 (K:{stoch_k:.1f} > D:{stoch_d:.1f})")
        elif stoch_k > 80 and stoch_k < stoch_d:
            sell_conditions.append(f"Stochastic 超买死叉 (K:{stoch_k:.1f} < D:{stoch_d:.1f})")
    
    # 5. CCI
    cci = indicators.get('cci')
    if cci is not None:
        if cci < -100:
            buy_conditions.append(f"CCI 超卖 ({cci:.1f})")
        elif cci > 100:
            sell_conditions.append(f"CCI 超买 ({cci:.1f})")
    
    # === 舆情情绪判断 (可选增强) ===
    sentiment_score = indicators.get('sentiment_score')
    if sentiment_score is not None:
        if sentiment_score > 0.5:
            buy_conditions.append(f"正面舆情 ({sentiment_score:.2f})")
        elif sentiment_score < -0.5:
            sell_conditions.append(f"负面舆情 ({sentiment_score:.2f})")
    
    # === 决策逻辑 ===
    
    # 买入：至少 2 个买入条件，且没有卖出条件
    if len(buy_conditions) >= 2 and len(sell_conditions) == 0:
        return 'buy'
    
    # 卖出：至少 2 个卖出条件，或者 1 个卖出条件 + 当前持仓
    if len(sell_conditions) >= 2:
        return 'sell'
    if len(sell_conditions) == 1 and len(buy_conditions) == 0:
        return 'sell'
    
    # 默认持有
    return 'hold'


def create_custom_strategy(config: Dict[str, Any]) -> Callable:
    """
    创建自定义策略
    
    Args:
        config: 策略配置
            {
                "rsi_buy_threshold": 30,
                "rsi_sell_threshold": 70,
                "use_macd": True,
                "use_sma": True,
                "use_sentiment": False,
                "min_buy_conditions": 2,
                "min_sell_conditions": 2
            }
    
    Returns:
        策略函数
    """
    def custom_strategy(row: Any, indicators: Dict[str, Any]) -> str:
        buy_conditions = []
        sell_conditions = []
        
        # RSI
        if config.get('use_rsi', True):
            rsi = indicators.get('rsi_14')
            rsi_buy = config.get('rsi_buy_threshold', 30)
            rsi_sell = config.get('rsi_sell_threshold', 70)
            if rsi is not None:
                if rsi < rsi_buy:
                    buy_conditions.append(f"RSI<{rsi_buy}")
                elif rsi > rsi_sell:
                    sell_conditions.append(f"RSI>{rsi_sell}")
        
        # MACD
        if config.get('use_macd', True):
            macd = indicators.get('macd')
            signal = indicators.get('macd_signal')
            if macd is not None and signal is not None:
                if macd > signal:
                    buy_conditions.append("MACD 金叉")
                elif macd < signal:
                    sell_conditions.append("MACD 死叉")
        
        # SMA
        if config.get('use_sma', True):
            sma_20 = indicators.get('sma_20')
            current_price = indicators.get('current_price', row.get('close', 0))
            if sma_20 is not None and current_price > 0:
                if current_price > sma_20:
                    buy_conditions.append("价格>SMA20")
                elif current_price < sma_20:
                    sell_conditions.append("价格<SMA20")
        
        #  sentiment
        if config.get('use_sentiment', False):
            sentiment = indicators.get('sentiment_score')
            if sentiment is not None:
                if sentiment > 0.5:
                    buy_conditions.append(f"正面舆情 ({sentiment:.2f})")
                elif sentiment < -0.5:
                    sell_conditions.append(f"负面舆情 ({sentiment:.2f})")
        
        # 决策
        min_buy = config.get('min_buy_conditions', 2)
        min_sell = config.get('min_sell_conditions', 2)
        
        if len(buy_conditions) >= min_buy:
            return 'buy'
        elif len(sell_conditions) >= min_sell:
            return 'sell'
        else:
            return 'hold'
    
    return custom_strategy


# 策略模板：可用于 LLM 生成自定义策略
STRATEGY_TEMPLATE = """
def llm_generated_strategy(row, indicators):
    \"\"\"
    由 LLM 生成的自定义策略
    
    可用指标:
    - indicators['rsi_14']: RSI(14)
    - indicators['macd']: MACD 线
    - indicators['macd_signal']: MACD 信号线
    - indicators['sma_20']: 20 日简单移动平均
    - indicators['ema_20']: 20 日指数移动平均
    - indicators['stoch_k']: 随机指标 %K
    - indicators['stoch_d']: 随机指标 %D
    - indicators['cci']: 商品通道指标
    - indicators['adx']: 平均趋向指标
    - indicators['williams_r']: 威廉指标
    - indicators['sentiment_score']: 舆情情绪评分 (-1 到 1)
    
    K 线数据:
    - row['open'], row['high'], row['low'], row['close'], row['volume']
    
    返回值: 'buy' / 'sell' / 'hold'
    \"\"\"
    buy_conditions = []
    sell_conditions = []
    
    # TODO: 在这里添加你的交易逻辑
    
    if len(buy_conditions) >= 2:
        return 'buy'
    elif len(sell_conditions) >= 2:
        return 'sell'
    else:
        return 'hold'
"""

if __name__ == "__main__":
    # 测试默认策略
    test_indicators = {
        'rsi_14': 28.5,
        'macd': 2.02,
        'macd_signal': 0.84,
        'sma_20': 182.30,
        'current_price': 185.50,
        'stoch_k': 25.3,
        'stoch_d': 22.1,
        'cci': -110.5,
        'sentiment_score': 0.45
    }
    
    class MockRow:
        def __init__(self):
            self.close = 185.50
            self.open = 184.00
            self.high = 186.50
            self.low = 183.50
            self.volume = 50000000
        
        def get(self, key, default=None):
            return getattr(self, key, default)
    
    signal = default_strategy(MockRow(), test_indicators)
    print(f"测试信号：{signal}")
    print(f"指标: RSI={test_indicators['rsi_14']}, MACD={test_indicators['macd']}, SMA20={test_indicators['sma_20']}")
