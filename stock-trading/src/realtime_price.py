"""
实时股价查询 - 网页数据源
作为 Massive API 的补充 (15 分钟延迟)
使用 Yahoo Finance 等公开数据源
"""
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import re


def get_yahoo_finance_price(symbol: str) -> Optional[Dict[str, Any]]:
    """
    从 Yahoo Finance 获取实时股价
    
    注意：这是网页爬取，可能不稳定
    建议仅作为辅助参考
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('chart', {}).get('result', [{}])[0]
            
            if result:
                meta = result.get('meta', {})
                quote = result.get('meta', {})
                
                return {
                    'symbol': symbol,
                    'price': meta.get('regularMarketPrice'),
                    'previous_close': meta.get('previousClose'),
                    'open': meta.get('regularMarketPrice'),  # 近似
                    'high': meta.get('regularMarketDayHigh'),
                    'low': meta.get('regularMarketDayLow'),
                    'volume': meta.get('regularMarketVolume'),
                    'change': meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0),
                    'change_percent': ((meta.get('regularMarketPrice', 0) / meta.get('previousClose', 1)) - 1) * 100,
                    'source': 'Yahoo Finance',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        
        return None
        
    except Exception as e:
        print(f"Yahoo Finance 获取失败：{e}")
        return None


def get_finviz_price(symbol: str) -> Optional[Dict[str, Any]]:
    """
    从 Finviz 获取股价 (延迟约 15 分钟)
    """
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # 查找价格
            price_match = re.search(r'Price</td>.*?<b>([\d.]+)</b>', html, re.DOTALL)
            change_match = re.search(r'Change</td>.*?<b>([+-]?[\d.]+%)</b>', html, re.DOTALL)
            volume_match = re.search(r'Volume</td>.*?<td>([\d,.]+)</td>', html, re.DOTALL)
            
            if price_match:
                price = float(price_match.group(1).replace(',', ''))
                change_str = change_match.group(1) if change_match else '0%'
                change_percent = float(change_str.replace('%', ''))
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'change_percent': change_percent,
                    'volume': float(volume_match.group(1).replace(',', '')) if volume_match else None,
                    'source': 'Finviz (15min delay)',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        
        return None
        
    except Exception as e:
        print(f"Finviz 获取失败：{e}")
        return None


def get_real_time_price(symbol: str) -> Dict[str, Any]:
    """
    获取实时股价 (多源尝试)
    
    优先级:
    1. Yahoo Finance (实时)
    2. Finviz (15 分钟延迟)
    """
    # 尝试 Yahoo Finance
    yahoo_data = get_yahoo_finance_price(symbol)
    if yahoo_data:
        return yahoo_data
    
    # 尝试 Finviz
    finviz_data = get_finviz_price(symbol)
    if finviz_data:
        return finviz_data
    
    return {
        'symbol': symbol,
        'error': '无法获取实时股价',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def compare_prices(symbol: str, massive_data: Dict = None) -> Dict[str, Any]:
    """
    对比 Massive API 和网页实时价格
    
    Args:
        symbol: 股票代码
        massive_data: Massive API 数据 (可选，如不提供则自动获取)
    
    Returns:
        价格对比信息
    """
    from .massive_api import get_real_time_data as get_massive_data
    
    # 获取 Massive 数据 (15 分钟延迟)
    if massive_data is None:
        massive_data = get_massive_data(symbol)
    
    # 获取网页实时数据
    web_data = get_real_time_price(symbol)
    
    # 对比
    comparison = {
        'symbol': symbol,
        'massive': {
            'price': massive_data.get('price'),
            'source': 'Massive API (15min delay)',
            'timestamp': massive_data.get('trade_date')
        },
        'web': {
            'price': web_data.get('price'),
            'source': web_data.get('source', 'Web'),
            'timestamp': web_data.get('timestamp')
        },
        'difference': None,
        'difference_pct': None
    }
    
    if massive_data.get('price') and web_data.get('price'):
        diff = web_data['price'] - massive_data['price']
        diff_pct = (diff / massive_data['price']) * 100 if massive_data['price'] > 0 else 0
        
        comparison['difference'] = round(diff, 2)
        comparison['difference_pct'] = round(diff_pct, 2)
        comparison['recommendation'] = '使用网页价格' if abs(diff_pct) > 0.5 else '两者相近'
    
    return comparison


if __name__ == "__main__":
    # 测试
    symbols = ["AAPL", "GOOGL", "META", "NVDA"]
    
    print("\n" + "="*60)
    print("📈 实时股价查询测试")
    print("="*60)
    
    for symbol in symbols:
        print(f"\n{symbol}:")
        
        # 网页实时价格
        web_price = get_real_time_price(symbol)
        if web_price.get('price'):
            print(f"  网页价格：${web_price['price']:.2f} ({web_price.get('source', 'Unknown')})")
            print(f"  涨跌：{web_price.get('change_percent', 0):+.2f}%")
        else:
            print(f"  网页价格：获取失败")
        
        # 对比
        comp = compare_prices(symbol)
        if comp['difference'] is not None:
            print(f"  差异：${comp['difference']:+.2f} ({comp['difference_pct']:+.2f}%)")
            print(f"  建议：{comp['recommendation']}")
    
    print("\n" + "="*60)
