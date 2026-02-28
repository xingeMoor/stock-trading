"""
Stock Trading System - 美股量化交易系统
"""
from .config import MASSIVE_API_KEY, BACKTEST_CONFIG, SENTIMENT_CONFIG
from .massive_api import get_real_time_data, get_all_indicators, get_aggs
from .sentiment_api import calculate_sentiment_score, get_news_sentiment
from .llm_decision import make_trading_decision
from .backtest import backtest_strategy, calculate_metrics

__version__ = "4.0.0"
__all__ = [
    "MASSIVE_API_KEY",
    "BACKTEST_CONFIG",
    "SENTIMENT_CONFIG",
    "get_real_time_data",
    "get_all_indicators",
    "get_aggs",
    "calculate_sentiment_score",
    "get_news_sentiment",
    "make_trading_decision",
    "backtest_strategy",
    "calculate_metrics"
]
