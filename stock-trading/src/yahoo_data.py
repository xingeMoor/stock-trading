"""
Yahoo Finance 数据源
作为 Massive API 的免费备用方案
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time

# Yahoo Finance 缓存
cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'yahoo_cache')
os.makedirs(cache_dir, exist_ok=True)


def fetch_yahoo_data(symbol: str, start: str, end: str, interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    从 Yahoo Finance 获取股票数据
    
    Args:
        symbol: 股票代码 (如 AAPL, MSFT)
        start: 开始日期 YYYY-MM-DD
        end: 结束日期 YYYY-MM-DD
        interval: 时间间隔 (1d=日线, 1h=小时线)
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        import yfinance as yf
        
        # 转换日期格式
        if len(start) == 8:  # YYYYMMDD
            start = f"{start[:4]}-{start[4:6]}-{start[6:]}"
        if len(end) == 8:
            end = f"{end[:4]}-{end[4:6]}-{end[6:]}"
        
        # 下载数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval)
        
        if df.empty:
            return None
        
        # 标准化列名
        df = df.reset_index()
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        
        # 确保列名一致
        column_map = {
            'date': 'date',
            'datetime': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'adj_close': 'adj_close',
            'volume': 'volume'
        }
        
        df = df.rename(columns=column_map)
        
        # 格式化日期
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        return df
        
    except Exception as e:
        print(f"❌ Yahoo Finance 获取失败 {symbol}: {e}")
        return None


def fetch_batch(symbols: list, start: str, end: str) -> Dict[str, pd.DataFrame]:
    """
    批量获取多只股票数据
    """
    results = {}
    
    for i, symbol in enumerate(symbols):
        print(f"   📥 获取 {symbol} ({i+1}/{len(symbols)})...")
        
        df = fetch_yahoo_data(symbol, start, end)
        if df is not None and not df.empty:
            results[symbol] = df
            print(f"      ✅ {len(df)} 条记录")
        else:
            print(f"      ❌ 无数据")
        
        # 避免速率限制
        time.sleep(0.5)
    
    return results


def get_sp500_symbols() -> list:
    """获取标普500成分股列表"""
    try:
        import yfinance as yf
        
        # 使用 SPY ETF 持仓作为参考
        spy = yf.Ticker("SPY")
        holdings = spy.info.get('holdings', [])
        
        if holdings:
            return [h.get('symbol') for h in holdings if h.get('symbol')]
        
        # 备用：返回主要大盘股
        return [
            "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "BRK-B",
            "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "BAC", "ABBV", "PFE",
            "KO", "PEP", "WMT", "MRK", "CSCO", "ABT", "CVX", "ACN", "XOM",
            "LLY", "TMO", "AVGO", "DIS", "COST", "VZ", "ADBE", "CRM", "TXN",
            "NKE", "WFC", "BMY", "QCOM", "NEE", "RTX", "HON", "INTC", "LIN",
            "UPS", "LOW", "AMD", "PM", "SPGI", "AMGN", "CAT", "GS", "SBUX",
            "MS", "BLK", "IBM", "GE", "T", "DE", "LMT", "BA", "MMM", "CVS"
        ]
    except:
        return []


def test_yahoo():
    """测试 Yahoo Finance 连接"""
    print("🧪 测试 Yahoo Finance 数据源\n")
    
    # 测试单只股票
    print("1️⃣  获取 AAPL 最近30天数据...")
    end = datetime.now()
    start = end - timedelta(days=30)
    
    df = fetch_yahoo_data("AAPL", start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    if df is not None and not df.empty:
        print(f"   ✅ 成功! {len(df)} 条记录")
        print(f"   📊 最新数据:")
        latest = df.iloc[-1]
        print(f"      日期: {latest['date']}")
        print(f"      收盘: ${latest['close']:.2f}")
        print(f"      成交量: {int(latest['volume']):,}")
    else:
        print("   ❌ 失败")
    
    # 测试多只股票
    print("\n2️⃣  批量获取多只股票...")
    symbols = ["MSFT", "GOOGL", "AMZN", "TSLA"]
    results = fetch_batch(symbols, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    print(f"\n   ✅ 成功获取 {len(results)}/{len(symbols)} 只股票")
    for sym, data in results.items():
        if not data.empty:
            print(f"      {sym}: ${data['close'].iloc[-1]:.2f}")
    
    print("\n✅ Yahoo Finance 测试完成!")


if __name__ == "__main__":
    test_yahoo()
