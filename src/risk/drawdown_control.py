"""
回撤控制模块 - Drawdown Controller
负责监控和控制组合回撤

核心功能:
- 最大回撤限制
- 日亏损限制
- 连续亏损限制
- 自动降仓机制
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import math


class DrawdownLevel(Enum):
    """回撤等级"""
    NORMAL = "normal"  # 正常
    WARNING = "warning"  # 警告
    DANGER = "danger"  # 危险
    CRITICAL = "critical"  # 严重


@dataclass
class DrawdownConfig:
    """回撤配置"""
    # 最大回撤限制
    max_drawdown_pct: float = 0.15  # 最大回撤 15%
    warning_drawdown_pct: float = 0.10  # 警告回撤 10%
    
    # 日亏损限制
    max_daily_loss_pct: float = 0.03  # 单日最大亏损 3%
    warning_daily_loss_pct: float = 0.02  # 日亏损警告 2%
    
    # 连续亏损限制
    max_consecutive_losses: int = 5  # 最大连续亏损次数
    consecutive_loss_window: int = 10  # 连续亏损统计窗口
    
    # 自动降仓机制
    enable_auto_deleveraging: bool = True
    deleveraging_thresholds: List[float] = field(default_factory=lambda: [0.05, 0.10, 0.15])
    deleveraging_ratios: List[float] = field(default_factory=lambda: [0.8, 0.5, 0.25])
    
    # 恢复机制
    recovery_required_pct: float = 0.05  # 回撤恢复后才能恢复仓位 (5%)
    cooldown_days: int = 5  # 降仓后冷却期 (天)


@dataclass
class DailyPerformance:
    """每日表现"""
    date: datetime
    daily_return: float
    cumulative_return: float
    peak_value: float
    current_value: float
    drawdown: float
    is_loss_day: bool


class DrawdownController:
    """
    回撤控制器
    
    监控组合回撤，触发自动降仓保护
    """
    
    def __init__(self, config: Optional[DrawdownConfig] = None):
        self.config = config or DrawdownConfig()
        
        # 组合价值追踪
        self.initial_value: float = 0.0
        self.peak_value: float = 0.0
        self.current_value: float = 0.0
        
        # 历史记录
        self.daily_history: List[DailyPerformance] = []
        self.drawdown_history: List[Dict] = []
        
        # 亏损统计
        self.consecutive_losses: int = 0
        self.recent_results: List[bool] = []  # True=盈利, False=亏损
        
        # 降仓状态
        self.current_leverage_ratio: float = 1.0
        self.deleveraging_active: bool = False
        self.deleveraging_start_date: Optional[datetime] = None
        self.last_drawdown_level: DrawdownLevel = DrawdownLevel.NORMAL
        
    def initialize(self, initial_value: float):
        """初始化组合"""
        self.initial_value = initial_value
        self.peak_value = initial_value
        self.current_value = initial_value
        
    # ==================== 回撤计算 ====================
    
    def update_portfolio_value(
        self,
        current_value: float,
        current_date: datetime
    ) -> Dict:
        """
        更新组合价值并计算回撤
        
        Args:
            current_value: 当前组合价值
            current_date: 当前日期
            
        Returns:
            回撤状态信息
        """
        previous_value = self.current_value
        self.current_value = current_value
        
        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # 计算回撤
        current_drawdown = (self.peak_value - current_value) / self.peak_value if self.peak_value > 0 else 0
        
        # 计算日收益率
        daily_return = (current_value - previous_value) / previous_value if previous_value > 0 else 0
        
        # 记录每日表现
        daily_perf = DailyPerformance(
            date=current_date,
            daily_return=daily_return,
            cumulative_return=(current_value - self.initial_value) / self.initial_value if self.initial_value > 0 else 0,
            peak_value=self.peak_value,
            current_value=current_value,
            drawdown=current_drawdown,
            is_loss_day=daily_return < 0
        )
        self.daily_history.append(daily_perf)
        
        # 更新亏损统计
        self._update_loss_statistics(daily_return)
        
        # 检查回撤等级
        drawdown_level = self._check_drawdown_level(current_drawdown)
        
        # 检查是否需要降仓
        if self.config.enable_auto_deleveraging:
            self._check_deleveraging(current_drawdown, drawdown_level, current_date)
        
        return {
            'date': current_date,
            'current_value': current_value,
            'peak_value': self.peak_value,
            'drawdown': current_drawdown,
            'daily_return': daily_return,
            'drawdown_level': drawdown_level.value,
            'leverage_ratio': self.current_leverage_ratio,
            'consecutive_losses': self.consecutive_losses
        }
    
    def _update_loss_statistics(self, daily_return: float):
        """更新亏损统计"""
        is_profit = daily_return >= 0
        self.recent_results.append(is_profit)
        
        # 保持窗口大小
        if len(self.recent_results) > self.config.consecutive_loss_window:
            self.recent_results.pop(0)
        
        # 更新连续亏损计数
        if daily_return < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
    
    def _check_drawdown_level(self, drawdown: float) -> DrawdownLevel:
        """检查回撤等级"""
        if drawdown >= self.config.max_drawdown_pct:
            return DrawdownLevel.CRITICAL
        elif drawdown >= self.config.warning_drawdown_pct:
            return DrawdownLevel.DANGER
        elif drawdown >= self.config.warning_drawdown_pct * 0.5:
            return DrawdownLevel.WARNING
        else:
            return DrawdownLevel.NORMAL
    
    # ==================== 自动降仓机制 ====================
    
    def _check_deleveraging(
        self,
        current_drawdown: float,
        drawdown_level: DrawdownLevel,
        current_date: datetime
    ):
        """检查并执行自动降仓"""
        # 检查连续亏损
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            self._trigger_deleveraging(0.5, f"consecutive_losses_{self.consecutive_losses}", current_date)
            return
        
        # 根据回撤等级降仓
        if drawdown_level == DrawdownLevel.CRITICAL:
            self._trigger_deleveraging(0.25, "max_drawdown_breach", current_date)
        elif drawdown_level == DrawdownLevel.DANGER and not self.deleveraging_active:
            # 找到对应的降仓比例
            for i, threshold in enumerate(self.config.deleveraging_thresholds):
                if current_drawdown >= threshold:
                    ratio = self.config.deleveraging_ratios[i] if i < len(self.config.deleveraging_ratios) else 0.5
                    self._trigger_deleveraging(ratio, f"drawdown_{threshold:.0%}", current_date)
                    break
    
    def _trigger_deleveraging(
        self,
        target_ratio: float,
        reason: str,
        current_date: datetime
    ):
        """触发降仓"""
        if not self.config.enable_auto_deleveraging:
            return
        
        old_ratio = self.current_leverage_ratio
        self.current_leverage_ratio = target_ratio
        self.deleveraging_active = True
        self.deleveraging_start_date = current_date
        
        self.drawdown_history.append({
            'date': current_date,
            'reason': reason,
            'old_ratio': old_ratio,
            'new_ratio': target_ratio,
            'drawdown': (self.peak_value - self.current_value) / self.peak_value if self.peak_value > 0 else 0
        })
    
    def check_recovery(self, current_date: datetime) -> bool:
        """
        检查是否可以恢复仓位
        
        Returns:
            是否可以恢复仓位
        """
        if not self.deleveraging_active:
            return True
        
        # 检查冷却期
        if self.deleveraging_start_date:
            days_since_deleveraging = (current_date - self.deleveraging_start_date).days
            if days_since_deleveraging < self.config.cooldown_days:
                return False
        
        # 检查是否从低点恢复
        if self.daily_history:
            min_value = min(h.current_value for h in self.daily_history[-self.config.cooldown_days * 2:])
            recovery_pct = (self.current_value - min_value) / min_value if min_value > 0 else 0
            
            if recovery_pct >= self.config.recovery_required_pct:
                self.current_leverage_ratio = 1.0
                self.deleveraging_active = False
                self.deleveraging_start_date = None
                return True
        
        return False
    
    def get_allowed_position_size(
        self,
        base_position_size: float
    ) -> float:
        """
        根据当前杠杆率计算允许的仓位大小
        
        Args:
            base_position_size: 基础仓位大小
            
        Returns:
            调整后的仓位大小
        """
        return base_position_size * self.current_leverage_ratio
    
    # ==================== 日亏损限制 ====================
    
    def check_daily_loss_limit(
        self,
        daily_pnl_pct: float
    ) -> Tuple[bool, str]:
        """
        检查是否触及日亏损限制
        
        Returns:
            (是否允许继续交易, 原因)
        """
        if daily_pnl_pct <= -self.config.max_daily_loss_pct:
            return False, f"触及日亏损限制 ({self.config.max_daily_loss_pct:.1%})"
        
        if daily_pnl_pct <= -self.config.warning_daily_loss_pct:
            return True, f"警告：日亏损接近限制 ({self.config.warning_daily_loss_pct:.1%})"
        
        return True, "正常"
    
    def get_remaining_daily_risk(self) -> float:
        """获取当日剩余风险额度"""
        if not self.daily_history:
            return self.config.max_daily_loss_pct
        
        today = self.daily_history[-1].date if self.daily_history else datetime.now()
        today_records = [h for h in self.daily_history if h.date.date() == today.date()]
        
        if not today_records:
            return self.config.max_daily_loss_pct
        
        cumulative_today = sum(h.daily_return for h in today_records)
        
        if cumulative_today >= 0:
            return self.config.max_daily_loss_pct
        
        return self.config.max_daily_loss_pct - abs(cumulative_today)
    
    # ==================== 统计和报告 ====================
    
    def get_drawdown_statistics(self) -> Dict:
        """获取回撤统计"""
        if not self.daily_history:
            return {}
        
        drawdowns = [h.drawdown for h in self.daily_history]
        max_dd = max(drawdowns) if drawdowns else 0
        current_dd = drawdowns[-1] if drawdowns else 0
        
        # 计算平均回撤
        avg_dd = sum(drawdowns) / len(drawdowns) if drawdowns else 0
        
        # 计算回撤持续时间
        in_drawdown = [h for h in self.daily_history if h.drawdown > 0.01]  # >1% 算回撤
        avg_drawdown_days = len(in_drawdown) / len(self.daily_history) if self.daily_history else 0
        
        # 最大回撤持续时间
        max_dd_duration = 0
        current_dd_duration = 0
        for h in self.daily_history:
            if h.drawdown > 0.05:  # >5% 算显著回撤
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)
            else:
                current_dd_duration = 0
        
        return {
            'current_drawdown': current_dd,
            'max_drawdown': max_dd,
            'avg_drawdown': avg_dd,
            'max_drawdown_duration_days': max_dd_duration,
            'drawdown_frequency': avg_drawdown_days,
            'peak_value': self.peak_value,
            'current_value': self.current_value,
            'initial_value': self.initial_value
        }
    
    def get_risk_status(self) -> Dict:
        """获取风险状态"""
        stats = self.get_drawdown_statistics()
        current_dd = stats.get('current_drawdown', 0)
        
        return {
            'level': self._check_drawdown_level(current_dd).value,
            'leverage_ratio': self.current_leverage_ratio,
            'deleveraging_active': self.deleveraging_active,
            'consecutive_losses': self.consecutive_losses,
            'daily_history_count': len(self.daily_history),
            'triggered_events': len(self.drawdown_history),
            'statistics': stats
        }
    
    def get_recent_performance(self, days: int = 30) -> Dict:
        """获取近期表现"""
        if not self.daily_history:
            return {}
        
        recent = self.daily_history[-days:] if len(self.daily_history) >= days else self.daily_history
        
        if not recent:
            return {}
        
        returns = [h.daily_return for h in recent]
        profit_days = sum(1 for r in returns if r > 0)
        loss_days = sum(1 for r in returns if r < 0)
        
        total_return = (self.current_value - recent[0].current_value) / recent[0].current_value if recent else 0
        
        return {
            'period_days': len(recent),
            'total_return': total_return,
            'avg_daily_return': sum(returns) / len(returns) if returns else 0,
            'profit_days': profit_days,
            'loss_days': loss_days,
            'win_rate': profit_days / len(returns) if returns else 0,
            'best_day': max(returns) if returns else 0,
            'worst_day': min(returns) if returns else 0,
            'consecutive_losses': self.consecutive_losses
        }
    
    def reset(self):
        """重置控制器"""
        self.consecutive_losses = 0
        self.recent_results = []
        self.deleveraging_active = False
        self.deleveraging_start_date = None
        self.current_leverage_ratio = 1.0
        self.last_drawdown_level = DrawdownLevel.NORMAL


# ==================== 使用示例 ====================

if __name__ == "__main__":
    import random
    
    # 创建回撤控制器
    config = DrawdownConfig(
        max_drawdown_pct=0.15,
        max_daily_loss_pct=0.03,
        max_consecutive_losses=5
    )
    dc = DrawdownController(config)
    
    # 初始化
    dc.initialize(1000000)  # 100 万初始资金
    
    # 模拟 30 天交易
    current_date = datetime.now()
    value = 1000000
    
    for i in range(30):
        # 模拟日收益率 (正态分布)
        daily_return = random.gauss(0.001, 0.02)  # 期望 0.1%, 波动 2%
        value = value * (1 + daily_return)
        
        status = dc.update_portfolio_value(value, current_date + timedelta(days=i))
        
        if status['drawdown_level'] != 'normal':
            print(f"Day {i}: 回撤={status['drawdown']:.2%}, 等级={status['drawdown_level']}, 杠杆={status['leverage_ratio']:.2f}")
    
    print(f"\n最终统计：{dc.get_drawdown_statistics()}")
    print(f"风险状态：{dc.get_risk_status()}")
