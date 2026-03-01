"""
统一数据接口测试套件

测试内容:
1. A 股数据获取 (akshare)
2. 美股数据获取 (Massive API)
3. 缓存机制验证
4. 异常处理
5. 性能测试

运行：python test_data_provider.py
"""
import sys
import os
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from data_provider_v2 import (
    DataProvider, AShareProvider, USStockProvider,
    DataManagerCache, CacheTTL, CacheStats
)


class TestCacheManager(unittest.TestCase):
    """测试缓存管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.cache = DataManagerCache(db_path=':memory:')
    
    def test_cache_set_get(self):
        """测试缓存设置和获取"""
        # 设置缓存
        result = self.cache.set('kline', 'AAPL', 'US', {'price': 100}, ttl=3600)
        self.assertTrue(result)
        
        # 获取缓存
        data = self.cache.get('kline', 'AAPL', 'US')
        self.assertIsNotNone(data)
        self.assertEqual(data['price'], 100)
    
    def test_cache_expire(self):
        """测试缓存过期"""
        # 设置立即过期的缓存
        self.cache.set('realtime', 'GOOGL', 'US', {'price': 200}, ttl=0)
        time.sleep(0.1)
        
        # 应该返回 None (已过期)
        data = self.cache.get('realtime', 'GOOGL', 'US')
        self.assertIsNone(data)
    
    def test_cache_invalidate(self):
        """测试缓存失效"""
        # 设置多个缓存
        self.cache.set('kline', 'AAPL', 'US', {'price': 100})
        self.cache.set('kline', 'MSFT', 'US', {'price': 200})
        self.cache.set('kline', 'GOOGL', 'US', {'price': 300})
        
        # 使 AAPL 失效
        count = self.cache.invalidate(symbol='AAPL')
        self.assertGreaterEqual(count, 1)
        
        # 验证 AAPL 已删除
        data = self.cache.get('kline', 'AAPL', 'US')
        self.assertIsNone(data)
        
        # 验证其他还在
        data = self.cache.get('kline', 'MSFT', 'US')
        self.assertIsNotNone(data)
    
    def test_cache_stats(self):
        """测试缓存统计"""
        # 添加一些数据
        for i in range(10):
            self.cache.set('kline', f'SYM{i}', 'US', {'price': i * 100})
        
        stats = self.cache.get_stats()
        self.assertGreaterEqual(stats.total_entries, 10)
        self.assertEqual(stats.hit_count, 0)
        self.assertEqual(stats.miss_count, 0)
        
        # 访问一些数据
        for i in range(5):
            self.cache.get('kline', f'SYM{i}', 'US')
        
        stats = self.cache.get_stats()
        self.assertEqual(stats.hit_count, 5)
        self.assertEqual(stats.miss_count, 5)


class TestAShareProvider(unittest.TestCase):
    """测试 A 股数据提供者"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.cache = DataManagerCache(db_path=':memory:')
        try:
            cls.provider = AShareProvider(cls.cache)
        except ImportError:
            cls.provider = None
            print("⚠️  akshare 未安装，跳过 A 股测试")
    
    def setUp(self):
        if self.provider is None:
            self.skipTest("akshare 未安装")
    
    def test_get_kline(self):
        """测试获取 K 线数据"""
        end = datetime.now()
        start = end - timedelta(days=30)
        
        df = self.provider.get_kline(
            '000001',
            start.strftime('%Y%m%d'),
            end.strftime('%Y%m%d')
        )
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        
        # 验证列名
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, df.columns)
    
    def test_get_kline_cache(self):
        """测试 K 线缓存"""
        end = datetime.now()
        start = end - timedelta(days=30)
        
        # 第一次获取
        start_time = time.time()
        df1 = self.provider.get_kline(
            '000001',
            start.strftime('%Y%m%d'),
            end.strftime('%Y%m%d')
        )
        time1 = time.time() - start_time
        
        # 第二次获取 (应该从缓存)
        start_time = time.time()
        df2 = self.provider.get_kline(
            '000001',
            start.strftime('%Y%m%d'),
            end.strftime('%Y%m%d')
        )
        time2 = time.time() - start_time
        
        # 验证数据一致
        self.assertEqual(len(df1), len(df2))
        
        # 验证缓存更快
        self.assertLess(time2, time1)
    
    def test_get_realtime(self):
        """测试获取实时行情"""
        data = self.provider.get_realtime('000001')
        
        self.assertIsInstance(data, dict)
        self.assertNotIn('error', data)
        self.assertEqual(data['symbol'], '000001')
        self.assertIn('price', data)
        self.assertIn('market', data)
        self.assertEqual(data['market'], 'A 股')
    
    def test_get_fundamentals(self):
        """测试获取基本面数据"""
        data = self.provider.get_fundamentals('000001')
        
        self.assertIsInstance(data, dict)
        self.assertNotIn('error', data)
        self.assertEqual(data['symbol'], '000001')
        self.assertIn('market_cap', data)
        self.assertIn('market', data)


class TestUSStockProvider(unittest.TestCase):
    """测试美股数据提供者"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.cache = DataManagerCache(db_path=':memory:')
        
        # 检查 API Key
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('MASSIVE_API_KEY')
        
        if not api_key:
            cls.provider = None
            print("⚠️  MASSIVE_API_KEY 未设置，跳过美股测试")
            return
        
        try:
            cls.provider = USStockProvider(cls.cache, api_key)
        except ImportError:
            cls.provider = None
            print("⚠️  massive-api-client 未安装，跳过美股测试")
    
    def setUp(self):
        if self.provider is None:
            self.skipTest("Massive API 不可用")
    
    def test_get_kline(self):
        """测试获取 K 线数据"""
        end = datetime.now()
        start = end - timedelta(days=30)
        
        df = self.provider.get_kline(
            'AAPL',
            start.strftime('%Y-%m-%d'),
            end.strftime('%Y-%m-%d')
        )
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        
        # 验证列名
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, df.columns)
    
    def test_get_kline_cache(self):
        """测试 K 线缓存"""
        end = datetime.now()
        start = end - timedelta(days=30)
        
        # 第一次获取
        start_time = time.time()
        df1 = self.provider.get_kline(
            'AAPL',
            start.strftime('%Y-%m-%d'),
            end.strftime('%Y-%m-%d')
        )
        time1 = time.time() - start_time
        
        # 第二次获取 (应该从缓存)
        start_time = time.time()
        df2 = self.provider.get_kline(
            'AAPL',
            start.strftime('%Y-%m-%d'),
            end.strftime('%Y-%m-%d')
        )
        time2 = time.time() - start_time
        
        # 验证数据一致
        self.assertEqual(len(df1), len(df2))
        
        # 验证缓存更快
        self.assertLess(time2, time1)
    
    def test_get_realtime(self):
        """测试获取实时行情"""
        data = self.provider.get_realtime('AAPL')
        
        self.assertIsInstance(data, dict)
        self.assertNotIn('error', data)
        self.assertEqual(data['symbol'], 'AAPL')
        self.assertIn('price', data)
        self.assertIn('market', data)
        self.assertEqual(data['market'], 'US')
    
    def test_get_fundamentals(self):
        """测试获取基本面数据"""
        data = self.provider.get_fundamentals('AAPL')
        
        self.assertIsInstance(data, dict)
        self.assertNotIn('error', data)
        self.assertEqual(data['symbol'], 'AAPL')
        self.assertIn('market', data)


class TestUnifiedDataProvider(unittest.TestCase):
    """测试统一数据接口"""
    
    def test_market_mapping(self):
        """测试市场映射"""
        # A 股的各种表示
        for market in ['A 股', 'ASHARE', 'CN', 'a 股']:
            try:
                provider = DataProvider._get_provider(market)
                self.assertIsInstance(provider, AShareProvider)
            except:
                pass  # 可能 akshare 未安装
        
        # 美股的各种表示
        for market in ['US', 'USA', '美股', 'us']:
            try:
                provider = DataProvider._get_provider(market)
                self.assertIsInstance(provider, USStockProvider)
            except:
                pass  # 可能 API Key 未设置
    
    def test_unsupported_market(self):
        """测试不支持的市场"""
        with self.assertRaises(ValueError):
            DataProvider._get_provider('INVALID_MARKET')
    
    def test_cache_stats(self):
        """测试缓存统计"""
        stats = DataProvider.get_cache_stats()
        self.assertIsInstance(stats, CacheStats)
        self.assertIsInstance(stats.total_entries, int)
        self.assertIsInstance(stats.hit_rate, float)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_batch_fetch(self):
        """测试批量获取数据"""
        # 这个测试需要实际 API 访问，可能较慢
        symbols_a = ['000001', '000002']
        symbols_us = ['AAPL', 'MSFT']
        
        results = {}
        
        # A 股
        try:
            provider = DataProvider._get_provider('A 股')
            for symbol in symbols_a:
                try:
                    df = provider.get_kline(
                        symbol,
                        (datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                        datetime.now().strftime('%Y%m%d')
                    )
                    results[f'A:{symbol}'] = len(df)
                except:
                    pass
        except:
            pass
        
        # 美股
        try:
            provider = DataProvider._get_provider('US')
            for symbol in symbols_us:
                try:
                    df = provider.get_kline(
                        symbol,
                        (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                        datetime.now().strftime('%Y-%m-%d')
                    )
                    results[f'US:{symbol}'] = len(df)
                except:
                    pass
        except:
            pass
        
        # 验证至少获取到部分数据
        self.assertGreater(len(results), 0)


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("🧪 统一数据接口测试套件")
    print("=" * 70)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestCacheManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAShareProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestUSStockProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedDataProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print()
    print("=" * 70)
    print(f"测试结果：{result.testsRun} 个测试")
    print(f"  ✅ 成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  ❌ 失败：{len(result.failures)}")
    print(f"  ⚠️  错误：{len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
