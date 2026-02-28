"""
AkShare 简化版工具 - 基础功能
注意: 需要安装 akshare: pip install akshare
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import akshare as ak
except ImportError:
    print("⚠️  akshare 未安装，请先运行: pip install akshare")
    ak = None

def get_a_stock_list():
    """获取A股股票列表"""
    if not ak:
        return {"error": "akshare not installed"}
    try:
        df = ak.stock_zh_a_spot_em()
        return {
            "total": len(df),
            "stocks": df[['代码', '名称', '最新价', '涨跌幅']].head(100).to_dict('records')
        }
    except Exception as e:
        return {"error": str(e)}

def get_stock_daily(symbol, start_date, end_date):
    """获取股票日线数据"""
    if not ak:
        return {"error": "akshare not installed"}
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
        return {
            "symbol": symbol,
            "data": df.to_dict('records') if not df.empty else []
        }
    except Exception as e:
        return {"error": str(e)}

def get_index_list():
    """获取指数列表"""
    if not ak:
        return {"error": "akshare not installed"}
    try:
        df = ak.index_stock_info()
        return {
            "total": len(df),
            "indices": df.head(50).to_dict('records')
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("🧪 测试 AkShare 工具 (简化版)\n")
    
    # 测试股票列表
    print("1️⃣  测试股票列表...")
    result = get_a_stock_list()
    print(f"   {'✅' if 'stocks' in result else '❌'} {result.get('total', 0)} 只股票")
    
    # 测试个股数据
    print("\n2️⃣  测试平安银行历史数据...")
    result = get_stock_daily("000001", "20250101", "20260228")
    print(f"   {'✅' if 'data' in result else '❌'} {len(result.get('data', []))} 条记录")
    
    print("\n✅ 测试完成")
