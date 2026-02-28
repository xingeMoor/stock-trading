"""
统一数据接口 - 支持A股+美股多数据源
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
import json
import os

# 缓存配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

class DataProviderBase(ABC):
    """数据提供者基类"""
    
    @abstractmethod
    def get_kline(self, symbol: str, start: str, end: str, **kwargs) -> pd.DataFrame:
        """获取K线数据"""
        pass
    
    @abstractmethod
    def get_realtime(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情"""
        pass
    
    @abstractmethod
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取基本面数据"""
        pass


class AShareProvider(DataProviderBase):
    """A股数据提供者 - 使用akshare"""
    
    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            raise ImportError("请安装akshare: pip install akshare")
    
    def get_kline(self, symbol: str, start: str, end: str, **kwargs) -> pd.DataFrame:
        """
        获取A股K线数据
        
        Args:
            symbol: 股票代码，如 "000001"
            start: 开始日期 YYYYMMDD
            end: 结束日期 YYYYMMDD
        """
        # 检查缓存
        cache_key = f"ashare_{symbol}_{start}_{end}"
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.parquet")
        
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if datetime.now().timestamp() - mtime < 3600:  # 1小时缓存
                return pd.read_parquet(cache_file)
        
        # 从akshare获取
        df = self.ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq"  # 前复权
        )
        
        # 标准化列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'change_pct',
            '涨跌额': 'change',
            '换手率': 'turnover'
        })
        
        # 保存缓存
        df.to_parquet(cache_file)
        
        return df
    
    def get_realtime(self, symbol: str) -> Dict[str, Any]:
        """获取A股实时行情"""
        try:
            df = self.ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == symbol]
            
            if stock.empty:
                return {'error': f'股票 {symbol} 未找到'}
            
            row = stock.iloc[0]
            return {
                'symbol': symbol,
                'name': row.get('名称', ''),
                'price': float(row.get('最新价', 0)),
                'open': float(row.get('今开', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'prev_close': float(row.get('昨收', 0)),
                'volume': int(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'market': 'A股',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取A股基本面数据"""
        try:
            info = self.ak.stock_individual_info_em(symbol=symbol)
            return {
                'symbol': symbol,
                'market_cap': info.get('总市值', 0),
                'pe_ratio': info.get('市盈率', 0),
                'pb_ratio': info.get('市净率', 0),
                'roe': info.get('ROE', 0),
                'industry': info.get('行业', ''),
                'market': 'A股'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_etf_list(self) -> pd.DataFrame:
        """获取ETF列表"""
        return self.ak.fund_etf_spot_em()
    
    def get_sector_strength(self) -> pd.DataFrame:
        """获取板块强度"""
        return self.ak.stock_sector_spot()


class USStockProvider(DataProviderBase):
    """美股数据提供者 - 使用Massive API"""
    
    def __init__(self, api_key: str = None):
        from .config import MASSIVE_API_KEY
        self.api_key = api_key or MASSIVE_API_KEY
    
    def get_kline(self, symbol: str, start: str, end: str, **kwargs) -> pd.DataFrame:
        """获取美股K线数据"""
        from .massive_api import get_aggs
        
        # 转换日期格式
        start_dt = datetime.strptime(start, '%Y%m%d')
        end_dt = datetime.strptime(end, '%Y%m%d')
        
        # 检查缓存
        cache_key = f"us_{symbol}_{start}_{end}"
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.parquet")
        
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if datetime.now().timestamp() - mtime < 3600:
                return pd.read_parquet(cache_file)
        
        # 从Massive API获取
        data = get_aggs(symbol, from_=start, to=end, timespan='day')
        
        if 'error' in data:
            raise Exception(data['error'])
        
        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'vwap': 'vwap'
        })
        
        # 保存缓存
        df.to_parquet(cache_file)
        
        return df
    
    def get_realtime(self, symbol: str) -> Dict[str, Any]:
        """获取美股实时行情"""
        from .massive_api import get_real_time_data
        return get_real_time_data(symbol)
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取美股基本面数据"""
        # Massive API暂不支持，返回空
        return {'symbol': symbol, 'market': 'US', 'note': 'Fundamentals not available'}


class DataProvider:
    """统一数据接口"""
    
    _providers = {}
    
    @classmethod
    def get_provider(cls, market: str) -> DataProviderBase:
        """获取市场对应的数据提供者"""
        if market not in cls._providers:
            if market == 'A股':
                cls._providers[market] = AShareProvider()
            elif market == 'US':
                cls._providers[market] = USStockProvider()
            else:
                raise ValueError(f"不支持的市场: {market}")
        
        return cls._providers[market]
    
    @classmethod
    def get_kline(cls, symbol: str, market: str, start: str, end: str, **kwargs) -> pd.DataFrame:
        """
        统一获取K线数据
        
        Args:
            symbol: 股票代码
            market: 市场 (A股/US)
            start: 开始日期 YYYYMMDD
            end: 结束日期 YYYYMMDD
        """
        provider = cls.get_provider(market)
        return provider.get_kline(symbol, start, end, **kwargs)
    
    @classmethod
    def get_realtime(cls, symbol: str, market: str) -> Dict[str, Any]:
        """统一获取实时行情"""
        provider = cls.get_provider(market)
        return provider.get_realtime(symbol)
    
    @classmethod
    def get_fundamentals(cls, symbol: str, market: str) -> Dict[str, Any]:
        """统一获取基本面数据"""
        provider = cls.get_provider(market)
        return provider.get_fundamentals(symbol)


def test_data_provider():
    """测试数据提供者"""
    print("🧪 测试统一数据接口\n")
    
    # 测试A股
    print("1️⃣  A股数据测试...")
    try:
        df = DataProvider.get_kline('000001', 'A股', '20250101', '20260228')
        print(f"   ✅ 平安银行: {len(df)} 条数据")
        print(f"   📊 最新收盘价: ¥{df['close'].iloc[-1]:.2f}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 测试美股
    print("\n2️⃣  美股数据测试...")
    try:
        df = DataProvider.get_kline('AAPL', 'US', '20250101', '20260228')
        print(f"   ✅ AAPL: {len(df)} 条数据")
        print(f"   📊 最新收盘价: ${df['close'].iloc[-1]:.2f}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_data_provider()
