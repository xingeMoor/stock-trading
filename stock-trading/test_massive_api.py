"""
测试所有 Massive API 接口
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.massive_api import (
    get_aggs, get_last_trade, get_last_quote, get_sma, get_ema,
    get_macd, get_rsi, get_stoch, get_cci, get_adx, get_williams_r,
    get_snapshot_ticker, get_market_status, get_real_time_data,
    get_all_indicators, list_tickers, list_dividends, list_splits
)

def test_api(name, func, *args, **kwargs):
    """测试单个 API"""
    print(f"\n{'='*60}")
    print(f"🧪 测试：{name}")
    print(f"{'='*60}")
    
    try:
        result = func(*args, **kwargs)
        
        if 'error' in result:
            print(f"❌ 错误：{result['error']}")
            return False
        else:
            print(f"✅ 成功")
            
            # 打印关键信息
            if 'symbol' in result:
                print(f"   股票：{result['symbol']}")
            
            if 'price' in result:
                print(f"   价格：${result['price']}")
            
            if 'data' in result and isinstance(result['data'], list):
                print(f"   数据条数：{len(result['data'])}")
            
            if 'last_trade' in result and isinstance(result['last_trade'], dict):
                print(f"   最新交易：${result['last_trade'].get('price', 'N/A')}")
            
            return True
            
    except Exception as e:
        print(f"❌ 异常：{e}")
        return False

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 Massive API 全面测试")
    print("="*60)
    
    test_symbol = "AAPL"
    results = {}
    
    # 1. K 线数据
    results['get_aggs'] = test_api(
        "聚合数据 (K 线)",
        get_aggs,
        test_symbol,
        from_="2026-02-01",
        to="2026-02-28"
    )
    
    # 2. 最新交易
    results['get_last_trade'] = test_api(
        "最新成交",
        get_last_trade,
        test_symbol
    )
    
    # 3. 最新报价
    results['get_last_quote'] = test_api(
        "最新买卖报价",
        get_last_quote,
        test_symbol
    )
    
    # 4. SMA
    results['get_sma'] = test_api(
        "SMA 指标",
        get_sma,
        test_symbol,
        window=20,
        from_="2026-02-01"
    )
    
    # 5. EMA
    results['get_ema'] = test_api(
        "EMA 指标",
        get_ema,
        test_symbol,
        window=20,
        from_="2026-02-01"
    )
    
    # 6. MACD
    results['get_macd'] = test_api(
        "MACD 指标",
        get_macd,
        test_symbol,
        from_="2026-02-01"
    )
    
    # 7. RSI
    results['get_rsi'] = test_api(
        "RSI 指标",
        get_rsi,
        test_symbol,
        window=14,
        from_="2026-02-01"
    )
    
    # 8. 随机指标
    results['get_stoch'] = test_api(
        "随机指标 (Stoch)",
        get_stoch,
        test_symbol,
        from_="2026-02-01"
    )
    
    # 9. CCI
    results['get_cci'] = test_api(
        "CCI 指标",
        get_cci,
        test_symbol,
        from_="2026-02-01"
    )
    
    # 10. ADX
    results['get_adx'] = test_api(
        "ADX 指标",
        get_adx,
        test_symbol,
        from_="2026-02-01"
    )
    
    # 11. Williams %R
    results['get_williams_r'] = test_api(
        "威廉指标",
        get_williams_r,
        test_symbol,
        from_="2026-02-01"
    )
    
    # 12. 股票快照
    results['get_snapshot_ticker'] = test_api(
        "股票快照",
        get_snapshot_ticker,
        test_symbol
    )
    
    # 13. 市场状态
    results['get_market_status'] = test_api(
        "市场状态",
        get_market_status
    )
    
    # 14. 实时数据
    results['get_real_time_data'] = test_api(
        "实时数据",
        get_real_time_data,
        test_symbol
    )
    
    # 15. 所有指标
    results['get_all_indicators'] = test_api(
        "所有技术指标",
        get_all_indicators,
        test_symbol
    )
    
    # 16. 股票列表
    results['list_tickers'] = test_api(
        "股票列表",
        list_tickers,
        limit=10
    )
    
    # 17. 分红数据
    results['list_dividends'] = test_api(
        "分红数据",
        list_dividends,
        test_symbol
    )
    
    # 18. 拆股数据
    results['list_splits'] = test_api(
        "拆股数据",
        list_splits,
        test_symbol
    )
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"总测试：{total}")
    print(f"✅ 通过：{passed}")
    print(f"❌ 失败：{failed}")
    
    if failed > 0:
        print("\n失败的测试:")
        for name, result in results.items():
            if not result:
                print(f"  - {name}")
    
    print("\n" + "="*60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
