#!/usr/bin/env python3
"""
量化交易系统 - 主入口
支持回测、实盘分析、策略迭代等功能
"""
import argparse
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.massive_api import get_real_time_data, get_all_indicators, get_market_status
from src.sentiment_api import calculate_sentiment_score
from src.backtest import backtest_strategy
from src.strategy_runner import run_iteration_loop
from src.paper_trading import run_paper_trading, PaperTradingRunner
from src.trading_db import TradingDatabase
from strategies.default_strategy import default_strategy
from strategies.relaxed_strategy import relaxed_strategy
from strategies.optimized_strategy import optimized_strategy
from strategies.optimized_v2_strategy import optimized_v2_strategy
from strategies.adaptive_strategy_v6 import AdaptiveStrategyCoordinatorV6 as MultiStrategyCoordinator
from src.backtest_v2 import backtest_strategy_v2 as backtest_strategy


def cmd_analyze(args):
    """分析单只股票"""
    print(f"\n📊 分析股票：{args.symbol}\n")
    
    # 获取实时数据
    print("⏳ 获取市场数据...")
    price_data = get_real_time_data(args.symbol)
    
    if 'error' in price_data:
        print(f"❌ 获取价格数据失败：{price_data['error']}")
        return
    
    print(f"   当前价格：${price_data.get('price', 'N/A')}")
    print(f"   今日开盘：${price_data.get('open', 'N/A')}")
    print(f"   今日最高：${price_data.get('high', 'N/A')}")
    print(f"   今日最低：${price_data.get('low', 'N/A')}")
    print(f"   成交量：{price_data.get('volume', 'N/A'):,}")
    
    # 获取技术指标
    print("\n⏳ 计算技术指标...")
    indicators = get_all_indicators(args.symbol, period=90)
    
    if 'error' in indicators:
        print(f"❌ 获取指标失败：{indicators['error']}")
        return
    
    print(f"   RSI(14): {indicators.get('rsi_14', 'N/A')}")
    print(f"   MACD: {indicators.get('macd', 'N/A')}")
    print(f"   MACD Signal: {indicators.get('macd_signal', 'N/A')}")
    print(f"   SMA(20): {indicators.get('sma_20', 'N/A')}")
    print(f"   EMA(20): {indicators.get('ema_20', 'N/A')}")
    
    # 获取舆情
    print("\n⏳ 分析舆情...")
    sentiment = calculate_sentiment_score(args.symbol)
    
    print(f"   综合评分：{sentiment.get('composite_score', 'N/A')} ({sentiment.get('sentiment_level', 'N/A')})")
    print(f"   新闻情绪：{sentiment.get('components', {}).get('news', {}).get('score', 'N/A')}")
    print(f"   社交情绪：{sentiment.get('components', {}).get('social', {}).get('score', 'N/A')}")
    
    # 生成 LLM 决策提示词
    print("\n🤖 生成 LLM 决策提示词...")
    from src.llm_decision import build_decision_prompt
    
    data = {
        'current_price': price_data.get('price'),
        'technical_indicators': indicators,
        'sentiment': sentiment,
        'portfolio': {
            'current_position': args.position,
            'average_cost': args.cost,
            'available_capital': args.capital
        }
    }
    
    prompt = build_decision_prompt(args.symbol, data)
    print("\n" + "="*60)
    print("LLM 决策提示词:")
    print("="*60)
    print(prompt)
    print("="*60)
    print("\n💡 将此提示词发送给 LLM 获取交易决策")


def cmd_backtest(args):
    """运行回测"""
    print(f"\n📊 回测策略：{args.symbol}\n")
    
    # 解析日期
    if args.end == 'today':
        end_date = datetime.now().strftime('%Y-%m-%d')
    else:
        end_date = args.end
    
    # 选择策略
    strategy_map = {
        'default': default_strategy,
        'relaxed': relaxed_strategy,
        'optimized': optimized_strategy,
        'optimized_v2': optimized_v2_strategy
    }
    
    # 多策略框架特殊处理
    if args.strategy == 'multi':
        print(f"📈 使用策略：多策略框架 (自动选择)\n")
        coordinator = MultiStrategyCoordinator()
        
        trade_count = 0
        
        def multi_strategy_func(row, indicators, symbol_arg, position=None):
            nonlocal trade_count
            result = coordinator.execute(args.symbol, row, indicators, position)
            action = result.get('action', 'hold')
            action_lower = action.lower() if isinstance(action, str) else 'hold'
            
            # 调试输出 (前 10 次)
            if trade_count < 10:
                print(f"   [Day {trade_count+1}] {args.symbol}: {result.get('market_regime')} + {result.get('stock_type')} → {result.get('strategy_used')} → {action_lower}")
                trade_count += 1
            
            return action_lower
        
        strategy = multi_strategy_func
    else:
        strategy = strategy_map.get(args.strategy, relaxed_strategy)
        print(f"📈 使用策略：{args.strategy}\n")
    
    # 运行回测
    result = backtest_strategy(
        symbol=args.symbol,
        start_date=args.start,
        end_date=end_date,
        strategy_func=strategy,
        initial_capital=args.capital,
        verbose=True
    )
    
    if result.get('status') == 'completed':
        # 保存结果
        import json
        output_file = f"data/backtest_{args.symbol}_{args.start}_{end_date}.json"
        os.makedirs("data", exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"📁 结果已保存到：{output_file}")


def cmd_iterate(args):
    """运行策略迭代"""
    symbols = args.symbols.split(',')
    
    print(f"\n🚀 策略迭代循环")
    print(f"   股票池：{', '.join(symbols)}")
    print(f"   目标收益率：≥{args.target_return}%")
    print(f"   最大回撤：≤{args.max_drawdown}%")
    
    # 自定义目标
    targets = {
        'min_total_return': args.target_return,
        'max_drawdown': args.max_drawdown,
        'min_sharpe_ratio': args.min_sharpe,
        'min_win_rate': 50,
        'min_trades': 10
    }
    
    # 选择策略
    strategy_map = {
        'default': default_strategy,
        'relaxed': relaxed_strategy,
        'optimized': optimized_strategy,
        'optimized_v2': optimized_v2_strategy
    }
    
    # 多策略框架特殊处理
    if args.strategy == 'multi':
        print(f"📈 使用策略：自适应策略 V3 (多策略框架 + 股票筛选 + 动态止损)\n")
        
        # 为每个股票单独回测
        all_results = []
        for symbol in symbols:
            print(f"\n{'='*60}")
            print(f"📊 回测 {symbol}")
            print(f"{'='*60}")
            
            coordinator = MultiStrategyCoordinator()
            
            def make_strategy_func(sym):
                def strategy_func(row, indicators):
                    result = coordinator.execute(sym, row, indicators)
                    return result.get('action', 'hold').lower()
                return strategy_func
            
            strategy_func = make_strategy_func(symbol)
            
            from src.backtest import backtest_strategy
            result = backtest_strategy(
                symbol=symbol,
                start_date=args.start,
                end_date=args.end,
                strategy_func=strategy_func,
                verbose=True
            )
            
            all_results.append(result)
        
        # 返回综合结果
        return {
            'status': 'completed',
            'results': all_results,
            'symbols': symbols
        }
    else:
        strategy_func = strategy_map.get(args.strategy, relaxed_strategy)
        print(f"📈 使用策略：{args.strategy}\n")
    
    # 运行迭代
    results = run_iteration_loop(
        symbols=symbols,
        start_date=args.start,
        end_date=args.end,
        strategy_func=strategy_func,
        targets=targets,
        max_iterations=args.max_iterations
    )
    
    # 保存结果
    import json
    output_file = "data/iteration_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 详细结果已保存到：{output_file}")


def cmd_status(args):
    """检查市场状态"""
    print("\n📈 市场状态\n")
    
    status = get_market_status()
    
    if 'error' in status:
        print(f"❌ 获取市场状态失败：{status['error']}")
        return
    
    print(f"   状态：{status.get('status', 'N/A')}")
    print(f"   服务器时间：{status.get('server_time', 'N/A')}")
    print(f"   下次开盘：{status.get('next_open', 'N/A')}")
    print(f"   下次收盘：{status.get('next_close', 'N/A')}")
    print(f"   延长交易：{status.get('extended_hours', False)}")


def cmd_paper_trading(args):
    """模拟交易"""
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    print(f"\n📈 模拟交易")
    print(f"{'='*60}")
    print(f"股票池：{', '.join(symbols)}")
    print(f"初始资金：${args.capital:,.2f}")
    print(f"策略：{args.strategy}")
    print(f"仓位比例：{args.position_size*100:.1f}%")
    print(f"{'='*60}\n")
    
    # 运行模拟交易
    runner = PaperTradingRunner(
        initial_capital=args.capital,
        strategy_name=args.strategy,
        position_size_pct=args.position_size
    )
    
    # 执行今日交易
    report = runner.execute_daily_trading(symbols)
    
    # 显示绩效报告
    if args.show_report:
        perf_report = runner.get_performance_report()
        print("\n📊 绩效报告")
        print(f"{'='*60}")
        
        if 'error' not in perf_report:
            returns = perf_report.get('returns', {})
            stats = perf_report.get('statistics', {})
            
            print(f"交易天数：{perf_report.get('period', {}).get('trading_days', 0)}")
            print(f"总收益：{returns.get('total_return_pct', 0):.2f}%")
            print(f"年化收益：{returns.get('annual_return_pct', 0):.2f}%")
            print(f"夏普比率：{returns.get('sharpe_ratio', 0):.2f}")
            print(f"最大回撤：{returns.get('max_drawdown_pct', 0):.2f}%")
            print(f"胜率：{stats.get('win_rate', 0):.1f}%")
            print(f"总交易：{stats.get('total_trades', 0)}")
        
        print(f"{'='*60}\n")
    
    # 导出报告
    if args.export:
        runner.export_report(args.export)


def main():
    parser = argparse.ArgumentParser(
        description='美股量化交易系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py analyze AAPL                    # 分析单只股票
  python main.py backtest AAPL --start 2024-01-01  # 回测
  python main.py iterate AAPL,MSFT,GOOGL         # 策略迭代
  python main.py status                          # 市场状态
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='分析股票')
    analyze_parser.add_argument('symbol', help='股票代码')
    analyze_parser.add_argument('--position', type=int, default=0, help='当前持仓')
    analyze_parser.add_argument('--cost', type=float, default=0, help='平均成本')
    analyze_parser.add_argument('--capital', type=float, default=10000, help='可用资金')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # backtest 命令
    backtest_parser = subparsers.add_parser('backtest', help='回测策略')
    backtest_parser.add_argument('symbol', help='股票代码')
    backtest_parser.add_argument('--start', required=True, help='开始日期 (YYYY-MM-DD)')
    backtest_parser.add_argument('--end', default='today', help='结束日期 (YYYY-MM-DD 或 today)')
    backtest_parser.add_argument('--capital', type=float, default=10000, help='初始资金')
    backtest_parser.add_argument('--strategy', default='relaxed', 
                                 choices=['default', 'relaxed', 'optimized', 'optimized_v2', 'multi'],
                                 help='策略选择 (default: relaxed, multi=多策略框架)')
    backtest_parser.set_defaults(func=cmd_backtest)
    
    # iterate 命令
    iterate_parser = subparsers.add_parser('iterate', help='策略迭代')
    iterate_parser.add_argument('symbols', help='股票列表 (逗号分隔)')
    iterate_parser.add_argument('--start', required=True, help='开始日期')
    iterate_parser.add_argument('--end', required=True, help='结束日期')
    iterate_parser.add_argument('--strategy', default='multi', 
                                 choices=['default', 'relaxed', 'optimized', 'optimized_v2', 'multi'],
                                 help='策略选择 (default: multi)')
    iterate_parser.add_argument('--target-return', type=float, default=20, help='目标收益率%')
    iterate_parser.add_argument('--max-drawdown', type=float, default=-15, help='最大回撤%')
    iterate_parser.add_argument('--min-sharpe', type=float, default=1.5, help='最小夏普比率')
    iterate_parser.add_argument('--max-iterations', type=int, default=10, help='最大迭代次数')
    iterate_parser.set_defaults(func=cmd_iterate)
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='市场状态')
    status_parser.set_defaults(func=cmd_status)
    
    # paper 命令 (模拟交易)
    paper_parser = subparsers.add_parser('paper', help='模拟交易')
    paper_parser.add_argument('symbols', help='股票列表 (逗号分隔)')
    paper_parser.add_argument('--capital', type=float, default=10000, help='初始资金')
    paper_parser.add_argument('--strategy', default='optimized_v2',
                              choices=['relaxed', 'optimized_v2'],
                              help='策略选择')
    paper_parser.add_argument('--position-size', type=float, default=0.3,
                              help='仓位比例 (默认 0.3=30%)')
    paper_parser.add_argument('--show-report', action='store_true',
                              help='显示绩效报告')
    paper_parser.add_argument('--export', help='导出报告到文件')
    paper_parser.set_defaults(func=cmd_paper_trading)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
