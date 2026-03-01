"""
舆情监控核心模块
负责舆情数据采集、情感分析和实时监控
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import pandas as pd
import requests
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class StockSentimentMonitor:
    """股票舆情监控器"""
    
    def __init__(self):
        self.stocks = set()  # 监控股票列表
        self.analyzer = SentimentIntensityAnalyzer()
        self.news_sources = {
            'eastmoney': self.fetch_eastmoney_news,
            'xueqiu': self.fetch_xueqiu_news,
            'sina_finance': self.fetch_sina_finance_news,
            'twitter': self.fetch_twitter_news,
            'reddit': self.fetch_reddit_news,
            'weibo': self.fetch_weibo_news
        }
        self.logger = logging.getLogger(__name__)
        
    def add_stock(self, symbol: str, name: str = None):
        """添加监控股票"""
        self.stocks.add(symbol)
        self.logger.info(f"Added stock to monitor: {symbol}")
        
    def remove_stock(self, symbol: str):
        """移除监控股票"""
        if symbol in self.stocks:
            self.stocks.remove(symbol)
            self.logger.info(f"Removed stock from monitor: {symbol}")
            
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """分析文本情感倾向"""
        # 使用TextBlob进行基础情感分析
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        
        # 使用VADER进行更细致的情感分析
        vader_scores = self.analyzer.polarity_scores(text)
        
        # 综合判断情感倾向
        if vader_scores['compound'] >= 0.05:
            sentiment_label = 'positive'
        elif vader_scores['compound'] <= -0.05:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
            
        return {
            'label': sentiment_label,
            'compound': vader_scores['compound'],
            'positive': vader_scores['pos'],
            'negative': vader_scores['neg'],
            'neutral': vader_scores['neu'],
            'textblob_polarity': polarity
        }
    
    def classify_event_type(self, text: str) -> str:
        """事件类型分类"""
        keywords = {
            'product': ['产品', '发布', '新品', '研发', '技术', '创新', '专利', '服务'],
            'financial': ['财报', '业绩', '营收', '利润', '收入', '亏损', '增长', '下降', '盈利', '亏损'],
            'legal': ['诉讼', '违规', '处罚', '监管', '调查', '违法', '纠纷', '仲裁'],
            'personnel': ['高管', '辞职', '任命', '人事', '裁员', '招聘', '离职', '变动']
        }
        
        text_lower = text.lower()
        for category, words in keywords.items():
            for word in words:
                if word in text_lower:
                    return category
                    
        return 'other'
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """关键词提取（简化版）"""
        # 这里使用简单的词频统计作为示例
        # 在实际应用中可以使用jieba、TF-IDF等方法
        import jieba
        
        # 分词
        words = jieba.lcut(text)
        
        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        filtered_words = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 统计词频
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
            
        # 返回频率最高的前N个词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_n]]
    
    async def fetch_eastmoney_news(self, symbol: str) -> List[Dict]:
        """获取东方财富新闻"""
        # 这里是模拟实现，实际应调用东方财富API
        news_list = []
        # 示例：实际应用中需要替换为真实API调用
        return news_list
    
    async def fetch_xueqiu_news(self, symbol: str) -> List[Dict]:
        """获取雪球新闻"""
        # 这里是模拟实现，实际应调用雪球API
        news_list = []
        # 示例：实际应用中需要替换为真实API调用
        return news_list
    
    async def fetch_sina_finance_news(self, symbol: str) -> List[Dict]:
        """获取新浪财经新闻"""
        # 这里是模拟实现，实际应调用新浪财经API
        news_list = []
        # 示例：实际应用中需要替换为真实API调用
        return news_list
    
    async def fetch_twitter_news(self, symbol: str) -> List[Dict]:
        """获取Twitter/X相关消息"""
        # 这里是模拟实现，实际应调用Twitter API
        news_list = []
        # 示例：实际应用中需要替换为真实API调用
        return news_list
    
    async def fetch_reddit_news(self, symbol: str) -> List[Dict]:
        """获取Reddit相关消息"""
        # 这里是模拟实现，实际应调用Reddit API
        news_list = []
        # 示例：实际应用中需要替换为真实API调用
        return news_list
    
    async def fetch_weibo_news(self, symbol: str) -> List[Dict]:
        """获取微博相关消息"""
        # 这里是模拟实现，实际应调用微博API
        news_list = []
        # 示例：实际应用中需要替换为真实API调用
        return news_list
    
    async def collect_sentiment_data(self, symbol: str) -> List[Dict]:
        """收集特定股票的舆情数据"""
        all_news = []
        
        for source_name, source_func in self.news_sources.items():
            try:
                news = await source_func(symbol)
                for item in news:
                    item['source'] = source_name
                    item['stock_symbol'] = symbol
                    item['timestamp'] = datetime.now().isoformat()
                    
                    # 分析情感
                    sentiment = self.analyze_sentiment(item.get('title', '') + ' ' + item.get('summary', ''))
                    item.update(sentiment)
                    
                    # 分类事件类型
                    item['event_type'] = self.classify_event_type(item.get('title', '') + ' ' + item.get('summary', ''))
                    
                    # 提取关键词
                    item['keywords'] = self.extract_keywords(item.get('title', '') + ' ' + item.get('summary', ''))
                    
                    all_news.append(item)
            except Exception as e:
                self.logger.error(f"Error fetching data from {source_name} for {symbol}: {str(e)}")
                
        return all_news
    
    async def monitor_all_stocks(self) -> Dict[str, List[Dict]]:
        """监控所有股票的舆情"""
        all_results = {}
        
        for stock in self.stocks:
            all_results[stock] = await self.collect_sentiment_data(stock)
            
        return all_results
    
    def detect_alerts(self, sentiment_data: List[Dict]) -> List[Dict]:
        """检测异常舆情"""
        alerts = []
        
        for item in sentiment_data:
            # 如果情感强度超过阈值，则发出警报
            if abs(item.get('compound', 0)) > 0.8:  # 强烈情感
                alerts.append({
                    'stock_symbol': item.get('stock_symbol'),
                    'title': item.get('title'),
                    'sentiment': item.get('label'),
                    'intensity': abs(item.get('compound', 0)),
                    'timestamp': item.get('timestamp'),
                    'source': item.get('source')
                })
                
        return alerts


# 示例使用
if __name__ == "__main__":
    monitor = StockSentimentMonitor()
    monitor.add_stock("AAPL", "Apple Inc.")
    monitor.add_stock("TSLA", "Tesla Inc.")
    monitor.add_stock("000001.SZ", "平安银行")