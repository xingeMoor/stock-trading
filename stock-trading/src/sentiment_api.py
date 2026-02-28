"""
舆情数据获取模块
集成多个数据源：新闻、社交媒体、分析师评级
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re

from .config import SENTIMENT_CONFIG


def get_finviz_news(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取 Finviz 财经新闻
    """
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_table = soup.find('table', class_='fullview-news-outer')
        
        if not news_table:
            return []
        
        news_items = []
        rows = news_table.find_all('tr')
        
        for row in rows[:limit]:
            try:
                date_cell = row.find('td', class_='news-date-cell')
                title_cell = row.find('a')
                
                if not title_cell:
                    continue
                
                date_text = date_cell.text.strip() if date_cell else ""
                title = title_cell.text.strip()
                link = title_cell.get('href', '')
                
                # 简单情绪判断
                sentiment = analyze_text_sentiment(title)
                
                news_items.append({
                    "source": "finviz",
                    "title": title,
                    "link": link,
                    "date": date_text,
                    "sentiment": sentiment
                })
            except Exception:
                continue
        
        return news_items
    except Exception as e:
        print(f"Finviz 新闻获取失败：{e}")
        return []


def get_reddit_sentiment(symbol: str, limit: int = 20) -> Dict[str, Any]:
    """
    获取 Reddit WallStreetBets 情绪数据
    通过 Pushshift API 或替代方案
    """
    try:
        # 使用 Reddit 搜索 API 的替代方案
        # 注意：实际使用可能需要 API key
        url = f"https://www.reddit.com/r/wallstreetbets/search.json?q={symbol}&sort=new&limit={limit}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"mentions": 0, "sentiment_score": 0, "posts": []}
        
        data = response.json()
        posts = data.get('data', {}).get('children', [])
        
        if not posts:
            return {"mentions": 0, "sentiment_score": 0, "posts": []}
        
        total_sentiment = 0
        valid_posts = []
        
        for post in posts[:limit]:
            post_data = post.get('data', {})
            title = post_data.get('title', '')
            score = post_data.get('score', 0)
            
            sentiment = analyze_text_sentiment(title)
            total_sentiment += sentiment
            
            valid_posts.append({
                "title": title,
                "score": score,
                "sentiment": sentiment,
                "url": f"https://reddit.com{post_data.get('permalink', '')}"
            })
        
        avg_sentiment = total_sentiment / len(valid_posts) if valid_posts else 0
        
        return {
            "mentions": len(valid_posts),
            "sentiment_score": avg_sentiment,
            "posts": valid_posts
        }
    except Exception as e:
        print(f"Reddit 情绪获取失败：{e}")
        return {"mentions": 0, "sentiment_score": 0, "posts": []}


def get_seeking_alpha_ratings(symbol: str) -> Dict[str, Any]:
    """
    获取 Seeking Alpha 分析师评级
    """
    try:
        url = f"https://seekingalpha.com/symbol/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"rating": "Hold", "score": 0, "details": {}}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尝试提取评级信息 (页面结构可能变化)
        rating_map = {
            "Very Bullish": 1.0,
            "Bullish": 0.5,
            "Neutral": 0,
            "Bearish": -0.5,
            "Very Bearish": -1.0
        }
        
        # 简化处理，返回默认值
        return {
            "rating": "Hold",
            "score": 0,
            "details": {
                "buy": 0,
                "hold": 1,
                "sell": 0
            }
        }
    except Exception as e:
        print(f"Seeking Alpha 评级获取失败：{e}")
        return {"rating": "Hold", "score": 0, "details": {}}


def analyze_text_sentiment(text: str) -> float:
    """
    简单文本情绪分析
    返回 -1 (负面) 到 1 (正面)
    """
    text = text.lower()
    
    positive_words = [
        'surge', 'soar', 'jump', 'rise', 'gain', 'beat', 'outperform',
        'bullish', 'upgrade', 'buy', 'strong', 'growth', 'profit',
        'record', 'high', 'success', 'positive', 'optimistic'
    ]
    
    negative_words = [
        'drop', 'fall', 'plunge', 'crash', 'decline', 'miss', 'underperform',
        'bearish', 'downgrade', 'sell', 'weak', 'loss', 'warning',
        'low', 'failure', 'negative', 'pessimistic', 'risk'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    total = positive_count + negative_count
    if total == 0:
        return 0
    
    return (positive_count - negative_count) / total


def get_news_sentiment(symbol: str) -> Dict[str, Any]:
    """
    获取新闻情绪评分
    """
    news = get_finviz_news(symbol, limit=10)
    
    if not news:
        return {
            "symbol": symbol,
            "news_count": 0,
            "sentiment_score": 0,
            "articles": []
        }
    
    total_sentiment = sum(item['sentiment'] for item in news)
    avg_sentiment = total_sentiment / len(news)
    
    return {
        "symbol": symbol,
        "news_count": len(news),
        "sentiment_score": round(avg_sentiment, 3),
        "articles": news
    }


def get_social_sentiment(symbol: str) -> Dict[str, Any]:
    """
    获取社交媒体情绪评分
    """
    reddit_data = get_reddit_sentiment(symbol, limit=20)
    
    return {
        "symbol": symbol,
        "mentions": reddit_data['mentions'],
        "sentiment_score": round(reddit_data['sentiment_score'], 3),
        "posts": reddit_data['posts'][:5]  # 只返回前 5 条
    }


def get_analyst_ratings(symbol: str) -> Dict[str, Any]:
    """
    获取分析师评级
    """
    sa_ratings = get_seeking_alpha_ratings(symbol)
    
    return {
        "symbol": symbol,
        "rating": sa_ratings['rating'],
        "score": sa_ratings['score'],
        "details": sa_ratings['details']
    }


def calculate_sentiment_score(symbol: str) -> Dict[str, Any]:
    """
    计算综合情绪评分
    整合新闻、社交、分析师评级
    """
    # 获取各数据源
    news_data = get_news_sentiment(symbol)
    social_data = get_social_sentiment(symbol)
    analyst_data = get_analyst_ratings(symbol)
    
    # 加权平均
    weights = SENTIMENT_CONFIG['weights']
    
    composite_score = (
        weights['news'] * news_data['sentiment_score'] +
        weights['social'] * social_data['sentiment_score'] +
        weights['analyst'] * analyst_data['score']
    )
    
    # 情绪等级
    if composite_score >= 0.5:
        sentiment_level = "Very Positive"
    elif composite_score >= 0.2:
        sentiment_level = "Positive"
    elif composite_score >= -0.2:
        sentiment_level = "Neutral"
    elif composite_score >= -0.5:
        sentiment_level = "Negative"
    else:
        sentiment_level = "Very Negative"
    
    return {
        "symbol": symbol,
        "composite_score": round(composite_score, 3),
        "sentiment_level": sentiment_level,
        "components": {
            "news": {
                "score": news_data['sentiment_score'],
                "count": news_data['news_count']
            },
            "social": {
                "score": social_data['sentiment_score'],
                "mentions": social_data['mentions']
            },
            "analyst": {
                "score": analyst_data['score'],
                "rating": analyst_data['rating']
            }
        },
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == "__main__":
    # 测试
    symbol = "AAPL"
    print(f"测试股票：{symbol}\n")
    
    sentiment = calculate_sentiment_score(symbol)
    print(f"综合情绪评分：{sentiment['composite_score']}")
    print(f"情绪等级：{sentiment['sentiment_level']}")
    print(f"\n各数据源:")
    print(f"  新闻：{sentiment['components']['news']['score']} ({sentiment['components']['news']['count']} 条)")
    print(f"  社交：{sentiment['components']['social']['score']} ({sentiment['components']['social']['mentions']} 提及)")
    print(f"  分析师：{sentiment['components']['analyst']['score']} ({sentiment['components']['analyst']['rating']})")
