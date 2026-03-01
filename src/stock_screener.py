#!/usr/bin/env python3
"""
Q 脑量化交易系统 - 选股引擎
Stock Screener for Q-Brain Trading System

四层漏斗筛选系统：
1. 第一层：基础筛选（市值、流动性、行业）
2. 第二层：财务质量筛选（ROE、负债率、现金流）
3. 第三层：因子评分筛选（动量、价值、质量）
4. 第四层：技术面筛选（趋势、突破）

支持市场：A 股、美股
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from filters.basic_filter import BasicFilter
from filters.financial_filter import FinancialFilter
from filters.factor_scorer import FactorScorer
from filters.technical_filter import TechnicalFilter


class StockScreener:
    """
    选股引擎主类
    实现四层漏斗筛选系统
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化选股引擎
        
        Args:
            config_path: 配置文件路径，如 None 则使用默认路径
        """
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        
        # 初始化各层筛选器
        self.basic_filter = BasicFilter(self.config.get('basic_filters'))
        self.financial_filter = FinancialFilter(self.config.get('financial_filters'))
        self.factor_scorer = FactorScorer(self.config.get('factor_filters'))
        self.technical_filter = TechnicalFilter(self.config.get('technical_filters'))
        
        # 日志配置
        self._setup_logging()
        
        self.logger.info("选股引擎初始化完成")
        self.logger.info(f"配置文件：{self.config_path}")
        self.logger.info(f"支持市场：{self.config.get('market', {}).get('supported', ['A', 'US'])}")
    
    def _find_config_path(self) -> str:
        """查找配置文件"""
        possible_paths = [
            Path(__file__).parent.parent / 'config' / 'screener_config.yaml',
            Path(__file__).parent / 'config' / 'screener_config.yaml',
            Path('config') / 'screener_config.yaml',
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        raise FileNotFoundError("未找到配置文件 screener_config.yaml")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'logs/stock_screener.log')
        
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('StockScreener')
    
    def load_stock_data(self, market: str = 'A', data_source: Optional[str] = None) -> pd.DataFrame:
        """
        加载股票数据
        
        Args:
            market: 市场类型 ('A' 或 'US')
            data_source: 数据源路径或标识
            
        Returns:
            股票数据 DataFrame
        """
        self.logger.info(f"加载 {market} 股市场数据")
        
        # TODO: 实现实际的数据加载逻辑
        # 这里提供示例数据结构
        if data_source:
            # 从文件加载
            if data_source.endswith('.csv'):
                df = pd.read_csv(data_source)
            elif data_source.endswith('.parquet'):
                df = pd.read_parquet(data_source)
            else:
                raise ValueError(f"不支持的数据格式：{data_source}")
        else:
            # 示例数据（实际使用时需要替换）
            df = self._create_sample_data(market)
        
        self.logger.info(f"加载完成，共 {len(df)} 只股票")
        return df
    
    def _create_sample_data(self, market: str) -> pd.DataFrame:
        """创建示例数据（用于测试）"""
        np = __import__('numpy')
        
        n_stocks = 1000
        data = {
            'symbol': [f'{market}{i:04d}' for i in range(n_stocks)],
            'name': [f'Stock_{i}' for i in range(n_stocks)],
            'market': market,
            'price': np.random.uniform(10, 500, n_stocks),
            'market_cap_usd': np.random.uniform(1e9, 1e12, n_stocks),
            'avg_volume_30d': np.random.uniform(1e5, 1e7, n_stocks),
            'industry_cn': np.random.choice(['科技', '医疗', '消费', '金融', '制造', '能源'], n_stocks),
            'roe': np.random.uniform(-10, 30, n_stocks),
            'debt_ratio': np.random.uniform(20, 80, n_stocks),
            'operating_cf_usd': np.random.uniform(-1e8, 1e9, n_stocks),
            'return_1m': np.random.uniform(-20, 30, n_stocks),
            'return_3m': np.random.uniform(-30, 50, n_stocks),
            'return_6m': np.random.uniform(-40, 80, n_stocks),
            'pe_ratio': np.random.uniform(5, 100, n_stocks),
            'pb_ratio': np.random.uniform(0.5, 10, n_stocks),
            'ma_20': np.random.uniform(10, 400, n_stocks),
            'ma_50': np.random.uniform(10, 400, n_stocks),
            'ma_200': np.random.uniform(10, 400, n_stocks),
            'high_52w': np.random.uniform(50, 600, n_stocks),
            'rsi': np.random.uniform(20, 80, n_stocks),
        }
        
        df = pd.DataFrame(data)
        # 让价格和均线更相关
        df['ma_20'] = df['price'] * np.random.uniform(0.95, 1.05, n_stocks)
        df['ma_50'] = df['price'] * np.random.uniform(0.90, 1.10, n_stocks)
        df['ma_200'] = df['price'] * np.random.uniform(0.80, 1.20, n_stocks)
        df['high_52w'] = df['price'] * np.random.uniform(1.0, 1.5, n_stocks)
        
        return df
    
    def screen(self, df: pd.DataFrame, market: str = 'A') -> Tuple[pd.DataFrame, Dict]:
        """
        执行四层漏斗筛选
        
        Args:
            df: 股票数据 DataFrame
            market: 市场类型
            
        Returns:
            Tuple[通过筛选的股票 DataFrame, 筛选统计信息 Dict]
        """
        self.logger.info(f"开始执行 {market} 股市场筛选")
        start_time = datetime.now()
        
        stats = {
            'market': market,
            'start_time': start_time.isoformat(),
            'layers': {}
        }
        
        # 第一层：基础筛选
        self.logger.info("第一层：基础筛选（市值、流动性、行业）")
        original_count = len(df)
        df = self.basic_filter.apply(df)
        stats['layers']['basic'] = self.basic_filter.get_filter_stats(
            pd.DataFrame(index=range(original_count)), df
        )
        self.logger.info(f"  通过：{len(df)} / {original_count} ({stats['layers']['basic']['pass_rate']:.1f}%)")
        
        if df.empty:
            self.logger.warning("基础筛选后无股票通过")
            return df, stats
        
        # 第二层：财务质量筛选
        self.logger.info("第二层：财务质量筛选（ROE、负债率、现金流）")
        original_count = len(df)
        df = self.financial_filter.apply(df)
        stats['layers']['financial'] = self.financial_filter.get_filter_stats(
            pd.DataFrame(index=range(original_count)), df
        )
        self.logger.info(f"  通过：{len(df)} / {original_count} ({stats['layers']['financial']['pass_rate']:.1f}%)")
        
        if df.empty:
            self.logger.warning("财务筛选后无股票通过")
            return df, stats
        
        # 第三层：因子评分筛选
        self.logger.info("第三层：因子评分筛选（动量、价值、质量）")
        original_count = len(df)
        df_scored, df = self.factor_scorer.apply(df)
        stats['layers']['factor'] = {
            'filter_name': 'Factor Scoring Filter',
            'original_count': original_count,
            'filtered_count': len(df),
            'removed_count': original_count - len(df),
            'pass_rate': len(df) / original_count * 100 if original_count > 0 else 0
        }
        stats['factor_stats'] = self.factor_scorer.get_score_stats(df_scored)
        self.logger.info(f"  通过：{len(df)} / {original_count} ({stats['layers']['factor']['pass_rate']:.1f}%)")
        
        if df.empty:
            self.logger.warning("因子评分后无股票通过")
            return df, stats
        
        # 第四层：技术面筛选
        self.logger.info("第四层：技术面筛选（趋势、突破）")
        original_count = len(df)
        df = self.technical_filter.apply(df)
        stats['layers']['technical'] = self.technical_filter.get_filter_stats(
            pd.DataFrame(index=range(original_count)), df
        )
        self.logger.info(f"  通过：{len(df)} / {original_count} ({stats['layers']['technical']['pass_rate']:.1f}%)")
        
        # 排序和限制结果数量
        if not df.empty and 'total_score' in df.columns:
            output_config = self.config.get('output', {})
            sort_by = output_config.get('sort_by', 'total_score')
            sort_order = output_config.get('sort_order', 'desc')
            max_results = output_config.get('max_results', 100)
            
            ascending = (sort_order.lower() == 'asc')
            df = df.sort_values(by=sort_by, ascending=ascending).head(max_results)
        
        # 完成统计
        end_time = datetime.now()
        stats['end_time'] = end_time.isoformat()
        stats['duration_seconds'] = (end_time - start_time).total_seconds()
        stats['final_count'] = len(df)
        
        self.logger.info(f"筛选完成，耗时 {stats['duration_seconds']:.2f} 秒，最终通过 {len(df)} 只股票")
        
        return df, stats
    
    def run(self, market: str = 'A', data_source: Optional[str] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        完整运行选股流程
        
        Args:
            market: 市场类型 ('A' 或 'US')
            data_source: 数据源路径
            
        Returns:
            Tuple[筛选结果 DataFrame, 统计信息 Dict]
        """
        # 加载数据
        df = self.load_stock_data(market, data_source)
        
        # 执行筛选
        result, stats = self.screen(df, market)
        
        return result, stats
    
    def export_results(self, df: pd.DataFrame, output_path: str, format: str = 'csv'):
        """
        导出筛选结果
        
        Args:
            df: 筛选结果 DataFrame
            output_path: 输出文件路径
            format: 输出格式 ('csv', 'excel', 'parquet')
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif format == 'excel':
            df.to_excel(output_path, index=False)
        elif format == 'parquet':
            df.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"不支持的输出格式：{format}")
        
        self.logger.info(f"结果已导出至：{output_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Q 脑选股引擎')
    parser.add_argument('--market', type=str, default='A', choices=['A', 'US'],
                        help='市场类型 (A 或 US)')
    parser.add_argument('--data', type=str, default=None,
                        help='数据源文件路径')
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径')
    parser.add_argument('--output', type=str, default='results/screener_output.csv',
                        help='输出文件路径')
    parser.add_argument('--format', type=str, default='csv',
                        choices=['csv', 'excel', 'parquet'],
                        help='输出格式')
    
    args = parser.parse_args()
    
    # 初始化选股引擎
    screener = StockScreener(config_path=args.config)
    
    # 运行筛选
    result, stats = screener.run(market=args.market, data_source=args.data)
    
    # 导出结果
    if not result.empty:
        screener.export_results(result, args.output, format=args.format)
        print(f"\n筛选完成！共选出 {len(result)} 只股票")
        print(f"结果已保存至：{args.output}")
    else:
        print("\n筛选完成，但未找到符合条件的股票")
    
    # 打印统计信息
    print("\n=== 筛选统计 ===")
    for layer, layer_stats in stats.get('layers', {}).items():
        print(f"{layer}: {layer_stats.get('filtered_count', 0)} / {layer_stats.get('original_count', 0)} "
              f"({layer_stats.get('pass_rate', 0):.1f}%)")
    print(f"总耗时：{stats.get('duration_seconds', 0):.2f} 秒")


if __name__ == '__main__':
    main()
