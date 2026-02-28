#!/usr/bin/env python3
"""
大规模美股回测 - 2024-2026
100只跨行业股票，严格避免未来函数污染
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

from us_stock_universe import get_all_us_stocks
from atomic_cache import cache


class StrictBacktestEngine:
    """
    严格回测引擎 - 绝对避免未来函数
    
    核心原则:
    1. 每天只能使用当天及之前的数据
    2. 信号生成在开盘前，执行在开盘后
    3. 所有指标必须基于历史数据计算
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.commission_rate = 0.00025  # 万2.5
        self.min_commission = 1.0       # 美股最低$1
        self.slippage_rate = 0.001      # 滑点千1
        
    def run_single_stock(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        单只股票回测 - 严格时序控制
        
        流程:
        1. 获取历史数据
        2. 逐日遍历（从第60天开始，确保有足够历史计算指标）
        3. 每天收盘后计算信号（用于第二天）
        4. 第二天开盘价执行交易
        """
        print(f"   📈 回测 {symbol}...")
        
        # 获取数据（需要额外60天用于计算初始指标）
        data_start = (datetime.strptime(start_date, '%Y%m%d') - timedelta(days=90)).strftime('%Y%m%d')
        
        try:
            # 从缓存或API获取数据
            df = self._get_stock_data(symbol, data_start, end_date)
            
            if df is None or len(df) < 60:
                return {'symbol': symbol, 'error': '数据不足'}
            
            df = df.sort_values('date').reset_index(drop=True)
            
            # 找到正式回测起始位置
            start_idx = df[df['date'] >= start_date].index[0]
            if start_idx < 60:
                start_idx = 60  # 确保有足够历史数据
            
            # 初始化账户
            cash = self.initial_capital
            position = 0  # 持仓股数
            avg_cost = 0  # 平均成本
            trades = []
            daily_values = []
            
            # 逐日回测
            for i in range(start_idx, len(df)):
                current_row = df.iloc[i]
                current_date = current_row['date']
                current_price = current_row['close']
                
                # 获取历史数据（到今天为止，不包含未来）
                hist_data = df.iloc[:i+1].copy()
                
                # 盘前决策（基于昨天收盘前的数据）
                if i > start_idx:
                    prev_data = df.iloc[:i].copy()  # 昨天及之前的数据
                    signal = self._generate_signal(prev_data, position)
                else:
                    signal = 'hold'
                
                # 当天开盘价执行（模拟）
                open_price = current_row.get('open', current_price)
                
                # 执行交易
                if signal == 'buy' and position == 0:
                    # 计算买入数量（全仓的90%）
                    position_value = cash * 0.9
                    shares = int(position_value / open_price)
                    
                    if shares > 0:
                        cost = shares * open_price * (1 + self.slippage_rate)
                        commission = max(cost * self.commission_rate, self.min_commission)
                        total_cost = cost + commission
                        
                        if total_cost <= cash:
                            position = shares
                            avg_cost = open_price
                            cash -= total_cost
                            
                            trades.append({
                                'date': current_date,
                                'action': 'buy',
                                'shares': shares,
                                'price': open_price,
                                'cost': total_cost
                            })
                
                elif signal == 'sell' and position > 0:
                    # 卖出
                    proceeds = position * open_price * (1 - self.slippage_rate)
                    commission = max(proceeds * self.commission_rate, self.min_commission)
                    net_proceeds = proceeds - commission
                    
                    pnl = (open_price - avg_cost) * position - commission
                    
                    cash += net_proceeds
                    
                    trades.append({
                        'date': current_date,
                        'action': 'sell',
                        'shares': position,
                        'price': open_price,
                        'proceeds': net_proceeds,
                        'pnl': pnl
                    })
                    
                    position = 0
                    avg_cost = 0
                
                # 收盘后记录净值
                market_value = position * current_price
                total_value = cash + market_value
                
                daily_values.append({
                    'date': current_date,
                    'price': current_price,
                    'cash': cash,
                    'position': position,
                    'market_value': market_value,
                    'total_value': total_value
                })
            
            # 计算绩效指标
            return self._calculate_performance(symbol, daily_values, trades)
            
        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}
    
    def _get_stock_data(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """获取股票数据 - 优先从本地缓存"""
        # 尝试从缓存获取
        df = cache.get_kline_atomic("US", symbol, start, end)
        
        if df is not None and not df.empty:
            return df
        
        # 如果缓存没有，返回None（实际应该从yfinance等获取）
        return None
    
    def _generate_signal(self, hist_data: pd.DataFrame, current_position: int) -> str:
        """
        生成交易信号 - 仅基于历史数据
        
        策略: 双均线 crossover + RSI过滤
        """
        if len(hist_data) < 30:
            return 'hold'
        
        # 计算指标
        close = hist_data['close']
        
        # 移动平均线
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        current_price = close.iloc[-1]
        
        # 生成信号
        if current_position == 0:
            # 空仓时寻找买入机会
            if ma5 > ma20 and rsi < 70:  # 金叉且RSI不过热
                return 'buy'
        else:
            # 持仓时寻找卖出机会
            if ma5 < ma20 or rsi > 80:  # 死叉或RSI超买
                return 'sell'
        
        return 'hold'
    
    def _calculate_performance(
        self,
        symbol: str,
        daily_values: List[Dict],
        trades: List[Dict]
    ) -> Dict[str, Any]:
        """计算绩效指标"""
        if not daily_values:
            return {'symbol': symbol, 'error': '无交易数据'}
        
        values = [d['total_value'] for d in daily_values]
        dates = [d['date'] for d in daily_values]
        
        # 基础收益
        initial = values[0]
        final = values[-1]
        total_return = (final - initial) / initial
        
        # 日收益率
        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
        
        # 年化收益
        days = len(daily_values)
        annualized_return = ((1 + total_return) ** (252 / days) - 1) if days > 0 else 0
        
        # 波动率
        volatility = np.std(returns) * np.sqrt(252) if returns else 0
        
        # 夏普比率 (假设无风险利率2%)
        sharpe = (annualized_return - 0.02) / volatility if volatility > 0 else 0
        
        # 最大回撤
        cummax = np.maximum.accumulate(values)
        drawdowns = [(v - m) / m for v, m in zip(values, cummax)]
        max_drawdown = min(drawdowns) if drawdowns else 0
        
        # 交易统计
        buy_trades = [t for t in trades if t['action'] == 'buy']
        sell_trades = [t for t in trades if t['action'] == 'sell']
        win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
        
        return {
            'symbol': symbol,
            'start_date': dates[0],
            'end_date': dates[-1],
            'trading_days': days,
            'initial_value': initial,
            'final_value': final,
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'trades_count': len(trades),
            'buy_count': len(buy_trades),
            'sell_count': len(sell_trades),
            'win_rate': round(len(win_trades) / len(sell_trades) * 100, 2) if sell_trades else 0,
            'daily_values': daily_values,
            'trades': trades
        }


def run_batch_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    max_workers: int = 8
) -> Dict[str, Any]:
    """
    批量回测 - 并发执行
    """
    print(f"\n{'='*80}")
    print(f"🚀 大规模美股回测启动")
    print(f"{'='*80}")
    print(f"标的数量: {len(symbols)} 只")
    print(f"回测周期: {start_date} ~ {end_date}")
    print(f"并发数: {max_workers}")
    print(f"策略: 双均线Crossover + RSI过滤")
    print(f"{'='*80}\n")
    
    engine = StrictBacktestEngine(initial_capital=10000)  # 每只股票1万美元
    results = []
    completed = 0
    failed = 0
    
    # 串行执行（避免数据获取冲突）
    for i, symbol in enumerate(symbols):
        result = engine.run_single_stock(symbol, start_date, end_date)
        
        if 'error' not in result:
            results.append(result)
            completed += 1
        else:
            failed += 1
            print(f"   ❌ {symbol}: {result['error']}")
        
        # 进度显示
        if (i + 1) % 10 == 0 or (i + 1) == len(symbols):
            print(f"   进度: {i+1}/{len(symbols)} ({completed}成功 {failed}失败)")
    
    # 生成汇总报告
    report = generate_summary_report(results, start_date, end_date)
    
    return report


def generate_summary_report(
    results: List[Dict],
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """生成汇总报告"""
    if not results:
        return {'error': '无有效回测结果'}
    
    # 提取关键指标
    returns = [r['total_return'] for r in results]
    sharpes = [r['sharpe_ratio'] for r in results]
    drawdowns = [r['max_drawdown'] for r in results]
    
    # 排序找出最佳/最差
    sorted_by_return = sorted(results, key=lambda x: x['total_return'], reverse=True)
    
    report = {
        'meta': {
            'start_date': start_date,
            'end_date': end_date,
            'total_stocks': len(results),
            'strategy': 'MA_Crossover_RSI',
            'generated_at': datetime.now().isoformat()
        },
        'summary': {
            'avg_return': round(np.mean(returns), 2),
            'median_return': round(np.median(returns), 2),
            'best_return': round(max(returns), 2),
            'worst_return': round(min(returns), 2),
            'positive_count': sum(1 for r in returns if r > 0),
            'negative_count': sum(1 for r in returns if r < 0),
            'avg_sharpe': round(np.mean(sharpes), 2),
            'avg_max_dd': round(np.mean(drawdowns), 2),
        },
        'top_performers': [
            {
                'symbol': r['symbol'],
                'return': r['total_return'],
                'sharpe': r['sharpe_ratio'],
                'max_dd': r['max_drawdown'],
                'trades': r['trades_count']
            }
            for r in sorted_by_return[:10]
        ],
        'bottom_performers': [
            {
                'symbol': r['symbol'],
                'return': r['total_return'],
                'sharpe': r['sharpe_ratio'],
                'max_dd': r['max_drawdown'],
                'trades': r['trades_count']
            }
            for r in sorted_by_return[-10:]
        ],
        'all_results': results
    }
    
    return report


def print_report(report: Dict):
    """打印报告"""
    print("\n" + "="*80)
    print("📊 大规模回测汇总报告")
    print("="*80)
    
    meta = report['meta']
    print(f"\n回测信息:")
    print(f"   周期: {meta['start_date']} ~ {meta['end_date']}")
    print(f"   标的: {meta['total_stocks']} 只")
    print(f"   策略: {meta['strategy']}")
    
    s = report['summary']
    print(f"\n收益统计:")
    print(f"   平均收益: {s['avg_return']:+.2f}%")
    print(f"   中位数: {s['median_return']:+.2f}%")
    print(f"   最佳: {s['best_return']:+.2f}%")
    print(f"   最差: {s['worst_return']:+.2f}%")
    print(f"   正收益: {s['positive_count']} 只 ({s['positive_count']/meta['total_stocks']*100:.1f}%)")
    print(f"   负收益: {s['negative_count']} 只 ({s['negative_count']/meta['total_stocks']*100:.1f}%)")
    
    print(f"\n风险指标:")
    print(f"   平均夏普: {s['avg_sharpe']:.2f}")
    print(f"   平均最大回撤: {s['avg_max_dd']:.2f}%")
    
    print(f"\n🏆 TOP 10 表现:")
    for i, p in enumerate(report['top_performers'], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"   {emoji} {i}. {p['symbol']}: {p['return']:+7.2f}% | 夏普{p['sharpe']:.2f} | 回撤{p['max_dd']:.1f}%")
    
    print(f"\n⚠️  BOTTOM 10 表现:")
    for i, p in enumerate(report['bottom_performers'], 1):
        print(f"      {i}. {p['symbol']}: {p['return']:+7.2f}% | 夏普{p['sharpe']:.2f} | 回撤{p['max_dd']:.1f}%")
    
    print("\n" + "="*80)


def save_report(report: Dict):
    """保存报告到文件"""
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"massive_backtest_US_100stocks_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 详细报告已保存: {filepath}")
    return filepath


def main():
    """主函数"""
    # 获取100只美股
    symbols = get_all_us_stocks()
    
    print(f"🎯 美股大规模回测")
    print(f"   股票数量: {len(symbols)} 只")
    print(f"   行业覆盖: 11个GICS行业")
    
    # 回测参数
    start_date = "20240101"  # 2024年1月1日
    end_date = "20260228"     # 2026年2月28日
    
    # 执行回测
    report = run_batch_backtest(symbols, start_date, end_date)
    
    # 打印和保存报告
    if 'error' not in report:
        print_report(report)
        save_report(report)
    else:
        print(f"❌ 回测失败: {report['error']}")


if __name__ == "__main__":
    main()
