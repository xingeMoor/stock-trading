"""
Technical Factors Module
技术因子计算模块

提供各类技术指标因子的计算功能:
- 趋势类: SMA, EMA, MACD, ADX
- 动量类: RSI, Williams %R, CCI
- 波动类: Bollinger Bands, ATR
- 成交量类: OBV, VWAP
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


class TechnicalFactors:
    """技术因子计算器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化技术因子计算器
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame，列名应为 ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        self._validate_data()
    
    def _validate_data(self):
        """验证数据完整性"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in self.df.columns]
        if missing:
            raise ValueError(f"缺少必要的列：{missing}")
    
    # ==================== 趋势类因子 ====================
    
    def sma(self, period: int = 20) -> pd.Series:
        """
        简单移动平均 (Simple Moving Average)
        
        Args:
            period: 计算周期
            
        Returns:
            SMA 序列
        """
        return self.df['close'].rolling(window=period).mean()
    
    def ema(self, period: int = 20) -> pd.Series:
        """
        指数移动平均 (Exponential Moving Average)
        
        Args:
            period: 计算周期
            
        Returns:
            EMA 序列
        """
        return self.df['close'].ewm(span=period, adjust=False).mean()
    
    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """
        MACD 指标 (Moving Average Convergence Divergence)
        
        Args:
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            包含 MACD 线、信号线、柱状图的字典
        """
        ema_fast = self.df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df['close'].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def adx(self, period: int = 14) -> pd.Series:
        """
        平均趋向指标 (Average Directional Index)
        
        Args:
            period: 计算周期
            
        Returns:
            ADX 序列
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        # 计算真实波幅 TR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # 计算 +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # 计算 +DI 和 -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # 计算 DX 和 ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    # ==================== 动量类因子 ====================
    
    def rsi(self, period: int = 14) -> pd.Series:
        """
        相对强弱指标 (Relative Strength Index)
        
        Args:
            period: 计算周期
            
        Returns:
            RSI 序列
        """
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def williams_r(self, period: int = 14) -> pd.Series:
        """
        威廉指标 (Williams %R)
        
        Args:
            period: 计算周期
            
        Returns:
            Williams %R 序列
        """
        highest_high = self.df['high'].rolling(window=period).max()
        lowest_low = self.df['low'].rolling(window=period).min()
        
        wr = -100 * (highest_high - self.df['close']) / (highest_high - lowest_low)
        
        return wr
    
    def cci(self, period: int = 20) -> pd.Series:
        """
        商品通道指标 (Commodity Channel Index)
        
        Args:
            period: 计算周期
            
        Returns:
            CCI 序列
        """
        tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (tp - sma_tp) / (0.015 * mad)
        
        return cci
    
    # ==================== 波动类因子 ====================
    
    def bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """
        布林带 (Bollinger Bands)
        
        Args:
            period: 计算周期
            std_dev: 标准差倍数
            
        Returns:
            包含上轨、中轨、下轨的字典
        """
        middle = self.df['close'].rolling(window=period).mean()
        std = self.df['close'].rolling(window=period).std()
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'bandwidth': (upper - lower) / middle,  # 带宽
            'percent_b': (self.df['close'] - lower) / (upper - lower)  # %B 指标
        }
    
    def atr(self, period: int = 14) -> pd.Series:
        """
        平均真实波幅 (Average True Range)
        
        Args:
            period: 计算周期
            
        Returns:
            ATR 序列
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    # ==================== 成交量类因子 ====================
    
    def obv(self) -> pd.Series:
        """
        能量潮指标 (On-Balance Volume)
        
        Returns:
            OBV 序列
        """
        obv = [0]
        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.append(obv[-1] + self.df['volume'].iloc[i])
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.append(obv[-1] - self.df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=self.df.index)
    
    def vwap(self) -> pd.Series:
        """
        成交量加权平均价 (Volume Weighted Average Price)
        
        Returns:
            VWAP 序列
        """
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        vwap = (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()
        
        return vwap
    
    def volume_ratio(self, period: int = 20) -> pd.Series:
        """
        成交量比率 (当前成交量 / 平均成交量)
        
        Args:
            period: 计算周期
            
        Returns:
            成交量比率序列
        """
        avg_volume = self.df['volume'].rolling(window=period).mean()
        volume_ratio = self.df['volume'] / avg_volume
        
        return volume_ratio
    
    # ==================== 综合因子计算 ====================
    
    def calculate_all_trend_factors(self) -> pd.DataFrame:
        """计算所有趋势类因子"""
        factors = pd.DataFrame(index=self.df.index)
        factors['sma_20'] = self.sma(20)
        factors['sma_60'] = self.sma(60)
        factors['ema_12'] = self.ema(12)
        factors['ema_26'] = self.ema(26)
        
        macd_result = self.macd()
        factors['macd'] = macd_result['macd']
        factors['macd_signal'] = macd_result['signal']
        factors['macd_hist'] = macd_result['histogram']
        
        factors['adx_14'] = self.adx(14)
        
        return factors
    
    def calculate_all_momentum_factors(self) -> pd.DataFrame:
        """计算所有动量类因子"""
        factors = pd.DataFrame(index=self.df.index)
        factors['rsi_14'] = self.rsi(14)
        factors['williams_r_14'] = self.williams_r(14)
        factors['cci_20'] = self.cci(20)
        
        return factors
    
    def calculate_all_volatility_factors(self) -> pd.DataFrame:
        """计算所有波动类因子"""
        factors = pd.DataFrame(index=self.df.index)
        
        bb = self.bollinger_bands()
        factors['bb_upper'] = bb['upper']
        factors['bb_middle'] = bb['middle']
        factors['bb_lower'] = bb['lower']
        factors['bb_bandwidth'] = bb['bandwidth']
        factors['bb_percent_b'] = bb['percent_b']
        
        factors['atr_14'] = self.atr(14)
        
        return factors
    
    def calculate_all_volume_factors(self) -> pd.DataFrame:
        """计算所有成交量类因子"""
        factors = pd.DataFrame(index=self.df.index)
        factors['obv'] = self.obv()
        factors['vwap'] = self.vwap()
        factors['volume_ratio'] = self.volume_ratio(20)
        
        return factors
    
    def calculate_all_factors(self) -> pd.DataFrame:
        """计算所有技术因子"""
        trend = self.calculate_all_trend_factors()
        momentum = self.calculate_all_momentum_factors()
        volatility = self.calculate_all_volatility_factors()
        volume = self.calculate_all_volume_factors()
        
        all_factors = pd.concat([trend, momentum, volatility, volume], axis=1)
        
        return all_factors


# 使用示例
if __name__ == "__main__":
    # 示例数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(100)),
        'high': 100 + np.cumsum(np.random.randn(100)) + np.abs(np.random.randn(100)),
        'low': 100 + np.cumsum(np.random.randn(100)) - np.abs(np.random.randn(100)),
        'close': 100 + np.cumsum(np.random.randn(100)),
        'volume': 1000000 + np.random.randint(-100000, 100000, 100)
    }, index=dates)
    
    # 创建计算器
    tf = TechnicalFactors(df)
    
    # 计算单个因子
    rsi = tf.rsi(14)
    print("RSI(14) 最后 5 个值:")
    print(rsi.tail())
    
    # 计算所有因子
    all_factors = tf.calculate_all_factors()
    print("\n所有技术因子 (最后 5 行):")
    print(all_factors.tail())
