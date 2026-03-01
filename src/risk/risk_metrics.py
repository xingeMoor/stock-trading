"""
风险指标模块 - Risk Metrics Calculator
负责计算各类风险指标

核心功能:
- VaR (Value at Risk) 计算
- 夏普比率监控
- Beta 暴露计算
- 行业/因子暴露分析
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math
from datetime import datetime, timedelta


class VaRMethod(Enum):
    """VaR 计算方法"""
    HISTORICAL = "historical"  # 历史法
    PARAMETRIC = "parametric"  # 参数法
    MONTE_CARLO = "monte_carlo"  # 蒙特卡洛


class FactorType(Enum):
    """因子类型"""
    MARKET = "market"  # 市场因子
    SIZE = "size"  # 规模因子
    VALUE = "value"  # 价值因子
    MOMENTUM = "momentum"  # 动量因子
    VOLATILITY = "volatility"  # 波动率因子
    SECTOR = "sector"  # 行业因子


@dataclass
class RiskMetricsConfig:
    """风险指标配置"""
    # VaR 配置
    var_confidence_level: float = 0.95  # 95% 置信度
    var_window_days: int = 252  # 计算窗口 (1 年交易日)
    var_method: VaRMethod = VaRMethod.HISTORICAL
    
    # 夏普比率配置
    risk_free_rate: float = 0.04  # 无风险利率 4%
    sharpe_window_days: int = 252  # 计算窗口
    
    # Beta 配置
    beta_benchmark: str = "SPY"  # 基准指数
    beta_window_days: int = 252  # 计算窗口
    
    # 风险限额
    max_var_pct: float = 0.05  # 最大 VaR 5%
    min_sharpe: float = 1.0  # 最小夏普比率
    max_beta: float = 1.5  # 最大 Beta
    max_sector_exposure: float = 0.4  # 最大行业暴露 40%


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    weight: float
    sector: str
    beta: float = 1.0
    market_value: float = 0.0


class RiskMetricsCalculator:
    """
    风险指标计算器
    
    计算 VaR、夏普比率、Beta、因子暴露等风险指标
    """
    
    def __init__(self, config: Optional[RiskMetricsConfig] = None):
        self.config = config or RiskMetricsConfig()
        self.returns_history: List[float] = []
        self.benchmark_returns: List[float] = []
        self.dates: List[datetime] = []
        self.positions: Dict[str, Position] = {}
        
    # ==================== 数据输入 ====================
    
    def add_return(
        self,
        portfolio_return: float,
        benchmark_return: float,
        date: datetime
    ):
        """添加收益率数据"""
        self.returns_history.append(portfolio_return)
        self.benchmark_returns.append(benchmark_return)
        self.dates.append(date)
        
        # 保持窗口大小
        if len(self.returns_history) > self.config.var_window_days:
            self.returns_history.pop(0)
            self.benchmark_returns.pop(0)
            self.dates.pop(0)
    
    def update_position(self, position: Position):
        """更新持仓信息"""
        self.positions[position.symbol] = position
    
    def remove_position(self, symbol: str):
        """移除持仓"""
        if symbol in self.positions:
            del self.positions[symbol]
    
    # ==================== VaR 计算 ====================
    
    def calculate_var(
        self,
        portfolio_value: float,
        method: Optional[VaRMethod] = None,
        confidence_level: Optional[float] = None
    ) -> Dict:
        """
        计算 VaR (Value at Risk)
        
        Args:
            portfolio_value: 组合价值
            method: VaR 计算方法
            confidence_level: 置信度
            
        Returns:
            VaR 计算结果
        """
        method = method or self.config.var_method
        confidence = confidence_level or self.config.var_confidence_level
        
        if len(self.returns_history) < 20:
            return {
                'var_1d': 0.0,
                'var_1d_pct': 0.0,
                'var_10d': 0.0,
                'var_10d_pct': 0.0,
                'method': method.value,
                'confidence': confidence,
                'warning': '数据不足'
            }
        
        if method == VaRMethod.HISTORICAL:
            var_result = self._calculate_historical_var(confidence)
        elif method == VaRMethod.PARAMETRIC:
            var_result = self._calculate_parametric_var(confidence)
        elif method == VaRMethod.MONTE_CARLO:
            var_result = self._calculate_monte_carlo_var(confidence)
        else:
            var_result = self._calculate_historical_var(confidence)
        
        # 转换为金额
        var_1d_value = portfolio_value * var_result['var_1d_pct']
        var_10d_value = portfolio_value * var_result['var_10d_pct']
        
        return {
            'var_1d': var_1d_value,
            'var_1d_pct': var_result['var_1d_pct'],
            'var_10d': var_10d_value,
            'var_10d_pct': var_result['var_10d_pct'],
            'method': method.value,
            'confidence': confidence,
            'num_observations': len(self.returns_history),
            'exceeds_limit': var_result['var_1d_pct'] > self.config.max_var_pct
        }
    
    def _calculate_historical_var(self, confidence: float) -> Dict:
        """历史法计算 VaR"""
        sorted_returns = sorted(self.returns_history)
        
        # 找到对应分位数
        index = int((1 - confidence) * len(sorted_returns))
        var_1d = -sorted_returns[index] if index < len(sorted_returns) else 0
        
        # 10 日 VaR (平方根法则)
        var_10d = var_1d * math.sqrt(10)
        
        return {
            'var_1d_pct': var_1d,
            'var_10d_pct': var_10d
        }
    
    def _calculate_parametric_var(self, confidence: float) -> Dict:
        """参数法计算 VaR (假设正态分布)"""
        # 计算均值和标准差
        mean_return = sum(self.returns_history) / len(self.returns_history)
        variance = sum((r - mean_return) ** 2 for r in self.returns_history) / len(self.returns_history)
        std_dev = math.sqrt(variance)
        
        # Z 分数 (95% = 1.645, 99% = 2.326)
        z_scores = {0.95: 1.645, 0.99: 2.326, 0.975: 1.96}
        z_score = z_scores.get(confidence, 1.645)
        
        # VaR = 均值 - Z * 标准差
        var_1d = -(mean_return - z_score * std_dev)
        var_1d = max(0, var_1d)  # VaR 不为负
        
        # 10 日 VaR
        var_10d = var_1d * math.sqrt(10)
        
        return {
            'var_1d_pct': var_1d,
            'var_10d_pct': var_10d,
            'mean_return': mean_return,
            'std_dev': std_dev
        }
    
    def _calculate_monte_carlo_var(self, confidence: float, simulations: int = 10000) -> Dict:
        """蒙特卡洛模拟计算 VaR"""
        import random
        
        # 计算参数
        mean_return = sum(self.returns_history) / len(self.returns_history)
        variance = sum((r - mean_return) ** 2 for r in self.returns_history) / len(self.returns_history)
        std_dev = math.sqrt(variance)
        
        # 模拟
        simulated_returns = []
        for _ in range(simulations):
            simulated = random.gauss(mean_return, std_dev)
            simulated_returns.append(simulated)
        
        # 排序找分位数
        simulated_returns.sort()
        index = int((1 - confidence) * simulations)
        var_1d = -simulated_returns[index] if index < len(simulated_returns) else 0
        var_1d = max(0, var_1d)
        
        # 10 日 VaR
        var_10d = var_1d * math.sqrt(10)
        
        return {
            'var_1d_pct': var_1d,
            'var_10d_pct': var_10d
        }
    
    # ==================== 夏普比率 ====================
    
    def calculate_sharpe_ratio(
        self,
        returns: Optional[List[float]] = None,
        annualization_factor: int = 252
    ) -> Dict:
        """
        计算夏普比率
        
        Args:
            returns: 收益率序列 (默认使用历史数据)
            annualization_factor: 年化因子
            
        Returns:
            夏普比率计算结果
        """
        data = returns if returns else self.returns_history
        
        if len(data) < 20:
            return {
                'sharpe_ratio': 0.0,
                'annualized_return': 0.0,
                'annualized_volatility': 0.0,
                'warning': '数据不足'
            }
        
        # 计算均值和标准差
        mean_return = sum(data) / len(data)
        variance = sum((r - mean_return) ** 2 for r in data) / len(data)
        std_dev = math.sqrt(variance)
        
        # 年化
        annualized_return = mean_return * annualization_factor
        annualized_volatility = std_dev * math.sqrt(annualization_factor)
        
        # 夏普比率
        excess_return = annualized_return - self.config.risk_free_rate
        sharpe = excess_return / annualized_volatility if annualized_volatility > 0 else 0
        
        return {
            'sharpe_ratio': sharpe,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'excess_return': excess_return,
            'risk_free_rate': self.config.risk_free_rate,
            'num_observations': len(data),
            'meets_minimum': sharpe >= self.config.min_sharpe
        }
    
    def calculate_sortino_ratio(
        self,
        returns: Optional[List[float]] = None,
        annualization_factor: int = 252
    ) -> Dict:
        """
        计算索提诺比率 (只考虑下行波动)
        
        Returns:
            索提诺比率
        """
        data = returns if returns else self.returns_history
        
        if len(data) < 20:
            return {'sortino_ratio': 0.0, 'warning': '数据不足'}
        
        mean_return = sum(data) / len(data)
        
        # 下行偏差
        downside_returns = [r for r in data if r < 0]
        if downside_returns:
            downside_variance = sum(r ** 2 for r in downside_returns) / len(data)
            downside_deviation = math.sqrt(downside_variance) * math.sqrt(annualization_factor)
        else:
            downside_deviation = 0.0001  # 避免除零
        
        # 年化收益
        annualized_return = mean_return * annualization_factor
        excess_return = annualized_return - self.config.risk_free_rate
        
        sortino = excess_return / downside_deviation if downside_deviation > 0 else 0
        
        return {
            'sortino_ratio': sortino,
            'annualized_return': annualized_return,
            'downside_deviation': downside_deviation,
            'num_negative_days': len(downside_returns)
        }
    
    # ==================== Beta 计算 ====================
    
    def calculate_beta(
        self,
        portfolio_returns: Optional[List[float]] = None,
        benchmark_returns: Optional[List[float]] = None
    ) -> Dict:
        """
        计算 Beta (市场敏感度)
        
        Beta = Cov(Rp, Rm) / Var(Rm)
        
        Returns:
            Beta 计算结果
        """
        port_ret = portfolio_returns if portfolio_returns else self.returns_history
        bench_ret = benchmark_returns if benchmark_returns else self.benchmark_returns
        
        if len(port_ret) < 20 or len(bench_ret) < 20:
            return {'beta': 0.0, 'warning': '数据不足'}
        
        # 确保长度一致
        min_len = min(len(port_ret), len(bench_ret))
        port_ret = port_ret[-min_len:]
        bench_ret = bench_ret[-min_len:]
        
        # 计算均值
        port_mean = sum(port_ret) / len(port_ret)
        bench_mean = sum(bench_ret) / len(bench_ret)
        
        # 计算协方差和方差
        covariance = sum((p - port_mean) * (b - bench_mean) for p, b in zip(port_ret, bench_ret)) / len(port_ret)
        benchmark_variance = sum((b - bench_mean) ** 2 for b in bench_ret) / len(bench_ret)
        
        # Beta
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
        
        # R 平方
        correlation = covariance / (math.sqrt(sum((p - port_mean) ** 2 for p in port_ret) / len(port_ret)) * 
                                   math.sqrt(benchmark_variance)) if benchmark_variance > 0 else 0
        r_squared = correlation ** 2
        
        return {
            'beta': beta,
            'correlation': correlation,
            'r_squared': r_squared,
            'benchmark': self.config.beta_benchmark,
            'exceeds_limit': abs(beta) > self.config.max_beta,
            'num_observations': min_len
        }
    
    # ==================== 因子暴露 ====================
    
    def calculate_factor_exposures(
        self,
        factor_returns: Dict[str, List[float]]
    ) -> Dict[str, float]:
        """
        计算因子暴露 (通过回归)
        
        Args:
            factor_returns: 因子收益率字典 {factor_name: [returns]}
            
        Returns:
            因子暴露字典
        """
        if len(self.returns_history) < 60:
            return {}
        
        exposures = {}
        
        for factor_name, returns in factor_returns.items():
            if len(returns) < 60:
                continue
            
            # 简化回归 (单因子 Beta)
            port_ret = self.returns_history[-len(returns):]
            
            port_mean = sum(port_ret) / len(port_ret)
            factor_mean = sum(returns) / len(returns)
            
            covariance = sum((p - port_mean) * (f - factor_mean) for p, f in zip(port_ret, returns)) / len(returns)
            factor_variance = sum((f - factor_mean) ** 2 for f in returns) / len(returns)
            
            exposure = covariance / factor_variance if factor_variance > 0 else 0
            exposures[factor_name] = exposure
        
        return exposures
    
    # ==================== 行业暴露 ====================
    
    def calculate_sector_exposure(self) -> Dict[str, float]:
        """
        计算行业暴露
        
        Returns:
            行业权重字典
        """
        sector_weights = {}
        total_weight = 0.0
        
        for position in self.positions.values():
            sector = position.sector
            weight = position.weight
            sector_weights[sector] = sector_weights.get(sector, 0) + weight
            total_weight += weight
        
        # 转换为百分比
        if total_weight > 0:
            sector_weights = {k: v / total_weight for k, v in sector_weights.items()}
        
        return sector_weights
    
    def check_sector_concentration(self) -> Dict:
        """检查行业集中度"""
        sector_weights = self.calculate_sector_exposure()
        
        # 找出最大行业暴露
        max_sector = max(sector_weights.items(), key=lambda x: x[1]) if sector_weights else ('', 0)
        
        # 检查是否超限
        concentrated_sectors = [
            (sector, weight) for sector, weight in sector_weights.items()
            if weight > self.config.max_sector_exposure
        ]
        
        return {
            'sector_weights': sector_weights,
            'max_sector': max_sector[0],
            'max_sector_weight': max_sector[1],
            'concentrated_sectors': concentrated_sectors,
            'exceeds_limit': len(concentrated_sectors) > 0
        }
    
    # ==================== 综合风险评分 ====================
    
    def calculate_risk_score(self, portfolio_value: float) -> Dict:
        """
        计算综合风险评分 (0-100, 越高风险越大)
        
        Returns:
            风险评分和详情
        """
        scores = {}
        weights = {
            'var': 0.30,
            'sharpe': 0.20,
            'beta': 0.20,
            'concentration': 0.15,
            'drawdown': 0.15
        }
        
        # VaR 评分
        var_result = self.calculate_var(portfolio_value)
        var_pct = var_result.get('var_1d_pct', 0)
        var_score = min(100, (var_pct / self.config.max_var_pct) * 100) if self.config.max_var_pct > 0 else 0
        scores['var'] = var_score
        
        # 夏普评分 (夏普越低，风险越高)
        sharpe_result = self.calculate_sharpe_ratio()
        sharpe = sharpe_result.get('sharpe_ratio', 0)
        sharpe_score = max(0, 100 - sharpe * 50)  # 夏普 2.0 得 0 分，0 得 100 分
        scores['sharpe'] = sharpe_score
        
        # Beta 评分
        beta_result = self.calculate_beta()
        beta = abs(beta_result.get('beta', 0))
        beta_score = min(100, (beta / self.config.max_beta) * 100) if self.config.max_beta > 0 else 0
        scores['beta'] = beta_score
        
        # 集中度评分
        sector_check = self.check_sector_concentration()
        max_sector_weight = sector_check.get('max_sector_weight', 0)
        concentration_score = min(100, (max_sector_weight / self.config.max_sector_exposure) * 100) if self.config.max_sector_exposure > 0 else 0
        scores['concentration'] = concentration_score
        
        # 回撤评分 (使用近期最大回撤)
        if self.returns_history:
            cumulative = 1.0
            peak = 1.0
            max_dd = 0.0
            for r in self.returns_history[-60:]:  # 近 60 天
                cumulative *= (1 + r)
                peak = max(peak, cumulative)
                dd = (peak - cumulative) / peak
                max_dd = max(max_dd, dd)
            drawdown_score = min(100, (max_dd / 0.15) * 100)  # 15% 回撤得 100 分
        else:
            drawdown_score = 0
        scores['drawdown'] = drawdown_score
        
        # 加权总分
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # 风险等级
        if total_score >= 80:
            risk_level = "CRITICAL"
        elif total_score >= 60:
            risk_level = "HIGH"
        elif total_score >= 40:
            risk_level = "MEDIUM"
        elif total_score >= 20:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        return {
            'total_score': total_score,
            'risk_level': risk_level,
            'component_scores': scores,
            'weights': weights,
            'timestamp': datetime.now()
        }
    
    # ==================== 风险报告 ====================
    
    def get_risk_report(self, portfolio_value: float) -> Dict:
        """获取完整风险报告"""
        return {
            'portfolio_value': portfolio_value,
            'var_metrics': self.calculate_var(portfolio_value),
            'sharpe_metrics': self.calculate_sharpe_ratio(),
            'sortino_metrics': self.calculate_sortino_ratio(),
            'beta_metrics': self.calculate_beta(),
            'sector_exposure': self.check_sector_concentration(),
            'risk_score': self.calculate_risk_score(portfolio_value),
            'num_observations': len(self.returns_history),
            'num_positions': len(self.positions)
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    import random
    
    # 创建风险指标计算器
    config = RiskMetricsConfig(
        var_confidence_level=0.95,
        max_var_pct=0.05,
        min_sharpe=1.0
    )
    rmc = RiskMetricsCalculator(config)
    
    # 模拟 252 天数据
    for i in range(252):
        port_return = random.gauss(0.0005, 0.015)  # 日收益 0.05%, 波动 1.5%
        bench_return = random.gauss(0.0004, 0.012)  # 基准
        rmc.add_return(port_return, bench_return, datetime.now() - timedelta(days=252-i))
    
    # 计算风险指标
    report = rmc.get_risk_report(1000000)
    
    print(f"VaR (95%): {report['var_metrics']['var_1d_pct']:.2%}")
    print(f"夏普比率：{report['sharpe_metrics']['sharpe_ratio']:.2f}")
    print(f"Beta: {report['beta_metrics']['beta']:.2f}")
    print(f"风险评分：{report['risk_score']['total_score']:.1f} ({report['risk_score']['risk_level']})")
