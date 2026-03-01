#!/usr/bin/env python3
"""
A 股 ETF 批量回测 - Q 脑量化交易系统
====================================
对 A 股热门 ETF 进行批量回测（2024-2026）

策略：
1. 均线交叉策略（MA Cross）
2. RSI 超买超卖策略
3. 布林带策略

作者：Backer-Agent (Q 脑回测架构师)
创建：2026-03-01
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

# 添加路径
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_DIR)

# 确保能导入 src 模块
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

try:
    from src.batch_backtester import BatchBacktester, BacktestConfig, create_etf_config
    from src.performance_analyzer import EnhancedPerformanceAnalyzer, BatchPerformanceAnalyzer
    from src.backtest.performance import Trade
except ImportError as e:
    print(f"导入错误：{e}")
    print(f"工作目录：{WORKSPACE_DIR}")
    print(f"Python 路径：{sys.path}")
    raise

# A 股 ETF 列表（按板块分类）
A_SHARE_ETF_LIST = {
    # 科技类
    "512760": "芯片 ETF",
    "159995": "半导体 ETF",
    "515030": "新能源车 ETF",
    "515050": "5GETF",
    "159819": "人工智能 ETF",
    "515980": "人工智能 AI ETF",
    "515880": "通信 ETF",
    
    # 医药类
    "512010": "医药 ETF",
    "512170": "医疗 ETF",
    "159992": "创新药 ETF",
    "512290": "生物医药 ETF",
    "159837": "生物科技 ETF",
    
    # 消费类
    "159928": "消费 ETF",
    "510150": "消费 50ETF",
    "159736": "酒 ETF",
    "512600": "主要消费 ETF",
    "515650": "消费龙头 ETF",
    
    # 宽基类
    "510300": "沪深 300ETF",
    "510050": "上证 50ETF",
    "159915": "创业板 ETF",
    "588000": "科创 50ETF",
    "510500": "中证 500ETF",
    "510880": "红利 ETF",
    "512010": "医药 ETF",
    
    # 金融类
    "512880": "证券 ETF",
    "512000": "券商 ETF",
    "512730": "银行 ETF",
    "512640": "金融 ETF",
    "515030": "新能源车 ETF",
    
    # 周期类
    "159980": "有色 ETF",
    "512400": "有色金属 ETF",
    "159985": "豆粕 ETF",
    "159981": "能源化工 ETF",
    "515220": "煤炭 ETF",
    
    # 主题类
    "512660": "军工 ETF",
    "512580": "环保 ETF",
    "515700": "新能源 ETF",
    "516160": "新能源车 ETF",
    "515790": "光伏 ETF",
}


def get_etf_data_sina(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取 ETF 历史数据（新浪财经）
    
    Args:
        symbol: ETF 代码
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        import akshare as ak
        
        # 添加交易所前缀
        if not symbol.startswith(('sh', 'sz')):
            prefix = 'sh' if symbol.startswith('5') or symbol.startswith('1') else 'sz'
            full_symbol = f"{prefix}{symbol}"
        else:
            full_symbol = symbol
        
        # 获取历史数据
        df = ak.fund_etf_hist_sina(symbol=full_symbol)
        
        if df is None or len(df) == 0:
            return None
        
        # 日期过滤
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        df = df[mask].copy()
        
        if len(df) < 60:
            return None
        
        # 设置索引
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
        
    except Exception as e:
        print(f"❌ 获取数据失败 {symbol}: {e}")
        return None


def ma_cross_strategy(
    df: pd.DataFrame,
    params: Dict = None
) -> Tuple[pd.Series, pd.Series]:
    """
    均线交叉策略
    
    买入信号：短均线上穿长均线
    卖出信号：短均线下穿长均线
    
    Args:
        df: 价格数据
        params: 参数 {short_window, long_window}
    
    Returns:
        (buy_signals, sell_signals)
    """
    if params is None:
        params = {'short_window': 5, 'long_window': 20}
    
    short_window = params.get('short_window', 5)
    long_window = params.get('long_window', 20)
    
    # 计算均线
    df['ma_short'] = df['close'].rolling(window=short_window).mean()
    df['ma_long'] = df['close'].rolling(window=long_window).mean()
    
    # 生成信号
    buy_signals = pd.Series(False, index=df.index)
    sell_signals = pd.Series(False, index=df.index)
    
    # 金叉：短均线上穿长均线
    golden_cross = (df['ma_short'] > df['ma_long']) & (df['ma_short'].shift(1) <= df['ma_long'].shift(1))
    buy_signals[golden_cross] = True
    
    # 死叉：短均线下穿长均线
    death_cross = (df['ma_short'] < df['ma_long']) & (df['ma_short'].shift(1) >= df['ma_long'].shift(1))
    sell_signals[death_cross] = True
    
    return buy_signals, sell_signals


def rsi_strategy(
    df: pd.DataFrame,
    params: Dict = None
) -> Tuple[pd.Series, pd.Series]:
    """
    RSI 超买超卖策略
    
    买入信号：RSI < 30 (超卖)
    卖出信号：RSI > 70 (超买)
    
    Args:
        df: 价格数据
        params: 参数 {rsi_period, oversold, overbought}
    
    Returns:
        (buy_signals, sell_signals)
    """
    if params is None:
        params = {'rsi_period': 14, 'oversold': 30, 'overbought': 70}
    
    rsi_period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    
    # 计算 RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 生成信号
    buy_signals = df['rsi'] < oversold
    sell_signals = df['rsi'] > overbought
    
    return buy_signals, sell_signals


def bollinger_strategy(
    df: pd.DataFrame,
    params: Dict = None
) -> Tuple[pd.Series, pd.Series]:
    """
    布林带策略
    
    买入信号：价格跌破下轨
    卖出信号：价格突破上轨
    
    Args:
        df: 价格数据
        params: 参数 {window, num_std}
    
    Returns:
        (buy_signals, sell_signals)
    """
    if params is None:
        params = {'window': 20, 'num_std': 2}
    
    window = params.get('window', 20)
    num_std = params.get('num_std', 2)
    
    # 计算布林带
    df['ma'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper'] = df['ma'] + (num_std * df['std'])
    df['lower'] = df['ma'] - (num_std * df['std'])
    
    # 生成信号
    buy_signals = df['close'] < df['lower']
    sell_signals = df['close'] > df['upper']
    
    return buy_signals, sell_signals


def run_etf_batch_backtest(
    etf_list: Dict[str, str] = None,
    start_date: str = "2024-01-01",
    end_date: str = "2026-12-31",
    strategy: str = "ma_cross",
    max_workers: int = 4,
    output_dir: str = "results/etf_batch_results"
):
    """
    运行 ETF 批量回测
    
    Args:
        etf_list: ETF 列表 {code: name}
        start_date: 开始日期
        end_date: 结束日期
        strategy: 策略名称 (ma_cross, rsi, bollinger)
        max_workers: 并发数
        output_dir: 输出目录
    """
    if etf_list is None:
        etf_list = A_SHARE_ETF_LIST
    
    # 选择策略函数
    strategy_map = {
        'ma_cross': ma_cross_strategy,
        'rsi': rsi_strategy,
        'bollinger': bollinger_strategy
    }
    
    if strategy not in strategy_map:
        raise ValueError(f"未知策略：{strategy}")
    
    strategy_func = strategy_map[strategy]
    
    print("=" * 70)
    print("  A 股 ETF 批量回测")
    print("=" * 70)
    print(f"  回测周期：{start_date} 至 {end_date}")
    print(f"  策略：{strategy}")
    print(f"  ETF 数量：{len(etf_list)}")
    print(f"  并发数：{max_workers}")
    print("=" * 70)
    print()
    
    # 创建回测配置
    configs = []
    for symbol, name in etf_list.items():
        config = create_etf_config(
            symbol=symbol,
            name=name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0
        )
        configs.append(config)
    
    # 创建批量回测引擎
    backtester = BatchBacktester(
        data_source=get_etf_data_sina,
        strategy_func=strategy_func,
        cache_enabled=True,
        cache_dir="cache/etf_backtest",
        max_workers=max_workers
    )
    
    # 进度回调
    def on_progress(completed: int, total: int, result):
        if result.status == 'success':
            m = result.metrics
            print(f"  ✓ [{completed}/{total}] {result.symbol} {result.name}: "
                  f"{m.total_return:+.2f}% (Sharpe: {m.sharpe_ratio:.2f})")
        elif result.status == 'error':
            print(f"  ✗ [{completed}/{total}] {result.symbol}: {result.error_message}")
        else:
            print(f"  - [{completed}/{total}] {result.symbol}: 跳过")
    
    backtester.set_progress_callback(on_progress)
    
    # 执行回测
    strategy_params = {}
    results = backtester.run_batch(configs, strategy_params, use_multiprocessing=False)
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = backtester.save_results(
        output_dir=output_dir,
        prefix=f"etf_{strategy}"
    )
    
    # 绩效分析
    print("\n" + "=" * 70)
    print("  绩效分析")
    print("=" * 70)
    
    analyzer = BatchPerformanceAnalyzer()
    
    for r in results:
        if r.status == 'success' and r.equity_curve:
            # 转换日期
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in r.dates] if r.dates else None
            
            analyzer.add_result(
                symbol=r.symbol,
                name=r.name,
                equity_curve=r.equity_curve,
                dates=dates,
                trades=r.trades,
                initial_capital=r.config.initial_capital
            )
    
    # 生成汇总报告
    report_file = os.path.join(output_dir, f"summary_report_{strategy}_{timestamp}.md")
    summary_report = analyzer.generate_summary_report(output_path=report_file)
    
    print("\n" + summary_report)
    
    # 保存 DataFrame
    df = analyzer.to_dataframe()
    csv_file = os.path.join(output_dir, f"etf_performance_{strategy}_{timestamp}.csv")
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    print(f"\n📁 结果保存:")
    print(f"   - 详细结果：{output_path}")
    print(f"   - 汇总报告：{report_file}")
    print(f"   - CSV 数据：{csv_file}")
    
    return results, analyzer


def run_multi_strategy_comparison(
    etf_list: Dict[str, str] = None,
    start_date: str = "2024-01-01",
    end_date: str = "2026-12-31",
    output_dir: str = "results/etf_batch_results"
):
    """
    运行多策略对比回测
    
    Args:
        etf_list: ETF 列表
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
    """
    strategies = ['ma_cross', 'rsi', 'bollinger']
    all_results = {}
    
    for strategy in strategies:
        print(f"\n{'='*70}")
        print(f"  执行策略：{strategy}")
        print('='*70)
        
        results, analyzer = run_etf_batch_backtest(
            etf_list=etf_list,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            max_workers=4,
            output_dir=output_dir
        )
        
        all_results[strategy] = {
            'results': results,
            'analyzer': analyzer
        }
    
    # 生成策略对比报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    comparison_file = os.path.join(output_dir, f"strategy_comparison_{timestamp}.md")
    
    lines = []
    lines.append("=" * 70)
    lines.append("  多策略对比分析报告")
    lines.append(f"  生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")
    
    for strategy, data in all_results.items():
        analyzer = data['analyzer']
        if analyzer.results:
            avg_return = np.mean([r['metrics'].total_return for r in analyzer.results])
            avg_sharpe = np.mean([r['metrics'].sharpe_ratio for r in analyzer.results])
            avg_dd = np.mean([r['metrics'].max_drawdown for r in analyzer.results])
            
            lines.append(f"📊 {strategy.upper()} 策略")
            lines.append("-" * 70)
            lines.append(f"  平均收益：  {avg_return:+.2f}%")
            lines.append(f"  平均夏普：  {avg_sharpe:.2f}")
            lines.append(f"  平均回撤：  {avg_dd:.2f}%")
            lines.append("")
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n📁 策略对比报告：{comparison_file}")
    
    return all_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='A 股 ETF 批量回测')
    parser.add_argument('--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2026-12-31', help='结束日期')
    parser.add_argument('--strategy', type=str, default='ma_cross', 
                       choices=['ma_cross', 'rsi', 'bollinger', 'all'],
                       help='策略选择')
    parser.add_argument('--workers', type=int, default=4, help='并发数')
    parser.add_argument('--output', type=str, default='results/etf_batch_results', help='输出目录')
    parser.add_argument('--symbols', type=str, help='指定 ETF 代码 (逗号分隔)')
    
    args = parser.parse_args()
    
    # 确定 ETF 列表
    if args.symbols:
        symbols = args.symbols.split(',')
        etf_list = {s: A_SHARE_ETF_LIST.get(s, f"ETF{s}") for s in symbols}
    else:
        etf_list = A_SHARE_ETF_LIST
    
    # 执行回测
    if args.strategy == 'all':
        run_multi_strategy_comparison(
            etf_list=etf_list,
            start_date=args.start,
            end_date=args.end,
            output_dir=args.output
        )
    else:
        run_etf_batch_backtest(
            etf_list=etf_list,
            start_date=args.start,
            end_date=args.end,
            strategy=args.strategy,
            max_workers=args.workers,
            output_dir=args.output
        )
