"""
回测系统使用示例
================
演示如何使用新一代回测系统进行策略回测和绩效分析。
"""

from datetime import datetime, timedelta
import numpy as np

from src.backtest import (
    BacktestEngine,
    MovingAverageStrategy,
    FixedSlippage,
    SquareRootImpact,
    PerformanceAnalyzer,
    Bar,
    generate_performance_report,
)


def generate_sample_data(symbol: str, days: int = 252) -> list:
    """生成示例 K 线数据"""
    np.random.seed(42)
    
    # 生成随机价格序列 (几何布朗运动)
    returns = np.random.normal(0.0005, 0.02, days)  # 日收益均值 0.05%, 波动 2%
    price_series = 100 * np.cumprod(1 + returns)
    
    bars = []
    base_date = datetime(2025, 1, 1)
    
    for i in range(days):
        date = base_date + timedelta(days=i)
        # 跳过周末
        if date.weekday() >= 5:
            continue
        
        close = price_series[i]
        open_price = close * (1 + np.random.uniform(-0.01, 0.01))
        high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.01)))
        low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.01)))
        volume = int(np.random.uniform(100000, 1000000))
        
        bar = Bar(
            symbol=symbol,
            timestamp=date,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            freq="1d"
        )
        bars.append(bar)
    
    return bars


def run_basic_backtest():
    """运行基础回测示例"""
    print("=" * 60)
    print("回测系统示例 - 双均线策略")
    print("=" * 60)
    
    # 生成数据
    print("\n1. 生成示例数据...")
    bars = generate_sample_data("AAPL", days=252)
    bars_dict = {"AAPL": bars}
    print(f"   生成 {len(bars)} 个交易日数据")
    
    # 创建引擎
    print("\n2. 创建回测引擎...")
    engine = BacktestEngine(
        initial_cash=1000000,
        slippage_model=FixedSlippage(0.01),  # 每股 1 美分滑点
        impact_model=SquareRootImpact(0.1),   # 平方根冲击模型
        commission_rate=0.0003,               # 万三手续费
        freq="1d"
    )
    
    # 添加策略
    print("\n3. 添加策略 (MA5/MA20)...")
    strategy = MovingAverageStrategy(short_window=5, long_window=20)
    engine.add_strategy(strategy)
    
    # 设置数据
    print("\n4. 加载数据...")
    engine.set_data(bars_dict)
    
    # 运行回测
    print("\n5. 运行回测...")
    results = engine.run()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果摘要")
    print("=" * 60)
    print(f"初始资金：    ${results['initial_cash']:,.2f}")
    print(f"最终资金：    ${results['final_cash']:,.2f}")
    print(f"总收益率：    {(results['final_cash']/results['initial_cash']-1)*100:.2f}%")
    print(f"成交笔数：    {results['total_fills']}")
    print(f"总滑点成本：  ${results['total_slippage']:.2f}")
    print(f"总冲击成本：  ${results['total_impact']:.2f}")
    print(f"总手续费：    ${results['total_commission']:.2f}")
    
    return results


def run_performance_analysis():
    """运行绩效分析示例"""
    print("\n\n" + "=" * 60)
    print("绩效分析示例")
    print("=" * 60)
    
    # 先生成回测结果
    results = run_basic_backtest()
    
    # 创建绩效分析器
    print("\n6. 执行绩效分析...")
    analyzer = PerformanceAnalyzer(risk_free_rate=0.03)
    
    # 模拟权益曲线 (实际应从回测结果中提取)
    base_date = datetime(2025, 1, 1)
    equity = results['initial_cash']
    
    for i, fill in enumerate(results['fills'][:50]):  # 简化示例
        date = base_date + timedelta(days=i)
        # 模拟权益增长
        equity *= (1 + np.random.normal(0.001, 0.01))
        analyzer.add_equity_point(date, equity)
    
    # 计算绩效指标
    metrics = analyzer.analyze(initial_capital=results['initial_cash'])
    
    # 生成报告
    print("\n")
    report = generate_performance_report(metrics)
    print(report)
    
    return metrics


def run_parameter_optimization():
    """参数优化示例"""
    print("\n\n" + "=" * 60)
    print("参数优化示例")
    print("=" * 60)
    
    # 生成数据
    bars = generate_sample_data("AAPL", days=252)
    bars_dict = {"AAPL": bars}
    
    # 参数网格
    param_grid = [
        (5, 15), (5, 20), (5, 25),
        (10, 20), (10, 25), (10, 30),
        (15, 25), (15, 30), (15, 40),
    ]
    
    print(f"\n测试 {len(param_grid)} 组参数...")
    
    best_sharpe = -float('inf')
    best_params = None
    
    for short_window, long_window in param_grid:
        # 创建引擎
        engine = BacktestEngine(
            initial_cash=1000000,
            slippage_model=FixedSlippage(0.01),
            impact_model=SquareRootImpact(0.1),
            commission_rate=0.0003,
            freq="1d"
        )
        
        # 添加策略
        strategy = MovingAverageStrategy(short_window, long_window)
        engine.add_strategy(strategy)
        engine.set_data(bars_dict)
        
        # 运行回测
        results = engine.run()
        
        # 简化计算夏普比率
        total_return = (results['final_cash'] - results['initial_cash']) / results['initial_cash']
        sharpe = total_return / 0.1  # 简化假设波动率 10%
        
        print(f"  MA({short_window}/{long_window}): 收益={total_return:>7.2%}, 夏普={sharpe:>6.2f}")
        
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = (short_window, long_window)
    
    print(f"\n最优参数：MA{best_params[0]}/MA{best_params[1]}, 夏普比率={best_sharpe:.2f}")
    
    return best_params


if __name__ == "__main__":
    # 运行示例
    print("\n🧠 Q-Brain 回测系统示例\n")
    
    # 示例 1: 基础回测
    run_basic_backtest()
    
    # 示例 2: 绩效分析
    run_performance_analysis()
    
    # 示例 3: 参数优化
    run_parameter_optimization()
    
    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)
