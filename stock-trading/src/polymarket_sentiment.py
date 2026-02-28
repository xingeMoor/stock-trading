"""
Polymarket 市场情绪分析
Polymarket 是一个预测市场平台，反映了市场对各类事件的真实预期
API文档: https://docs.polymarket.com/
"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

class PolymarketSentiment:
    """
    Polymarket 情绪分析器
    
    通过分析预测市场的价格（即概率），获取市场情绪指标
    """
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    # 与股市相关的重要市场分类
    MARKET_CATEGORIES = {
        'economy': '经济形势',
        'fed_policy': '美联储政策',
        'elections': '选举政治',
        'crypto': '加密货币',
        'tech_earnings': '科技财报'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_active_markets(self, limit: int = 50) -> List[Dict]:
        """
        获取活跃的市场列表
        
        Returns:
            活跃市场列表，包含标题、概率、交易量等
        """
        try:
            url = f"{self.BASE_URL}/markets"
            params = {
                'active': 'true',
                'closed': 'false',
                'limit': limit,
                'sort': 'volume',  # 按交易量排序
                'order': 'desc'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                markets = []
                
                for market in data.get('markets', []):
                    markets.append({
                        'id': market.get('id'),
                        'title': market.get('question'),
                        'probability': market.get('probability'),  # 当前概率 0-1
                        'volume': market.get('volume'),  # 交易量
                        'liquidity': market.get('liquidity'),  # 流动性
                        'category': self._categorize_market(market.get('question', '')),
                        'end_date': market.get('endDate'),
                        'created_at': market.get('createdAt')
                    })
                
                return markets
            else:
                return [{'error': f'HTTP {response.status_code}'}]
                
        except Exception as e:
            return [{'error': str(e)}]
    
    def _categorize_market(self, title: str) -> str:
        """根据标题分类市场"""
        title_lower = title.lower()
        
        keywords = {
            'economy': ['gdp', 'recession', 'inflation', 'cpi', 'unemployment', 'jobs'],
            'fed_policy': ['fed', 'federal reserve', 'interest rate', 'rate hike', 'powell'],
            'elections': ['election', 'trump', 'biden', 'vote', 'poll'],
            'crypto': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto'],
            'tech_earnings': ['apple', 'google', 'meta', 'amazon', 'tesla', 'earnings']
        }
        
        for category, words in keywords.items():
            if any(word in title_lower for word in words):
                return category
        
        return 'other'
    
    def get_economy_sentiment(self) -> Dict[str, Any]:
        """
        获取经济情绪指标
        
        Returns:
            综合经济情绪评分 -1(悲观) 到 +1(乐观)
        """
        markets = self.get_active_markets(limit=100)
        
        if not markets or 'error' in markets[0]:
            return {'error': '无法获取数据'}
        
        economy_markets = [m for m in markets if m.get('category') == 'economy']
        fed_markets = [m for m in markets if m.get('category') == 'fed_policy']
        
        sentiment_score = 0
        total_volume = 0
        
        # 分析经济相关市场
        for market in economy_markets:
            prob = market.get('probability', 0.5)
            volume = market.get('volume', 0)
            
            # 判断是正面还是负面事件
            title = market.get('title', '').lower()
            
            if any(word in title for word in ['recession', 'crash', 'default', 'crisis']):
                # 负面事件：概率越高越悲观
                sentiment = -(prob * 2 - 1)  # -1 to 1
            else:
                # 正面事件：概率越高越乐观
                sentiment = prob * 2 - 1  # -1 to 1
            
            sentiment_score += sentiment * volume
            total_volume += volume
        
        # 分析美联储政策
        for market in fed_markets:
            prob = market.get('probability', 0.5)
            volume = market.get('volume', 0)
            
            title = market.get('title', '').lower()
            
            if any(word in title for word in ['hike', 'raise', 'increase']):
                # 加息：概率高对股市偏负面
                sentiment = -(prob * 2 - 1)
            elif any(word in title for word in ['cut', 'lower', 'decrease']):
                # 降息：概率高对股市偏正面
                sentiment = prob * 2 - 1
            else:
                sentiment = 0
            
            sentiment_score += sentiment * volume
            total_volume += volume
        
        if total_volume > 0:
            final_score = sentiment_score / total_volume
        else:
            final_score = 0
        
        return {
            'sentiment_score': round(final_score, 3),  # -1 to 1
            'interpretation': self._interpret_score(final_score),
            'economy_markets_count': len(economy_markets),
            'fed_markets_count': len(fed_markets),
            'total_volume': total_volume,
            'timestamp': datetime.now().isoformat()
        }
    
    def _interpret_score(self, score: float) -> str:
        """解释情绪分数"""
        if score > 0.5:
            return "强烈乐观 - 市场普遍看好经济和政策"
        elif score > 0.2:
            return "温和乐观 - 市场情绪偏正面"
        elif score > -0.2:
            return "中性 - 市场情绪平衡"
        elif score > -0.5:
            return "温和悲观 - 市场情绪偏负面"
        else:
            return "强烈悲观 - 市场担忧经济和政策风险"
    
    def get_crypto_correlation(self) -> Dict[str, Any]:
        """
        获取加密货币与传统市场的相关性情绪
        """
        markets = self.get_active_markets(limit=100)
        
        crypto_markets = [m for m in markets if m.get('category') == 'crypto']
        
        if not crypto_markets:
            return {'error': '无加密货币市场数据'}
        
        btc_markets = [m for m in crypto_markets if 'bitcoin' in m.get('title', '').lower() or 'btc' in m.get('title', '').lower()]
        
        if btc_markets:
            avg_probability = sum(m.get('probability', 0) for m in btc_markets) / len(btc_markets)
            avg_volume = sum(m.get('volume', 0) for m in btc_markets) / len(btc_markets)
            
            return {
                'btc_sentiment': '看涨' if avg_probability > 0.5 else '看跌',
                'btc_probability': round(avg_probability, 3),
                'avg_volume': round(avg_volume, 2),
                'markets_analyzed': len(btc_markets),
                'correlation_hint': '高风险偏好' if avg_probability > 0.6 else '避险情绪' if avg_probability < 0.4 else '中性'
            }
        
        return {'error': '无BTC相关市场'}
    
    def generate_sentiment_report(self) -> str:
        """生成情绪分析报告"""
        economy = self.get_economy_sentiment()
        crypto = self.get_crypto_correlation()
        
        report = f"""
📊 Polymarket 市场情绪报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🌍 宏观经济情绪
━━━━━━━━━━━━━━━━━━━━━
情绪评分: {economy.get('sentiment_score', 'N/A')} ({economy.get('interpretation', 'N/A')})
参考市场数: 经济{economy.get('economy_markets_count', 0)}个 | 美联储{economy.get('fed_markets_count', 0)}个
总交易量: ${economy.get('total_volume', 0):,.0f}

💡 交易启示:
"""
        
        score = economy.get('sentiment_score', 0)
        if score > 0.3:
            report += "• 市场情绪乐观，可考虑增加风险资产配置\n"
            report += "• 关注成长股和高Beta股票\n"
        elif score < -0.3:
            report += "• 市场情绪悲观，建议降低仓位或对冲风险\n"
            report += "• 关注防御性板块和避险资产\n"
        else:
            report += "• 市场情绪中性，保持均衡配置\n"
            report += "• 关注结构性机会\n"
        
        if 'btc_probability' in crypto:
            report += f"\n₿ 加密货币情绪\n━━━━━━━━━━━━━━━━━━━━━\n"
            report += f"BTC预期: {crypto.get('btc_sentiment')} (概率{crypto.get('btc_probability', 0):.1%})\n"
            report += f"风险偏好: {crypto.get('correlation_hint')}\n"
        
        return report


def test_polymarket():
    """测试Polymarket情绪分析"""
    print("🧪 测试 Polymarket 情绪分析\n")
    
    analyzer = PolymarketSentiment()
    
    print("1️⃣  获取活跃市场...")
    markets = analyzer.get_active_markets(limit=20)
    if markets and 'error' not in markets[0]:
        print(f"   ✅ 获取 {len(markets)} 个市场")
        print(f"   📊 TOP3市场:")
        for m in markets[:3]:
            print(f"      - {m['title'][:40]}... ({m['probability']:.1%})")
    else:
        print(f"   ⚠️  {markets[0].get('error', '未知错误')}")
    
    print("\n2️⃣  经济情绪分析...")
    sentiment = analyzer.get_economy_sentiment()
    if 'error' not in sentiment:
        print(f"   ✅ 情绪评分: {sentiment['sentiment_score']}")
        print(f"   💭 {sentiment['interpretation']}")
    else:
        print(f"   ⚠️  {sentiment['error']}")
    
    print("\n3️⃣  生成完整报告...")
    report = analyzer.generate_sentiment_report()
    print(report)


if __name__ == "__main__":
    test_polymarket()
