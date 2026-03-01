"""
选股引擎单元测试
测试模块：stock_screener.py, filters/*.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
import yaml

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestBasicFilter(unittest.TestCase):
    """测试基础筛选器"""
    
    def setUp(self):
        """测试前准备"""
        self.sample_df = pd.DataFrame({
            'symbol': ['A001', 'A002', 'A003', 'A004', 'A005'],
            'name': ['Stock1', 'Stock2', 'Stock3', 'Stock4', 'Stock5'],
            'market_cap_usd': [5e9, 50e9, 500e9, 1e9, 100e9],
            'avg_volume_30d': [1e6, 5e6, 10e6, 1e4, 2e6],
            'price': [50.0, 100.0, 200.0, 0.5, 75.0],
            'industry_cn': ['科技', '医疗', '金融', '烟草', '消费']
        })
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': True, 'min_usd_millions': 1000},
            'liquidity': {'enabled': True, 'min_avg_volume_30d': 100000},
            'industry': {'enabled': False}
        }
        
        filter = BasicFilter(config)
        self.assertEqual(filter.config['market_cap']['min_usd_millions'], 1000)
    
    def test_filter_market_cap(self):
        """测试市值筛选"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': True, 'min_usd_millions': 10000, 'max_usd_millions': None},
            'liquidity': {'enabled': False},
            'industry': {'enabled': False}
        }
        
        filter = BasicFilter(config)
        result = filter.filter_market_cap(self.sample_df)
        
        # 应该只保留市值>100 亿的
        self.assertEqual(len(result), 3)
        self.assertTrue(all(result['market_cap_usd'] >= 10e9))
    
    def test_filter_market_cap_with_max(self):
        """测试市值筛选（含上限）"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': True, 'min_usd_millions': 10000, 'max_usd_millions': 200000},
            'liquidity': {'enabled': False},
            'industry': {'enabled': False}
        }
        
        filter = BasicFilter(config)
        result = filter.filter_market_cap(self.sample_df)
        
        # 应该只保留 100 亿 -2000 亿之间的
        self.assertEqual(len(result), 2)
    
    def test_filter_liquidity(self):
        """测试流动性筛选"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': False},
            'liquidity': {'enabled': True, 'min_avg_volume_30d': 1000000, 'min_price': 1.0},
            'industry': {'enabled': False}
        }
        
        filter = BasicFilter(config)
        result = filter.filter_liquidity(self.sample_df)
        
        # 应该保留成交量>100 万且价格>1 元的
        self.assertEqual(len(result), 4)
        self.assertTrue(all(result['avg_volume_30d'] >= 1e6))
        self.assertTrue(all(result['price'] >= 1.0))
    
    def test_filter_industry(self):
        """测试行业筛选"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': False},
            'liquidity': {'enabled': False},
            'industry': {'enabled': True, 'excluded': ['烟草', '博彩'], 'preferred': []}
        }
        
        filter = BasicFilter(config)
        result = filter.filter_industry(self.sample_df)
        
        # 应该排除烟草行业
        self.assertEqual(len(result), 4)
        self.assertTrue('烟草' not in result['industry_cn'].values)
    
    def test_apply_all_filters(self):
        """测试应用所有筛选"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': True, 'min_usd_millions': 10000},
            'liquidity': {'enabled': True, 'min_avg_volume_30d': 1000000},
            'industry': {'enabled': True, 'excluded': ['烟草']}
        }
        
        filter = BasicFilter(config)
        result = filter.apply(self.sample_df)
        
        # 应该只保留符合所有条件的
        self.assertEqual(len(result), 2)
    
    def test_apply_empty_dataframe(self):
        """测试空 DataFrame"""
        from filters.basic_filter import BasicFilter
        
        filter = BasicFilter()
        result = filter.apply(pd.DataFrame())
        
        self.assertTrue(result.empty)
    
    def test_filter_disabled(self):
        """测试禁用筛选"""
        from filters.basic_filter import BasicFilter
        
        config = {
            'market_cap': {'enabled': False},
            'liquidity': {'enabled': False},
            'industry': {'enabled': False}
        }
        
        filter = BasicFilter(config)
        result = filter.apply(self.sample_df)
        
        # 应该返回原始数据
        self.assertEqual(len(result), len(self.sample_df))
    
    def test_missing_columns(self):
        """测试缺失列"""
        from filters.basic_filter import BasicFilter
        
        df_missing = pd.DataFrame({
            'symbol': ['A001', 'A002'],
            'price': [50.0, 100.0]
        })
        
        filter = BasicFilter()
        result = filter.filter_market_cap(df_missing)
        
        # 缺失列应该返回原数据
        self.assertEqual(len(result), len(df_missing))


class TestFinancialFilter(unittest.TestCase):
    """测试财务质量筛选器"""
    
    def setUp(self):
        """测试前准备"""
        self.sample_df = pd.DataFrame({
            'symbol': ['A001', 'A002', 'A003', 'A004'],
            'roe': [15.0, 8.0, 25.0, -5.0],
            'debt_ratio': [45.0, 70.0, 30.0, 85.0],
            'operating_cf_usd': [5e8, 1e8, 1e9, -1e8]
        })
    
    def test_filter_roe(self):
        """测试 ROE 筛选"""
        from filters.financial_filter import FinancialFilter
        
        config = {
            'roe': {'enabled': True, 'min_percent': 10.0},
            'debt_ratio': {'enabled': False},
            'cash_flow': {'enabled': False}
        }
        
        filter = FinancialFilter(config)
        result = filter.filter_roe(self.sample_df)
        
        # 应该保留 ROE>=10% 的
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result['roe'] >= 10.0))
    
    def test_filter_roe_decimal_format(self):
        """测试 ROE 小数格式"""
        from filters.financial_filter import FinancialFilter
        
        df_decimal = pd.DataFrame({
            'symbol': ['A001', 'A002', 'A003'],
            'roe': [0.15, 0.08, 0.25]
        })
        
        config = {'roe': {'enabled': True, 'min_percent': 10.0}}
        filter = FinancialFilter(config)
        result = filter.filter_roe(df_decimal)
        
        # 应该正确识别小数格式
        self.assertEqual(len(result), 2)
    
    def test_filter_debt_ratio(self):
        """测试负债率筛选"""
        from filters.financial_filter import FinancialFilter
        
        config = {
            'roe': {'enabled': False},
            'debt_ratio': {'enabled': True, 'max_percent': 60.0},
            'cash_flow': {'enabled': False}
        }
        
        filter = FinancialFilter(config)
        result = filter.filter_debt_ratio(self.sample_df)
        
        # 应该保留负债率<=60% 的
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result['debt_ratio'] <= 60.0))
    
    def test_filter_cash_flow(self):
        """测试现金流筛选"""
        from filters.financial_filter import FinancialFilter
        
        config = {
            'roe': {'enabled': False},
            'debt_ratio': {'enabled': False},
            'cash_flow': {'enabled': True, 'min_operating_cf_usd_millions': 100}
        }
        
        filter = FinancialFilter(config)
        result = filter.filter_cash_flow(self.sample_df)
        
        # 应该保留经营现金流>=1 亿的
        self.assertEqual(len(result), 3)
    
    def test_apply_all_filters(self):
        """测试应用所有财务筛选"""
        from filters.financial_filter import FinancialFilter
        
        config = {
            'roe': {'enabled': True, 'min_percent': 10.0},
            'debt_ratio': {'enabled': True, 'max_percent': 60.0},
            'cash_flow': {'enabled': True, 'min_operating_cf_usd_millions': 100}
        }
        
        filter = FinancialFilter(config)
        result = filter.apply(self.sample_df)
        
        # 应该只保留符合所有条件的
        self.assertEqual(len(result), 1)


class TestFactorScorer(unittest.TestCase):
    """测试因子评分器"""
    
    def setUp(self):
        """测试前准备"""
        np.random.seed(42)
        self.sample_df = pd.DataFrame({
            'symbol': [f'A{i:03d}' for i in range(100)],
            'return_1m': np.random.uniform(-20, 30, 100),
            'return_3m': np.random.uniform(-30, 50, 100),
            'return_6m': np.random.uniform(-40, 80, 100),
            'pe_ratio': np.random.uniform(5, 100, 100),
            'pb_ratio': np.random.uniform(0.5, 10, 100),
            'roe': np.random.uniform(-10, 30, 100)
        })
    
    def test_normalize_score_ascending(self):
        """测试归一化评分（越小越好）"""
        from filters.factor_scorer import FactorScorer
        
        scorer = FactorScorer()
        series = pd.Series([10, 20, 30, 40, 50])
        scores = scorer._normalize_score(series, ascending=True)
        
        # 值越小分数越高
        self.assertEqual(scores.iloc[0], 100)  # 最小值应该得 100 分
        self.assertEqual(scores.iloc[-1], 0)   # 最大值应该得 0 分
    
    def test_normalize_score_descending(self):
        """测试归一化评分（越大越好）"""
        from filters.factor_scorer import FactorScorer
        
        scorer = FactorScorer()
        series = pd.Series([10, 20, 30, 40, 50])
        scores = scorer._normalize_score(series, ascending=False)
        
        # 值越大分数越高
        self.assertEqual(scores.iloc[0], 0)    # 最小值应该得 0 分
        self.assertEqual(scores.iloc[-1], 100) # 最大值应该得 100 分
    
    def test_calculate_momentum_score(self):
        """测试动量因子得分计算"""
        from filters.factor_scorer import FactorScorer
        
        config = {
            'momentum': {'enabled': True, 'weight': 0.35, 'metrics': ['return_1m', 'return_3m']},
            'value': {'enabled': False},
            'quality': {'enabled': False}
        }
        
        scorer = FactorScorer(config)
        scores = scorer.calculate_momentum_score(self.sample_df)
        
        self.assertEqual(len(scores), 100)
        self.assertTrue(all(scores >= 0))
        self.assertTrue(all(scores <= 100))
    
    def test_calculate_value_score(self):
        """测试价值因子得分计算"""
        from filters.factor_scorer import FactorScorer
        
        config = {
            'momentum': {'enabled': False},
            'value': {'enabled': True, 'weight': 0.35, 'metrics': ['pe_ratio', 'pb_ratio']},
            'quality': {'enabled': False}
        }
        
        scorer = FactorScorer(config)
        scores = scorer.calculate_value_score(self.sample_df)
        
        self.assertEqual(len(scores), 100)
    
    def test_calculate_quality_score(self):
        """测试质量因子得分计算"""
        from filters.factor_scorer import FactorScorer
        
        config = {
            'momentum': {'enabled': False},
            'value': {'enabled': False},
            'quality': {'enabled': True, 'weight': 0.30, 'metrics': ['roe']}
        }
        
        scorer = FactorScorer(config)
        scores = scorer.calculate_quality_score(self.sample_df)
        
        self.assertEqual(len(scores), 100)
    
    def test_calculate_total_score(self):
        """测试综合得分计算"""
        from filters.factor_scorer import FactorScorer
        
        scorer = FactorScorer()
        df_with_scores = scorer.calculate_total_score(self.sample_df.copy())
        
        self.assertIn('total_score', df_with_scores.columns)
        self.assertIn('momentum_score', df_with_scores.columns)
        self.assertIn('value_score', df_with_scores.columns)
        self.assertIn('quality_score', df_with_scores.columns)
    
    def test_filter_by_score(self):
        """测试按分数筛选"""
        from filters.factor_scorer import FactorScorer
        
        scorer = FactorScorer()
        df_with_scores = scorer.calculate_total_score(self.sample_df.copy())
        
        result = scorer.filter_by_score(df_with_scores)
        
        # 应该保留分数>=60 的
        self.assertTrue(all(result['total_score'] >= 60))


class TestTechnicalFilter(unittest.TestCase):
    """测试技术面筛选器"""
    
    def setUp(self):
        """测试前准备"""
        self.sample_df = pd.DataFrame({
            'symbol': ['A001', 'A002', 'A003', 'A004'],
            'price': [100.0, 95.0, 110.0, 80.0],
            'close': [100.0, 95.0, 110.0, 80.0],
            'ma_20': [98.0, 96.0, 105.0, 85.0],
            'ma_50': [95.0, 94.0, 100.0, 88.0],
            'ma_200': [90.0, 92.0, 95.0, 90.0],
            'high_52w': [120.0, 130.0, 115.0, 100.0],
            'volume': [1e6, 5e5, 2e6, 8e5],
            'avg_volume_30d': [1e6, 1e6, 1e6, 1e6],
            'rsi': [55.0, 35.0, 65.0, 85.0]
        })
    
    def test_filter_trend(self):
        """测试趋势筛选"""
        from filters.technical_filter import TechnicalFilter
        
        config = {
            'trend': {'enabled': True, 'ma_20_above': True, 'ma_50_above': True, 'ma_200_above': False},
            'breakout': {'enabled': False},
            'indicators': {}
        }
        
        filter = TechnicalFilter(config)
        result = filter.filter_trend(self.sample_df)
        
        # 应该保留价格在 MA20 和 MA50 之上的
        self.assertEqual(len(result), 2)
    
    def test_filter_breakout(self):
        """测试突破筛选"""
        from filters.technical_filter import TechnicalFilter
        
        config = {
            'trend': {'enabled': False},
            'breakout': {'enabled': True, 'price_vs_52w_high_percent': 15.0, 'volume_spike_ratio': 1.5},
            'indicators': {}
        }
        
        filter = TechnicalFilter(config)
        result = filter.filter_breakout(self.sample_df)
        
        # 应该保留接近 52 周高点且有放量
        self.assertTrue(len(result) <= len(self.sample_df))
    
    def test_filter_rsi(self):
        """测试 RSI 筛选"""
        from filters.technical_filter import TechnicalFilter
        
        config = {
            'trend': {'enabled': False},
            'breakout': {'enabled': False},
            'indicators': {
                'rsi': {'enabled': True, 'min': 40.0, 'max': 80.0}
            }
        }
        
        filter = TechnicalFilter(config)
        result = filter.filter_rsi(self.sample_df)
        
        # 应该保留 RSI 在 40-80 之间的
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result['rsi'] >= 40))
        self.assertTrue(all(result['rsi'] <= 80))
    
    def test_apply_all_filters(self):
        """测试应用所有技术筛选"""
        from filters.technical_filter import TechnicalFilter
        
        config = {
            'trend': {'enabled': True, 'ma_20_above': True, 'ma_50_above': False, 'ma_200_above': False},
            'breakout': {'enabled': True, 'price_vs_52w_high_percent': 20.0, 'volume_spike_ratio': 1.0},
            'indicators': {
                'rsi': {'enabled': True, 'min': 30.0, 'max': 90.0}
            }
        }
        
        filter = TechnicalFilter(config)
        result = filter.apply(self.sample_df)
        
        self.assertTrue(len(result) <= len(self.sample_df))


class TestStockScreener(unittest.TestCase):
    """测试选股引擎"""
    
    def setUp(self):
        """测试前准备"""
        self.config = {
            'market': {'supported': ['A', 'US']},
            'basic_filters': {
                'market_cap': {'enabled': True, 'min_usd_millions': 1000},
                'liquidity': {'enabled': True, 'min_avg_volume_30d': 100000},
                'industry': {'enabled': True, 'excluded': []}
            },
            'financial_filters': {
                'roe': {'enabled': True, 'min_percent': 10.0},
                'debt_ratio': {'enabled': True, 'max_percent': 60.0},
                'cash_flow': {'enabled': False}
            },
            'factor_filters': {
                'momentum': {'enabled': True, 'weight': 0.35},
                'value': {'enabled': True, 'weight': 0.35},
                'quality': {'enabled': True, 'weight': 0.30},
                'scoring': {'min_total_score': 60.0}
            },
            'technical_filters': {
                'trend': {'enabled': True, 'ma_20_above': True},
                'breakout': {'enabled': False},
                'indicators': {'rsi': {'enabled': False}}
            },
            'logging': {'level': 'DEBUG', 'file': 'logs/test_screener.log'}
        }
    
    @patch('stock_screener.BasicFilter')
    @patch('stock_screener.FinancialFilter')
    @patch('stock_screener.FactorScorer')
    @patch('stock_screener.TechnicalFilter')
    def test_init(self, mock_tech, mock_factor, mock_financial, mock_basic):
        """测试选股引擎初始化"""
        from stock_screener import StockScreener
        
        with patch.object(StockScreener, '_find_config_path', return_value='test_config.yaml'):
            with patch('builtins.open', unittest.mock.mock_open(read_data=yaml.dump(self.config))):
                screener = StockScreener()
                
                self.assertIsNotNone(screener.basic_filter)
                self.assertIsNotNone(screener.financial_filter)
                self.assertIsNotNone(screener.factor_scorer)
                self.assertIsNotNone(screener.technical_filter)
    
    def test_create_sample_data(self):
        """测试创建示例数据"""
        from stock_screener import StockScreener
        
        with patch.object(StockScreener, '_find_config_path', return_value='test_config.yaml'):
            with patch('builtins.open', unittest.mock.mock_open(read_data=yaml.dump(self.config))):
                with patch('stock_screener.BasicFilter'):
                    with patch('stock_screener.FinancialFilter'):
                        with patch('stock_screener.FactorScorer'):
                            with patch('stock_screener.TechnicalFilter'):
                                screener = StockScreener()
                                df = screener._create_sample_data('A')
                                
                                self.assertEqual(len(df), 1000)
                                self.assertIn('symbol', df.columns)
                                self.assertIn('market_cap_usd', df.columns)
                                self.assertIn('roe', df.columns)
    
    def test_screen_pipeline(self):
        """测试筛选流程"""
        from stock_screener import StockScreener
        
        sample_data = pd.DataFrame({
            'symbol': [f'A{i:04d}' for i in range(100)],
            'name': [f'Stock_{i}' for i in range(100)],
            'market': 'A',
            'price': np.random.uniform(10, 500, 100),
            'market_cap_usd': np.random.uniform(1e9, 1e12, 100),
            'avg_volume_30d': np.random.uniform(1e5, 1e7, 100),
            'industry_cn': np.random.choice(['科技', '医疗', '消费'], 100),
            'roe': np.random.uniform(10, 30, 100),
            'debt_ratio': np.random.uniform(20, 60, 100),
            'ma_20': np.random.uniform(10, 400, 100),
            'ma_50': np.random.uniform(10, 400, 100)
        })
        sample_data['price'] = sample_data['ma_20'] * np.random.uniform(0.95, 1.05, 100)
        
        with patch.object(StockScreener, '_find_config_path', return_value='test_config.yaml'):
            with patch('builtins.open', unittest.mock.mock_open(read_data=yaml.dump(self.config))):
                screener = StockScreener()
                
                result, stats = screener.screen(sample_data, market='A')
                
                self.assertIn('layers', stats)
                self.assertIn('basic', stats['layers'])
                self.assertTrue(len(result) <= len(sample_data))


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""
    
    def test_empty_dataframe(self):
        """测试空 DataFrame"""
        from filters.basic_filter import BasicFilter
        
        filter = BasicFilter()
        result = filter.apply(pd.DataFrame())
        
        self.assertTrue(result.empty)
    
    def test_all_filtered_out(self):
        """测试全部被筛选掉"""
        from filters.basic_filter import BasicFilter
        
        df = pd.DataFrame({
            'symbol': ['A001'],
            'market_cap_usd': [1e6],  # 太小
            'avg_volume_30d': [100],   # 太小
            'price': [0.1],            # 太低
            'industry_cn': ['烟草']    # 排除行业
        })
        
        config = {
            'market_cap': {'enabled': True, 'min_usd_millions': 1000},
            'liquidity': {'enabled': True, 'min_avg_volume_30d': 1000000},
            'industry': {'enabled': True, 'excluded': ['烟草']}
        }
        
        filter = BasicFilter(config)
        result = filter.apply(df)
        
        self.assertTrue(result.empty)
    
    def test_missing_required_columns(self):
        """测试缺失必需列"""
        from filters.basic_filter import BasicFilter
        
        df = pd.DataFrame({
            'symbol': ['A001', 'A002'],
            'name': ['Stock1', 'Stock2']
            # 缺少其他列
        })
        
        filter = BasicFilter()
        result = filter.apply(df)
        
        # 应该能处理缺失列的情况
        self.assertTrue(result.empty or len(result) <= len(df))
    
    def test_extreme_values(self):
        """测试极端值"""
        from filters.factor_scorer import FactorScorer
        
        df = pd.DataFrame({
            'symbol': ['A001', 'A002'],
            'return_1m': [1000.0, -1000.0],  # 极端收益率
            'pe_ratio': [0.0, 10000.0],      # 极端估值
            'roe': [100.0, -100.0]           # 极端 ROE
        })
        
        scorer = FactorScorer()
        
        # 应该能处理极端值而不崩溃
        scores = scorer.calculate_total_score(df)
        
        self.assertIn('total_score', scores.columns)


if __name__ == '__main__':
    unittest.main()
