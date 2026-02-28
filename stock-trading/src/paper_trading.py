"""
模拟交易运行器
每日自动执行：获取数据 → 策略决策 → 执行交易 → 记录保存
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os

from .config import BACKTEST_CONFIG, MASSIVE_API_KEY
from .massive_api import get_real_time_data, get_all_indicators, get_market_status
from .trading_db import TradingDatabase
from strategies.relaxed_strategy import relaxed_strategy
from strategies.optimized_v2_strategy import optimized_v2_strategy


class PaperTradingRunner:
    """
    模拟交易运行器
    
    功能:
    1. 每日自动获取市场数据
    2. 执行策略决策
    3. 模拟交易执行
    4. 记录到数据库
    5. 生成每日报告
    """
    
    def __init__(self, initial_capital: float = 10000.0, 
                 strategy_name: str = "optimized_v2",
                 position_size_pct: float = 0.3,
                 db_path: str = None):
        """
        初始化模拟交易运行器
        
        Args:
            initial_capital: 初始资金
            strategy_name: 策略名称 (relaxed/optimized_v2)
            position_size_pct: 单笔交易仓位比例 (0.3 = 30%)
            db_path: 数据库路径
        """
        self.initial_capital = initial_capital
        self.strategy_name = strategy_name
        self.position_size_pct = position_size_pct
        self.db = TradingDatabase(db_path)
        
        # 选择策略
        if strategy_name == "relaxed":
            self.strategy_func = relaxed_strategy
        elif strategy_name == "optimized_v2":
            self.strategy_func = optimized_v2_strategy
        else:
            raise ValueError(f"未知策略：{strategy_name}")
        
        # 交易配置
        self.commission_rate = 0.001  # 0.1%
        self.slippage = 0.0005  # 0.05%
    
    def get_current_capital(self) -> float:
        """获取当前可用资金"""
        snapshot = self.db.get_latest_snapshot()
        
        if snapshot is None:
            return self.initial_capital
        
        # 可用资金 = 总资金 - 持仓市值
        return snapshot['cash']
    
    def get_current_positions(self) -> List[Dict]:
        """获取当前持仓"""
        return self.db.get_positions()
    
    def execute_daily_trading(self, symbols: List[str], 
                              trading_date: str = None) -> Dict[str, Any]:
        """
        执行每日交易
        
        Args:
            symbols: 待交易的股票列表
            trading_date: 交易日期 (默认今天)
        
        Returns:
            交易执行报告
        """
        if trading_date is None:
            trading_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*60}")
        print(f"📅 模拟交易执行 - {trading_date}")
        print(f"{'='*60}")
        
        # 1. 检查市场状态
        market_status = get_market_status()
        if market_status.get('status') == 'closed':
            print(f"⚠️  市场已关闭，使用最新数据")
        
        # 2. 获取当前账户状态
        cash = self.get_current_capital()
        positions = self.get_current_positions()
        
        print(f"\n💰 账户状态:")
        print(f"  可用资金：${cash:,.2f}")
        print(f"  当前持仓：{len(positions)} 只")
        
        # 3. 更新持仓价格
        print(f"\n⏳ 更新持仓价格...")
        for pos in positions:
            symbol = pos['symbol']
            try:
                data = get_real_time_data(symbol)
                if 'error' not in data:
                    current_price = data['price']
                    self.db.update_position(
                        symbol=symbol,
                        shares=pos['shares'],
                        average_cost=pos['average_cost'],
                        current_price=current_price
                    )
                    pnl = (current_price - pos['average_cost']) * pos['shares']
                    print(f"  {symbol}: ${current_price:.2f}, 盈亏：${pnl:+,.2f}")
            except Exception as e:
                print(f"  ❌ {symbol} 更新失败：{e}")
        
        # 4. 执行交易决策
        executed_trades = []
        
        print(f"\n🤖 执行交易决策...")
        for symbol in symbols:
            try:
                trade_result = self._execute_symbol_decision(symbol, cash, positions, trading_date)
                if trade_result:
                    executed_trades.append(trade_result)
                    
                    # 更新可用资金
                    if trade_result['trade_type'] == 'buy':
                        cash -= trade_result['value'] + trade_result['commission']
                    else:
                        cash += trade_result['value'] - trade_result['commission']
                
            except Exception as e:
                print(f"  ❌ {symbol} 决策失败：{e}")
        
        # 5. 计算账户总值
        positions = self.get_current_positions()
        position_value = sum(pos['market_value'] for pos in positions)
        total_value = cash + position_value
        
        # 6. 保存每日快照
        self.db.add_snapshot(
            total_capital=self.initial_capital,
            cash=cash,
            position_value=position_value
        )
        
        # 7. 生成报告
        report = {
            'trading_date': trading_date,
            'executed_trades': executed_trades,
            'account_summary': {
                'cash': round(cash, 2),
                'position_value': round(position_value, 2),
                'total_value': round(total_value, 2),
                'total_return': round(total_value - self.initial_capital, 2),
                'total_return_pct': round((total_value - self.initial_capital) / self.initial_capital * 100, 2)
            },
            'positions': positions,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 8. 打印报告
        self._print_report(report)
        
        return report
    
    def _execute_symbol_decision(self, symbol: str, cash: float, 
                                  positions: List[Dict], 
                                  trading_date: str) -> Optional[Dict]:
        """
        执行单只股票的交易决策
        
        Returns:
            交易记录 (如果有执行)
        """
        # 获取数据
        data = get_real_time_data(symbol)
        if 'error' in data:
            print(f"  ⚠️  {symbol} 数据获取失败：{data.get('error')}")
            return None
        
        indicators = get_all_indicators(symbol)
        if 'error' in indicators:
            print(f"  ⚠️  {symbol} 指标获取失败")
            return None
        
        # 构建策略需要的数据格式
        class MockRow:
            def __init__(self, data):
                self.close = data.get('price', 0)
                self.open = data.get('open', 0)
                self.high = data.get('high', 0)
                self.low = data.get('low', 0)
                self.volume = data.get('volume', 0)
        
        row = MockRow(data)
        current_indicators = {
            'current_price': data.get('price', 0),
            'current_date': trading_date,
            **indicators
        }
        
        # 获取当前持仓
        current_position = None
        for pos in positions:
            if pos['symbol'] == symbol:
                current_position = pos
                break
        
        # 执行策略
        try:
            signal = self.strategy_func(row, current_indicators, symbol)
        except TypeError:
            # 向后兼容
            signal = self.strategy_func(row, current_indicators)
        
        # 检查是否需要交易
        if signal == 'hold':
            print(f"  ⏸️  {symbol}: 持有")
            return None
        
        # 执行交易
        current_price = data['price']
        
        if signal == 'buy' and current_position is None:
            # 买入
            available_cash = cash * self.position_size_pct
            shares = int(available_cash / (current_price * (1 + self.slippage + self.commission_rate)))
            
            if shares <= 0:
                print(f"  ⚠️  {symbol}: 资金不足")
                return None
            
            effective_price = current_price * (1 + self.slippage)
            value = shares * effective_price
            commission = value * self.commission_rate
            
            # 记录交易
            trade_id = self.db.add_trade(
                symbol=symbol,
                trade_type='buy',
                price=effective_price,
                shares=shares,
                strategy=self.strategy_name,
                confidence=0.75,  # 可以传给策略计算
                reasoning=f"{signal} signal"
            )
            
            # 更新持仓
            self.db.update_position(
                symbol=symbol,
                shares=shares,
                average_cost=effective_price,
                current_price=effective_price
            )
            
            print(f"  → {symbol}: BUY {shares}股 @ ${effective_price:.2f}")
            
            return {
                'trade_id': trade_id,
                'symbol': symbol,
                'trade_type': 'buy',
                'price': effective_price,
                'shares': shares,
                'value': value,
                'commission': commission
            }
        
        elif signal == 'sell' and current_position is not None:
            # 卖出
            shares = current_position['shares']
            effective_price = current_price * (1 - self.slippage)
            value = shares * effective_price
            commission = value * self.commission_rate
            pnl = (effective_price - current_position['average_cost']) * shares
            
            # 记录交易
            trade_id = self.db.add_trade(
                symbol=symbol,
                trade_type='sell',
                price=effective_price,
                shares=shares,
                strategy=self.strategy_name,
                confidence=0.75,
                reasoning=f"{signal} signal",
                pnl=pnl
            )
            
            # 清除持仓
            self.db.clear_position(symbol)
            
            print(f"  ← {symbol}: SELL {shares}股 @ ${effective_price:.2f}, PnL: ${pnl:+,.2f}")
            
            return {
                'trade_id': trade_id,
                'symbol': symbol,
                'trade_type': 'sell',
                'price': effective_price,
                'shares': shares,
                'value': value,
                'commission': commission,
                'pnl': pnl
            }
        
        return None
    
    def _print_report(self, report: Dict[str, Any]):
        """打印交易报告"""
        print(f"\n{'='*60}")
        print(f"📊 交易报告")
        print(f"{'='*60}")
        
        # 账户摘要
        summary = report['account_summary']
        print(f"\n💰 账户摘要:")
        print(f"  现金：      ${summary['cash']:>12,.2f}")
        print(f"  持仓市值：  ${summary['position_value']:>12,.2f}")
        print(f"  总资产：    ${summary['total_value']:>12,.2f}")
        print(f"  总收益：    ${summary['total_return']:>12,.2f} ({summary['total_return_pct']:+.2f}%)")
        
        #  executed trades
        trades = report['executed_trades']
        if trades:
            print(f"\n📝 今日交易:")
            for trade in trades:
                arrow = "→" if trade['trade_type'] == 'buy' else "←"
                pnl_str = f" (PnL: ${trade['pnl']:+,.2f})" if trade['trade_type'] == 'sell' else ""
                print(f"  {arrow} {trade['symbol']}: {trade['shares']}股 @ ${trade['price']:.2f}{pnl_str}")
        else:
            print(f"\n📝 今日交易：无")
        
        # 持仓
        positions = report['positions']
        if positions:
            print(f"\n📈 当前持仓:")
            for pos in positions:
                pnl_pct = pos['unrealized_pnl_pct']
                print(f"  {pos['symbol']}: {pos['shares']}股, 盈亏：${pos['unrealized_pnl']:+,.2f} ({pnl_pct:+.2f}%)")
        
        print(f"\n{'='*60}\n")
    
    def get_performance_report(self, start_date: str = None, 
                                end_date: str = None) -> Dict[str, Any]:
        """
        获取绩效报告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            绩效报告
        """
        snapshots = self.db.get_snapshots(start_date=start_date, end_date=end_date, limit=1000)
        statistics = self.db.get_statistics()
        
        if not snapshots:
            return {'error': '无数据'}
        
        # 计算绩效指标
        values = [s['total_value'] for s in reversed(snapshots)]
        
        import numpy as np
        
        # 收益率
        total_return = (values[-1] - values[0]) / values[0] * 100
        
        # 日收益率
        daily_returns = np.diff(values) / values[:-1]
        
        # 年化收益率 (假设 252 交易日)
        trading_days = len(values)
        annual_return = (values[-1] / values[0]) ** (252 / trading_days) - 1 if trading_days > 0 else 0
        
        # 波动率
        volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 else 0
        
        # 夏普比率 (假设无风险利率 0)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # 最大回撤
        cummax = np.maximum.accumulate(values)
        drawdown = (np.array(values) - cummax) / cummax
        max_drawdown = np.min(drawdown) * 100
        
        return {
            'period': {
                'start': snapshots[-1]['snapshot_date'] if snapshots else None,
                'end': snapshots[0]['snapshot_date'] if snapshots else None,
                'trading_days': len(snapshots)
            },
            'returns': {
                'total_return_pct': round(total_return, 2),
                'annual_return_pct': round(annual_return * 100, 2),
                'volatility_pct': round(volatility * 100, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown_pct': round(max_drawdown, 2)
            },
            'statistics': statistics,
            'daily_values': [
                {
                    'date': s['snapshot_date'],
                    'total_value': s['total_value'],
                    'daily_return_pct': s['daily_return_pct']
                } for s in reversed(snapshots)
            ]
        }
    
    def export_report(self, output_path: str):
        """导出绩效报告到文件"""
        report = self.get_performance_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✓ 绩效报告已导出：{output_path}")


def run_paper_trading(symbols: List[str], initial_capital: float = 10000.0,
                      strategy: str = "optimized_v2", position_size: float = 0.3):
    """
    便捷函数：运行模拟交易
    
    Args:
        symbols: 股票列表
        initial_capital: 初始资金
        strategy: 策略名称
        position_size: 仓位比例
    """
    runner = PaperTradingRunner(
        initial_capital=initial_capital,
        strategy_name=strategy,
        position_size_pct=position_size
    )
    
    return runner.execute_daily_trading(symbols)


if __name__ == "__main__":
    # 测试运行
    symbols = ["GOOGL", "META", "AAPL"]
    
    report = run_paper_trading(
        symbols=symbols,
        initial_capital=10000,
        strategy="optimized_v2",
        position_size=0.3
    )
    
    print(json.dumps(report, indent=2, default=str))
