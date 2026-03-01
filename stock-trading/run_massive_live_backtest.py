#!/usr/bin/env python3
"""
大规模美股回测 - 使用真实 Massive API 数据
110只股票，2024-2026两年数据
严格无未来函数
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

from us_stock_universe import get_all_us_stocks
from unified_data_fetcher import UnifiedDataFetcher
from backtest_db import BacktestDatabase


class LiveBacktestEngine:
    """实盘数据回测引擎"""
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.commission_rate = 0.00025
        self.min_commission = 1.0
        self.slippage_rate = 0.001
        self.data_fetcher = UnifiedDataFetcher()
        
    def run_single_stock(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """单只股票回测"""
        print(f"   📈 回测 {symbol}...", end=" ")
        
        try:
            # 获取数据（需要额外60天用于计算初始指标）
            data_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
            
            df = self.data_fetcher.get_stock_data(symbol, data_start, end_date)
            
            if df is None or len(df) < 60:
                print("❌ 数据不足")
                return {'symbol': symbol, 'error': '数据不足'}
            
            df = df.sort_values('date').reset_index(drop=True)
            
            # 找到正式回测起始位置
            start_idx = df[df['date'] >= start_date].index[0]
            if start_idx < 60:
                start_idx = 60
            
            # 初始化账户
            cash = self.initial_capital
            position = 0
            avg_cost = 0
            trades = []
            daily_values = []
            
            # 逐日回测
            for i in range(start_idx, len(df)):
                current_row = df.iloc[i]
                current_date = current_row['date']
                current_price = current_row['close']
                open_price = current_row.get('open', current_price)
                
                # 盘前决策（基于昨天收盘前的数据）
                if i > start_idx:
                    hist_data = df.iloc[:i].copy()
                    signal = self._generate_signal(hist_data, position)
                else:
                    signal = 'hold'
                
                # 当天开盘价执行交易
                if signal == 'buy' and position == 0:
                    position_value = cash * 0.95
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
                                'price': round(open_price, 2),
                                'cost': round(total_cost, 2)
                            })
                
                elif signal == 'sell' and position > 0:
                    proceeds = position * open_price * (1 - self.slippage_rate)
                    commission = max(proceeds * self.commission_rate, self.min_commission)
                    net_proceeds = proceeds - commission
                    pnl = (open_price - avg_cost) * position - commission
                    
                    cash += net_proceeds
                    
                    trades.append({
                        'date': current_date,
                        'action': 'sell',
                        'shares': position,
                        'price': round(open_price, 2),
                        'proceeds': round(net_proceeds, 2),
                        'pnl': round(pnl, 2)
                    })
                    
                    position = 0
                    avg_cost = 0
                
                # 收盘后记录净值
                market_value = position * current_price
                total_value = cash + market_value
                
                daily_values.append({
                    'date': current_date,
                    'price': round(current_price, 2),
                    'cash': round(cash, 2),
                    'position': position,
                    'market_value': round(market_value, 2),
                    'total_value': round(total_value, 2)
                })
            
            result = self._calculate_performance(symbol, daily_values, trades)
            print(f"✅ 收益 {result['total_return']:+.2f}%")
            return result
            
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _generate_signal(self, hist_data: pd.DataFrame, current_position: int) -> str:
        """生成交易信号 - 仅基于历史数据"""
        if len(hist_data) < 30:
            return 'hold'
        
        close = hist_data['close']
        
        # 移动平均线
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        prev_ma5 = close.rolling(5).mean().iloc[-2] if len(close) >= 2 else ma5
        prev_ma20 = close.rolling(20).mean().iloc[-2] if len(close) >= 2 else ma20
        
        # RSI计算
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 金叉/死叉判断
        golden_cross = (prev_ma5 <= prev_ma20) and (ma5 > ma20)
        dead_cross = (prev_ma5 >= prev_ma20) and (ma5 < ma20)
        
        if current_position == 0:
            if golden_cross and rsi < 70:
                return 'buy'
        else:
            if dead_cross or rsi > 80:
                return 'sell'
        
        return 'hold'
    
    def _calculate_performance(self, symbol: str, daily_values: list, trades: list) -> dict:
        """计算绩效指标"""
        if not daily_values:
            return {'symbol': symbol, 'error': '无交易数据'}
        
        values = [d['total_value'] for d in daily_values]
        dates = [d['date'] for d in daily_values]
        
        initial = values[0]
        final = values[-1]
        total_return = (final - initial) / initial
        
        days = len(daily_values)
        annualized_return = ((1 + total_return) ** (252 / days) - 1) if days > 0 else 0
        
        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
        volatility = np.std(returns) * np.sqrt(252) if returns else 0
        sharpe = (annualized_return - 0.02) / volatility if volatility > 0 else 0
        
        cummax = np.maximum.accumulate(values)
        drawdowns = [(v - m) / m for v, m in zip(values, cummax)]
        max_drawdown = min(drawdowns) if drawdowns else 0
        
        sell_trades = [t for t in trades if t['action'] == 'sell']
        win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
        
        return {
            'symbol': symbol,
            'start_date': dates[0],
            'end_date': dates[-1],
            'trading_days': days,
            'initial_value': round(initial, 2),
            'final_value': round(final, 2),
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'trades_count': len(trades),
            'win_rate': round(len(win_trades) / len(sell_trades) * 100, 2) if sell_trades else 0,
        }


def run_massive_backtest(symbols: list, start_date: str, end_date: str):
    """批量回测"""
    print(f"\n{'='*80}")
    print(f"🚀 大规模美股回测 - 真实数据")
    print(f"{'='*80}")
    print(f"标的数量: {len(symbols)} 只")
    print(f"回测周期: {start_date} ~ {end_date}")
    print(f"策略: 双均线Crossover + RSI过滤")
    print(f"数据源: Massive API (优先) + Yahoo Finance (备用)")
    print(f"{'='*80}\n")
    
    engine = LiveBacktestEngine(initial_capital=10000)
    results = []
    
    for i, symbol in enumerate(symbols):
        result = engine.run_single_stock(symbol, start_date, end_date)
        
        if 'error' not in result:
            results.append(result)
        
        if (i + 1) % 10 == 0 or (i + 1) == len(symbols):
            print(f"\n   📊 进度: {i+1}/{len(symbols)} ({len(results)}成功)")
            if results:
                avg_return = np.mean([r['total_return'] for r in results])
                print(f"       平均收益: {avg_return:+.2f}%")
        
        # 避免速率限制
        if (i + 1) % 5 == 0:
            import time
            time.sleep(1)
    
    return generate_report(results, start_date, end_date)


def generate_report(results: list, start_date: str, end_date: str):
    """生成报告"""
    if not results:
        return {'error': '无有效结果'}
    
    returns = [r['total_return'] for r in results]
    sharpes = [r['sharpe_ratio'] for r in results]
    drawdowns = [r['max_drawdown'] for r in results]
    
    sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    
    report = {
        'meta': {
            'start_date': start_date,
            'end_date': end_date,
            'total_stocks': len(results),
            'data_source': 'massive_api_real_data',
            'strategy': 'MA_Crossover_RSI_Strict_NoFutureFunction'
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
        'top_performers': sorted_results[:10],
        'bottom_performers': sorted_results[-10:],
        'all_results': results
    }
    
    return report


def print_report(report: dict):
    """打印报告"""
    print("\n" + "="*80)
    print("📊 大规模回测汇总报告 - 真实数据")
    print("="*80)
    
    meta = report['meta']
    print(f"\n回测信息:")
    print(f"   周期: {meta['start_date']} ~ {meta['end_date']}")
    print(f"   标的: {meta['total_stocks']} 只")
    print(f"   策略: {meta['strategy']}")
    print(f"   数据源: {meta['data_source']}")
    
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
        print(f"   {emoji} {i}. {p['symbol']}: {p['total_return']:+7.2f}% | 夏普{p['sharpe_ratio']:.2f} | 回撤{p['max_drawdown']:.1f}%")
    
    print(f"\n⚠️  BOTTOM 10 表现:")
    for i, p in enumerate(report['bottom_performers'], 1):
        print(f"      {i}. {p['symbol']}: {p['total_return']:+7.2f}% | 夏普{p['sharpe_ratio']:.2f} | 回撤{p['max_drawdown']:.1f}%")
    
    # 行业分布分析
    from us_stock_universe import US_STOCK_UNIVERSE
    sector_performance = {}
    for r in report['all_results']:
        for sector, stocks in US_STOCK_UNIVERSE.items():
            if r['symbol'] in stocks:
                if sector not in sector_performance:
                    sector_performance[sector] = []
                sector_performance[sector].append(r['total_return'])
                break
    
    print(f"\n📊 行业表现:")
    for sector, returns in sorted(sector_performance.items(), key=lambda x: np.mean(x[1]), reverse=True):
        avg = np.mean(returns)
        print(f"   {sector}: {avg:+.2f}% (平均)")
    
    print("\n" + "="*80)
    print("✅ 关键说明:")
    print("   • 使用真实市场数据 (Massive API)")
    print("   • 严格避免未来函数")
    print("   • 信号在盘前生成，交易在开盘价执行")
    print("="*80)


def save_report(report: dict):
    """保存报告"""
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"live_backtest_100stocks_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 详细报告已保存: {filepath}")
    return filepath


def main():
    """主函数"""
    symbols = get_all_us_stocks()
    
    print("🎯 美股大规模回测 - 真实数据")
    print(f"   股票数量: {len(symbols)} 只")
    print(f"   行业覆盖: 11个GICS行业")
    
    # 回测2024-2026两年
    start_date = "2024-01-01"
    end_date = "2026-02-28"
    
    report = run_massive_backtest(symbols, start_date, end_date)
    
    if 'error' not in report:
        print_report(report)
        save_report(report)
        
        # 保存到数据库
        print("\n💾 保存到数据库...")
        db = BacktestDatabase()
        batch_id = f"massive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 添加行业信息
        from us_stock_universe import US_STOCK_UNIVERSE
        for r in report['all_results']:
            for sector, stocks in US_STOCK_UNIVERSE.items():
                if r['symbol'] in stocks:
                    r['sector'] = sector
                    break
        
        db.save_backtest_batch(
            batch_id=batch_id,
            name="美股110只两年回测",
            strategy_name="MA_Crossover_RSI",
            market="US",
            start_date=start_date,
            end_date=end_date,
            results=report['all_results'],
            description="使用Massive API真实数据，双均线+RSI策略",
            strategy_params={
                'ma_fast': 5,
                'ma_slow': 20,
                'rsi_period': 14,
                'rsi_buy': 70,
                'rsi_sell': 80
            }
        )
        print(f"✅ 已保存到数据库，批次ID: {batch_id}")
    else:
        print(f"❌ {report['error']}")


if __name__ == "__main__":
    main()
