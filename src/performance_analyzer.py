"""
绩效分析器 - Q 脑量化交易系统
==============================
增强的绩效分析模块，支持多策略对比、归因分析和报告生成

功能：
- 全面的绩效指标计算
- 多策略对比分析
- 归因分析
- 可视化报告生成
- 风险指标深度分析

作者：Backer-Agent (Q 脑回测架构师)
创建：2026-03-01
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from scipy import stats
import json
from pathlib import Path

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest.performance import PerformanceAnalyzer, PerformanceMetrics, Trade


@dataclass
class StrategyComparison:
    """策略对比结果"""
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade: float
    calmar_ratio: float
    omega_ratio: float
    tail_ratio: float


@dataclass
class AttributionAnalysis:
    """归因分析结果"""
    timing_contribution: float  # 择时贡献
    selection_contribution: float  # 选股贡献
    interaction_contribution: float  # 交互贡献
    sector_contribution: Dict[str, float]  # 行业贡献
    factor_contribution: Dict[str, float]  # 因子贡献


class EnhancedPerformanceAnalyzer(PerformanceAnalyzer):
    """增强的绩效分析器"""
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        trading_days_per_year: int = 252,
        benchmark_returns: Optional[pd.Series] = None
    ):
        """
        初始化增强绩效分析器
        
        Args:
            risk_free_rate: 无风险利率（年化）
            trading_days_per_year: 年交易日数
            benchmark_returns: 基准收益率序列（用于计算 Alpha/Beta）
        """
        super().__init__(risk_free_rate, trading_days_per_year)
        self.benchmark_returns = benchmark_returns
    
    def analyze_equity_curve(
        self,
        equity_curve: List[float],
        dates: List[datetime] = None,
        initial_capital: float = 100000.0
    ) -> PerformanceMetrics:
        """
        分析权益曲线
        
        Args:
            equity_curve: 权益曲线
            dates: 日期序列
            initial_capital: 初始资金
        
        Returns:
            PerformanceMetrics: 绩效指标
        """
        if not equity_curve or len(equity_curve) < 2:
            return PerformanceMetrics()
        
        equity = np.array(equity_curve)
        returns = np.diff(equity) / equity[:-1]
        
        # 基础指标
        total_return = (equity[-1] - equity[0]) / equity[0]
        
        # 年化收益率
        if dates and len(dates) >= 2:
            days = (dates[-1] - dates[0]).days
            years = days / 365.25
            annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        else:
            annual_return = total_return * (self.trading_days_per_year / len(returns))
        
        # 波动率
        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(self.trading_days_per_year)
        
        # 夏普比率
        if annual_vol > 0:
            sharpe = (annual_return - self.risk_free_rate) / annual_vol
        else:
            sharpe = 0
        
        # 索提诺比率（只考虑下行波动）
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_vol = np.std(downside_returns) * np.sqrt(self.trading_days_per_year)
            sortino = (annual_return - self.risk_free_rate) / downside_vol if downside_vol > 0 else 0
        else:
            sortino = 0
        
        # 最大回撤
        peak = equity[0]
        max_dd = 0
        max_dd_duration = 0
        current_dd_duration = 0
        
        for i, val in enumerate(equity):
            if val > peak:
                peak = val
                current_dd_duration = 0
            else:
                current_dd_duration += 1
                dd = (peak - val) / peak
                if dd > max_dd:
                    max_dd = dd
                    max_dd_duration = current_dd_duration
        
        # 卡尔玛比率
        calmar = annual_return / max_dd if max_dd > 0 else 0
        
        # VaR 和 CVaR
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        cvar_95 = np.mean(returns[returns <= var_95]) if len(returns[returns <= var_95]) > 0 else var_95
        
        # 基准相关指标
        beta = 0
        alpha = 0
        correlation = 0
        
        if self.benchmark_returns is not None and len(self.benchmark_returns) == len(returns):
            bench = np.array(self.benchmark_returns)
            if len(bench) > 1 and np.std(bench) > 0:
                covariance = np.cov(returns, bench)[0, 1]
                beta = covariance / np.var(bench)
                correlation = np.corrcoef(returns, bench)[0, 1]
                alpha = annual_return - (self.risk_free_rate + beta * (np.mean(bench) * self.trading_days_per_year - self.risk_free_rate))
        
        metrics = PerformanceMetrics(
            total_return=total_return * 100,  # 转换为百分比
            annual_return=annual_return * 100,
            max_drawdown=max_dd * 100,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            volatility=annual_vol * 100,
            var_95=var_95 * 100,
            var_99=var_99 * 100,
            cvar_95=cvar_95 * 100,
            beta=beta,
            alpha=alpha * 100,
            correlation=correlation,
            trading_days=len(returns),
            start_date=dates[0] if dates else None,
            end_date=dates[-1] if dates else None,
            initial_capital=initial_capital,
            final_capital=equity[-1]
        )
        
        return metrics
    
    def analyze_trades(
        self,
        trades: List[Trade],
        metrics: PerformanceMetrics = None
    ) -> PerformanceMetrics:
        """
        分析交易记录
        
        Args:
            trades: 交易记录列表
            metrics: 已有的绩效指标（可选）
        
        Returns:
            PerformanceMetrics: 更新后的绩效指标
        """
        if not trades:
            return metrics if metrics else PerformanceMetrics()
        
        closed_trades = [t for t in trades if not t.is_open]
        
        if not closed_trades:
            return metrics if metrics else PerformanceMetrics()
        
        # 盈亏统计
        pnls = [t.pnl for t in closed_trades]
        pnl_pcts = [t.pnl_pct for t in closed_trades]
        
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]
        
        total_trades = len(closed_trades)
        win_count = len(winning_trades)
        lose_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # 平均盈亏
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        avg_trade = np.mean(pnls)
        
        # 盈亏比
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # 最大盈亏
        max_win = max(pnls) if pnls else 0
        max_loss = min(pnls) if pnls else 0
        
        if metrics is None:
            metrics = PerformanceMetrics()
        
        metrics.total_trades = total_trades
        metrics.winning_trades = win_count
        metrics.losing_trades = lose_count
        metrics.win_rate = win_rate * 100
        metrics.profit_factor = profit_factor
        metrics.avg_win = avg_win
        metrics.avg_loss = avg_loss
        metrics.avg_trade = avg_trade
        metrics.max_win = max_win
        metrics.max_loss = max_loss
        
        return metrics
    
    def calculate_omega_ratio(
        self,
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> float:
        """
        计算 Omega 比率
        
        Args:
            returns: 收益率序列
            threshold: 目标收益率
        
        Returns:
            Omega 比率
        """
        if len(returns) == 0:
            return 0
        
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns <= threshold]
        
        if len(losses) == 0 or np.sum(losses) == 0:
            return float('inf')
        
        return np.sum(gains) / np.sum(losses)
    
    def calculate_tail_ratio(
        self,
        returns: np.ndarray,
        percentile: float = 95
    ) -> float:
        """
        计算尾部比率（右尾/左尾）
        
        Args:
            returns: 收益率序列
            percentile: 分位数
        
        Returns:
            尾部比率
        """
        if len(returns) < 20:
            return 0
        
        right_tail = np.percentile(returns, percentile)
        left_tail = np.percentile(returns, 100 - percentile)
        
        if left_tail == 0:
            return 0
        
        return abs(right_tail / left_tail)
    
    def compare_strategies(
        self,
        equity_curves: Dict[str, List[float]],
        dates: List[datetime] = None,
        initial_capital: float = 100000.0
    ) -> Dict[str, StrategyComparison]:
        """
        对比多个策略
        
        Args:
            equity_curves: {策略名：权益曲线}
            dates: 日期序列
            initial_capital: 初始资金
        
        Returns:
            {策略名：StrategyComparison}
        """
        results = {}
        
        for name, equity in equity_curves.items():
            metrics = self.analyze_equity_curve(equity, dates, initial_capital)
            
            # 计算额外指标
            returns = np.diff(equity) / equity[:-1]
            omega = self.calculate_omega_ratio(returns)
            tail = self.calculate_tail_ratio(returns)
            
            results[name] = StrategyComparison(
                strategy_name=name,
                total_return=metrics.total_return,
                annual_return=metrics.annual_return,
                sharpe_ratio=metrics.sharpe_ratio,
                sortino_ratio=metrics.sortino_ratio,
                max_drawdown=metrics.max_drawdown,
                volatility=metrics.volatility,
                win_rate=metrics.win_rate,
                profit_factor=metrics.profit_factor,
                total_trades=metrics.total_trades,
                avg_trade=metrics.avg_trade,
                calmar_ratio=metrics.calmar_ratio,
                omega_ratio=omega,
                tail_ratio=tail
            )
        
        return results
    
    def generate_report(
        self,
        metrics: PerformanceMetrics,
        trades: List[Trade] = None,
        equity_curve: List[float] = None,
        title: str = "绩效分析报告",
        output_path: str = None
    ) -> str:
        """
        生成绩效分析报告
        
        Args:
            metrics: 绩效指标
            trades: 交易记录
            equity_curve: 权益曲线
            title: 报告标题
            output_path: 输出路径（可选）
        
        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"  {title}")
        lines.append("=" * 70)
        lines.append("")
        
        # 基本信息
        lines.append("📊 基本信息")
        lines.append("-" * 70)
        lines.append(f"  初始资金：    ¥{metrics.initial_capital:,.2f}")
        lines.append(f"  最终资金：    ¥{metrics.final_capital:,.2f}")
        lines.append(f"  交易天数：    {metrics.trading_days}")
        if metrics.start_date:
            lines.append(f"  开始日期：    {metrics.start_date.strftime('%Y-%m-%d')}")
        if metrics.end_date:
            lines.append(f"  结束日期：    {metrics.end_date.strftime('%Y-%m-%d')}")
        lines.append("")
        
        # 收益指标
        lines.append("📈 收益指标")
        lines.append("-" * 70)
        lines.append(f"  总收益率：    {metrics.total_return:+.2f}%")
        lines.append(f"  年化收益：    {metrics.annual_return:+.2f}%")
        lines.append(f"  夏普比率：    {metrics.sharpe_ratio:.2f}")
        lines.append(f"  索提诺比率：  {metrics.sortino_ratio:.2f}")
        lines.append(f"  卡尔玛比率：  {metrics.calmar_ratio:.2f}")
        lines.append("")
        
        # 风险指标
        lines.append("⚠️  风险指标")
        lines.append("-" * 70)
        lines.append(f"  最大回撤：    {metrics.max_drawdown:.2f}%")
        lines.append(f"  回撤持续：    {metrics.max_drawdown_duration} 天")
        lines.append(f"  年化波动：    {metrics.volatility:.2f}%")
        lines.append(f"  VaR(95%):     {metrics.var_95:.2f}%")
        lines.append(f"  VaR(99%):     {metrics.var_99:.2f}%")
        lines.append(f"  CVaR(95%):    {metrics.cvar_95:.2f}%")
        lines.append("")
        
        # 基准对比
        if abs(metrics.beta) > 0.01 or abs(metrics.alpha) > 0.01:
            lines.append("📊 基准对比")
            lines.append("-" * 70)
            lines.append(f"  Beta 系数：    {metrics.beta:.2f}")
            lines.append(f"  Alpha 收益：   {metrics.alpha:+.2f}%")
            lines.append(f"  相关系数：    {metrics.correlation:.2f}")
            lines.append("")
        
        # 交易统计
        if metrics.total_trades > 0:
            lines.append("💼 交易统计")
            lines.append("-" * 70)
            lines.append(f"  总交易次数：  {metrics.total_trades}")
            lines.append(f"  盈利次数：    {metrics.winning_trades}")
            lines.append(f"  亏损次数：    {metrics.losing_trades}")
            lines.append(f"  胜率：        {metrics.win_rate:.1f}%")
            lines.append(f"  盈亏比：      {metrics.profit_factor:.2f}")
            lines.append(f"  平均盈利：    ¥{metrics.avg_win:,.2f}")
            lines.append(f"  平均亏损：    ¥{metrics.avg_loss:,.2f}")
            lines.append(f"  单笔平均：    ¥{metrics.avg_trade:,.2f}")
            lines.append(f"  最大盈利：    ¥{metrics.max_win:,.2f}")
            lines.append(f"  最大亏损：    ¥{metrics.max_loss:,.2f}")
            lines.append("")
        
        # 评价
        lines.append("📝 综合评价")
        lines.append("-" * 70)
        
        # 夏普评价
        if metrics.sharpe_ratio > 2:
            sharpe_comment = "优秀"
        elif metrics.sharpe_ratio > 1:
            sharpe_comment = "良好"
        elif metrics.sharpe_ratio > 0:
            sharpe_comment = "一般"
        else:
            sharpe_comment = "较差"
        
        # 回撤评价
        if metrics.max_drawdown < 10:
            dd_comment = "优秀"
        elif metrics.max_drawdown < 20:
            dd_comment = "良好"
        elif metrics.max_drawdown < 30:
            dd_comment = "一般"
        else:
            dd_comment = "较高"
        
        # 胜率评价
        if metrics.win_rate > 60:
            wr_comment = "优秀"
        elif metrics.win_rate > 50:
            wr_comment = "良好"
        elif metrics.win_rate > 40:
            wr_comment = "一般"
        else:
            wr_comment = "较低"
        
        lines.append(f"  风险收益比：  {sharpe_comment} (Sharpe: {metrics.sharpe_ratio:.2f})")
        lines.append(f"  回撤控制：    {dd_comment} (MDD: {metrics.max_drawdown:.1f}%)")
        lines.append(f"  交易胜率：    {wr_comment} (Win Rate: {metrics.win_rate:.1f}%)")
        
        # 总体评分
        score = 0
        if metrics.sharpe_ratio > 1:
            score += 1
        if metrics.sharpe_ratio > 2:
            score += 1
        if metrics.max_drawdown < 20:
            score += 1
        if metrics.win_rate > 50:
            score += 1
        if metrics.profit_factor > 1.5:
            score += 1
        
        lines.append(f"  综合评分：    ⭐" * score + "☆" * (5 - score) + f" ({score}/5)")
        lines.append("")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        # 保存到文件
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📁 报告已保存：{output_file}")
        
        return report


class BatchPerformanceAnalyzer:
    """批量绩效分析器"""
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        trading_days_per_year: int = 252
    ):
        self.analyzer = EnhancedPerformanceAnalyzer(risk_free_rate, trading_days_per_year)
        self.results = []
    
    def add_result(
        self,
        symbol: str,
        name: str,
        equity_curve: List[float],
        dates: List[datetime] = None,
        trades: List[Trade] = None,
        initial_capital: float = 100000.0
    ):
        """添加回测结果"""
        metrics = self.analyzer.analyze_equity_curve(equity_curve, dates, initial_capital)
        
        if trades:
            metrics = self.analyzer.analyze_trades(trades, metrics)
        
        self.results.append({
            'symbol': symbol,
            'name': name,
            'metrics': metrics,
            'trades': trades,
            'equity_curve': equity_curve,
            'dates': dates
        })
    
    def generate_summary_report(
        self,
        output_path: str = None,
        top_n: int = 10
    ) -> str:
        """生成批量分析汇总报告"""
        if not self.results:
            return "无分析结果"
        
        lines = []
        lines.append("=" * 70)
        lines.append("  A 股 ETF 批量回测绩效分析报告")
        lines.append(f"  生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        
        # 总体统计
        lines.append("📊 总体统计")
        lines.append("-" * 70)
        lines.append(f"  标的数量：    {len(self.results)}")
        
        successful = [r for r in self.results if r['metrics'].total_trades > 0]
        lines.append(f"  有效策略：    {len(successful)}")
        
        if successful:
            avg_return = np.mean([r['metrics'].total_return for r in successful])
            avg_sharpe = np.mean([r['metrics'].sharpe_ratio for r in successful])
            avg_dd = np.mean([r['metrics'].max_drawdown for r in successful])
            
            lines.append(f"  平均收益：    {avg_return:+.2f}%")
            lines.append(f"  平均夏普：    {avg_sharpe:.2f}")
            lines.append(f"  平均回撤：    {avg_dd:.2f}%")
        
        lines.append("")
        
        # TOP  performers
        lines.append(f"🏆 收益 TOP {top_n}")
        lines.append("-" * 70)
        
        sorted_by_return = sorted(
            self.results,
            key=lambda x: x['metrics'].total_return,
            reverse=True
        )[:top_n]
        
        lines.append(f"{'排名':<4} {'代码':<8} {'名称':<15} {'收益':>10} {'夏普':>8} {'回撤':>10} {'交易':>6}")
        lines.append("-" * 70)
        
        for i, r in enumerate(sorted_by_return, 1):
            m = r['metrics']
            lines.append(
                f"{i:<4} {r['symbol']:<8} {r['name']:<15} "
                f"{m.total_return:>9.2f}% {m.sharpe_ratio:>8.2f} "
                f"{m.max_drawdown:>9.2f}% {m.total_trades:>6}"
            )
        
        lines.append("")
        
        # 夏普比率 TOP
        lines.append(f"📈 夏普比率 TOP {top_n}")
        lines.append("-" * 70)
        
        sorted_by_sharpe = sorted(
            self.results,
            key=lambda x: x['metrics'].sharpe_ratio,
            reverse=True
        )[:top_n]
        
        lines.append(f"{'排名':<4} {'代码':<8} {'名称':<15} {'夏普':>8} {'收益':>10} {'回撤':>10}")
        lines.append("-" * 70)
        
        for i, r in enumerate(sorted_by_sharpe, 1):
            m = r['metrics']
            lines.append(
                f"{i:<4} {r['symbol']:<8} {r['name']:<15} "
                f"{m.sharpe_ratio:>8.2f} {m.total_return:>9.2f}% {m.max_drawdown:>9.2f}%"
            )
        
        lines.append("")
        
        # 风险控制 TOP
        lines.append(f"🛡️  回撤控制 TOP {top_n}")
        lines.append("-" * 70)
        
        sorted_by_dd = sorted(
            self.results,
            key=lambda x: x['metrics'].max_drawdown
        )[:top_n]
        
        lines.append(f"{'排名':<4} {'代码':<8} {'名称':<15} {'回撤':>10} {'收益':>10} {'夏普':>8}")
        lines.append("-" * 70)
        
        for i, r in enumerate(sorted_by_dd, 1):
            m = r['metrics']
            lines.append(
                f"{i:<4} {r['symbol']:<8} {r['name']:<15} "
                f"{m.max_drawdown:>9.2f}% {m.total_return:>9.2f}% {m.sharpe_ratio:>8.2f}"
            )
        
        lines.append("")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        # 保存
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📁 汇总报告已保存：{output_file}")
        
        return report
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        data = []
        
        for r in self.results:
            m = r['metrics']
            data.append({
                'symbol': r['symbol'],
                'name': r['name'],
                'total_return': m.total_return,
                'annual_return': m.annual_return,
                'sharpe_ratio': m.sharpe_ratio,
                'sortino_ratio': m.sortino_ratio,
                'calmar_ratio': m.calmar_ratio,
                'max_drawdown': m.max_drawdown,
                'volatility': m.volatility,
                'var_95': m.var_95,
                'beta': m.beta,
                'alpha': m.alpha,
                'total_trades': m.total_trades,
                'win_rate': m.win_rate,
                'profit_factor': m.profit_factor,
                'avg_trade': m.avg_trade
            })
        
        return pd.DataFrame(data)


if __name__ == "__main__":
    print("增强绩效分析器已加载")
    print(f"版本：2026-03-01")
    print(f"作者：Backer-Agent (Q 脑回测架构师)")
