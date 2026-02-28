"""
回测引擎 V2 (修复版)
修复:
1. ✅ 支持 position 参数传递 (用于追踪止盈)
2. ✅ 添加交易成本计算 (佣金 + 滑点)
3. ✅ 修复胜率统计 (基于完成轮次)
4. ✅ 添加持仓天数追踪 (用于时间止盈)
"""
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class Trade:
    """交易记录"""
    date: str
    type: str
    price: float
    shares: int
    value: float
    commission: float
    slippage: float
    pnl: float = 0.0


def calculate_metrics(trades: List[Trade], portfolio_values: List[float], 
                      initial_capital: float) -> Dict[str, Any]:
    """计算回测绩效指标 (修复 3: 正确统计胜率)"""
    if not trades or len(portfolio_values) < 2:
        return {
            "total_return": 0,
            "cagr": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "total_trades": 0,
            "completed_rounds": 0,
            "total_pnl": 0,
            "avg_holding_period": 0,
            "trading_days": len(portfolio_values),
            "total_cost": 0
        }
    
    # 总收益率
    final_value = portfolio_values[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    # 年化收益率
    days = len(portfolio_values)
    years = days / 252
    cagr = ((final_value / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    # 最大回撤
    portfolio_array = np.array(portfolio_values)
    peak = np.maximum.accumulate(portfolio_array)
    drawdown = (portfolio_array - peak) / peak * 100
    max_drawdown = np.min(drawdown)
    
    # 夏普比率
    daily_returns = pd.Series(portfolio_values).pct_change().dropna()
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
    
    # 交易分析 (修复 3: 基于完成轮次)
    buy_trades = [t for t in trades if t.type == 'buy']
    sell_trades = [t for t in trades if t.type == 'sell']
    
    winning_trades = 0
    total_pnl = 0
    winning_pnl = 0
    losing_pnl = 0
    total_cost = 0
    
    for i, sell_trade in enumerate(sell_trades):
        if i < len(buy_trades):
            buy_trade = buy_trades[i]
            pnl = sell_trade.pnl
            total_pnl += pnl
            total_cost += buy_trade.commission + buy_trade.slippage + sell_trade.commission + sell_trade.slippage
            
            if pnl > 0:
                winning_trades += 1
                winning_pnl += pnl
            else:
                losing_pnl += abs(pnl)
    
    completed_rounds = min(len(buy_trades), len(sell_trades))
    win_rate = (winning_trades / completed_rounds * 100) if completed_rounds > 0 else 0
    
    # 盈亏比
    if losing_pnl > 0:
        profit_factor = winning_pnl / losing_pnl
    elif winning_pnl > 0:
        profit_factor = float('inf')
    else:
        profit_factor = 0
    
    # 平均持仓时间
    holding_periods = []
    for i in range(completed_rounds):
        buy_date = datetime.strptime(buy_trades[i].date, '%Y-%m-%d')
        sell_date = datetime.strptime(sell_trades[i].date, '%Y-%m-%d')
        holding_periods.append((sell_date - buy_date).days)
    
    avg_holding_period = np.mean(holding_periods) if holding_periods else 0
    
    return {
        "total_return": round(total_return, 2),
        "cagr": round(cagr, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
        "total_trades": len(trades),
        "completed_rounds": completed_rounds,
        "total_pnl": round(total_pnl, 2),
        "avg_holding_period": round(avg_holding_period, 1),
        "trading_days": days,
        "total_cost": round(total_cost, 2)
    }


def backtest_strategy_v2(symbol: str, start_date: str, end_date: str, 
                          strategy_func: Callable, 
                          initial_capital: Optional[float] = None,
                          position_size: Optional[float] = None,
                          verbose: bool = True) -> Dict[str, Any]:
    """
    回测策略 V2 (修复 1,2,4)
    """
    from .massive_api import get_aggs
    
    initial_capital = initial_capital or 10000
    config = {
        'position_size': position_size or 1.0,
        'commission_rate': 0.001,
        'slippage_rate': 0.002
    }
    
    # 获取历史数据
    history_data = get_aggs(symbol, from_=start_date, to=end_date)
    
    if 'error' in history_data or not history_data.get('data'):
        return {"error": history_data.get('error', '无数据'), "symbol": symbol, "status": "failed"}
    
    # 转换为 DataFrame
    df = pd.DataFrame(history_data['data'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
    
    if verbose:
        print(f"✓ 获取到 {len(df)} 天数据")
    
    # 计算技术指标
    if verbose:
        print("⏳ 计算技术指标...")
    
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr_14'] = true_range.rolling(14).mean()
    
    # 初始化回测变量
    capital = initial_capital
    shares = 0
    position = None  # 持仓信息 (修复 1)
    trades = []
    portfolio_values = []
    
    # 回测主循环
    for i, (date, row) in enumerate(df.iterrows()):
        date_str = date.strftime('%Y-%m-%d')
        current_price = row['close']
        
        # 准备指标
        current_indicators = {
            'current_price': current_price,
            'sma_20': row.get('sma_20'),
            'ema_20': row.get('ema_20'),
            'sma_50': row.get('sma_50'),
            'sma_200': row.get('sma_200'),
            'macd': row.get('macd'),
            'macd_signal': row.get('macd_signal'),
            'macd_histogram': row.get('macd_histogram'),
            'rsi_14': row.get('rsi_14'),
            'atr_14': row.get('atr_14'),
            'volume': row.get('volume', 0)
        }
        
        # 更新持仓信息 (修复 1,4)
        if position:
            position['highest_price'] = max(position['highest_price'], current_price)
        
        # 获取交易信号 (修复 1: 传入 position)
        signal = strategy_func(row, current_indicators, symbol, position)
        
        # 执行交易 (修复 2: 添加交易成本)
        executed_trade = None
        
        if signal == 'buy' and shares == 0:
            # 买入
            effective_price = current_price * (1 + config['slippage_rate'])
            buy_capital = capital * config['position_size']
            shares_to_buy = int(buy_capital / effective_price)
            
            if shares_to_buy > 0:
                trade_value = shares_to_buy * effective_price
                commission = trade_value * config['commission_rate']
                slippage = trade_value * config['slippage_rate']
                total_cost = trade_value + commission + slippage
                
                if total_cost <= capital:
                    capital -= total_cost
                    shares = shares_to_buy
                    position = {
                        'entry_price': effective_price,
                        'entry_date': date_str,
                        'highest_price': effective_price,
                        'shares': shares_to_buy
                    }
                    
                    executed_trade = Trade(
                        date=date_str,
                        type='buy',
                        price=effective_price,
                        shares=shares_to_buy,
                        value=trade_value,
                        commission=commission,
                        slippage=slippage
                    )
        
        elif signal == 'sell' and shares > 0 and position:
            # 卖出
            effective_price = current_price * (1 - config['slippage_rate'])
            trade_value = shares * effective_price
            commission = trade_value * config['commission_rate']
            slippage = trade_value * config['slippage_rate']
            pnl = (effective_price - position['entry_price']) * shares
            
            capital += trade_value - commission - slippage
            
            executed_trade = Trade(
                date=date_str,
                type='sell',
                price=effective_price,
                shares=shares,
                value=trade_value,
                commission=commission,
                slippage=slippage,
                pnl=pnl
            )
            
            shares = 0
            position = None
        
        if executed_trade:
            trades.append(executed_trade)
        
        # 记录组合价值
        portfolio_value = capital + (shares * current_price if shares > 0 else 0)
        portfolio_values.append(portfolio_value)
    
    # 计算绩效指标
    metrics = calculate_metrics(trades, portfolio_values, initial_capital)
    
    # 输出结果
    if verbose:
        print(f"\n{'='*60}")
        print(f"📊 回测结果 - {symbol}")
        print(f"{'='*60}")
        print(f"回测周期：{start_date} 至 {end_date} ({len(df)} 交易日)")
        print(f"\n💰 资金变化:")
        print(f"  初始资金：${initial_capital:,.2f}")
        print(f"  最终资金：${portfolio_values[-1]:,.2f}")
        print(f"  总收益：  ${portfolio_values[-1] - initial_capital:+,.2f}")
        print(f"\n📈 绩效指标:")
        print(f"  总收益率：  {metrics['total_return']:+.2f}%")
        print(f"  年化收益：  {metrics['cagr']:+.2f}%")
        print(f"  最大回撤：  {metrics['max_drawdown']:.2f}%")
        print(f"  夏普比率：  {metrics['sharpe_ratio']:.2f}")
        print(f"  胜率：      {metrics['win_rate']:.1f}%")
        print(f"  盈亏比：    {metrics['profit_factor']}")
        print(f"\n📝 交易统计:")
        print(f"  总交易次数：{metrics['total_trades']}")
        print(f"  完成轮次：  {metrics['completed_rounds']}")
        print(f"  总盈亏：    ${metrics['total_pnl']:+,.2f}")
        print(f"  交易成本：  ${metrics['total_cost']:+,.2f}")
        print(f"  平均持仓：  {metrics['avg_holding_period']:.1f} 天")
        
        if trades:
            print(f"\n📋 交易记录:")
            for trade in trades[:10]:
                pnl_str = f" (PnL: ${trade.pnl:+,.2f})" if trade.type == 'sell' else ""
                arrow = "→" if trade.type == 'buy' else "←"
                print(f"  {trade.date} {arrow} {trade.type.upper():4} " +
                      f"${trade.price:>8.2f} x {trade.shares:>4}股 = ${trade.value:>10,.2f}{pnl_str}")
            if len(trades) > 10:
                print(f"  ... 还有 {len(trades) - 10} 条交易")
        print(f"{'='*60}")
    
    return {
        "symbol": symbol,
        "status": "completed",
        "start_date": start_date,
        "end_date": end_date,
        "trading_days": len(df),
        "initial_capital": initial_capital,
        "final_value": portfolio_values[-1],
        "total_return": metrics['total_return'],
        "cagr": metrics['cagr'],
        "max_drawdown": metrics['max_drawdown'],
        "sharpe_ratio": metrics['sharpe_ratio'],
        "win_rate": metrics['win_rate'],
        "profit_factor": metrics['profit_factor'],
        "total_trades": metrics['total_trades'],
        "completed_rounds": metrics['completed_rounds'],
        "total_pnl": metrics['total_pnl'],
        "total_cost": metrics['total_cost'],
        "avg_holding_period": metrics['avg_holding_period'],
        "trades": trades
    }
