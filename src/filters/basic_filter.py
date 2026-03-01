"""
第一层：基础筛选器
Basic Filter - Market Cap, Liquidity, Industry Screening

筛选标准：
- 市值：剔除过小市值股票，保证流动性
- 流动性：确保足够的交易量和合理股价
- 行业：排除高风险或不符合投资理念的行业
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import yaml
from pathlib import Path


class BasicFilter:
    """基础筛选器 - 第一层漏斗"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化基础筛选器
        
        Args:
            config: 筛选配置字典，如 None 则从配置文件加载
        """
        self.config = config or self._load_default_config()
        
    def _load_default_config(self) -> Dict:
        """加载默认配置文件"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'screener_config.yaml'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)
                return full_config.get('basic_filters', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'market_cap': {
                'enabled': True,
                'min_usd_millions': 1000,
                'max_usd_millions': None
            },
            'liquidity': {
                'enabled': True,
                'min_avg_volume_30d': 500000,
                'min_price': 1.0
            },
            'industry': {
                'enabled': True,
                'excluded': ['烟草', '博彩', '军工'],
                'preferred': ['科技', '医疗', '消费', '金融']
            }
        }
    
    def filter_market_cap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        市值筛选
        
        Args:
            df: 股票数据 DataFrame，需包含 'market_cap_usd' 列
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('market_cap', {}).get('enabled', True):
            return df
            
        min_cap = self.config['market_cap'].get('min_usd_millions', 1000)
        max_cap = self.config['market_cap'].get('max_usd_millions')
        
        mask = df['market_cap_usd'] >= (min_cap * 1_000_000)
        
        if max_cap is not None:
            mask &= df['market_cap_usd'] <= (max_cap * 1_000_000)
        
        return df[mask].copy()
    
    def filter_liquidity(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        流动性筛选
        
        Args:
            df: 股票数据 DataFrame，需包含 'avg_volume_30d', 'price' 列
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('liquidity', {}).get('enabled', True):
            return df
            
        min_volume = self.config['liquidity'].get('min_avg_volume_30d', 500000)
        min_price = self.config['liquidity'].get('min_price', 1.0)
        
        mask = (df['avg_volume_30d'] >= min_volume) & (df['price'] >= min_price)
        
        return df[mask].copy()
    
    def filter_industry(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        行业筛选
        
        Args:
            df: 股票数据 DataFrame，需包含 'industry' 或 'industry_cn' 列
            
        Returns:
            筛选后的 DataFrame
        """
        if not self.config.get('industry', {}).get('enabled', True):
            return df
            
        excluded = self.config['industry'].get('excluded', [])
        preferred = self.config['industry'].get('preferred', [])
        
        # 确定行业列名
        industry_col = 'industry_cn' if 'industry_cn' in df.columns else 'industry'
        
        if industry_col not in df.columns:
            return df
        
        # 排除禁止行业
        mask = ~df[industry_col].isin(excluded)
        
        # 如果有优选行业且数据包含该列，可以加权但不强制排除
        # 这里只做排除，优选在评分阶段处理
        
        return df[mask].copy()
    
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用所有基础筛选
        
        Args:
            df: 股票数据 DataFrame
            
        Returns:
            通过基础筛选的 DataFrame
        """
        if df.empty:
            return df
            
        # 按顺序应用筛选
        df = self.filter_market_cap(df)
        if df.empty:
            return df
            
        df = self.filter_liquidity(df)
        if df.empty:
            return df
            
        df = self.filter_industry(df)
        
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
            'filter_name': 'Basic Filter',
            'original_count': len(original_df),
            'filtered_count': len(filtered_df),
            'removed_count': len(original_df) - len(filtered_df),
            'pass_rate': len(filtered_df) / len(original_df) * 100 if len(original_df) > 0 else 0
        }
