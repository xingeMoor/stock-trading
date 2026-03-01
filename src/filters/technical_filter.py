"""
第四层：技术面筛选器
Technical Filter - Trend, Breakout, Technical Indicators

筛选标准：
- 趋势：均线系统判断趋势方向
- 突破：价格突破和成交量确认
- 技术指标：RSI、MACD 等
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import yaml
from pathlib import Path


class TechnicalFilter:
    """技术面筛选器 - 第四层漏斗"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化技术面筛选器
        
        Args:
            config: 筛选配置字典
        """
        self.config = config or self._load_default_config()
        
    def _load_default_config(self) -> Dict:
        """加载默认配置文件"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'screener_config.yaml'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)
                return full_config.get('technical_filters', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'trend': {
                'enabled': True,
                'ma_20_above': True,
                'ma_50_above': True,
                'ma_200_above': False
            },
            'breakout': {
                'enabled': True,
                'price_vs_52w_high_percent': 15.0,
                'volume_spike_ratio': 1.5
            },
            'indicators': {
                'rsi': {
                    'enabled': True,
                    'min': 40.0,
                    'max': 80.0
                },
                'macd': {
                    'enabled': False
                }
            }
        }
    
    def filter_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        趋势筛选 - 均线系统
        
        Args:
            df: 股票数据 DataFrame，需包含价格均线列
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('trend', {}).get('enabled', True):
            return df
        
        trend_config = self.config['trend']
        mask = pd.Series(True, index=df.index)
        
        # MA20 筛选
        if trend_config.get('ma_20_above', True):
            if 'ma_20' in df.columns and 'price' in df.columns:
                mask &= df['price'] > df['ma_20']
            elif 'close' in df.columns and 'ma_20' in df.columns:
                mask &= df['close'] > df['ma_20']
        
        # MA50 筛选
        if trend_config.get('ma_50_above', True):
            if 'ma_50' in df.columns and 'price' in df.columns:
                mask &= df['price'] > df['ma_50']
            elif 'close' in df.columns and 'ma_50' in df.columns:
                mask &= df['close'] > df['ma_50']
        
        # MA200 筛选（可选）
        if trend_config.get('ma_200_above', False):
            if 'ma_200' in df.columns and 'price' in df.columns:
                mask &= df['price'] > df['ma_200']
            elif 'close' in df.columns and 'ma_200' in df.columns:
                mask &= df['close'] > df['ma_200']
        
        return df[mask].copy()
    
    def filter_breakout(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        突破筛选 - 价格和成交量
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('breakout', {}).get('enabled', True):
            return df
        
        breakout_config = self.config['breakout']
        mask = pd.Series(True, index=df.index)
        
        # 距离 52 周高点的距离
        high_threshold = breakout_config.get('price_vs_52w_high_percent', 15.0)
        if 'high_52w' in df.columns and 'price' in df.columns:
            # 当前价格应在 52 周高点的 threshold% 以内
            distance_percent = (df['high_52w'] - df['price']) / df['high_52w'] * 100
            mask &= distance_percent <= high_threshold
        elif 'high_52w' in df.columns and 'close' in df.columns:
            distance_percent = (df['high_52w'] - df['close']) / df['high_52w'] * 100
            mask &= distance_percent <= high_threshold
        
        # 成交量放大
        volume_ratio = breakout_config.get('volume_spike_ratio', 1.5)
        if 'volume' in df.columns and 'avg_volume_30d' in df.columns:
            mask &= df['volume'] >= (df['avg_volume_30d'] * volume_ratio)
        
        return df[mask].copy()
    
    def filter_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        RSI 指标筛选
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            筛选后的 DataFrame
        """
        rsi_config = self.config.get('indicators', {}).get('rsi', {})
        if not rsi_config.get('enabled', True):
            return df
        
        if 'rsi' not in df.columns:
            return df
        
        min_rsi = rsi_config.get('min', 40.0)
        max_rsi = rsi_config.get('max', 80.0)
        
        mask = (df['rsi'] >= min_rsi) & (df['rsi'] <= max_rsi)
        
        return df[mask].copy()
    
    def filter_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        MACD 指标筛选（金叉）
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            筛选后的 DataFrame
        """
        macd_config = self.config.get('indicators', {}).get('macd', {})
        if not macd_config.get('enabled', False):
            return df
        
        # MACD 金叉：MACD 线从下向上穿过信号线
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            # 当前 MACD > 信号线，且之前 MACD < 信号线（金叉）
            mask = (df['macd'] > df['macd_signal'])
            return df[mask].copy()
        
        return df
    
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用所有技术面筛选
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            通过技术面筛选的 DataFrame
        """
        if df.empty:
            return df
            
        # 按顺序应用筛选
        df = self.filter_trend(df)
        if df.empty:
            return df
            
        df = self.filter_breakout(df)
        if df.empty:
            return df
            
        df = self.filter_rsi(df)
        if df.empty:
            return df
            
        df = self.filter_macd(df)
        
        return df
    
    def get_filter_stats(self, original_df: pd.DataFrame, filtered_df: pd.DataFrame) -> Dict:
        """
        获取筛选统计信息
        
        Args:
            original_df: 原始数据
            filtered_df: 筛选后数据
            
        Returns:
            统计信息字典
        """
        return {
            'filter_name': 'Technical Filter',
            'original_count': len(original_df),
            'filtered_count': len(filtered_df),
            'removed_count': len(original_df) - len(filtered_df),
            'pass_rate': len(filtered_df) / len(original_df) * 100 if len(original_df) > 0 else 0
        }
