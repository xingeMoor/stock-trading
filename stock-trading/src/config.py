"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# Massive API Key - 从环境变量读取
MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY')

if not MASSIVE_API_KEY:
    raise ValueError(
        "MASSIVE_API_KEY 未设置！\n"
        "请在项目根目录创建 .env 文件，添加：\n"
        "MASSIVE_API_KEY=your_api_key_here"
    )

# 回测配置
BACKTEST_CONFIG = {
    "initial_capital": 10000,          # 初始资金
    "commission_rate": 0.001,          # 手续费率 0.1%
    "slippage": 0.0005,                # 滑点 0.05%
    "position_size": 1.0,              # 仓位比例 (1.0=全仓)
    "stop_loss_pct": 0.05,             # 止损比例 5%
    "take_profit_pct": 0.15,           # 止盈比例 15%
    "max_positions": 1,                # 最大持仓数量
}

# 舆情数据源配置
SENTIMENT_CONFIG = {
    "sources": ["finviz", "reddit", "seeking_alpha"],
    "weights": {
        "news": 0.5,
        "social": 0.3,
        "analyst": 0.2
    },
    "update_frequency": "daily",
    "cache_hours": 24
}

# 策略迭代目标
TARGET_METRICS = {
    "min_total_return": 20.0,          # 最低总收益率 20%
    "max_drawdown": -15.0,             # 最大回撤不超过 -15%
    "min_sharpe_ratio": 1.5,           # 最低夏普比率 1.5
    "min_win_rate": 55.0,              # 最低胜率 55%
    "min_trades": 20,                  # 最少交易次数
    "min_profit_factor": 1.5           # 最低盈亏比
}

# LLM 决策配置
LLM_DECISION_CONFIG = {
    "min_confidence": 0.6,             # 最低置信度
    "default_quantity_pct": 0.5,       # 默认交易仓位比例
    "enable_stop_loss": True,          # 启用止损
    "enable_take_profit": True,        # 启用止盈
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/trading.log"
}
