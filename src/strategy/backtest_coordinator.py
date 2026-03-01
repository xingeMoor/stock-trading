#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测协调器 (Backtest Coordinator)
协调策略开发和回测验证，跟踪回测结果并提出优化建议
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import json


class BacktestStatus(Enum):
    """回测状态"""
    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class PerformanceRating(Enum):
    """绩效评级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    ACCEPTABLE = "acceptable"  # 可接受
    POOR = "poor"  # 较差
    UNACCEPTABLE = "unacceptable"  # 不可接受


@dataclass
class BacktestRequest:
    """回测请求"""
    request_id: str
    strategy_id: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    universe: List[str]  # 股票池
    frequency: str  # daily/intraday
    parameters: Dict[str, Any]
    benchmark: str = "SPY"
    include_costs: bool = True
    slippage_model: str = "fixed"
    commission_rate: float = 0.001


@dataclass
class BacktestResult:
    """回测结果"""
    request_id: str
    strategy_id: str
    status: BacktestStatus
    start_time: str
    end_time: str
    duration_seconds: float
    error_message: Optional[str]
    
    # 绩效指标
    total_return: float
    annual_return: float
    benchmark_return: float
    alpha: float
    beta: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    avg_holding_period_days: int
    
    # 风险分析
    volatility: float
    var_95: float
    cvar_95: float
    correlation_benchmark: float
    
    # 交易成本
    total_commission: float
    total_slippage: float
    turnover_rate: float


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    suggestion_id: str
    category: str  # parameter/risk/execution/data
    priority: str  # high/medium/low
    description: str
    current_value: Any
    suggested_value: Any
    expected_improvement: str
    implementation_effort: str  # low/medium/high
    validation_required: bool


class BacktestCoordinator:
    """回测协调器核心类"""
    
    def __init__(self):
        self.backtest_queue: List[BacktestRequest] = []
        self.completed_backtests: Dict[str, BacktestResult] = {}
        self.optimization_history: Dict[str, List[OptimizationSuggestion]] = {}
        
        # 绩效阈值
        self.performance_thresholds = {
            "excellent": {
                "sharpe_ratio": 2.0,
                "max_drawdown": 0.10,
                "annual_return": 0.20,
                "win_rate": 0.55
            },
            "good": {
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.15,
                "annual_return": 0.12,
                "win_rate": 0.50
            },
            "acceptable": {
                "sharpe_ratio": 1.0,
                "max_drawdown": 0.20,
                "annual_return": 0.08,
                "win_rate": 0.45
            }
        }
    
    def submit_backtest(self, request: BacktestRequest) -> str:
        """
        提交回测请求
        
        Args:
            request: 回测请求对象
            
        Returns:
            str: 回测请求 ID
        """
        self.backtest_queue.append(request)
        return request.request_id
    
    def process_backtest(
        self,
        request: BacktestRequest,
        result_data: Dict[str, Any]
    ) -> BacktestResult:
        """
        处理回测结果
        
        Args:
            request: 回测请求
            result_data: 回测引擎返回的原始数据
            
        Returns:
            BacktestResult: 回测结果对象
        """
        # 解析回测结果
        result = self._parse_backtest_result(request, result_data)
        
        # 存储结果
        self.completed_backtests[request.request_id] = result
        
        # 生成优化建议
        suggestions = self._generate_optimization_suggestions(request, result)
        self.optimization_history[request.request_id] = suggestions
        
        # 评估绩效评级
        rating = self._evaluate_performance(result)
        
        # 记录日志
        self._log_backtest_completion(request, result, rating)
        
        return result
    
    def _parse_backtest_result(
        self,
        request: BacktestRequest,
        data: Dict[str, Any]
    ) -> BacktestResult:
        """解析回测结果数据"""
        metrics = data.get("metrics", {})
        risk = data.get("risk", {})
        trades = data.get("trades", {})
        costs = data.get("costs", {})
        
        return BacktestResult(
            request_id=request.request_id,
            strategy_id=request.strategy_id,
            status=BacktestStatus.COMPLETED if data.get("success") else BacktestStatus.FAILED,
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            duration_seconds=data.get("duration_seconds", 0),
            error_message=data.get("error_message"),
            
            # 绩效指标
            total_return=metrics.get("total_return", 0),
            annual_return=metrics.get("annual_return", 0),
            benchmark_return=metrics.get("benchmark_return", 0),
            alpha=metrics.get("alpha", 0),
            beta=metrics.get("beta", 0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0),
            sortino_ratio=metrics.get("sortino_ratio", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            max_drawdown_duration_days=metrics.get("max_drawdown_duration", 0),
            win_rate=trades.get("win_rate", 0),
            profit_factor=trades.get("profit_factor", 0),
            total_trades=trades.get("total_trades", 0),
            winning_trades=trades.get("winning_trades", 0),
            losing_trades=trades.get("losing_trades", 0),
            avg_win=trades.get("avg_win", 0),
            avg_loss=trades.get("avg_loss", 0),
            avg_holding_period_days=trades.get("avg_holding_period", 0),
            
            # 风险分析
            volatility=risk.get("volatility", 0),
            var_95=risk.get("var_95", 0),
            cvar_95=risk.get("cvar_95", 0),
            correlation_benchmark=risk.get("correlation_benchmark", 0),
            
            # 交易成本
            total_commission=costs.get("commission", 0),
            total_slippage=costs.get("slippage", 0),
            turnover_rate=costs.get("turnover_rate", 0)
        )
    
    def _generate_optimization_suggestions(
        self,
        request: BacktestRequest,
        result: BacktestResult
    ) -> List[OptimizationSuggestion]:
        """生成优化建议"""
        suggestions = []
        suggestion_id = 0
        
        # 1. 参数优化建议
        if result.sharpe_ratio < 1.0:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="parameter",
                priority="high",
                description="夏普比率偏低，建议优化入场/出场参数",
                current_value=request.parameters,
                suggested_value="使用网格搜索或贝叶斯优化寻找最优参数",
                expected_improvement="夏普比率提升 0.3-0.5",
                implementation_effort="medium",
                validation_required=True
            ))
        
        # 2. 风险控制建议
        if result.max_drawdown > 0.20:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="risk",
                priority="high",
                description="最大回撤过大，需要加强风险控制",
                current_value=f"当前回撤：{result.max_drawdown:.2%}",
                suggested_value="添加止损规则、降低仓位、增加分散度",
                expected_improvement="回撤降低至 15% 以内",
                implementation_effort="low",
                validation_required=True
            ))
        
        # 3. 交易成本优化
        if result.turnover_rate > 2.0:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="execution",
                priority="medium",
                description="换手率过高，交易成本侵蚀利润",
                current_value=f"年换手率：{result.turnover_rate:.2f}",
                suggested_value="减少交易频率、优化信号过滤、使用限价单",
                expected_improvement=f"年节省成本约 ${result.total_commission * 0.3:.2f}",
                implementation_effort="medium",
                validation_required=True
            ))
        
        # 4. 胜率优化
        if result.win_rate < 0.45 and result.profit_factor < 1.2:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="parameter",
                priority="high",
                description="胜率和盈亏比双低，策略逻辑可能需要调整",
                current_value=f"胜率：{result.win_rate:.2%}, 盈亏比：{result.profit_factor:.2f}",
                suggested_value="重新评估信号质量、添加过滤器、优化止损止盈",
                expected_improvement="胜率提升至 50%+, 盈亏比提升至 1.5+",
                implementation_effort="high",
                validation_required=True
            ))
        
        # 5. 持有期优化
        if result.avg_holding_period_days < 3 and result.total_trades > 100:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="parameter",
                priority="medium",
                description="交易过于频繁，可能过度交易",
                current_value=f"平均持有期：{result.avg_holding_period_days}天",
                suggested_value="增加信号确认条件、延长持有期",
                expected_improvement="减少无效交易，提升单笔收益",
                implementation_effort="low",
                validation_required=True
            ))
        
        # 6. 数据质量建议
        if result.total_trades < 30:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="data",
                priority="medium",
                description="交易样本不足，统计显著性不够",
                current_value=f"交易次数：{result.total_trades}",
                suggested_value="延长回测周期或扩展股票池",
                expected_improvement="提升结果可信度",
                implementation_effort="low",
                validation_required=False
            ))
        
        # 7. 分散度建议
        if result.correlation_benchmark > 0.8:
            suggestion_id += 1
            suggestions.append(OptimizationSuggestion(
                suggestion_id=f"OPT_{suggestion_id:03d}",
                category="risk",
                priority="medium",
                description="与市场相关性过高，缺乏 Alpha",
                current_value=f"与市场相关性：{result.correlation_benchmark:.2f}",
                suggested_value="添加市场中性对冲、开发独立信号",
                expected_improvement="降低相关性至 0.5 以下，提升 Alpha",
                implementation_effort="high",
                validation_required=True
            ))
        
        return suggestions
    
    def _evaluate_performance(self, result: BacktestResult) -> PerformanceRating:
        """评估绩效评级"""
        # 检查是否达到优秀标准
        excellent = self.performance_thresholds["excellent"]
        if (result.sharpe_ratio >= excellent["sharpe_ratio"] and
            result.max_drawdown <= excellent["max_drawdown"] and
            result.annual_return >= excellent["annual_return"]):
            return PerformanceRating.EXCELLENT
        
        # 检查是否达到良好标准
        good = self.performance_thresholds["good"]
        if (result.sharpe_ratio >= good["sharpe_ratio"] and
            result.max_drawdown <= good["max_drawdown"] and
            result.annual_return >= good["annual_return"]):
            return PerformanceRating.GOOD
        
        # 检查是否达到可接受标准
        acceptable = self.performance_thresholds["acceptable"]
        if (result.sharpe_ratio >= acceptable["sharpe_ratio"] and
            result.max_drawdown <= acceptable["max_drawdown"] and
            result.annual_return >= acceptable["annual_return"]):
            return PerformanceRating.ACCEPTABLE
        
        # 检查是否不可接受
        if result.max_drawdown > 0.30 or result.sharpe_ratio < 0.5:
            return PerformanceRating.UNACCEPTABLE
        
        return PerformanceRating.POOR
    
    def _log_backtest_completion(
        self,
        request: BacktestRequest,
        result: BacktestResult,
        rating: PerformanceRating
    ):
        """记录回测完成日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "strategy_id": request.strategy_id,
            "request_id": request.request_id,
            "rating": rating.value,
            "key_metrics": {
                "sharpe_ratio": result.sharpe_ratio,
                "annual_return": result.annual_return,
                "max_drawdown": result.max_drawdown,
                "total_trades": result.total_trades
            }
        }
        
        # 这里可以写入日志文件或数据库
        print(f"[Backtest Complete] {request.strategy_name}: {rating.value}")
    
    def get_backtest_history(
        self,
        strategy_id: str,
        limit: int = 10
    ) -> List[BacktestResult]:
        """获取策略回测历史"""
        history = [
            result for result in self.completed_backtests.values()
            if result.strategy_id == strategy_id
        ]
        
        # 按时间排序
        history.sort(key=lambda x: x.end_time, reverse=True)
        
        return history[:limit]
    
    def compare_backtests(
        self,
        request_ids: List[str]
    ) -> Dict[str, Any]:
        """比较多个回测结果"""
        results = [
            self.completed_backtests[rid]
            for rid in request_ids
            if rid in self.completed_backtests
        ]
        
        if not results:
            return {"error": "No valid backtests found"}
        
        comparison = {
            "backtests": [],
            "best_by_metric": {},
            "summary": {}
        }
        
        for result in results:
            comparison["backtests"].append({
                "request_id": result.request_id,
                "sharpe_ratio": result.sharpe_ratio,
                "annual_return": result.annual_return,
                "max_drawdown": result.max_drawdown,
                "win_rate": result.win_rate,
                "total_trades": result.total_trades
            })
        
        # 找出各指标最优
        if results:
            comparison["best_by_metric"] = {
                "sharpe_ratio": max(results, key=lambda x: x.sharpe_ratio).request_id,
                "annual_return": max(results, key=lambda x: x.annual_return).request_id,
                "max_drawdown": min(results, key=lambda x: x.max_drawdown).request_id,
                "win_rate": max(results, key=lambda x: x.win_rate).request_id
            }
        
        # 汇总统计
        comparison["summary"] = {
            "avg_sharpe": sum(r.sharpe_ratio for r in results) / len(results),
            "avg_return": sum(r.annual_return for r in results) / len(results),
            "avg_drawdown": sum(r.max_drawdown for r in results) / len(results),
            "total_backtests": len(results)
        }
        
        return comparison
    
    def generate_backtest_report(
        self,
        result: BacktestResult,
        suggestions: List[OptimizationSuggestion]
    ) -> str:
        """生成回测报告"""
        # 确定绩效评级
        rating = self._evaluate_performance(result)
        
        report = f"""# 策略回测报告

## 基本信息
- **策略名称**: (需补充)
- **策略 ID**: {result.strategy_id}
- **回测 ID**: {result.request_id}
- **回测时间**: {result.start_time} 至 {result.end_time}
- **运行时长**: {result.duration_seconds:.2f} 秒
- **状态**: {result.status.value}

## 绩效评级
### **{rating.value.upper()}**

## 核心绩效指标

| 指标 | 数值 | 评级 |
|------|------|------|
| 总收益率 | {result.total_return:.2%} | - |
| 年化收益率 | {result.annual_return:.2%} | {'✅' if result.annual_return > 0.1 else '⚠️'} |
| 基准收益率 | {result.benchmark_return:.2%} | - |
| Alpha | {result.alpha:.4f} | {'✅' if result.alpha > 0.05 else '⚠️'} |
| Beta | {result.beta:.2f} | - |
| 夏普比率 | {result.sharpe_ratio:.2f} | {'✅' if result.sharpe_ratio > 1.5 else '⚠️'} |
| 索提诺比率 | {result.sortino_ratio:.2f} | - |
| 最大回撤 | {result.max_drawdown:.2%} | {'✅' if result.max_drawdown < 0.15 else '⚠️'} |
| 回撤持续期 | {result.max_drawdown_duration_days} 天 | - |

## 交易统计

| 指标 | 数值 |
|------|------|
| 总交易次数 | {result.total_trades} |
| 盈利交易 | {result.winning_trades} |
| 亏损交易 | {result.losing_trades} |
| 胜率 | {result.win_rate:.2%} |
| 盈亏比 | {result.profit_factor:.2f} |
| 平均盈利 | {result.avg_win:.2%} |
| 平均亏损 | {result.avg_loss:.2%} |
| 平均持有期 | {result.avg_holding_period_days} 天 |

## 风险分析

| 指标 | 数值 |
|------|------|
| 波动率 (年化) | {result.volatility:.2%} |
| VaR (95%) | {result.var_95:.2%} |
| CVaR (95%) | {result.cvar_95:.2%} |
| 与基准相关性 | {result.correlation_benchmark:.2f} |

## 交易成本

| 项目 | 数值 |
|------|------|
| 总佣金 | ${result.total_commission:.2f} |
| 总滑点 | ${result.total_slippage:.2f} |
| 年换手率 | {result.turnover_rate:.2f} |

## 优化建议

{chr(10).join([self._format_suggestion(s) for s in suggestions]) if suggestions else '暂无优化建议'}

## 结论与建议

### 策略表现总结
{self._generate_summary(result, rating)}

### 下一步行动
{self._generate_next_steps(result, rating, suggestions)}

---
*报告由 BacktestCoordinator 自动生成*
"""
        return report
    
    def _format_suggestion(self, suggestion: OptimizationSuggestion) -> str:
        """格式化优化建议"""
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = priority_icon.get(suggestion.priority, "⚪")
        
        return f"""### {icon} {suggestion.suggestion_id} - {suggestion.description}
- **类别**: {suggestion.category}
- **优先级**: {suggestion.priority.upper()}
- **当前状态**: {suggestion.current_value}
- **建议方案**: {suggestion.suggested_value}
- **预期改善**: {suggestion.expected_improvement}
- **实施难度**: {suggestion.implementation_effort}
- **需要验证**: {'是' if suggestion.validation_required else '否'}
"""
    
    def _generate_summary(
        self,
        result: BacktestResult,
        rating: PerformanceRating
    ) -> str:
        """生成表现总结"""
        if rating == PerformanceRating.EXCELLENT:
            return (
                "策略表现优秀，各项指标均达到或超过预期标准。"
                "夏普比率、收益率和回撤控制均表现良好，建议进入模拟交易阶段。"
            )
        elif rating == PerformanceRating.GOOD:
            return (
                "策略表现良好，核心指标达到可接受标准。"
                "建议针对薄弱环节进行优化后，再进行模拟交易验证。"
            )
        elif rating == PerformanceRating.ACCEPTABLE:
            return (
                "策略表现可接受，但存在明显改进空间。"
                "建议认真考虑优化建议，进行参数调优或策略调整后重新回测。"
            )
        elif rating == PerformanceRating.POOR:
            return (
                "策略表现较差，关键指标未达标准。"
                "建议深入分析问题原因，可能需要重新设计策略逻辑。"
            )
        else:
            return (
                "策略表现不可接受，存在严重问题。"
                "建议暂停该策略开发，重新评估策略可行性或考虑放弃。"
            )
    
    def _generate_next_steps(
        self,
        result: BacktestResult,
        rating: PerformanceRating,
        suggestions: List[OptimizationSuggestion]
    ) -> str:
        """生成下一步行动建议"""
        steps = []
        
        if rating in [PerformanceRating.EXCELLENT, PerformanceRating.GOOD]:
            steps.append("1. [ ] 安排策略评审会议")
            steps.append("2. [ ] 准备模拟交易环境")
            steps.append("3. [ ] 制定实盘上线计划")
        elif rating == PerformanceRating.ACCEPTABLE:
            steps.append("1. [ ] 优先实施高优先级优化建议")
            steps.append("2. [ ] 重新回测验证优化效果")
            steps.append("3. [ ] 如改善明显，进入模拟交易")
        else:
            steps.append("1. [ ] 组织策略问题诊断会议")
            steps.append("2. [ ] 评估是否需要重新设计策略")
            steps.append("3. [ ] 或考虑终止该策略开发")
        
        if suggestions:
            high_priority = [s for s in suggestions if s.priority == "high"]
            if high_priority:
                steps.append(f"4. [ ] 实施 {len(high_priority)} 项高优先级优化")
        
        return "\n".join(steps)


# 使用示例
if __name__ == "__main__":
    # 示例回测请求
    request = BacktestRequest(
        request_id="BT_20260301_001",
        strategy_id="STRAT_20260301_ABC123",
        strategy_name="双均线趋势策略",
        start_date="2020-01-01",
        end_date="2025-12-31",
        initial_capital=100000,
        universe=["AAPL", "GOOGL", "MSFT", "AMZN", "META"],
        frequency="daily",
        parameters={"short_window": 10, "long_window": 50},
        benchmark="SPY"
    )
    
    # 示例回测结果数据 (模拟回测引擎返回)
    result_data = {
        "success": True,
        "start_time": "2026-03-01 10:00:00",
        "end_time": "2026-03-01 10:05:30",
        "duration_seconds": 330,
        "metrics": {
            "total_return": 0.45,
            "annual_return": 0.15,
            "benchmark_return": 0.12,
            "alpha": 0.03,
            "beta": 1.1,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.3,
            "max_drawdown": 0.12,
            "max_drawdown_duration": 45
        },
        "risk": {
            "volatility": 0.18,
            "var_95": 0.025,
            "cvar_95": 0.035,
            "correlation_benchmark": 0.75
        },
        "trades": {
            "total_trades": 156,
            "winning_trades": 89,
            "losing_trades": 67,
            "win_rate": 0.57,
            "profit_factor": 1.65,
            "avg_win": 0.035,
            "avg_loss": 0.021,
            "avg_holding_period": 12
        },
        "costs": {
            "commission": 234.50,
            "slippage": 89.20,
            "turnover_rate": 1.8
        }
    }
    
    # 协调回测
    coordinator = BacktestCoordinator()
    result = coordinator.process_backtest(request, result_data)
    
    # 获取优化建议
    suggestions = coordinator.optimization_history.get(request.request_id, [])
    
    # 生成报告
    report = coordinator.generate_backtest_report(result, suggestions)
    print(report)
    
    # 保存报告
    with open(f"backtest_{result.request_id}.md", "w", encoding="utf-8") as f:
        f.write(report)
