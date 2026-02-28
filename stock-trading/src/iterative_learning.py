"""
多轮迭代学习系统
让量化交易系统通过不断回测 - 分析 - 优化来自我进化
"""
from typing import Dict, Any, List, Callable
from datetime import datetime
import json
import os


class IterativeLearningSystem:
    """
    迭代学习系统
    流程：回测 → 分析 → 提出假设 → 调整策略 → 再回测 → 验证
    """
    
    def __init__(self, symbols: List[str], start_date: str, end_date: str,
                 strategy_func: Callable, target_metrics: Dict[str, float]):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_func = strategy_func
        self.target_metrics = target_metrics
        
        self.iteration_history = []
        self.best_result = None
        self.learnings = []
    
    def run_iterations(self, max_iterations: int = 5) -> Dict[str, Any]:
        """
        运行多轮迭代
        """
        print(f"\n{'='*70}")
        print(f"🔄 迭代学习系统启动")
        print(f"{'='*70}")
        print(f"股票池：{', '.join(self.symbols)}")
        print(f"回测周期：{self.start_date} 至 {self.end_date}")
        print(f"目标指标：{self.target_metrics}")
        print(f"最大迭代次数：{max_iterations}")
        print(f"{'='*70}\n")
        
        for i in range(max_iterations):
            print(f"\n{'='*70}")
            print(f"🔁 第 {i+1}/{max_iterations} 轮迭代")
            print(f"{'='*70}\n")
            
            # Step 1: 回测所有股票
            print(f"[Step 1/4] 执行回测...")
            backtest_results = self._backtest_all_symbols()
            
            # Step 2: 分析结果
            print(f"\n[Step 2/4] 分析回测结果...")
            analysis = self._analyze_results(backtest_results)
            
            # Step 3: 提出优化假设
            print(f"\n[Step 3/4] 生成优化假设...")
            hypotheses = self._generate_hypotheses(analysis)
            
            # Step 4: 应用优化并验证
            print(f"\n[Step 4/4] 应用优化并验证...")
            if i < max_iterations - 1:  # 最后一轮不优化
                self._apply_optimizations(hypotheses)
            
            # 记录本轮结果
            iteration_record = {
                'iteration': i + 1,
                'timestamp': datetime.now().isoformat(),
                'backtest_results': backtest_results,
                'analysis': analysis,
                'hypotheses': hypotheses,
                'best_symbol': analysis.get('best_symbol'),
                'avg_return': analysis.get('avg_return')
            }
            self.iteration_history.append(iteration_record)
            
            # 更新最佳结果
            if not self.best_result or analysis.get('avg_return', 0) > self.best_result.get('avg_return', 0):
                self.best_result = analysis
            
            # 检查是否达标
            if self._check_targets(analysis):
                print(f"\n✅ 达到目标指标！停止迭代")
                break
        
        # 输出总结报告
        self._generate_final_report()
        
        return {
            'iterations_completed': len(self.iteration_history),
            'best_result': self.best_result,
            'learnings': self.learnings,
            'iteration_history': self.iteration_history
        }
    
    def _backtest_all_symbols(self) -> List[Dict[str, Any]]:
        """
        回测所有股票
        """
        from backtest import backtest_strategy
        
        results = []
        for symbol in self.symbols:
            print(f"   回测 {symbol}...", end=' ', flush=True)
            result = backtest_strategy(
                symbol=symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                strategy_func=self.strategy_func,
                verbose=False
            )
            
            if result.get('status') == 'completed':
                results.append({
                    'symbol': symbol,
                    'total_return': result.get('total_return', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'win_rate': result.get('win_rate', 0),
                    'total_trades': result.get('total_trades', 0)
                })
                print(f"收益 {result.get('total_return', 0):+.1f}%")
            else:
                print(f"❌ 失败")
        
        return results
    
    def _analyze_results(self, results: List[Dict]) -> Dict[str, Any]:
        """
        分析回测结果
        """
        if not results:
            return {'error': 'No results'}
        
        # 计算统计
        returns = [r['total_return'] for r in results]
        avg_return = sum(returns) / len(returns)
        best_idx = returns.index(max(returns))
        worst_idx = returns.index(min(returns))
        
        analysis = {
            'avg_return': avg_return,
            'best_symbol': results[best_idx]['symbol'],
            'best_return': results[best_idx]['total_return'],
            'worst_symbol': results[worst_idx]['symbol'],
            'worst_return': results[worst_idx]['total_return'],
            'symbols_above_target': sum(1 for r in results if r['total_return'] >= self.target_metrics.get('min_total_return', 0)),
            'symbols_below_target': sum(1 for r in results if r['total_return'] < self.target_metrics.get('min_total_return', 0)),
            'detailed_results': results
        }
        
        # 输出分析
        print(f"   平均收益：{avg_return:+.1f}%")
        print(f"   最佳股票：{analysis['best_symbol']} ({analysis['best_return']:+.1f}%)")
        print(f"   最差股票：{analysis['worst_symbol']} ({analysis['worst_return']:+.1f}%)")
        print(f"   达标股票：{analysis['symbols_above_target']}/{len(results)}")
        
        return analysis
    
    def _generate_hypotheses(self, analysis: Dict) -> List[Dict[str, Any]]:
        """
        生成优化假设
        """
        hypotheses = []
        
        # 假设 1: 如果平均收益低，可能是策略太保守
        if analysis.get('avg_return', 0) < self.target_metrics.get('min_total_return', 0):
            hypotheses.append({
                'type': 'strategy_adjustment',
                'observation': f"平均收益 {analysis.get('avg_return', 0):+.1f}% 低于目标 {self.target_metrics.get('min_total_return', 0)}%",
                'hypothesis': '策略可能过于保守，建议放宽买入条件',
                'proposed_change': '降低 RSI 买入阈值从 40 到 35',
                'expected_impact': '增加交易频率，提高收益'
            })
            self.learnings.append("策略保守导致收益不足")
        
        # 假设 2: 如果回撤大，需要加强风控
        avg_drawdown = sum(r.get('max_drawdown', 0) for r in analysis.get('detailed_results', [])) / max(len(analysis.get('detailed_results', [])), 1)
        if abs(avg_drawdown) > abs(self.target_metrics.get('max_drawdown', -15)):
            hypotheses.append({
                'type': 'risk_management',
                'observation': f"平均回撤 {avg_drawdown:+.1f}% 超过限制 {self.target_metrics.get('max_drawdown', -15)}%",
                'hypothesis': '止损设置过宽或趋势判断不准确',
                'proposed_change': '收紧止损从 -8% 到 -5%，加强趋势过滤',
                'expected_impact': '降低回撤，保护本金'
            })
            self.learnings.append("回撤控制需要加强")
        
        # 假设 3: 如果只有个别股票表现好，需要选股优化
        if analysis.get('symbols_above_target', 0) < len(self.symbols) * 0.5:
            hypotheses.append({
                'type': 'stock_selection',
                'observation': f"仅 {analysis.get('symbols_above_target', 0)}/{len(self.symbols)} 股票达标",
                'hypothesis': '策略只适合特定类型股票，需要优化选股',
                'proposed_change': f"重点关注 {analysis.get('best_symbol', 'N/A')} 类股票特性",
                'expected_impact': '提高选股准确率'
            })
            self.learnings.append(f"策略对股票类型敏感，{analysis.get('best_symbol', 'N/A')} 表现优异")
        
        # 输出假设
        if hypotheses:
            print(f"   生成 {len(hypotheses)} 个优化假设:")
            for i, h in enumerate(hypotheses, 1):
                print(f"   {i}. {h['hypothesis']}")
        else:
            print(f"   无需优化，当前策略已达标")
        
        return hypotheses
    
    def _apply_optimizations(self, hypotheses: List[Dict]):
        """
        应用优化 (简化版 - 实际应该修改策略参数)
        """
        if not hypotheses:
            return
        
        print(f"   应用优化:")
        for h in hypotheses:
            print(f"   - {h['proposed_change']}")
        
        # TODO: 实际应用中应该在这里修改策略参数
        # 目前只是记录学习
        
        self.learnings.append(f"第{len(self.iteration_history)+1}轮优化：{[h['proposed_change'] for h in hypotheses]}")
    
    def _check_targets(self, analysis: Dict) -> bool:
        """
        检查是否达到目标
        """
        if analysis.get('avg_return', 0) < self.target_metrics.get('min_total_return', 0):
            return False
        
        avg_drawdown = sum(r.get('max_drawdown', 0) for r in analysis.get('detailed_results', [])) / max(len(analysis.get('detailed_results', [])), 1)
        if avg_drawdown < self.target_metrics.get('max_drawdown', -15):
            return False
        
        return True
    
    def _generate_final_report(self):
        """
        生成最终报告
        """
        print(f"\n{'='*70}")
        print(f"📊 迭代学习总结报告")
        print(f"{'='*70}")
        
        print(f"\n【迭代统计】")
        print(f"  完成轮次：{len(self.iteration_history)}")
        print(f"  最佳平均收益：{self.best_result.get('avg_return', 0):+.1f}%")
        print(f"  最佳股票：{self.best_result.get('best_symbol', 'N/A')}")
        
        print(f"\n【关键学习】")
        for i, learning in enumerate(self.learnings[-5:], 1):  # 只显示最近 5 条
            print(f"  {i}. {learning}")
        
        print(f"\n【下一步建议】")
        if self.best_result.get('avg_return', 0) >= self.target_metrics.get('min_total_return', 0):
            print(f"  ✅ 策略已达标，可以进行实盘测试")
        else:
            print(f"  ⚠️ 策略仍需优化，建议：")
            print(f"     1. 收集更多数据")
            print(f"     2. 调整策略框架")
            print(f"     3. 考虑多策略组合")
        
        print(f"\n{'='*70}\n")


# 使用示例
if __name__ == "__main__":
    print("迭代学习系统 - 测试")
    
    # 导入策略
    from strategies.optimized_v2_strategy import optimized_v2_strategy
    
    # 创建系统
    system = IterativeLearningSystem(
        symbols=['GOOGL', 'AAPL', 'MSFT'],
        start_date='2025-06-01',
        end_date='2026-02-27',
        strategy_func=optimized_v2_strategy,
        target_metrics={
            'min_total_return': 20,
            'max_drawdown': -15
        }
    )
    
    # 运行迭代
    result = system.run_iterations(max_iterations=3)
    
    print(f"\n✅ 迭代学习完成！")
    print(f"关键学习：{result['learnings']}")
