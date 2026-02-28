"""
策略迭代运行器
自动执行回测 → 评估 → 复盘 → 调整 → 再验证的循环
"""
from typing import Dict, Any, List, Callable, Optional, Tuple
from datetime import datetime
import json
import os

from .config import TARGET_METRICS, BACKTEST_CONFIG
from .backtest import backtest_strategy, check_targets, calculate_metrics
from .massive_api import get_aggs


class StrategyIteraton:
    """
    策略迭代器
    自动执行多轮回测和策略优化
    """
    
    def __init__(self, targets: Optional[Dict[str, float]] = None):
        """
        初始化迭代器
        
        Args:
            targets: 目标指标配置
        """
        self.targets = targets or TARGET_METRICS.copy()
        self.iteration_history = []
        self.best_result = None
        self.best_metrics_score = -float('inf')
    
    def calculate_metrics_score(self, result: Dict[str, Any]) -> float:
        """
        计算综合指标分数 (用于比较策略优劣)
        """
        score = 0
        
        # 收益率贡献 (权重 40%)
        score += result.get('total_return', 0) * 0.4
        
        # 夏普比率贡献 (权重 30%)
        score += result.get('sharpe_ratio', 0) * 10 * 0.3
        
        # 回撤惩罚 (权重 20%)
        max_dd = result.get('max_drawdown', 0)
        if max_dd < -20:
            score -= 50  # 严重回撤惩罚
        elif max_dd < -10:
            score -= 20
        
        # 胜率贡献 (权重 10%)
        score += result.get('win_rate', 0) * 0.1
        
        return score
    
    def analyze_failure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析失败原因，提供调整建议
        """
        target_check = check_targets(result, self.targets)
        failed_metrics = target_check['failed_metrics']
        
        suggestions = []
        
        if 'total_return' in failed_metrics:
            suggestions.append({
                "metric": "total_return",
                "current": result.get('total_return', 0),
                "target": self.targets.get('min_total_return', 20),
                "suggestions": [
                    "放宽买入条件，增加交易机会",
                    "调整止盈比例，让利润奔跑",
                    "考虑在更强信号时增加仓位"
                ]
            })
        
        if 'max_drawdown' in failed_metrics:
            suggestions.append({
                "metric": "max_drawdown",
                "current": result.get('max_drawdown', 0),
                "target": self.targets.get('max_drawdown', -15),
                "suggestions": [
                    "收紧止损条件，减少单笔损失",
                    "降低仓位比例",
                    "增加趋势过滤，避免逆势交易"
                ]
            })
        
        if 'sharpe_ratio' in failed_metrics:
            suggestions.append({
                "metric": "sharpe_ratio",
                "current": result.get('sharpe_ratio', 0),
                "target": self.targets.get('min_sharpe_ratio', 1.5),
                "suggestions": [
                    "减少交易频率，提高信号质量",
                    "增加波动率过滤",
                    "优化持仓时间"
                ]
            })
        
        if 'win_rate' in failed_metrics:
            suggestions.append({
                "metric": "win_rate",
                "current": result.get('win_rate', 0),
                "target": self.targets.get('min_win_rate', 55),
                "suggestions": [
                    "增加确认条件，减少假信号",
                    "优化入场时机",
                    "考虑增加趋势过滤指标"
                ]
            })
        
        return {
            "failed_metrics": failed_metrics,
            "suggestions": suggestions,
            "summary": f"未达标项：{', '.join(failed_metrics)}" if failed_metrics else "所有指标达标"
        }
    
    def run_single_backtest(self, symbol: str, start_date: str, end_date: str,
                            strategy_func: Callable, 
                            iteration: int = 1) -> Dict[str, Any]:
        """
        执行单次回测
        """
        print(f"\n{'='*60}")
        print(f"🔄 迭代 #{iteration} - {symbol}")
        print(f"{'='*60}")
        
        result = backtest_strategy(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            strategy_func=strategy_func,
            verbose=True
        )
        
        if result.get('status') != 'completed':
            return {
                "iteration": iteration,
                "symbol": symbol,
                "status": "failed",
                "error": result.get('error')
            }
        
        # 检查目标
        target_check = check_targets(result, self.targets)
        
        # 计算综合分数
        metrics_score = self.calculate_metrics_score(result)
        
        iteration_result = {
            "iteration": iteration,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "metrics": {
                "total_return": result.get('total_return', 0),
                "max_drawdown": result.get('max_drawdown', 0),
                "sharpe_ratio": result.get('sharpe_ratio', 0),
                "win_rate": result.get('win_rate', 0),
                "total_trades": result.get('total_trades', 0)
            },
            "target_check": target_check,
            "metrics_score": metrics_score,
            "status": "passed" if target_check['passed'] else "failed",
            "trades": result.get('trades', [])
        }
        
        self.iteration_history.append(iteration_result)
        
        # 更新最佳结果
        if metrics_score > self.best_metrics_score:
            self.best_metrics_score = metrics_score
            self.best_result = iteration_result.copy()
        
        return iteration_result
    
    def run_iteration_loop(self, symbols: List[str], start_date: str, end_date: str,
                           strategy_func: Callable,
                           max_iterations: int = 10,
                           stop_on_success: bool = True) -> Dict[str, Any]:
        """
        运行迭代循环
        
        Args:
            symbols: 股票列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            strategy_func: 策略函数
            max_iterations: 最大迭代次数
            stop_on_success: 达到目标后是否停止
        
        Returns:
            迭代总结报告
        """
        print(f"\n🚀 开始策略迭代循环")
        print(f"   股票池：{', '.join(symbols)}")
        print(f"   回测周期：{start_date} 至 {end_date}")
        print(f"   最大迭代：{max_iterations}")
        print(f"   目标配置：{json.dumps(self.targets, indent=2)}")
        
        successful_runs = []
        failed_runs = []
        
        iteration = 0
        for symbol in symbols:
            if iteration >= max_iterations:
                break
            
            iteration += 1
            result = self.run_single_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                strategy_func=strategy_func,
                iteration=iteration
            )
            
            if result.get('status') == 'passed':
                successful_runs.append(result)
                if stop_on_success:
                    print(f"\n✅ {symbol} 回测通过目标！")
                    break
            else:
                failed_runs.append(result)
                # 分析失败原因
                analysis = self.analyze_failure({
                    **result.get('metrics', {}),
                    'total_trades': result.get('metrics', {}).get('total_trades', 0)
                })
                print(f"\n⚠️  {symbol} 未达标: {analysis['summary']}")
        
        # 生成总结报告
        summary = self.generate_summary(symbols, successful_runs, failed_runs)
        
        return summary
    
    def generate_summary(self, symbols: List[str], 
                         successful_runs: List[Dict], 
                         failed_runs: List[Dict]) -> Dict[str, Any]:
        """
        生成迭代总结报告
        """
        total_iterations = len(successful_runs) + len(failed_runs)
        
        summary = {
            "summary": {
                "total_iterations": total_iterations,
                "successful": len(successful_runs),
                "failed": len(failed_runs),
                "success_rate": round(len(successful_runs) / total_iterations * 100, 1) if total_iterations > 0 else 0,
                "symbols_tested": symbols[:total_iterations]
            },
            "best_result": self.best_result,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "all_iterations": self.iteration_history,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 打印总结
        print(f"\n{'='*60}")
        print(f"📊 迭代总结报告")
        print(f"{'='*60}")
        print(f"总迭代次数：{total_iterations}")
        print(f"成功次数：  {len(successful_runs)}")
        print(f"失败次数：  {len(failed_runs)}")
        print(f"成功率：    {summary['summary']['success_rate']}%")
        
        if self.best_result:
            print(f"\n🏆 最佳结果:")
            print(f"   股票：{self.best_result['symbol']}")
            print(f"   收益率：{self.best_result['metrics']['total_return']:.2f}%")
            print(f"   夏普比率：{self.best_result['metrics']['sharpe_ratio']:.2f}")
            print(f"   最大回撤：{self.best_result['metrics']['max_drawdown']:.2f}%")
            print(f"   胜率：{self.best_result['metrics']['win_rate']:.1f}%")
        
        print(f"{'='*60}\n")
        
        return summary


def run_iteration_loop(symbols: List[str], start_date: str, end_date: str,
                       strategy_func: Callable,
                       targets: Optional[Dict[str, float]] = None,
                       max_iterations: int = 10) -> Dict[str, Any]:
    """
    便捷函数：运行策略迭代循环
    """
    iterator = StrategyIteraton(targets=targets)
    return iterator.run_iteration_loop(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        strategy_func=strategy_func,
        max_iterations=max_iterations,
        stop_on_success=False  # 测试所有股票
    )


if __name__ == "__main__":
    # 示例策略
    def example_strategy(row, indicators):
        buy_conditions = []
        sell_conditions = []
        
        rsi = indicators.get('rsi_14', 50)
        if rsi < 30:
            buy_conditions.append("RSI 超卖")
        elif rsi > 70:
            sell_conditions.append("RSI 超买")
        
        macd = indicators.get('macd', 0)
        signal = indicators.get('macd_signal', 0)
        if macd > signal:
            buy_conditions.append("MACD 金叉")
        elif macd < signal:
            sell_conditions.append("MACD 死叉")
        
        if len(buy_conditions) >= 2:
            return 'buy'
        elif len(sell_conditions) >= 2:
            return 'sell'
        else:
            return 'hold'
    
    # 运行迭代
    symbols = ["AAPL", "MSFT", "GOOGL", "NVDA"]
    
    results = run_iteration_loop(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-12-31",
        strategy_func=example_strategy,
        max_iterations=5
    )
    
    # 保存结果
    output_file = "data/iteration_results.json"
    os.makedirs("data", exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📁 结果已保存到：{output_file}")
