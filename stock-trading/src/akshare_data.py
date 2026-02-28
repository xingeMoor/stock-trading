"""
A股数据获取模块 - 基于 akshare
文档: https://akshare.xyz/
安装: pip install akshare
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import akshare as ak
except ImportError:
    print("⚠️  akshare 未安装，请先运行: pip install akshare")
    ak = None

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd


class AShareDataProvider:
    """A股数据提供者"""
    
    def __init__(self):
        if ak is None:
            raise ImportError("akshare not installed. Run: pip install akshare")
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取A股所有股票列表"""
        return ak.stock_zh_a_spot_em()
    
    def get_daily_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票日线数据
        
        Args:
            symbol: 股票代码，如 "000001" (平安银行)
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
        """
        # 东方财富数据源
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        return df
    
    def get_realtime_data(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情数据"""
        try:
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == symbol]
            if stock_data.empty:
                return {'error': f'股票 {symbol} 未找到'}
            
            row = stock_data.iloc[0]
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
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_index_data(self, index_code: str = "sh000001") -> pd.DataFrame:
        """
        获取指数数据
        
        Args:
            index_code: 指数代码，如 "sh000001" (上证指数)
        """
        return ak.index_zh_a_hist(symbol=index_code, period="daily")
    
    def get_sector_data(self) -> pd.DataFrame:
        """获取板块行情数据"""
        return ak.stock_sector_spot()
    
    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """获取基本面数据"""
        try:
            # 个股信息
            info = ak.stock_individual_info_em(symbol=symbol)
            return {
                'symbol': symbol,
                'info': info.to_dict(),
                'market_cap': info.get('总市值', 0),
                'pe_ratio': info.get('市盈率', 0),
                'pb_ratio': info.get('市净率', 0)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_news_data(self, symbol: str) -> pd.DataFrame:
        """获取个股新闻"""
        return ak.stock_news_em(symbol=symbol)


def test_akshare():
    """测试 akshare 功能"""
    print("🧪 测试 akshare A股数据接口\n")
    
    try:
        provider = AShareDataProvider()
        
        # 1. 获取股票列表
        print("1️⃣  获取A股股票列表...")
        stocks = provider.get_stock_list()
        print(f"   ✅ 共获取 {len(stocks)} 只股票")
        print(f"   📊 前5只: {stocks['名称'].head(5).tolist()}")
        
        # 2. 获取单只股票历史数据
        print("\n2️⃣  获取平安银行(000001)历史数据...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        hist = provider.get_daily_data(
            "000001",
            start_date.strftime('%Y%m%d'),
            end_date.strftime('%Y%m%d')
        )
        print(f"   ✅ 获取 {len(hist)} 天数据")
        print(f"   📈 最新收盘价: {hist['收盘'].iloc[-1] if not hist.empty else 'N/A'}")
        
        # 3. 获取实时数据
        print("\n3️⃣  获取实时行情...")
        realtime = provider.get_realtime_data("000001")
        if 'error' not in realtime:
            print(f"   ✅ {realtime['name']} ({realtime['symbol']})")
            print(f"   💰 当前价格: ¥{realtime['price']}")
            print(f"   📊 涨跌幅: {realtime['change_pct']}%")
        else:
            print(f"   ⚠️  {realtime['error']}")
        
        # 4. 获取上证指数
        print("\n4️⃣  获取上证指数数据...")
        index_df = provider.get_index_data("sh000001")
        print(f"   ✅ 获取 {len(index_df)} 条记录")
        
        print("\n✅ 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_akshare()
