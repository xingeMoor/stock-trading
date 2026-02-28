"""
回测引擎 V2.0
支持A股+美股，最近2年历史数据回测
特性：T+1处理、滑点模拟、手续费计算、绩效归因
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

from atomic_cache import cache
from data_provider import DataProvider
from factor_engine import FactorEngine

@dataclass
class Trade:
    """交易记录"""
    date: str
    symbol: str
    action: str  # buy/sell
    shares: int
    price: float
    commission: float
    slippage: float
    pnl: float = 0  # 卖出时记录盈亏
    reason: str = ""

@dataclass
class DailyStats:
    """每日统计"""
    date: str
    total_value: float
    cash: float
    position_value: float
    daily_return: float
    daily_return_pct: float
    positions: Dict[str, Dict]


class BacktestEngine:
    """
    回测引擎
    
    核心改进：
    1. T+1处理（A股）
    2. 真实滑点模拟
    3. 完整手续费计算
    4. 多维度绩效归因
    """
    
    def __init__(self, 
                 initial_capital: float = 100000.0,
                 commission_rate: float = 0.00025,  # 万2.5
                 stamp_tax_rate: float = 0.001,      # 印花税千1
                 min_commission: float = 5.0,        # 最低佣金5元
                 slippage_rate: float = 0.001):      # 滑点千1
        
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.min_commission = min_commission
        self.slippage_rate = slippage_rate
        
        self.data_provider = DataProvider()
        self.factor_engine = FactorEngine()
        
        # 回测状态
        self.reset()
    
    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.positions = {}  # symbol -> {shares, avg_cost}
        self.trades = []
        self.daily_stats = []
        self.current_date = None
        
    def run_backtest(self,
                    symbols: List[str],
                    market: str,
                    start_date: str,
                    end_date: str,
                    strategy_mode: str = "balanced") -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            symbols: 股票池
            market: A股/US
            start_date: YYYYMMDD
            end_date: YYYYMMDD
            strategy_mode: 策略模式
        
        Returns:
            回测结果报告
        """
        print(f"\n🚀 开始回测")
        print(f"{'='*60}")
        print(f"市场: {market}")
        print(f"标的: {len(symbols)} 只")
        print(f"周期: {start_date} ~ {end_date}")
        print(f"策略: {strategy_mode}")
        print(f"初始资金: ¥{self.initial_capital:,.2f}")
        print(f"{'='*60}\n")
        
        self.reset()
        
        # 获取交易日历
        trading_days = self._get_trading_days(market, start_date, end_date)
        print(f"📅 交易日数量: {len(trading_days)}")
        
        # 逐日回测
        for i, date in enumerate(trading_days):
            self.current_date = date
            
            if i % 20 == 0:
                print(f"   进度: {i}/{len(trading_days)} ({i/len(trading_days)*100:.1f}%)")
            
            # 1. 盘前准备
            self._before_market_open(date, symbols, market, strategy_mode)
            
            # 2. 盘中交易（简化：假设开盘价执行）
            self._during_market_hours(date, symbols, market)
            
            # 3. 盘后结算
            self._after_market_close(date, symbols, market)
        
        # 生成报告
        report = self._generate_report()
        
        print(f"\n✅ 回测完成!")
        
        return report
    
    def _get_trading_days(self, market: str, start: str, end: str) -> List[str]:
        """获取交易日历"""
        # 简化：使用第一个标的的数据日期
        # 实际应该用完整的交易日历
        
        dates = pd.date_range(start=start, end=end, freq='B')  # 工作日
        return [d.strftime('%Y%m%d') for d in dates]
    
    def _before_market_open(self, date: str, symbols: List[str], market: str, mode: str):
        """盘前准备：选股和决策"""
        # 每5个交易日重新选股
        if len(self.daily_stats) % 5 == 0:
            # 计算所有标的的因子得分
            scores = {}
            
            for symbol in symbols[:20]:  # 限制数量提高速度
                try:
                    factors = self.factor_engine.calculate_all_factors(symbol, market, mode)
                    if factors:
                        # 综合得分
                        total_score = sum(f.score * f.weight for f in factors) / sum(f.weight for f in factors)
                        scores[symbol] = total_score
                except:
                    continue
            
            # 选出TOP5
            if scores:
                selected = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
                self.selected_stocks = [s[0] for s in selected]
            else:
                self.selected_stocks = []
        
        # 生成交易信号（简化版）
        self.signals = self._generate_signals(date, market)
    
    def _generate_signals(self, date: str, market: str) -> Dict[str, str]:
        """生成交易信号"""
        signals = {}
        
        for symbol in getattr(self, 'selected_stocks', []):
            if symbol not in self.positions:
                signals[symbol] = 'buy'
            else:
                # 检查是否需要止盈止损
                pos = self.positions[symbol]
                current_price = self._get_price(symbol, market, date)
                
                if current_price:
                    pnl_pct = (current_price - pos['avg_cost']) / pos['avg_cost']
                    
                    if pnl_pct > 0.15:  # 止盈15%
                        signals[symbol] = 'sell'
                    elif pnl_pct < -0.08:  # 止损8%
                        signals[symbol] = 'sell'
                    else:
                        signals[symbol] = 'hold'
        
        # 检查现有持仓是否需要卖出
        for symbol in list(self.positions.keys()):
            if symbol not in signals:
                signals[symbol] = 'hold'
        
        return signals
    
    def _get_price(self, symbol: str, market: str, date: str) -> Optional[float]:
        """获取指定日期的价格"""
        try:
            df = cache.get_kline_atomic(market, symbol, date, date)
            if df is not None and not df.empty:
                return float(df['close'].iloc[0])
        except:
            pass
        return None
    
    def _during_market_hours(self, date: str, symbols: List[str], market: str):
        """盘中交易执行"""
        for symbol, signal in self.signals.items():
            if signal == 'buy':
                self._execute_buy(symbol, market, date)
            elif signal == 'sell':
                self._execute_sell(symbol, market, date)
    
    def _execute_buy(self, symbol: str, market: str, date: str):
        """执行买入"""
        price = self._get_price(symbol, market, date)
        if not price:
            return
        
        # 计算买入金额（每只最多20%仓位）
        total_value = self._get_total_value()
        max_position_value = total_value * 0.20
        
        current_position_value = self.positions.get(symbol, {}).get('shares', 0) * price
        available_to_buy = max_position_value - current_position_value
        
        if available_to_buy <= 0:
            return
        
        # 考虑现金限制
        available_to_buy = min(available_to_buy, self.cash * 0.95)
        
        if available_to_buy < 1000:  # 最小交易金额
            return
        
        # 计算股数（整手）
        shares = int(available_to_buy / price / 100) * 100
        if shares < 100:
            return
        
        # 计算成本
        trade_value = shares * price
        slippage = trade_value * self.slippage_rate
        commission = max(trade_value * self.commission_rate, self.min_commission)
        total_cost = trade_value + slippage + commission
        
        if total_cost > self.cash:
            return
        
        # A股T+1：当天买入不能卖出
        # 这里简化处理，实际应该标记为不可卖
        
        # 更新持仓
        if symbol in self.positions:
            old_shares = self.positions[symbol]['shares']
            old_cost = self.positions[symbol]['avg_cost']
            total_shares = old_shares + shares
            avg_cost = (old_shares * old_cost + shares * price) / total_shares
            
            self.positions[symbol] = {
                'shares': total_shares,
                'avg_cost': avg_cost,
                'buy_date': date  # 记录最新买入日期，用于T+1判断
            }
        else:
            self.positions[symbol] = {
                'shares': shares,
                'avg_cost': price,
                'buy_date': date
            }
        
        self.cash -= total_cost
        
        # 记录交易
        self.trades.append(Trade(
            date=date,
            symbol=symbol,
            action='buy',
            shares=shares,
            price=price,
            commission=commission,
            slippage=slippage,
            reason='factor_signal'
        ))
    
    def _execute_sell(self, symbol: str, market: str, date: str):
        """执行卖出"""
        if symbol not in self.positions:
            return
        
        # T+1检查：A股当天买入不能卖出
        if market == "A股":
            buy_date = self.positions[symbol].get('buy_date')
            if buy_date == date:
                return  # 当天买入，不能卖出
        
        price = self._get_price(symbol, market, date)
        if not price:
            return
        
        pos = self.positions[symbol]
        shares = pos['shares']
        avg_cost = pos['avg_cost']
        
        # 计算收入和成本
        trade_value = shares * price
        slippage = trade_value * self.slippage_rate
        commission = max(trade_value * self.commission_rate, self.min_commission)
        stamp_tax = trade_value * self.stamp_tax_rate  # 卖出印花税
        
        total_cost = slippage + commission + stamp_tax
        net_proceeds = trade_value - total_cost
        
        # 计算盈亏
        pnl = (price - avg_cost) * shares - total_cost
        
        # 更新现金
        self.cash += net_proceeds
        
        # 清空持仓
        del self.positions[symbol]
        
        # 记录交易
        self.trades.append(Trade(
            date=date,
            symbol=symbol,
            action='sell',
            shares=shares,
            price=price,
            commission=commission + stamp_tax,
            slippage=slippage,
            pnl=pnl,
            reason='take_profit_or_stop_loss'
        ))
    
    def _after_market_close(self, date: str, symbols: List[str], market: str):
        """盘后结算"""
        # 计算当日总市值
        position_value = 0
        for symbol, pos in self.positions.items():
            price = self._get_price(symbol, market, date)
            if price:
                position_value += pos['shares'] * price
        
        total_value = self.cash + position_value
        
        # 计算日收益
        if self.daily_stats:
            prev_value = self.daily_stats[-1].total_value
            daily_return = total_value - prev_value
            daily_return_pct = daily_return / prev_value
        else:
            daily_return = 0
            daily_return_pct = 0
        
        # 记录统计
        self.daily_stats.append(DailyStats(
            date=date,
            total_value=total_value,
            cash=self.cash,
            position_value=position_value,
            daily_return=daily_return,
            daily_return_pct=daily_return_pct,
            positions=self.positions.copy()
        ))
    
    def _get_total_value(self) -> float:
        """获取当前总资产"""
        position_value = sum(
            pos['shares'] * pos.get('current_price', pos['avg_cost'])
            for pos in self.positions.values()
        )
        return self.cash + position_value
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成回测报告"""
        if not self.daily_stats:
            return {"error": "无回测数据"}
        
        # 基础指标
        initial = self.daily_stats[0].total_value
        final = self.daily_stats[-1].total_value
        total_return = (final - initial) / initial
        
        # 收益率序列
        returns = [s.daily_return_pct for s in self.daily_stats[1:]]
        
        # 风险指标
        volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
        sharpe_ratio = (np.mean(returns) * 252) / (np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
        
        # 最大回撤
        cummax = np.maximum.accumulate([s.total_value for s in self.daily_stats])
        drawdowns = [(s.total_value - m) / m for s, m in zip(self.daily_stats, cummax)]
        max_drawdown = min(drawdowns)
        
        # 交易统计
        buy_trades = [t for t in self.trades if t.action == 'buy']
        sell_trades = [t for t in self.trades if t.action == 'sell']
        win_trades = [t for t in sell_trades if t.pnl > 0]
        
        win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
        avg_pnl = np.mean([t.pnl for t in sell_trades]) if sell_trades else 0
        
        report = {
            "summary": {
                "initial_capital": self.initial_capital,
                "final_value": final,
                "total_return": round(total_return * 100, 2),
                "annualized_return": round(((1 + total_return) ** (252 / len(self.daily_stats)) - 1) * 100, 2),
                "volatility": round(volatility * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "max_drawdown": round(max_drawdown * 100, 2),
                "trading_days": len(self.daily_stats)
            },
            "trades": {
                "total": len(self.trades),
                "buy_count": len(buy_trades),
                "sell_count": len(sell_trades),
                "win_rate": round(win_rate * 100, 2),
                "avg_pnl_per_trade": round(avg_pnl, 2),
                "total_commission": round(sum(t.commission for t in self.trades), 2),
                "total_slippage": round(sum(t.slippage for t in self.trades), 2)
            },
            "daily_performance": [
                {
                    "date": s.date,
                    "total_value": round(s.total_value, 2),
                    "return_pct": round(s.daily_return_pct * 100, 2)
                }
                for s in self.daily_stats
            ]
        }
        
        return report


def test_backtest():
    """测试回测引擎"""
    print("🧪 测试回测引擎\n")
    
    engine = BacktestEngine(initial_capital=100000)
    
    # 使用ETF进行快速测试
    result = engine.run_backtest(
        symbols=["510300", "512760"],  # 沪深300 + 芯片
        market="A股",
        start_date="20250101",
        end_date="20250228",
        strategy_mode="balanced"
    )
    
    print("\n" + "="*60)
    print("📊 回测结果")
    print("="*60)
    
    if "error" not in result:
        summary = result['summary']
        print(f"\n总收益率: {summary['total_return']:+.2f}%")
        print(f"年化收益: {summary['annualized_return']:+.2f}%")
        print(f"夏普比率: {summary['sharpe_ratio']:.2f}")
        print(f"最大回撤: {summary['max_drawdown']:.2f}%")
        print(f"交易次数: {result['trades']['total']}")
        print(f"胜率: {result['trades']['win_rate']:.1f}%")
    else:
        print(f"❌ {result['error']}")


if __name__ == "__main__":
    test_backtest()
