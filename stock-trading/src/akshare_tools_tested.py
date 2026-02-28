"""
经过测试的 AkShare Tools - 只保留可用的工具
测试时间: 2026-02-28
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    print("⚠️  请先安装: pip install akshare pandas")
    raise

MAX_ROWS = 1000

# ============ 股票数据工具 (已测试通过) ============

def get_stock_list() -> dict:
    """获取A股所有股票列表 - ✅ 测试通过"""
    try:
        df = ak.stock_zh_a_spot_em()
        return {
            "status": "success",
            "count": len(df),
            "data": df.head(MAX_ROWS).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_stock_daily(symbol: str, start_date: str, end_date: str) -> dict:
    """
    获取股票日线数据 - ✅ 测试通过
    
    Args:
        symbol: 股票代码，如 "000001"
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
    """
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        return {
            "status": "success",
            "symbol": symbol,
            "count": len(df),
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_stock_realtime(symbol: str = None) -> dict:
    """获取实时行情 - ✅ 测试通过"""
    try:
        df = ak.stock_zh_a_spot_em()
        if symbol:
            df = df[df['代码'] == symbol]
            if df.empty:
                return {"status": "error", "message": f"股票 {symbol} 未找到"}
        return {
            "status": "success",
            "count": len(df),
            "data": df.head(MAX_ROWS).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============ 指数数据工具 (已测试通过) ============

def get_index_data(index_code: str = "sh000001") -> dict:
    """
    获取指数历史数据 - ✅ 测试通过
    
    Args:
        index_code: 指数代码，如 "sh000001" (上证指数)
    """
    try:
        df = ak.index_zh_a_hist(symbol=index_code, period="daily")
        return {
            "status": "success",
            "index_code": index_code,
            "count": len(df),
            "data": df.tail(MAX_ROWS).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_index_realtime() -> dict:
    """获取指数实时行情 - ✅ 测试通过"""
    try:
        df = ak.index_zh_a_spot_em()
        return {
            "status": "success",
            "count": len(df),
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============ 基金数据工具 (已测试通过) ============

def get_etf_list() -> dict:
    """获取ETF列表 - ✅ 测试通过"""
    try:
        df = ak.fund_etf_spot_em()
        return {
            "status": "success",
            "count": len(df),
            "data": df.head(MAX_ROWS).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_etf_hist(symbol: str, period: str = "daily") -> dict:
    """
    获取ETF历史数据 - ✅ 测试通过
    
    Args:
        symbol: ETF代码，如 "510300"
        period: daily/weekly/monthly
    """
    try:
        # 自动添加前缀
        if not symbol.startswith(('sh', 'sz')):
            symbol = 'sh' + symbol if symbol.startswith('5') else 'sz' + symbol
        
        df = ak.fund_etf_hist_em(
            symbol=symbol.replace('sh', '').replace('sz', ''),
            period=period,
            start_date="20240101",
            end_date="20261231",
            adjust="qfq"
        )
        return {
            "status": "success",
            "symbol": symbol,
            "count": len(df),
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============ 期货数据工具 (已测试通过) ============

def get_futures_list() -> dict:
    """获取期货合约列表 - ✅ 测试通过"""
    try:
        df = ak.futures_zh_realtime(symbol="主力连续")
        return {
            "status": "success",
            "count": len(df),
            "data": df.head(MAX_ROWS).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============ 测试函数 ============

def run_all_tests():
    """运行所有工具测试"""
    print("🧪 开始测试 AkShare Tools\n")
    
    tests = [
        ("股票列表", lambda: get_stock_list()),
        ("股票日线", lambda: get_stock_daily("000001", "20250101", "20260228")),
        ("实时行情", lambda: get_stock_realtime()),
        ("指数数据", lambda: get_index_data("sh000001")),
        ("指数实时", lambda: get_index_realtime()),
        ("ETF列表", lambda: get_etf_list()),
        ("ETF历史", lambda: get_etf_hist("510300")),
        ("期货列表", lambda: get_futures_list()),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result.get("status") == "success":
                print(f"✅ {name}: 通过 ({result.get('count', 0)} 条数据)")
                passed += 1
            else:
                print(f"❌ {name}: 失败 - {result.get('message', '未知错误')}")
                failed += 1
        except Exception as e:
            print(f"❌ {name}: 异常 - {e}")
            failed += 1
    
    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")
    return passed, failed

if __name__ == "__main__":
    run_all_tests()
