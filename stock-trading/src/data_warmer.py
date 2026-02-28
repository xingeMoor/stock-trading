"""
数据预热服务 - Data Warmer
每天开盘前自动加载关键数据到内存，减少盘中延迟
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from typing import Dict, Any, List
import schedule
import time

from data_lake import DataLake
from data_provider import DataProvider

class DataWarmer:
    """
    数据预热服务
    
    功能:
    1. 每日盘前预热 (9:00启动，9:25完成)
    2. 加载核心股票池历史数据
    3. 计算并缓存技术指标
    4. 准备选股所需数据
    """
    
    def __init__(self):
        self.lake = DataLake()
        self.provider = DataProvider()
        
        # 核心股票池 (可配置)
        self.core_stocks = {
            "A股": [
                # 指数ETF
                "510300",  # 沪深300
                "510050",  # 上证50
                "159915",  # 创业板
                "588000",  # 科创50
                # 行业ETF
                "512760",  # 芯片
                "515030",  # 新能源
                "512010",  # 医药
                "159928",  # 消费
                # 个股 (可选)
                "000001",  # 平安银行
                "000858",  # 五粮液
                "002594",  # 比亚迪
                "600519",  # 贵州茅台
            ],
            "US": [
                "SPY",   # 标普500
                "QQQ",   # 纳斯达克100
                "AAPL",  # 苹果
                "MSFT",  # 微软
                "GOOGL", # 谷歌
                "AMZN",  # 亚马逊
                "TSLA",  # 特斯拉
                "NVDA",  # 英伟达
            ]
        }
        
        # 预热数据缓存
        self.warmed_data = {}
        self.warmed_indicators = {}
    
    def warm_daily(self):
        """
        执行每日预热
        在开盘前调用 (建议9:00-9:25)
        """
        print("\n" + "🔥"*30)
        print("   数据预热服务启动")
        print("🔥"*30)
        print(f"\n📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for market, symbols in self.core_stocks.items():
            print(f"\n{'='*60}")
            print(f"🌏 预热市场: {market}")
            print(f"{'='*60}")
            
            # 1. 检查并更新数据
            self._update_market_data(market, symbols)
            
            # 2. 加载到内存
            self._load_to_memory(market, symbols)
            
            # 3. 预计算指标
            self._precompute_indicators(market, symbols)
        
        print("\n" + "="*60)
        print("✅ 数据预热完成!")
        print("="*60)
        
        return self.warmed_data, self.warmed_indicators
    
    def _update_market_data(self, market: str, symbols: List[str]):
        """更新市场数据"""
        print(f"\n📥 更新数据...")
        
        updated = 0
        for symbol in symbols:
            try:
                # 检查是否需要更新
                range_info = self.lake.get_data_range(market, symbol)
                
                if range_info['last_date']:
                    last_date = datetime.strptime(range_info['last_date'], '%Y-%m-%d')
                    days_since_update = (datetime.now() - last_date).days
                    
                    if days_since_update <= 1:
                        print(f"   ⏭️  {symbol}: 已是最新 ({range_info['last_date']})")
                        continue
                
                # 从API获取最新数据
                print(f"   🔄 {symbol}: 下载更新...")
                
                if market == "A股":
                    from akshare import stock_zh_a_hist
                    df = stock_zh_a_hist(
                        symbol=symbol,
                        period="daily",
                        start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                        end_date=datetime.now().strftime('%Y%m%d'),
                        adjust="qfq"
                    )
                else:  # US
                    from massive_api import get_aggs
                    data = get_aggs(symbol, 
                                   from_=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                                   to=datetime.now().strftime('%Y-%m-%d'))
                    df = pd.DataFrame(data.get('data', []))
                
                if not df.empty:
                    self.lake.save_kline(market, symbol, df, source="warmer_update")
                    updated += 1
                    
            except Exception as e:
                print(f"   ❌ {symbol}: {e}")
        
        print(f"   ✅ 更新完成: {updated}/{len(symbols)} 只")
    
    def _load_to_memory(self, market: str, symbols: List[str]):
        """加载数据到内存"""
        print(f"\n💾 加载到内存...")
        
        self.warmed_data[market] = {}
        
        for symbol in symbols:
            try:
                # 加载最近120天数据
                df = self.lake.get_kline(
                    market, symbol,
                    start_date=(datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
                )
                
                if not df.empty:
                    self.warmed_data[market][symbol] = df
                    print(f"   ✅ {symbol}: {len(df)} 天")
                else:
                    print(f"   ⚠️  {symbol}: 无数据")
                    
            except Exception as e:
                print(f"   ❌ {symbol}: {e}")
        
        print(f"   📊 共加载 {len(self.warmed_data[market])} 只")
    
    def _precompute_indicators(self, market: str, symbols: List[str]):
        """预计算技术指标"""
        print(f"\n📐 预计算指标...")
        
        import pandas as pd
        import numpy as np
        
        self.warmed_indicators[market] = {}
        
        for symbol in symbols:
            if symbol not in self.warmed_data.get(market, {}):
                continue
            
            try:
                df = self.warmed_data[market][symbol].copy()
                
                if len(df) < 60:
                    continue
                
                indicators = {}
                
                # 均线系统
                df['ma5'] = df['close'].rolling(5).mean()
                df['ma10'] = df['close'].rolling(10).mean()
                df['ma20'] = df['close'].rolling(20).mean()
                df['ma60'] = df['close'].rolling(60).mean()
                
                # 最新均线状态
                latest = df.iloc[-1]
                indicators['ma_trend'] = 'bullish' if latest['ma5'] > latest['ma20'] else 'bearish'
                indicators['ma_distance'] = (latest['close'] - latest['ma20']) / latest['ma20'] * 100
                
                # RSI
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                indicators['rsi'] = df['rsi'].iloc[-1]
                indicators['rsi_signal'] = 'oversold' if indicators['rsi'] < 30 else 'overbought' if indicators['rsi'] > 70 else 'neutral'
                
                # MACD
                exp1 = df['close'].ewm(span=12, adjust=False).mean()
                exp2 = df['close'].ewm(span=26, adjust=False).mean()
                df['macd'] = exp1 - exp2
                df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
                indicators['macd'] = df['macd'].iloc[-1]
                indicators['macd_signal_line'] = df['macd_signal'].iloc[-1]
                indicators['macd_cross'] = 'golden' if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] and df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2] else 'dead' if df['macd'].iloc[-1] < df['macd_signal'].iloc[-1] and df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2] else 'none'
                
                # 波动率
                df['returns'] = df['close'].pct_change()
                indicators['volatility_20d'] = df['returns'].rolling(20).std() * np.sqrt(252) * 100  # 年化波动率
                
                # 成交量趋势
                df['volume_ma20'] = df['volume'].rolling(20).mean()
                indicators['volume_trend'] = 'expansion' if latest['volume'] > latest['volume_ma20'] * 1.2 else 'contraction'
                
                # 价格位置
                high_52w = df['high'].rolling(252).max()
                low_52w = df['low'].rolling(252).min()
                indicators['price_position'] = (latest['close'] - low_52w.iloc[-1]) / (high_52w.iloc[-1] - low_52w.iloc[-1]) * 100
                
                self.warmed_indicators[market][symbol] = indicators
                
            except Exception as e:
                print(f"   ❌ {symbol}: {e}")
        
        print(f"   📊 预计算完成: {len(self.warmed_indicators[market])} 只")
    
    def get_warmed_data(self, symbol: str, market: str = "A股") -> Dict:
        """获取预热后的数据"""
        return {
            'kline': self.warmed_data.get(market, {}).get(symbol),
            'indicators': self.warmed_indicators.get(market, {}).get(symbol)
        }
    
    def get_all_warmed_symbols(self, market: str = "A股") -> List[str]:
        """获取所有已预热的股票"""
        return list(self.warmed_data.get(market, {}).keys())
    
    def schedule_daily_warmup(self, warmup_time: str = "09:00"):
        """
        设置每日定时预热
        
        Args:
            warmup_time: 预热时间，默认9:00
        """
        schedule.every().day.at(warmup_time).do(self.warm_daily)
        
        print(f"⏰ 已设置每日 {warmup_time} 自动预热")
        
        # 保持运行
        while True:
            schedule.run_pending()
            time.sleep(60)


def test_warmer():
    """测试数据预热服务"""
    print("🧪 测试数据预热服务\n")
    
    warmer = DataWarmer()
    
    # 使用更小的股票池测试
    warmer.core_stocks = {
        "A股": ["000001", "510300"],
        "US": ["SPY"]
    }
    
    # 执行预热
    data, indicators = warmer.warm_daily()
    
    print("\n" + "="*60)
    print("📊 预热结果统计")
    print("="*60)
    
    for market in ["A股", "US"]:
        if market in data:
            print(f"\n{market}:")
            print(f"   数据: {len(data[market])} 只")
            print(f"   指标: {len(indicators.get(market, {}))} 只")
            
            # 展示第一个的指标
            if indicators.get(market):
                first_sym = list(indicators[market].keys())[0]
                print(f"\n   示例 {first_sym}:")
                for k, v in list(indicators[market][first_sym].items())[:5]:
                    print(f"      {k}: {v:.2f}" if isinstance(v, float) else f"      {k}: {v}")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_warmer()
