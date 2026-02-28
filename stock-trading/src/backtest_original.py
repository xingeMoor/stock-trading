"""
本地回测系统
用于基于历史数据测试交易策略的效果
"""
from typing import Dict, Any, Callable
from datetime import datetime
import pandas as pd
import numpy as np
from massive_api import get_aggs, get_all_indicators

def backtest_strategy(symbol: str, start_date: str, end_date: str, strategy_func: Callable) -> Dict[str, Any]:
    """
    回测策略
    :param symbol: 股票代码
    :param start_date: 回测开始日期 (YYYY-MM-DD)
    :param end_date: 回测结束日期 (YYYY-MM-DD)
    :param strategy_func: 策略函数，接收当前K线数据和指标，返回交易信号（buy/sell/hold）
    :return: 回测结果，包含收益率、最大回撤、交易记录等
    """
    # 获取历史K线数据
    history_data = get_aggs(symbol, from_=start_date, to=end_date, timespan='day')
    if "error" in history_data:
        return {"error": history_data["error"], "symbol": symbol}
    
    # 转换为DataFrame
    df = pd.DataFrame(history_data['data'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.rename(columns={
        'o': 'open',
        'h': 'high',
        'l': 'low',
        'c': 'close',
        'v': 'volume'
    })
    
    # 获取所有指标数据
    indicators_data = []
    for idx, row in df.iterrows():
        # 计算当前时间点的指标
        days_since_start = (idx - df.index[0]).days + 1
        indicators = get_all_indicators(symbol, period=days_since_start)
        indicators_data.append(indicators)
    
    df_indicators = pd.DataFrame(indicators_data, index=df.index)
    df = pd.concat([df, df_indicators], axis=1)
    
    # 初始化回测参数
    initial_capital = 10000  # 初始资金
    capital = initial_capital
    shares = 0  # 持有股票数量
    current_position = 0  # 0: 空仓, 1: 持仓
    trades = []  # 交易记录
    positions = []  # 持仓历史
    
    # 运行策略
    for idx, row in df.iterrows():
        # 获取当前指标
        current_indicators = row.drop(['open', 'high', 'low', 'close', 'volume']).to_dict()
        # 获取交易信号
        signal = strategy_func(row, current_indicators)
        
        # 执行交易
        if signal == 'buy' and current_position == 0:
            # 买入：用全部资金买入
            shares = capital / row['close']
            capital = 0
            current_position = 1
            trades.append({
                'date': idx.strftime('%Y-%m-%d'),
                'type': 'buy',
                'price': round(row['close'], 2),
                'shares': round(shares, 4),
                'remaining_capital': round(capital, 2)
            })
        elif signal == 'sell' and current_position == 1:
            # 卖出：卖出全部持仓
            capital = shares * row['close']
            shares = 0
            current_position = 0
            trades.append({
                'date': idx.strftime('%Y-%m-%d'),
                'type': 'sell',
                'price': round(row['close'], 2),
                'shares': round(shares, 4),
                'remaining_capital': round(capital, 2)
            })
        positions.append(current_position)
    
    # 计算最终收益
    final_value = capital + shares * df.iloc[-1]['close']
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    # 计算最大回撤
    df['portfolio_value'] = initial_capital * (df['close'] / df.iloc[0]['close'])
    df['peak'] = df['portfolio_value'].cummax()
    df['drawdown'] = (df['portfolio_value'] - df['peak']) / df['peak'] * 100
    max_drawdown = df['drawdown'].min()
    
    # 计算夏普比率（简化版，假设无风险利率为0）
    daily_returns = df['close'].pct_change()
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
    
    # 计算胜率
    if len(trades) >= 2:
        winning_trades = 0
        for i in range(0, len(trades), 2):
            if i+1 < len(trades):
                buy_price = trades[i]['price']
                sell_price = trades[i+1]['price']
                if sell_price > buy_price:
                    winning_trades += 1
        win_rate = winning_trades / (len(trades) // 2) * 100 if len(trades) // 2 > 0 else 0
    else:
        win_rate = 0
    
    return {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'final_value': round(final_value, 2),
        'total_return': round(total_return, 2),
        'max_drawdown': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'win_rate': round(win_rate, 2),
        'total_trades': len(trades),
        'trades': trades,
        'position_history': positions
    }

def example_strategy(row, indicators):
    """
    示例策略：由大模型自定义的策略模板
    大模型可以根据获取的所有指标、市场数据、新闻等综合判断
    """
    # 这里只是示例，实际由大模型根据分析生成交易决策
    # 大模型可以结合多种指标、市场趋势、公司基本面等进行判断
    buy_conditions = []
    sell_conditions = []
    
    # 示例判断逻辑
    # RSI指标判断
    if indicators.get('rsi_14', 50) < 30:
        buy_conditions.append("RSI超卖")
    if indicators.get('rsi_14', 50) > 70:
        sell_conditions.append("RSI超买")
    
    # MACD指标判断
    if indicators.get('macd', 0) > indicators.get('macd_signal', 0):
        buy_conditions.append("MACD金叉")
    if indicators.get('macd', 0) < indicators.get('macd_signal', 0):
        sell_conditions.append("MACD死叉")
    
    # 均线判断
    if indicators.get('sma_20', 0) > row['close']:
        buy_conditions.append("价格站上20日均线")
    if indicators.get('sma_20', 0) < row['close']:
        sell_conditions.append("价格跌破20日均线")
    
    # 综合判断
    if len(buy_conditions) >= 2:
        return 'buy'
    elif len(sell_conditions) >= 2:
        return 'sell'
    else:
        return 'hold'

if __name__ == "__main__":
    # 示例：回测AAPL的策略
    result = backtest_strategy("AAPL", "2024-01-01", "2024-12-31", example_strategy)
    if "error" in result:
        print(f"❌ 回测出错：{result['error']}")
    else:
        print(f"📊 回测结果：")
        print(f"  股票代码：{result['symbol']}")
        print(f"  回测周期：{result['start_date']} 至 {result['end_date']}")
        print(f"  初始资金：${result['initial_capital']}")
        print(f"  最终资金：${result['final_value']}")
        print(f"  总收益率：{result['total_return']}%")
        print(f"  最大回撤：{result['max_drawdown']}%")
        print(f"  夏普比率：{result['sharpe_ratio']}")
        print(f"  胜率：{result['win_rate']}%")
        print(f"  交易次数：{result['total_trades']}")
        print(f"📝 交易记录：")
        for trade in result['trades']:
            print(f"  {trade['date']} {trade['type']} 价格：${trade['price']} 数量：{trade['shares']}")
