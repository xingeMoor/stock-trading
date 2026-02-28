"""
A股选股引擎 - 四层漏斗筛选
参考小红书博主架构 + 改进
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from data_provider import DataProvider

@dataclass
class StockScore:
    """股票评分结果"""
    symbol: str
    name: str
    sector: str
    total_score: float
    layer_scores: Dict[str, float]  # 各层得分
    metrics: Dict[str, Any]  # 关键指标
    
class StockSelector:
    """
    A股选股引擎 - 四层漏斗
    
    Layer 1: 板块强度筛选 (保留30%)
    Layer 2: 市值过滤 (保留50%)
    Layer 3: 技术指标动态阈值 (保留20%)
    Layer 4: 综合评分排序 (取TOP N)
    """
    
    def __init__(self, market: str = "A股"):
        self.market = market
        self.data_provider = DataProvider()
    
    def get_sector_strength(self, date: str) -> pd.DataFrame:
        """
        Layer 1: 获取板块强度
        
        Returns:
            板块排名，包含涨跌幅、资金流入等
        """
        try:
            from akshare import stock_sector_spot
            sectors = stock_sector_spot()
            
            # 计算板块强度分数
            sectors['strength_score'] = (
                sectors['涨跌幅'] * 0.4 +
                sectors['换手率'] * 0.3 +
                sectors['成交额'].rank(pct=True) * 20 * 0.3
            )
            
            return sectors.sort_values('strength_score', ascending=False)
        except Exception as e:
            print(f"❌ 获取板块强度失败: {e}")
            return pd.DataFrame()
    
    def filter_by_sector(self, stocks: pd.DataFrame, top_sectors: int = 10) -> pd.DataFrame:
        """
        Layer 1: 只保留强势板块的股票
        """
        sectors = self.get_sector_strength(datetime.now().strftime('%Y%m%d'))
        
        if sectors.empty:
            return stocks
        
        # 取TOP N板块
        strong_sectors = set(sectors.head(top_sectors)['板块名称'].tolist())
        
        # 过滤股票
        filtered = stocks[stocks['所属行业'].isin(strong_sectors)]
        
        print(f"   Layer 1: 板块筛选 {len(stocks)} → {len(filtered)} ({len(filtered)/len(stocks)*100:.1f}%)")
        
        return filtered
    
    def filter_by_market_cap(self, stocks: pd.DataFrame, 
                            min_cap: float = 50e8,  # 50亿
                            max_cap: float = 500e8) -> pd.DataFrame:
        """
        Layer 2: 市值过滤
        剔除太小（流动性差）和太大（弹性不足）的
        """
        # 获取市值数据
        stocks['市值'] = stocks['总市值'] if '总市值' in stocks.columns else 0
        
        filtered = stocks[
            (stocks['市值'] >= min_cap) & 
            (stocks['市值'] <= max_cap)
        ]
        
        print(f"   Layer 2: 市值筛选 {len(stocks)} → {len(filtered)} ({len(filtered)/len(stocks)*100:.1f}%)")
        
        return filtered
    
    def calculate_technical_score(self, symbol: str) -> Optional[Dict]:
        """
        Layer 3: 计算技术指标得分
        
        指标:
        - RSI: 超卖区域加分
        - MACD: 金叉加分
        - 均线: 多头排列加分
        - 成交量: 放量加分
        """
        try:
            # 获取历史数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            df = self.data_provider.get_kline(
                symbol, self.market,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            
            if len(df) < 30:
                return None
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            
            macd_golden_cross = macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]
            
            # 计算均线
            ma5 = df['close'].rolling(5).mean().iloc[-1]
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma60 = df['close'].rolling(60).mean().iloc[-1]
            
            bullish_arrangement = ma5 > ma20 > ma60
            
            # 成交量趋势
            vol_avg = df['volume'].rolling(20).mean().iloc[-1]
            vol_current = df['volume'].iloc[-1]
            volume_expansion = vol_current > vol_avg * 1.2
            
            # 综合评分 (0-100)
            score = 0
            details = {}
            
            # RSI评分 (超卖区域30以下加分)
            if current_rsi < 30:
                score += 25
                details['rsi'] = '超卖 (+25)'
            elif current_rsi < 40:
                score += 15
                details['rsi'] = '偏低 (+15)'
            elif current_rsi > 70:
                score -= 10
                details['rsi'] = '超买 (-10)'
            else:
                details['rsi'] = '中性 (0)'
            
            # MACD评分
            if macd_golden_cross:
                score += 25
                details['macd'] = '金叉 (+25)'
            elif macd.iloc[-1] > signal.iloc[-1]:
                score += 10
                details['macd'] = '多头 (+10)'
            else:
                details['macd'] = '空头 (0)'
            
            # 均线评分
            if bullish_arrangement:
                score += 25
                details['ma'] = '多头排列 (+25)'
            elif ma5 > ma20:
                score += 10
                details['ma'] = '短期多头 (+10)'
            else:
                details['ma'] = '空头排列 (0)'
            
            # 成交量评分
            if volume_expansion:
                score += 25
                details['volume'] = '放量 (+25)'
            else:
                details['volume'] = '平量 (0)'
            
            return {
                'score': score,
                'rsi': current_rsi,
                'macd_signal': 'golden_cross' if macd_golden_cross else 'bullish' if macd.iloc[-1] > signal.iloc[-1] else 'bearish',
                'ma_trend': 'bullish' if bullish_arrangement else 'neutral',
                'volume_trend': 'expansion' if volume_expansion else 'normal',
                'details': details
            }
            
        except Exception as e:
            print(f"      ⚠️  {symbol} 计算失败: {e}")
            return None
    
    def select_stocks(self, 
                     date: str = None,
                     max_stocks: int = 10,
                     min_score: float = 60) -> List[StockScore]:
        """
        执行四层漏斗选股
        
        Args:
            date: 选股日期 (默认今天)
            max_stocks: 最终选出股票数
            min_score: 最低技术评分
        
        Returns:
            选股结果列表
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        print(f"\n🎯 开始选股 ({date})")
        print("="*60)
        
        # Step 0: 获取全市场股票
        print("\n📊 获取全市场股票...")
        try:
            from akshare import stock_zh_a_spot_em
            all_stocks = stock_zh_a_spot_em()
            print(f"   ✅ 共 {len(all_stocks)} 只股票")
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")
            return []
        
        # Layer 1: 板块筛选
        print("\n🔍 Layer 1: 板块强度筛选...")
        stocks = self.filter_by_sector(all_stocks, top_sectors=10)
        
        # Layer 2: 市值筛选
        print("\n🔍 Layer 2: 市值筛选...")
        stocks = self.filter_by_market_cap(stocks, min_cap=50e8, max_cap=500e8)
        
        # Layer 3: 技术指标评分
        print("\n🔍 Layer 3: 技术指标评分...")
        scored_stocks = []
        
        for idx, row in stocks.head(100).iterrows():  # 只处理前100只提高效率
            symbol = row['代码']
            name = row['名称']
            sector = row.get('所属行业', 'Unknown')
            
            tech_score = self.calculate_technical_score(symbol)
            
            if tech_score and tech_score['score'] >= min_score:
                scored_stocks.append({
                    'symbol': symbol,
                    'name': name,
                    'sector': sector,
                    'total_score': tech_score['score'],
                    'layer_scores': {
                        'technical': tech_score['score']
                    },
                    'metrics': tech_score
                })
        
        print(f"   ✅ 技术评分通过: {len(scored_stocks)} 只")
        
        # Layer 4: 排序取TOP N
        print(f"\n🔍 Layer 4: 综合排序取TOP {max_stocks}...")
        
        # 按总分排序
        scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)
        
        selected = scored_stocks[:max_stocks]
        
        # 转换为StockScore对象
        results = [
            StockScore(
                symbol=s['symbol'],
                name=s['name'],
                sector=s['sector'],
                total_score=s['total_score'],
                layer_scores=s['layer_scores'],
                metrics=s['metrics']
            )
            for s in selected
        ]
        
        print(f"\n✅ 选股完成: {len(results)} 只股票")
        print("="*60)
        
        return results
    
    def format_report(self, stocks: List[StockScore]) -> str:
        """格式化选股报告"""
        report = f"""
📈 A股选股报告 ({datetime.now().strftime('%Y-%m-%d %H:%M')})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{"排名":<4} {"代码":<8} {"名称":<10} {"板块":<12} {"总分":<6} {"关键信号":<20}
{"─"*70}
"""
        
        for i, stock in enumerate(stocks, 1):
            metrics = stock.metrics
            key_signals = []
            
            if metrics.get('rsi', 50) < 35:
                key_signals.append("RSI超卖")
            if metrics.get('macd_signal') == 'golden_cross':
                key_signals.append("MACD金叉")
            if metrics.get('ma_trend') == 'bullish':
                key_signals.append("多头排列")
            if metrics.get('volume_trend') == 'expansion':
                key_signals.append("放量")
            
            signal_str = " | ".join(key_signals) if key_signals else "技术中性"
            
            report += f"{i:<4} {stock.symbol:<8} {stock.name:<10} {stock.sector:<12} {stock.total_score:<6.0f} {signal_str:<20}\n"
        
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 操作建议:
• 关注总分>75分的强势股
• RSI超卖+MACD金叉为最佳买点
• 建议分散配置3-5只不同板块
"""
        
        return report


def test_selector():
    """测试选股器"""
    print("🚀 测试A股选股引擎\n")
    
    selector = StockSelector(market="A股")
    
    # 执行选股
    selected = selector.select_stocks(
        date=datetime.now().strftime('%Y%m%d'),
        max_stocks=10,
        min_score=60
    )
    
    if selected:
        print(selector.format_report(selected))
    else:
        print("❌ 未选出符合条件的股票")


if __name__ == "__main__":
    test_selector()
