"""
回测系统
基于历史数据测试交易策略效果，支持多种绩效指标
"""
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass
import os
import sys

# 设置 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform != 'win32':
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass

from .config import BACKTEST_CONFIG, TARGET_METRICS
from .massive_api import get_aggs, get_all_indicators


@dataclass
class Trade:
    """交易记录"""
    date: str
    type: str  # buy/sell
    price: float
    shares: int
    value: float
    commission: float
    pnl: float = 0.0


@dataclass
class Position:
    """持仓记录"""
    symbol: str
    shares: int
    average_cost: float
    current_value: float
    unrealized_pnl: float


def calculate_metrics(trades: List[Trade], portfolio_values: List[float], 
                      initial_capital: float) -> Dict[str, Any]:
    """
    计算回测绩效指标
    """
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
            "trading_days": len(portfolio_values)
        }
    
    # 总收益率
    final_value = portfolio_values[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    # 年化收益率 (CAGR)
    days = len(portfolio_values)
    years = days / 252  # 交易日
    if years > 0 and final_value > 0:
        cagr = ((final_value / initial_capital) ** (1 / years) - 1) * 100
    else:
        cagr = 0
    
    # 最大回撤
    portfolio_array = np.array(portfolio_values)
    peak = np.maximum.accumulate(portfolio_array)
    drawdown = (portfolio_array - peak) / peak * 100
    max_drawdown = np.min(drawdown)
    
    # 日收益率
    daily_returns = pd.Series(portfolio_values).pct_change().dropna()
    
    # 夏普比率 (假设无风险利率为 0)
    if daily_returns.std() != 0:
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
    else:
        sharpe_ratio = 0
    
    # 交易分析
    buy_trades = [t for t in trades if t.type == 'buy']
    sell_trades = [t for t in trades if t.type == 'sell']
    
    # 胜率
    winning_trades = 0
    total_pnl = 0
    winning_pnl = 0
    losing_pnl = 0
    
    for i, sell_trade in enumerate(sell_trades):
        if i < len(buy_trades):
            buy_trade = buy_trades[i]
            pnl = (sell_trade.price - buy_trade.price) * sell_trade.shares
            total_pnl += pnl
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
        "trading_days": days
    }


def backtest_strategy(symbol: str, start_date: str, end_date: str, 
                      strategy_func: Callable, 
                      initial_capital: Optional[float] = None,
                      position_size: Optional[float] = None,
                      verbose: bool = True,
                      **kwargs) -> Dict[str, Any]:
    """
    回测策略
    
    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        strategy_func: 策略函数，接收 (row, indicators) 返回 'buy'/'sell'/'hold'
        initial_capital: 初始资金 (可选，默认使用配置)
        position_size: 仓位比例 (可选，默认使用配置)
        verbose: 是否打印详细日志
    
    Returns:
        回测结果字典
    """
    config = BACKTEST_CONFIG.copy()
    if initial_capital:
        config['initial_capital'] = initial_capital
    if position_size:
        config['position_size'] = position_size
    
    if verbose:
        print(f"📊 开始回测 {symbol} ({start_date} 至 {end_date})")
    
    # 获取历史 K 线数据
    try:
        history_data = get_aggs(symbol, from_=start_date, to=end_date, timespan='day')
    except UnicodeEncodeError as e:
        return {
            "error": f"编码错误：{str(e)}",
            "symbol": symbol,
            "status": "failed"
        }
    except Exception as e:
        return {
            "error": f"API 调用失败：{str(e)}",
            "symbol": symbol,
            "status": "failed"
        }
    
    if "error" in history_data:
        return {
            "error": history_data["error"],
            "symbol": symbol,
            "status": "failed"
        }
    
    if not history_data.get('data'):
        return {
            "error": "无历史数据",
            "symbol": symbol,
            "status": "failed"
        }
    
    # 转换为 DataFrame
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
    
    if verbose:
        print(f"✓ 获取到 {len(df)} 天数据")
    
    # 预计算滚动指标 (基于 K 线数据)
    if verbose:
        print("⏳ 计算技术指标...")
    
    # 计算滚动 SMA/EMA
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # 计算 MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # 计算 RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # 初始化回测变量
    capital = config['initial_capital']
    shares = 0
    current_position = 0  # 0: 空仓，1: 持仓
    average_cost = 0
    entry_price = 0  # 入场价 (用于止损止盈)
    entry_date = None
    
    trades: List[Trade] = []
    portfolio_values = []
    daily_positions = []
    
    commission_rate = config['commission_rate']
    slippage = config['slippage']
    stop_loss_pct = config.get('stop_loss_pct', 0.05)
    take_profit_pct = config.get('take_profit_pct', 0.15)
    
    # 逐日回测 - 修复未来函数问题
    # 使用昨日数据决策，今日开盘价执行
    prev_row = None
    for i, (idx, row) in enumerate(df.iterrows()):
        date_str = idx.strftime('%Y-%m-%d')
        
        # 跳过第一天 (无昨日数据)
        if i == 0:
            # 初始化组合价值
            portfolio_values.append(config['initial_capital'])
            daily_positions.append(0)
            prev_row = row
            continue
        
        # 使用昨日 close 计算信号
        prev_date_str = df.index[i-1].strftime('%Y-%m-%d')
        prev_price = prev_row['close']
        
        # 构建当前指标 (使用滚动计算的指标)
        current_indicators = {
            'current_price': prev_price,
            'current_date': prev_date_str,
            'sma_20': prev_row.get('sma_20'),
            'ema_20': prev_row.get('ema_20'),
            'sma_50': prev_row.get('sma_50'),
            'macd': prev_row.get('macd'),
            'macd_signal': prev_row.get('macd_signal'),
            'macd_histogram': prev_row.get('macd_histogram'),
            'rsi_14': prev_row.get('rsi_14')
        }
        
        # 获取交易信号 (支持 symbol 参数)
        try:
            signal = strategy_func(prev_row, current_indicators, symbol)
        except TypeError:
            # 向后兼容：旧策略不接受 symbol
            signal = strategy_func(prev_row, current_indicators)
        
        # 使用今日 open 执行交易 (修复未来函数)
        current_price = row['open']
        
        # 执行交易
        executed_trade = None
        
        # 检查止损止盈 (优先级最高)
        if current_position == 1 and entry_price > 0:
            if current_price <= entry_price * (1 - stop_loss_pct):
                signal = 'sell'  # 触发止损
                print(f"  🛑 {date_str}: 触发止损 (${entry_price:.2f} → ${current_price:.2f}, -{stop_loss_pct*100:.1f}%)")
            elif current_price >= entry_price * (1 + take_profit_pct):
                signal = 'sell'  # 触发止盈
                print(f"  🎯 {date_str}: 触发止盈 (${entry_price:.2f} → ${current_price:.2f}, +{take_profit_pct*100:.1f}%)")
        
        if signal == 'buy' and current_position == 0:
            # 买入
            effective_price = current_price * (1 + slippage)
            buy_capital = capital * config['position_size']
            shares_to_buy = int(buy_capital / effective_price)
            
            if shares_to_buy > 0:
                trade_value = shares_to_buy * effective_price
                commission = trade_value * commission_rate
                total_cost = trade_value + commission
                
                if total_cost <= capital:
                    capital -= total_cost
                    shares = shares_to_buy
                    current_position = 1
                    average_cost = effective_price
                    entry_price = effective_price
                    entry_date = date_str
                    
                    executed_trade = Trade(
                        date=date_str,
                        type='buy',
                        price=effective_price,
                        shares=shares_to_buy,
                        value=trade_value,
                        commission=commission
                    )
                    trades.append(executed_trade)
        
        elif signal == 'sell' and current_position == 1:
            # 卖出
            effective_price = current_price * (1 - slippage)
            trade_value = shares * effective_price
            commission = trade_value * commission_rate
            pnl = (effective_price - average_cost) * shares
            
            # 记录卖出股数 (在清零前)
            sell_shares = shares
            
            capital += trade_value - commission
            shares = 0
            current_position = 0
            entry_price = 0
            entry_date = None
            
            executed_trade = Trade(
                date=date_str,
                type='sell',
                price=effective_price,
                shares=sell_shares,
                value=trade_value,
                commission=commission,
                pnl=pnl
            )
            trades.append(executed_trade)
        
        # 计算当日组合价值 (使用 close 价估值)
        portfolio_value = capital + shares * row['close']
        portfolio_values.append(portfolio_value)
        daily_positions.append(current_position)
        
        prev_row = row
    
    # 计算绩效指标
    metrics = calculate_metrics(trades, portfolio_values, config['initial_capital'])
    
    # 最终结果
    final_value = portfolio_values[-1] if portfolio_values else config['initial_capital']
    
    result = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "trading_days": len(df),
        "initial_capital": config['initial_capital'],
        "final_value": round(final_value, 2),
        "total_return": metrics['total_return'],
        "cagr": metrics['cagr'],
        "max_drawdown": metrics['max_drawdown'],
        "sharpe_ratio": metrics['sharpe_ratio'],
        "win_rate": metrics['win_rate'],
        "profit_factor": metrics['profit_factor'],
        "total_trades": len(trades),
        "completed_rounds": metrics['completed_rounds'],
        "total_pnl": metrics['total_pnl'],
        "avg_holding_period": metrics['avg_holding_period'],
        "trades": [
            {
                "date": t.date,
                "type": t.type,
                "price": round(t.price, 2),
                "shares": t.shares,
                "value": round(t.value, 2),
                "commission": round(t.commission, 2),
                "pnl": round(t.pnl, 2)
            } for t in trades
        ],
        "position_history": daily_positions,
        "portfolio_values": [round(v, 2) for v in portfolio_values],
        "status": "completed"
    }
    
    if verbose:
        print_result(result)
    
    return result


def print_result(result: Dict[str, Any]):
    """
    打印回测结果
    """
    if result.get('status') == 'failed':
        print(f"❌ 回测失败：{result.get('error')}")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 回测结果 - {result['symbol']}")
    print(f"{'='*60}")
    print(f"回测周期：{result['start_date']} 至 {result['end_date']} ({result['trading_days']} 交易日)")
    print(f"\n💰 资金变化:")
    print(f"  初始资金：${result['initial_capital']:,.2f}")
    print(f"  最终资金：${result['final_value']:,.2f}")
    print(f"  总收益：  ${result['final_value'] - result['initial_capital']:,.2f}")
    
    print(f"\n📈 绩效指标:")
    print(f"  总收益率：  {result['total_return']:+.2f}%")
    print(f"  年化收益：  {result['cagr']:+.2f}%")
    print(f"  最大回撤：  {result['max_drawdown']:.2f}%")
    print(f"  夏普比率：  {result['sharpe_ratio']:.2f}")
    print(f"  胜率：      {result['win_rate']:.1f}%")
    print(f"  盈亏比：    {result['profit_factor']}")
    
    print(f"\n📝 交易统计:")
    print(f"  总交易次数：{result['total_trades']}")
    print(f"  完成轮次：  {result['completed_rounds']}")
    print(f"  总盈亏：    ${result['total_pnl']:+,.2f}")
    print(f"  平均持仓：  {result['avg_holding_period']:.1f} 天")
    
    if result['trades']:
        print(f"\n📋 交易记录:")
        for trade in result['trades'][:10]:  # 只显示前 10 条
            arrow = "→" if trade['type'] == 'buy' else "←"
            pnl_str = f" (PnL: ${trade['pnl']:+,.2f})" if trade['type'] == 'sell' else ""
            print(f"  {trade['date']} {arrow} {trade['type'].upper():4} ${trade['price']:>8.2f} x {trade['shares']:>4} 股{pnl_str}")
        
        if len(result['trades']) > 10:
            print(f"  ... 还有 {len(result['trades']) - 10} 条交易")
    
    print(f"{'='*60}\n")


def check_targets(result: Dict[str, Any], targets: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    检查回测结果是否达到目标
    """
    if targets is None:
        targets = TARGET_METRICS
    
    checks = {
        "total_return": result['total_return'] >= targets.get('min_total_return', 20),
        "max_drawdown": result['max_drawdown'] >= targets.get('max_drawdown', -15),
        "sharpe_ratio": result['sharpe_ratio'] >= targets.get('min_sharpe_ratio', 1.5),
        "win_rate": result['win_rate'] >= targets.get('min_win_rate', 55),
        "total_trades": result['total_trades'] >= targets.get('min_trades', 20)
    }
    
    # 盈亏比检查
    pf = result.get('profit_factor', 0)
    if isinstance(pf, (int, float)):
        checks['profit_factor'] = pf >= targets.get('min_profit_factor', 1.5)
    else:
        checks['profit_factor'] = True  # 无穷大视为通过
    
    all_passed = all(checks.values())
    
    return {
        "passed": all_passed,
        "checks": checks,
        "failed_metrics": [k for k, v in checks.items() if not v]
    }


if __name__ == "__main__":
    # 示例策略
    def example_strategy(row, indicators):
        """简单示例策略"""
        buy_conditions = []
        sell_conditions = []
        
        # RSI
        rsi = indicators.get('rsi_14', 50)
        if rsi < 30:
            buy_conditions.append("RSI 超卖")
        elif rsi > 70:
            sell_conditions.append("RSI 超买")
        
        # MACD
        macd = indicators.get('macd', 0)
        signal = indicators.get('macd_signal', 0)
        if macd > signal:
            buy_conditions.append("MACD 金叉")
        elif macd < signal:
            sell_conditions.append("MACD 死叉")
        
        # 均线
        sma_20 = indicators.get('sma_20', 0)
        if sma_20 and row['close'] > sma_20:
            buy_conditions.append("价格站上 SMA20")
        elif sma_20 and row['close'] < sma_20:
            sell_conditions.append("价格跌破 SMA20")
        
        if len(buy_conditions) >= 2:
            return 'buy'
        elif len(sell_conditions) >= 2:
            return 'sell'
        else:
            return 'hold'
    
    # 运行回测
    result = backtest_strategy(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        strategy_func=example_strategy,
        verbose=True
    )
    
    # 检查目标
    if result.get('status') == 'completed':
        target_check = check_targets(result)
        print(f"🎯 目标检查：{'✓ 通过' if target_check['passed'] else '✗ 未通过'}")
        if not target_check['passed']:
            print(f"   未达标项：{', '.join(target_check['failed_metrics'])}")
