"""
第三层：因子评分筛选器
Factor Scoring Filter - Momentum, Value, Quality Scoring

筛选标准：
- 动量因子：价格趋势强度
- 价值因子：估值吸引力
- 质量因子：公司基本面质量
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import yaml
from pathlib import Path


class FactorScorer:
    """因子评分筛选器 - 第三层漏斗"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化因子评分器
        
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
                return full_config.get('factor_filters', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'momentum': {
                'enabled': True,
                'weight': 0.35,
                'metrics': ['return_1m', 'return_3m', 'return_6m', 'relative_strength']
            },
            'value': {
                'enabled': True,
                'weight': 0.35,
                'metrics': ['pe_ratio', 'pb_ratio', 'ps_ratio', 'ev_ebitda']
            },
            'quality': {
                'enabled': True,
                'weight': 0.30,
                'metrics': ['roe', 'gross_margin', 'asset_turnover', 'earnings_stability']
            },
            'scoring': {
                'min_total_score': 60.0,
                'min_factor_score': 40.0
            }
        }
    
    def _normalize_score(self, series: pd.Series, ascending: bool = False) -> pd.Series:
        """
        将指标归一化为 0-100 分
        
        Args:
            series: 原始指标序列
            ascending: True 表示值越小越好（如 PE），False 表示值越大越好（如 ROE）
            
        Returns:
            归一化后的分数序列
        """
        if series.empty:
            return series
            
        # 使用百分位排名归一化
        if ascending:
            # 值越小越好（如估值指标）
            scores = 100 * (1 - series.rank(pct=True))
        else:
            # 值越大越好（如质量指标）
            scores = 100 * series.rank(pct=True)
        
        return scores.fillna(50)  # 缺失值给中间分
    
    def calculate_momentum_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算动量因子得分
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            动量得分 Series
        """
        if not self.config.get('momentum', {}).get('enabled', True):
            return pd.Series(50, index=df.index)
        
        scores = []
        metrics = self.config['momentum'].get('metrics', [])
        
        for metric in metrics:
            if metric in df.columns:
                # 收益率类指标：越大越好
                scores.append(self._normalize_score(df[metric], ascending=False))
        
        if not scores:
            return pd.Series(50, index=df.index)
        
        # 等权平均
        momentum_score = pd.DataFrame(scores).mean(axis=0)
        return momentum_score
    
    def calculate_value_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算价值因子得分
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            价值得分 Series
        """
        if not self.config.get('value', {}).get('enabled', True):
            return pd.Series(50, index=df.index)
        
        scores = []
        metrics = self.config['value'].get('metrics', [])
        
        for metric in metrics:
            if metric in df.columns:
                # 估值类指标：越小越好（PE、PB、PS 等）
                scores.append(self._normalize_score(df[metric], ascending=True))
        
        if not scores:
            return pd.Series(50, index=df.index)
        
        # 等权平均
        value_score = pd.DataFrame(scores).mean(axis=0)
        return value_score
    
    def calculate_quality_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算质量因子得分
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            质量得分 Series
        """
        if not self.config.get('quality', {}).get('enabled', True):
            return pd.Series(50, index=df.index)
        
        scores = []
        metrics = self.config['quality'].get('metrics', [])
        
        for metric in metrics:
            if metric in df.columns:
                # 质量类指标：越大越好
                scores.append(self._normalize_score(df[metric], ascending=False))
        
        if not scores:
            return pd.Series(50, index=df.index)
        
        # 等权平均
        quality_score = pd.DataFrame(scores).mean(axis=0)
        return quality_score
    
    def calculate_total_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算综合因子得分
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            包含各因子得分和总分的 DataFrame
        """
        result = df.copy()
        
        # 计算各因子得分
        result['momentum_score'] = self.calculate_momentum_score(df)
        result['value_score'] = self.calculate_value_score(df)
        result['quality_score'] = self.calculate_quality_score(df)
        
        # 获取权重
        momentum_weight = self.config.get('momentum', {}).get('weight', 0.35)
        value_weight = self.config.get('value', {}).get('weight', 0.35)
        quality_weight = self.config.get('quality', {}).get('weight', 0.30)
        
        # 计算加权总分
        result['total_score'] = (
            result['momentum_score'] * momentum_weight +
            result['value_score'] * value_weight +
            result['quality_score'] * quality_weight
        )
        
        return result
    
    def apply(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        应用因子评分筛选
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            Tuple[评分后的完整 DataFrame, 通过筛选的 DataFrame]
        """
        if df.empty:
            return df, df
            
        # 计算得分
        scored_df = self.calculate_total_score(df)
        
        # 获取筛选阈值
        scoring_config = self.config.get('scoring', {})
        min_total = scoring_config.get('min_total_score', 60.0)
        min_factor = scoring_config.get('min_factor_score', 40.0)
        
        # 筛选
        mask = (
            (scored_df['total_score'] >= min_total) &
            (scored_df['momentum_score'] >= min_factor) &
            (scored_df['value_score'] >= min_factor) &
            (scored_df['quality_score'] >= min_factor)
        )
        
        filtered_df = scored_df[mask].copy()
        
        return scored_df, filtered_df
    
    def get_score_stats(self, df: pd.DataFrame) -> Dict:
        """
        获取得分统计信息
        
        Args:
            df: 包含得分的 DataFrame
            
        Returns:
            统计信息字典
        """
        if 'total_score' not in df.columns:
            return {}
        
        return {
            'score_stats': {
                'total_score_mean': df['total_score'].mean(),
                'total_score_median': df['total_score'].median(),
                'total_score_std': df['total_score'].std(),
                'momentum_score_mean': df['momentum_score'].mean() if 'momentum_score' in df.columns else None,
                'value_score_mean': df['value_score'].mean() if 'value_score' in df.columns else None,
                'quality_score_mean': df['quality_score'].mean() if 'quality_score' in df.columns else None,
            }
        }
