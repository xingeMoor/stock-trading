"""
第二层：财务质量筛选器
Financial Quality Filter - ROE, Debt Ratio, Cash Flow Screening

筛选标准：
- ROE：筛选持续高回报的公司
- 负债率：控制财务风险
- 现金流：确保公司经营健康
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import yaml
from pathlib import Path


class FinancialFilter:
    """财务质量筛选器 - 第二层漏斗"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化财务筛选器
        
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
                return full_config.get('financial_filters', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'roe': {
                'enabled': True,
                'min_percent': 10.0,
                'min_years_consistent': 3
            },
            'debt_ratio': {
                'enabled': True,
                'max_percent': 60.0
            },
            'cash_flow': {
                'enabled': True,
                'min_operating_cf_usd_millions': 100,
                'min_free_cf_usd_millions': 50,
                'positive_cf_years': 2
            }
        }
    
    def filter_roe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ROE 筛选
        
        Args:
            df: 股票数据 DataFrame，需包含 'roe' 列（百分比或小数）
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('roe', {}).get('enabled', True):
            return df
            
        min_roe = self.config['roe'].get('min_percent', 10.0)
        
        # 假设 roe 列是百分比值（如 15 表示 15%）
        # 如果是小数（如 0.15），需要调整
        if 'roe' not in df.columns:
            return df
        
        # 判断 ROE 是百分比还是小数（如果最大值<1，可能是小数）
        if df['roe'].max() <= 1.0:
            mask = df['roe'] >= (min_roe / 100.0)
        else:
            mask = df['roe'] >= min_roe
        
        return df[mask].copy()
    
    def filter_debt_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        负债率筛选
        
        Args:
            df: 股票数据 DataFrame，需包含 'debt_ratio' 或 'debt_to_asset' 列
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('debt_ratio', {}).get('enabled', True):
            return df
            
        max_debt = self.config['debt_ratio'].get('max_percent', 60.0)
        
        # 确定负债率列名
        debt_col = None
        for col in ['debt_ratio', 'debt_to_asset', '资产负债率']:
            if col in df.columns:
                debt_col = col
                break
        
        if debt_col is None:
            return df
        
        # 判断是百分比还是小数
        if df[debt_col].max() <= 1.0:
            mask = df[debt_col] <= (max_debt / 100.0)
        else:
            mask = df[debt_col] <= max_debt
        
        return df[mask].copy()
    
    def filter_cash_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        现金流筛选
        
        Args:
            df: 股票数据 DataFrame，需包含现金流相关列
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('cash_flow', {}).get('enabled', True):
            return df
            
        min_operating_cf = self.config['cash_flow'].get('min_operating_cf_usd_millions', 100)
        min_free_cf = self.config['cash_flow'].get('min_free_cf_usd_millions', 50)
        
        mask = pd.Series(True, index=df.index)
        
        # 经营现金流筛选
        if 'operating_cf_usd' in df.columns:
            mask &= df['operating_cf_usd'] >= (min_operating_cf * 1_000_000)
        elif 'operating_cash_flow' in df.columns:
            mask &= df['operating_cash_flow'] >= (min_operating_cf * 1_000_000)
            
        # 自由现金流筛选
        if 'free_cf_usd' in df.columns:
            mask &= df['free_cf_usd'] >= (min_free_cf * 1_000_000)
        elif 'free_cash_flow' in df.columns:
            mask &= df['free_cash_flow'] >= (min_free_cf * 1_000_000)
        
        return df[mask].copy()
    
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用所有财务筛选
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            通过财务筛选的 DataFrame
        """
        if df.empty:
            return df
            
        # 按顺序应用筛选
        df = self.filter_roe(df)
        if df.empty:
            return df
            
        df = self.filter_debt_ratio(df)
        if df.empty:
            return df
            
        df = self.filter_cash_flow(df)
        
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
            'filter_name': 'Financial Quality Filter',
            'original_count': len(original_df),
            'filtered_count': len(filtered_df),
            'removed_count': len(original_df) - len(filtered_df),
            'pass_rate': len(filtered_df) / len(original_df) * 100 if len(original_df) > 0 else 0
        }
