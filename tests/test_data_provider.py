"""
数据层单元测试
测试模块：data_provider.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stock-trading', 'src'))


class TestDataProviderBase(unittest.TestCase):
    """测试数据提供者基类"""
    
    def test_abstract_base_class(self):
        """测试抽象基类不能直接实例化"""
        from data_provider import DataProviderBase
        
        with self.assertRaises(TypeError):
            DataProviderBase()


class TestAShareProvider(unittest.TestCase):
    """测试 A 股数据提供者"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_ak = MagicMock()
        self.sample_df = pd.DataFrame({
            '日期': ['20240101', '20240102', '20240103'],
            '开盘': [10.0, 10.5, 10.8],
            '收盘': [10.5, 10.8, 11.0],
            '最高': [10.8, 11.0, 11.2],
            '最低': [9.8, 10.3, 10.5],
            '成交量': [1000000, 1200000, 1100000],
            '成交额': [10500000, 12960000, 12100000],
            '振幅': [10.0, 8.5, 9.0],
            '涨跌幅': [5.0, 2.8, 1.8],
            '涨跌额': [0.5, 0.3, 0.2],
            '换手率': [2.5, 3.0, 2.8]
        })
    
    @patch('data_provider.akshare')
    def test_init_success(self, mock_akshare):
        """测试初始化成功"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        self.assertIsNotNone(provider.ak)
    
    @patch('data_provider.akshare')
    def test_get_kline_success(self, mock_akshare):
        """测试获取 K 线数据成功"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = self.mock_ak
        self.mock_ak.stock_zh_a_hist.return_value = self.sample_df
        
        df = provider.get_kline('000001', '20240101', '20240103')
        
        self.assertEqual(len(df), 3)
        self.assertIn('date', df.columns)
        self.assertIn('close', df.columns)
        self.mock_ak.stock_zh_a_hist.assert_called_once()
    
    @patch('data_provider.akshare')
    def test_get_kline_cache_hit(self, mock_akshare):
        """测试缓存命中"""
        from data_provider import AShareProvider
        import tempfile
        import os
        
        provider = AShareProvider()
        provider.ak = self.mock_ak
        
        # 创建缓存文件
        with tempfile.TemporaryDirectory() as tmpdir:
            from data_provider import CACHE_DIR
            # 修改缓存目录
            import data_provider
            data_provider.CACHE_DIR = tmpdir
            
            cache_key = f"ashare_000001_20240101_20240103"
            cache_file = os.path.join(tmpdir, f"{cache_key}.parquet")
            self.sample_df.to_parquet(cache_file)
            
            # 应该直接读取缓存，不调用 API
            df = provider.get_kline('000001', '20240101', '20240103')
            
            self.assertEqual(len(df), 3)
            self.mock_ak.stock_zh_a_hist.assert_not_called()
    
    def test_get_realtime_success(self):
        """测试获取实时行情成功"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = self.mock_ak
        
        mock_spot = pd.DataFrame({
            '代码': ['000001', '000002'],
            '名称': ['平安银行', '万科 A'],
            '最新价': [10.5, 15.8],
            '今开': [10.2, 15.5],
            '最高': [10.8, 16.0],
            '最低': [10.0, 15.3],
            '成交量': [1000000, 800000],
            '成交额': [10500000, 12640000],
            '涨跌幅': [2.5, 1.8]
        })
        self.mock_ak.stock_zh_a_spot_em.return_value = mock_spot
        
        result = provider.get_realtime('000001')
        
        self.assertEqual(result['symbol'], '000001')
        self.assertEqual(result['name'], '平安银行')
        self.assertEqual(result['price'], 10.5)
        self.assertEqual(result['market'], 'A 股')
    
    def test_get_realtime_not_found(self):
        """测试股票未找到"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = self.mock_ak
        self.mock_ak.stock_zh_a_spot_em.return_value = pd.DataFrame()
        
        result = provider.get_realtime('999999')
        
        self.assertIn('error', result)
    
    def test_get_fundamentals_success(self):
        """测试获取基本面数据成功"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = self.mock_ak
        self.mock_ak.stock_individual_info_em.return_value = {
            '总市值': 1000000000,
            '市盈率': 15.5,
            '市净率': 2.3,
            'ROE': 12.5,
            '行业': '银行'
        }
        
        result = provider.get_fundamentals('000001')
        
        self.assertEqual(result['symbol'], '000001')
        self.assertEqual(result['market_cap'], 1000000000)
        self.assertEqual(result['pe_ratio'], 15.5)
        self.assertEqual(result['market'], 'A 股')
    
    def test_get_fundamentals_error(self):
        """测试获取基本面数据失败"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = self.mock_ak
        self.mock_ak.stock_individual_info_em.side_effect = Exception("API Error")
        
        result = provider.get_fundamentals('000001')
        
        self.assertIn('error', result)


class TestUSStockProvider(unittest.TestCase):
    """测试美股数据提供者"""
    
    def setUp(self):
        """测试前准备"""
        self.sample_data = {
            'data': [
                {'timestamp': 1704067200000, 'open': 150.0, 'high': 152.0, 
                 'low': 149.0, 'close': 151.0, 'volume': 1000000, 'vwap': 150.5},
                {'timestamp': 1704153600000, 'open': 151.0, 'high': 153.0,
                 'low': 150.0, 'close': 152.0, 'volume': 1100000, 'vwap': 151.5}
            ]
        }
    
    @patch('data_provider.USStockProvider')
    def test_init_with_api_key(self, mock_provider):
        """测试带 API 密钥初始化"""
        from data_provider import USStockProvider
        
        provider = USStockProvider(api_key='test_key')
        self.assertEqual(provider.api_key, 'test_key')
    
    @patch('data_provider.get_aggs')
    def test_get_kline_success(self, mock_get_aggs):
        """测试获取美股 K 线数据成功"""
        from data_provider import USStockProvider
        
        mock_get_aggs.return_value = self.sample_data
        
        provider = USStockProvider(api_key='test_key')
        df = provider.get_kline('AAPL', '20240101', '20240102')
        
        self.assertEqual(len(df), 2)
        self.assertIn('close', df.columns)
        mock_get_aggs.assert_called_once()
    
    @patch('data_provider.get_aggs')
    def test_get_kline_error(self, mock_get_aggs):
        """测试获取 K 线数据失败"""
        from data_provider import USStockProvider
        
        mock_get_aggs.return_value = {'error': 'API limit exceeded'}
        
        provider = USStockProvider(api_key='test_key')
        
        with self.assertRaises(Exception):
            provider.get_kline('AAPL', '20240101', '20240102')
    
    @patch('data_provider.get_real_time_data')
    def test_get_realtime(self, mock_get_realtime):
        """测试获取美股实时行情"""
        from data_provider import USStockProvider
        
        mock_get_realtime.return_value = {
            'symbol': 'AAPL',
            'price': 150.5,
            'volume': 1000000
        }
        
        provider = USStockProvider(api_key='test_key')
        result = provider.get_realtime('AAPL')
        
        self.assertEqual(result['symbol'], 'AAPL')
        self.assertEqual(result['price'], 150.5)


class TestDataProvider(unittest.TestCase):
    """测试统一数据接口"""
    
    def test_get_provider_ashare(self):
        """测试获取 A 股数据提供者"""
        from data_provider import DataProvider, AShareProvider
        
        # 清除缓存
        DataProvider._providers = {}
        
        provider = DataProvider.get_provider('A 股')
        self.assertIsInstance(provider, AShareProvider)
    
    def test_get_provider_us(self):
        """测试获取美股数据提供者"""
        from data_provider import DataProvider, USStockProvider
        
        DataProvider._providers = {}
        
        with patch('data_provider.USStockProvider'):
            provider = DataProvider.get_provider('US')
            self.assertIsInstance(provider, USStockProvider)
    
    def test_get_provider_invalid_market(self):
        """测试无效市场类型"""
        from data_provider import DataProvider
        
        DataProvider._providers = {}
        
        with self.assertRaises(ValueError):
            DataProvider.get_provider('INVALID')
    
    @patch('data_provider.AShareProvider')
    def test_get_kline(self, mock_ashare_provider):
        """测试统一获取 K 线数据"""
        from data_provider import DataProvider
        
        DataProvider._providers = {}
        
        mock_provider = MagicMock()
        mock_provider.get_kline.return_value = pd.DataFrame({'close': [100, 101, 102]})
        mock_ashare_provider.return_value = mock_provider
        
        df = DataProvider.get_kline('000001', 'A 股', '20240101', '20240103')
        
        self.assertEqual(len(df), 3)
        mock_provider.get_kline.assert_called_once()
    
    @patch('data_provider.AShareProvider')
    def test_get_realtime(self, mock_ashare_provider):
        """测试统一获取实时行情"""
        from data_provider import DataProvider
        
        DataProvider._providers = {}
        
        mock_provider = MagicMock()
        mock_provider.get_realtime.return_value = {'price': 100.5}
        mock_ashare_provider.return_value = mock_provider
        
        result = DataProvider.get_realtime('000001', 'A 股')
        
        self.assertEqual(result['price'], 100.5)
    
    @patch('data_provider.AShareProvider')
    def test_get_fundamentals(self, mock_ashare_provider):
        """测试统一获取基本面数据"""
        from data_provider import DataProvider
        
        DataProvider._providers = {}
        
        mock_provider = MagicMock()
        mock_provider.get_fundamentals.return_value = {'pe_ratio': 15.5}
        mock_ashare_provider.return_value = mock_provider
        
        result = DataProvider.get_fundamentals('000001', 'A 股')
        
        self.assertEqual(result['pe_ratio'], 15.5)


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""
    
    def test_empty_date_range(self):
        """测试空日期范围"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = MagicMock()
        provider.ak.stock_zh_a_hist.return_value = pd.DataFrame()
        
        df = provider.get_kline('000001', '20240101', '20240101')
        
        self.assertTrue(df.empty)
    
    def test_invalid_symbol(self):
        """测试无效股票代码"""
        from data_provider import AShareProvider
        
        provider = AShareProvider()
        provider.ak = MagicMock()
        provider.ak.stock_zh_a_spot_em.return_value = pd.DataFrame()
        
        result = provider.get_realtime('INVALID')
        
        self.assertIn('error', result)
    
    def test_cache_file_corrupted(self):
        """测试缓存文件损坏"""
        from data_provider import AShareProvider
        import tempfile
        import os
        
        provider = AShareProvider()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            import data_provider
            data_provider.CACHE_DIR = tmpdir
            
            # 创建损坏的缓存文件
            cache_key = "ashare_000001_20240101_20240102"
            cache_file = os.path.join(tmpdir, f"{cache_key}.parquet")
            with open(cache_file, 'w') as f:
                f.write("corrupted data")
            
            # 应该能处理异常
            provider.ak = MagicMock()
            provider.ak.stock_zh_a_hist.return_value = pd.DataFrame({'close': [100]})
            
            df = provider.get_kline('000001', '20240101', '20240102')
            
            self.assertEqual(len(df), 1)
    
    def test_concurrent_cache_access(self):
        """测试并发缓存访问"""
        from data_provider import AShareProvider
        import tempfile
        import os
        import threading
        
        provider = AShareProvider()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            import data_provider
            data_provider.CACHE_DIR = tmpdir
            
            provider.ak = MagicMock()
            provider.ak.stock_zh_a_hist.return_value = pd.DataFrame({'close': [100]})
            
            errors = []
            
            def fetch_data():
                try:
                    provider.get_kline('000001', '20240101', '20240102')
                except Exception as e:
                    errors.append(e)
            
            # 创建多个线程同时访问
            threads = [threading.Thread(target=fetch_data) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
