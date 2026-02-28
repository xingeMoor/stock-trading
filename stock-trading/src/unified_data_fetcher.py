"""
统一数据获取器
优先使用 Massive API，失败时自动降级到 Yahoo Finance
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from yahoo_data import fetch_yahoo_data

# 尝试导入 Massive
try:
    from massive import RESTClient
    MASSIVE_AVAILABLE = True
except ImportError:
    MASSIVE_AVAILABLE = False
    print("⚠️  Massive 库未安装，将使用 Yahoo Finance")

# API Key
MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY', 'yLk1LGqL2zxTV8s04rogmJ8x2duhUYtV')


class UnifiedDataFetcher:
    """
    统一数据获取器
    
    优先级:
    1. Massive API (如果可用且有权限)
    2. Yahoo Finance (免费备用)
    3. 本地缓存
    """
    
    def __init__(self):
        self.massive_client = None
        self.massive_working = False
        
        if MASSIVE_AVAILABLE:
            try:
                self.massive_client = RESTClient(api_key=MASSIVE_API_KEY)
                # 测试连接
                self._test_massive_connection()
            except Exception as e:
                print(f"⚠️  Massive 初始化失败: {e}")
    
    def _test_massive_connection(self):
        """测试 Massive 连接"""
        try:
            # 尝试获取市场状态（通常不需要特殊权限）
            status = self.massive_client.get_market_status()
            print("✅ Massive API 连接正常")
            self.massive_working = True
        except Exception as e:
            if "NOT_AUTHORIZED" in str(e):
                print("⚠️  Massive API 需要升级订阅，将使用 Yahoo Finance")
            else:
                print(f"⚠️  Massive API 错误: {e}")
            self.massive_working = False
    
    def get_stock_data(
        self,
        symbol: str,
        start: str,
        end: str,
        prefer_source: str = "auto"  # auto, massive, yahoo
    ) -> Optional[pd.DataFrame]:
        """
        获取股票数据
        
        Args:
            symbol: 股票代码
            start: 开始日期 (YYYY-MM-DD 或 YYYYMMDD)
            end: 结束日期
            prefer_source: 首选数据源
        
        Returns:
            DataFrame with OHLCV data
        """
        # 标准化日期格式
        if len(start) == 8:
            start = f"{start[:4]}-{start[4:6]}-{start[6:]}"
        if len(end) == 8:
            end = f"{end[:4]}-{end[4:6]}-{end[6:]}"
        
        # 尝试 Massive
        if prefer_source in ["auto", "massive"] and self.massive_working:
            df = self._fetch_from_massive(symbol, start, end)
            if df is not None and not df.empty:
                print(f"   ✅ {symbol}: Massive API")
                return df
        
        # 降级到 Yahoo Finance
        if prefer_source in ["auto", "yahoo"]:
            df = fetch_yahoo_data(symbol, start, end)
            if df is not None and not df.empty:
                print(f"   ✅ {symbol}: Yahoo Finance")
                return df
        
        return None
    
    def _fetch_from_massive(self, symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """从 Massive 获取数据"""
        try:
            aggs = self.massive_client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan="day",
                from_=start,
                to=end
            )
            
            agg_list = list(aggs)
            if not agg_list:
                return None
            
            data = []
            for item in agg_list:
                data.append({
                    'date': datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    'open': float(item.open),
                    'high': float(item.high),
                    'low': float(item.low),
                    'close': float(item.close),
                    'volume': int(item.volume)
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            if "NOT_AUTHORIZED" in str(e):
                self.massive_working = False  # 标记为不可用
            return None
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """获取最新价格"""
        # 尝试 Massive
        if self.massive_working:
            try:
                trade = self.massive_client.get_last_trade(symbol)
                return float(trade.price)
            except:
                pass
        
        # 降级到 Yahoo
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('regularMarketPrice') or info.get('previousClose')
        except:
            pass
        
        return None
    
    def batch_fetch(
        self,
        symbols: list,
        start: str,
        end: str,
        max_workers: int = 4
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        def fetch_one(symbol):
            df = self.get_stock_data(symbol, start, end)
            return symbol, df
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_one, sym): sym for sym in symbols}
            
            for future in as_completed(futures):
                symbol, df = future.result()
                if df is not None and not df.empty:
                    results[symbol] = df
        
        return results


def test_unified_fetcher():
    """测试统一数据获取器"""
    print("🧪 测试统一数据获取器\n")
    
    fetcher = UnifiedDataFetcher()
    
    # 测试单只股票
    print("1️⃣  获取 AAPL 最近30天...")
    end = datetime.now()
    start = end - timedelta(days=30)
    
    df = fetcher.get_stock_data("AAPL", start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    if df is not None and not df.empty:
        print(f"\n   📊 数据预览:")
        print(df.tail(3).to_string())
    else:
        print("   ❌ 获取失败")
    
    # 测试批量获取
    print("\n2️⃣  批量获取多只股票...")
    symbols = ["MSFT", "GOOGL", "AMZN"]
    results = fetcher.batch_fetch(symbols, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    print(f"\n   ✅ 成功获取 {len(results)}/{len(symbols)} 只")
    for sym, data in results.items():
        print(f"      {sym}: {len(data)} 条记录")
    
    # 测试最新价格
    print("\n3️⃣  获取最新价格...")
    price = fetcher.get_last_price("AAPL")
    if price:
        print(f"   ✅ AAPL: ${price:.2f}")
    else:
        print("   ❌ 获取失败")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_unified_fetcher()
