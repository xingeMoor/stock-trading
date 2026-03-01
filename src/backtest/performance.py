"""
绩效分析模块
============
计算收益率指标、风险指标和归因分析。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    symbol: str
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    side: str  # "long" or "short"
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    impact_cost: float = 0.0
    
    def __post_init__(self):
        if self.exit_price is not None:
            if self.side == "long":
                self.pnl = (self.exit_price - self.entry_price) * self.quantity - self.total_cost
            else:
                self.pnl = (self.entry_price - self.exit_price) * self.quantity - self.total_cost
            
            if self.entry_price > 0:
                if self.side == "long":
                    self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price
                else:
                    self.pnl_pct = (self.entry_price - self.exit_price) / self.entry_price
    
    @property
    def total_cost(self) -> float:
        return self.commission + self.slippage + self.impact_cost
    
    @property
    def is_open(self) -> bool:
        return self.exit_price is None


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    # 收益率指标
    total_return: float = 0.0           # 总收益率
    annual_return: float = 0.0          # 年化收益率
    max_drawdown: float = 0.0           # 最大回撤
    max_drawdown_duration: int = 0      # 最大回撤持续时间 (天)
    sharpe_ratio: float = 0.0           # 夏普比率
    sortino_ratio: float = 0.0          # 索提诺比率
    calmar_ratio: float = 0.0           # 卡尔玛比率
    
    # 风险指标
    volatility: float = 0.0             # 年化波动率
    var_95: float = 0.0                 # 95% VaR
    var_99: float = 0.0                 # 99% VaR
    cvar_95: float = 0.0                # 95% 条件 VaR
    beta: float = 0.0                   # Beta 系数 (相对基准)
    alpha: float = 0.0                  # Alpha 收益
    correlation: float = 0.0            # 与基准的相关性
    
    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    
    # 其他
    trading_days: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: float = 0.0
    final_capital: float = 0.0


class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, risk_free_rate: float = 0.03, trading_days_per_year: int = 252):
        """
        Args:
            risk_free_rate: 无风险利率 (年化)
            trading_days_per_year: 年交易日数
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year
        
        self.equity_curve: List[float] = []
        self.timestamps: List[datetime] = []
        self.trades: List[Trade] = []
        self.daily_returns: np.ndarray = np.array([])
        self.benchmark_returns: np.ndarray = np.array([])
    
    def add_equity_point(self, timestamp: datetime, equity: float):
        """添加权益点"""
        self.timestamps.append(timestamp)
        self.equity_curve.append(equity)
    
    def add_trade(self, trade: Trade):
        """添加交易记录"""
        self.trades.append(trade)
    
    def set_benchmark_returns(self, returns: np.ndarray):
        """设置基准收益率"""
        self.benchmark_returns = returns
    
    def calculate_returns(self) -> np.ndarray:
        """计算日收益率序列"""
        if len(self.equity_curve) < 2:
            return np.array([])
        
        equity_array = np.array(self.equity_curve)
        self.daily_returns = np.diff(equity_array) / equity_array[:-1]
        return self.daily_returns
    
    def analyze(self, initial_capital: float) -> PerformanceMetrics:
        """执行完整绩效分析"""
        if len(self.equity_curve) < 2:
            logger.warning("数据不足，无法进行绩效分析")
            return PerformanceMetrics()
        
        # 计算收益率
        self.calculate_returns()
        
        metrics = PerformanceMetrics()
        metrics.initial_capital = initial_capital
        metrics.final_capital = self.equity_curve[-1]
        metrics.start_date = self.timestamps[0] if self.timestamps else None
        metrics.end_date = self.timestamps[-1] if self.timestamps else None
        metrics.trading_days = len(self.equity_curve)
        
        # === 收益率指标 ===
        self._calculate_return_metrics(metrics, initial_capital)
        
        # === 风险指标 ===
        self._calculate_risk_metrics(metrics)
        
        # === 交易统计 ===
        self._calculate_trade_stats(metrics)
        
        # === 基准相关指标 ===
        if len(self.benchmark_returns) > 0:
            self._calculate_benchmark_metrics(metrics)
        
        return metrics
    
    def _calculate_return_metrics(self, metrics: PerformanceMetrics, initial_capital: float):
        """计算收益率相关指标"""
        # 总收益率
        metrics.total_return = (self.equity_curve[-1] - initial_capital) / initial_capital
        
        # 年化收益率
        if len(self.timestamps) >= 2:
            days = (self.timestamps[-1] - self.timestamps[0]).days
            if days > 0:
                years = days / 365.0
                metrics.annual_return = (1 + metrics.total_return) ** (1 / years) - 1
        
        # 最大回撤
        metrics.max_drawdown, metrics.max_drawdown_duration = self._calculate_max_drawdown()
        
        # 夏普比率
        if len(self.daily_returns) > 0 and np.std(self.daily_returns) > 0:
            daily_rf = self.risk_free_rate / self.trading_days_per_year
            excess_returns = self.daily_returns - daily_rf
            metrics.sharpe_ratio = (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(self.trading_days_per_year)
        
        # 索提诺比率 (只考虑下行波动)
        if len(self.daily_returns) > 0:
            downside_returns = self.daily_returns[self.daily_returns < 0]
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                daily_rf = self.risk_free_rate / self.trading_days_per_year
                excess_returns = self.daily_returns - daily_rf
                metrics.sortino_ratio = (np.mean(excess_returns) / np.std(downside_returns)) * np.sqrt(self.trading_days_per_year)
        
        # 卡尔玛比率
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annual_return / metrics.max_drawdown
    
    def _calculate_max_drawdown(self) -> Tuple[float, int]:
        """计算最大回撤及其持续时间"""
        equity_array = np.array(self.equity_curve)
        
        # 计算累计最大值
        running_max = np.maximum.accumulate(equity_array)
        
        # 计算回撤
        drawdown = (running_max - equity_array) / running_max
        
        # 最大回撤
        max_dd = np.max(drawdown)
        
        # 最大回撤持续时间
        max_dd_duration = 0
        in_drawdown = False
        drawdown_start = 0
        
        for i, dd in enumerate(drawdown):
            if dd > 0 and not in_drawdown:
                in_drawdown = True
                drawdown_start = i
            elif dd == 0 and in_drawdown:
                in_drawdown = False
                duration = i - drawdown_start
                max_dd_duration = max(max_dd_duration, duration)
        
        # 如果最后在回撤中
        if in_drawdown:
            duration = len(drawdown) - drawdown_start
            max_dd_duration = max(max_dd_duration, duration)
        
        return max_dd, max_dd_duration
    
    def _calculate_risk_metrics(self, metrics: PerformanceMetrics):
        """计算风险指标"""
        if len(self.daily_returns) == 0:
            return
        
        # 年化波动率
        metrics.volatility = np.std(self.daily_returns) * np.sqrt(self.trading_days_per_year)
        
        # VaR (历史模拟法)
        metrics.var_95 = -np.percentile(self.daily_returns, 5)
        metrics.var_99 = -np.percentile(self.daily_returns, 1)
        
        # 条件 VaR (CVaR / Expected Shortfall)
        var_95_threshold = np.percentile(self.daily_returns, 5)
        tail_returns = self.daily_returns[self.daily_returns <= var_95_threshold]
        if len(tail_returns) > 0:
            metrics.cvar_95 = -np.mean(tail_returns)
    
    def _calculate_trade_stats(self, metrics: PerformanceMetrics):
        """计算交易统计"""
        if not self.trades:
            return
        
        closed_trades = [t for t in self.trades if not t.is_open]
        if not closed_trades:
            return
        
        metrics.total_trades = len(closed_trades)
        
        pnls = np.array([t.pnl for t in closed_trades])
        
        # 盈亏统计
        winning = pnls[pnls > 0]
        losing = pnls[pnls < 0]
        
        metrics.winning_trades = len(winning)
        metrics.losing_trades = len(losing)
        metrics.win_rate = len(winning) / len(closed_trades) if closed_trades else 0
        
        # 平均盈亏
        if len(winning) > 0:
            metrics.avg_win = np.mean(winning)
        if len(losing) > 0:
            metrics.avg_loss = np.abs(np.mean(losing))
        
        # 盈亏比
        if metrics.avg_loss > 0:
            metrics.profit_factor = np.sum(winning) / np.sum(np.abs(losing)) if len(losing) > 0 else float('inf')
        
        metrics.avg_trade = np.mean(pnls)
        metrics.max_win = np.max(winning) if len(winning) > 0 else 0
        metrics.max_loss = np.min(losing) if len(losing) > 0 else 0
    
    def _calculate_benchmark_metrics(self, metrics: PerformanceMetrics):
        """计算基准相关指标"""
        if len(self.daily_returns) == 0 or len(self.benchmark_returns) == 0:
            return
        
        # 对齐长度
        min_len = min(len(self.daily_returns), len(self.benchmark_returns))
        strategy_returns = self.daily_returns[:min_len]
        benchmark_returns = self.benchmark_returns[:min_len]
        
        # Beta 和 Alpha
        if np.var(benchmark_returns) > 0:
            covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
            metrics.beta = covariance / np.var(benchmark_returns)
            
            # Alpha (年化)
            strategy_mean = np.mean(strategy_returns) * self.trading_days_per_year
            benchmark_mean = np.mean(benchmark_returns) * self.trading_days_per_year
            metrics.alpha = strategy_mean - (self.risk_free_rate + metrics.beta * (benchmark_mean - self.risk_free_rate))
        
        # 相关系数
        if np.std(benchmark_returns) > 0 and np.std(strategy_returns) > 0:
            metrics.correlation = np.corrcoef(strategy_returns, benchmark_returns)[0, 1]


class AttributionAnalyzer:
    """归因分析器"""
    
    def __init__(self):
        self.trades: List[Trade] = []
        self.sector_exposures: Dict[str, float] = {}
    
    def add_trade(self, trade: Trade):
        """添加交易"""
        self.trades.append(trade)
    
    def set_sector_exposure(self, sector: str, exposure: float):
        """设置行业暴露"""
        self.sector_exposures[sector] = exposure
    
    def analyze_by_symbol(self) -> Dict[str, Dict[str, float]]:
        """按标的归因"""
        result = {}
        
        for trade in self.trades:
            if trade.symbol not in result:
                result[trade.symbol] = {
                    "total_pnl": 0.0,
                    "trade_count": 0,
                    "win_rate": 0.0,
                    "avg_pnl": 0.0
                }
            
            if not trade.is_open:
                result[trade.symbol]["total_pnl"] += trade.pnl
                result[trade.symbol]["trade_count"] += 1
        
        # 计算统计
        for symbol, data in result.items():
            if data["trade_count"] > 0:
                data["avg_pnl"] = data["total_pnl"] / data["trade_count"]
                winning = sum(1 for t in self.trades if t.symbol == symbol and not t.is_open and t.pnl > 0)
                data["win_rate"] = winning / data["trade_count"]
        
        return result
    
    def analyze_by_time(self, freq: str = "M") -> Dict[str, float]:
        """按时间归因 (按周/月/年)"""
        result = {}
        
        for trade in self.trades:
            if trade.is_open or trade.exit_date is None:
                continue
            
            if freq == "M":
                key = trade.exit_date.strftime("%Y-%m")
            elif freq == "W":
                key = trade.exit_date.strftime("%Y-W%W")
            elif freq == "Y":
                key = trade.exit_date.strftime("%Y")
            else:
                key = trade.exit_date.strftime("%Y-%m-%d")
            
            if key not in result:
                result[key] = 0.0
            result[key] += trade.pnl
        
        return dict(sorted(result.items()))
    
    def analyze_by_side(self) -> Dict[str, Dict[str, float]]:
        """按多空方向归因"""
        result = {
            "long": {"total_pnl": 0.0, "count": 0, "win_rate": 0.0},
            "short": {"total_pnl": 0.0, "count": 0, "win_rate": 0.0}
        }
        
        for trade in self.trades:
            if trade.is_open:
                continue
            
            side = trade.side
            result[side]["total_pnl"] += trade.pnl
            result[side]["count"] += 1
            if trade.pnl > 0:
                result[side]["win_rate"] += 1
        
        # 计算胜率
        for side in ["long", "short"]:
            if result[side]["count"] > 0:
                result[side]["win_rate"] /= result[side]["count"]
        
        return result


def generate_performance_report(metrics: PerformanceMetrics, 
                               attribution: Optional[Dict] = None) -> str:
    """生成绩效报告"""
    report = []
    report.append("=" * 60)
    report.append("                    绩效分析报告")
    report.append("=" * 60)
    
    # 基本信息
    report.append("\n【基本信息】")
    if metrics.start_date:
        report.append(f"  开始日期：{metrics.start_date.strftime('%Y-%m-%d')}")
    if metrics.end_date:
        report.append(f"  结束日期：{metrics.end_date.strftime('%Y-%m-%d')}")
    report.append(f"  交易天数：{metrics.trading_days}")
    report.append(f"  初始资金：{metrics.initial_capital:,.2f}")
    report.append(f"  最终资金：{metrics.final_capital:,.2f}")
    
    # 收益率指标
    report.append("\n【收益率指标】")
    report.append(f"  总收益率：  {metrics.total_return:>10.2%}")
    report.append(f"  年化收益：  {metrics.annual_return:>10.2%}")
    report.append(f"  最大回撤：  {metrics.max_drawdown:>10.2%}")
    report.append(f"  夏普比率：  {metrics.sharpe_ratio:>10.2f}")
    report.append(f"  索提诺比率：{metrics.sortino_ratio:>10.2f}")
    report.append(f"  卡尔玛比率：{metrics.calmar_ratio:>10.2f}")
    
    # 风险指标
    report.append("\n【风险指标】")
    report.append(f"  年化波动率：{metrics.volatility:>10.2%}")
    report.append(f"  VaR(95%):   {metrics.var_95:>10.2%}")
    report.append(f"  VaR(99%):   {metrics.var_99:>10.2%}")
    report.append(f"  CVaR(95%):  {metrics.cvar_95:>10.2%}")
    if metrics.beta != 0:
        report.append(f"  Beta:       {metrics.beta:>10.2f}")
    if metrics.alpha != 0:
        report.append(f"  Alpha:      {metrics.alpha:>10.2%}")
    
    # 交易统计
    report.append("\n【交易统计】")
    report.append(f"  总交易数：  {metrics.total_trades}")
    report.append(f"  胜率：      {metrics.win_rate:>10.2%}")
    report.append(f"  盈亏比：    {metrics.profit_factor:>10.2f}")
    report.append(f"  平均盈利：  {metrics.avg_win:>10.2f}")
    report.append(f"  平均亏损：  {metrics.avg_loss:>10.2f}")
    report.append(f"  单笔平均：  {metrics.avg_trade:>10.2f}")
    report.append(f"  最大盈利：  {metrics.max_win:>10.2f}")
    report.append(f"  最大亏损：  {metrics.max_loss:>10.2f}")
    
    # 归因分析
    if attribution:
        report.append("\n【归因分析】")
        if "by_symbol" in attribution:
            report.append("  按标的:")
            for symbol, data in sorted(attribution["by_symbol"].items(), 
                                      key=lambda x: x[1]["total_pnl"], 
                                      reverse=True)[:10]:
                report.append(f"    {symbol}: {data['total_pnl']:>10.2f} ({data['trade_count']}笔)")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)
