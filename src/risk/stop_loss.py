"""
止损止盈模块 - Stop Loss Manager
负责多种止损策略的执行和监控

核心功能:
- 固定比例止损
- 跟踪止损 (Trailing Stop)
- 时间止损
- 波动率止损
- 止盈策略
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


class StopLossType(Enum):
    """止损类型"""
    FIXED_PERCENT = "fixed_percent"  # 固定比例
    TRAILING = "trailing"  # 跟踪止损
    TIME_BASED = "time_based"  # 时间止损
    VOLATILITY = "volatility"  # 波动率止损
    TECHNICAL = "technical"  # 技术位止损


class StopLossStatus(Enum):
    """止损状态"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class StopLossConfig:
    """止损配置"""
    # 固定比例止损
    fixed_stop_loss_pct: float = 0.08  # 8% 固定止损
    fixed_take_profit_pct: float = 0.20  # 20% 固定止盈
    
    # 跟踪止损
    trailing_stop_pct: float = 0.10  # 10% 跟踪止损
    trailing_step_pct: float = 0.02  # 2% 调整步长
    
    # 时间止损
    max_holding_days: int = 30  # 最大持有天数
    time_stop_loss_pct: float = 0.05  # 时间止损阈值 5%
    
    # 波动率止损
    vol_multiple: float = 2.0  # 波动率倍数 (2倍ATR)
    min_vol_stop_pct: float = 0.05  # 最小波动率止损 5%
    max_vol_stop_pct: float = 0.15  # 最大波动率止损 15%
    
    # 分级止损
    enable_tiered_stop: bool = True
    tier1_loss_pct: float = 0.05  # 第一级 5%
    tier1_reduce_pct: float = 0.50  # 减仓 50%
    tier2_loss_pct: float = 0.10  # 第二级 10%
    tier2_reduce_pct: float = 1.00  # 清仓


@dataclass
class PositionStopLoss:
    """持仓止损信息"""
    symbol: str
    entry_price: float
    entry_date: datetime
    stop_type: StopLossType
    stop_price: float
    take_profit_price: Optional[float] = None
    status: StopLossStatus = StopLossStatus.ACTIVE
    highest_price: float = 0.0  # 用于跟踪止损
    lowest_price: float = 0.0  # 用于跟踪止损 (空头)
    last_adjustment_date: Optional[datetime] = None
    triggered_date: Optional[datetime] = None
    triggered_price: Optional[float] = None
    notes: str = ""


class StopLossManager:
    """
    止损管理器
    
    管理多种止损策略，保护资金安全
    """
    
    def __init__(self, config: Optional[StopLossConfig] = None):
        self.config = config or StopLossConfig()
        self.stop_losses: Dict[str, PositionStopLoss] = {}
        self.triggered_history: List[PositionStopLoss] = []
        
    # ==================== 创建止损 ====================
    
    def create_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        entry_date: datetime,
        stop_type: StopLossType = StopLossType.FIXED_PERCENT,
        custom_stop_price: Optional[float] = None,
        custom_take_profit: Optional[float] = None,
        volatility: Optional[float] = None
    ) -> PositionStopLoss:
        """
        创建止损订单
        
        Args:
            symbol: 标的代码
            entry_price: 入场价格
            entry_date: 入场日期
            stop_type: 止损类型
            custom_stop_price: 自定义止损价
            custom_take_profit: 自定义止盈价
            volatility: 波动率 (用于波动率止损)
            
        Returns:
            PositionStopLoss 对象
        """
        # 计算止损价
        if custom_stop_price:
            stop_price = custom_stop_price
        else:
            stop_price = self._calculate_stop_price(
                entry_price, stop_type, volatility
            )
        
        # 计算止盈价
        take_profit_price = custom_take_profit or self._calculate_take_profit(entry_price)
        
        stop_loss = PositionStopLoss(
            symbol=symbol,
            entry_price=entry_price,
            entry_date=entry_date,
            stop_type=stop_type,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
            highest_price=entry_price,
            lowest_price=entry_price
        )
        
        self.stop_losses[symbol] = stop_loss
        return stop_loss
    
    def _calculate_stop_price(
        self,
        entry_price: float,
        stop_type: StopLossType,
        volatility: Optional[float] = None
    ) -> float:
        """计算止损价格"""
        if stop_type == StopLossType.FIXED_PERCENT:
            return entry_price * (1 - self.config.fixed_stop_loss_pct)
        
        elif stop_type == StopLossType.TRAILING:
            return entry_price * (1 - self.config.trailing_stop_pct)
        
        elif stop_type == StopLossType.VOLATILITY:
            if volatility:
                vol_stop = volatility * self.config.vol_multiple
                vol_stop = max(self.config.min_vol_stop_pct, 
                              min(vol_stop, self.config.max_vol_stop_pct))
                return entry_price * (1 - vol_stop)
            else:
                return entry_price * (1 - self.config.fixed_stop_loss_pct)
        
        elif stop_type == StopLossType.TIME_BASED:
            return entry_price * (1 - self.config.time_stop_loss_pct)
        
        else:
            return entry_price * (1 - self.config.fixed_stop_loss_pct)
    
    def _calculate_take_profit(self, entry_price: float) -> float:
        """计算止盈价格"""
        return entry_price * (1 + self.config.fixed_take_profit_pct)
    
    # ==================== 价格更新和监控 ====================
    
    def update_price(
        self,
        symbol: str,
        current_price: float,
        current_date: datetime
    ) -> Optional[Dict]:
        """
        更新价格并检查是否触发止损
        
        Args:
            symbol: 标的代码
            current_price: 当前价格
            current_date: 当前日期
            
        Returns:
            如果触发止损，返回触发信息；否则返回 None
        """
        if symbol not in self.stop_losses:
            return None
        
        stop_loss = self.stop_losses[symbol]
        
        if stop_loss.status != StopLossStatus.ACTIVE:
            return None
        
        # 更新最高/最低价 (用于跟踪止损)
        if current_price > stop_loss.highest_price:
            stop_loss.highest_price = current_price
        
        if current_price < stop_loss.lowest_price:
            stop_loss.lowest_price = current_price
        
        # 根据止损类型调整止损价
        if stop_loss.stop_type == StopLossType.TRAILING:
            self._adjust_trailing_stop(stop_loss, current_price, current_date)
        
        # 检查是否触发止损
        trigger_info = self._check_trigger(stop_loss, current_price, current_date)
        
        if trigger_info:
            stop_loss.status = StopLossStatus.TRIGGERED
            stop_loss.triggered_date = current_date
            stop_loss.triggered_price = current_price
            self.triggered_history.append(stop_loss)
            del self.stop_losses[symbol]
        
        return trigger_info
    
    def _adjust_trailing_stop(
        self,
        stop_loss: PositionStopLoss,
        current_price: float,
        current_date: datetime
    ):
        """调整跟踪止损价"""
        # 计算新的止损价 (基于最高价)
        new_stop_price = stop_loss.highest_price * (1 - self.config.trailing_stop_pct)
        
        # 只有当新止损价高于当前止损价时才调整
        if new_stop_price > stop_loss.stop_price:
            # 检查是否达到调整步长
            if stop_loss.last_adjustment_date:
                days_since_last = (current_date - stop_loss.last_adjustment_date).days
                price_change_pct = (stop_loss.highest_price - stop_loss.entry_price) / stop_loss.entry_price
                
                if price_change_pct >= self.config.trailing_step_pct or days_since_last >= 5:
                    stop_loss.stop_price = new_stop_price
                    stop_loss.last_adjustment_date = current_date
            else:
                stop_loss.stop_price = new_stop_price
                stop_loss.last_adjustment_date = current_date
    
    def _check_trigger(
        self,
        stop_loss: PositionStopLoss,
        current_price: float,
        current_date: datetime
    ) -> Optional[Dict]:
        """检查是否触发止损/止盈"""
        trigger_reason = None
        
        # 检查止损
        if current_price <= stop_loss.stop_price:
            trigger_reason = "stop_loss"
        
        # 检查止盈
        elif stop_loss.take_profit_price and current_price >= stop_loss.take_profit_price:
            trigger_reason = "take_profit"
        
        # 检查时间止损
        elif stop_loss.stop_type == StopLossType.TIME_BASED:
            holding_days = (current_date - stop_loss.entry_date).days
            if holding_days >= self.config.max_holding_days:
                pnl_pct = (current_price - stop_loss.entry_price) / stop_loss.entry_price
                if pnl_pct < self.config.time_stop_loss_pct:
                    trigger_reason = "time_stop"
        
        if trigger_reason:
            return {
                'symbol': stop_loss.symbol,
                'reason': trigger_reason,
                'trigger_price': current_price,
                'entry_price': stop_loss.entry_price,
                'pnl_pct': (current_price - stop_loss.entry_price) / stop_loss.entry_price,
                'holding_days': (current_date - stop_loss.entry_date).days,
                'stop_type': stop_loss.stop_type.value
            }
        
        return None
    
    # ==================== 分级止损 ====================
    
    def check_tiered_stop(
        self,
        symbol: str,
        current_price: float,
        position_size: int
    ) -> Optional[Dict]:
        """
        检查分级止损
        
        Returns:
            减仓指令或 None
        """
        if symbol not in self.stop_losses:
            return None
        
        stop_loss = self.stop_losses[symbol]
        pnl_pct = (current_price - stop_loss.entry_price) / stop_loss.entry_price
        
        if not self.config.enable_tiered_stop:
            return None
        
        # 第一级止损
        if pnl_pct <= -self.config.tier1_loss_pct:
            reduce_qty = int(position_size * self.config.tier1_reduce_pct)
            if reduce_qty > 0:
                return {
                    'symbol': symbol,
                    'action': 'reduce',
                    'quantity': reduce_qty,
                    'reason': f'tier1_stop_loss_{self.config.tier1_loss_pct:.0%}',
                    'remaining_pct': 1 - self.config.tier1_reduce_pct
                }
        
        # 第二级止损 (清仓)
        if pnl_pct <= -self.config.tier2_loss_pct:
            return {
                'symbol': symbol,
                'action': 'close',
                'quantity': position_size,
                'reason': f'tier2_stop_loss_{self.config.tier2_loss_pct:.0%}',
                'remaining_pct': 0
            }
        
        return None
    
    # ==================== 波动率调整止损 ====================
    
    def adjust_stop_by_volatility(
        self,
        symbol: str,
        atr: float,
        current_price: float
    ) -> Optional[float]:
        """
        根据ATR波动率调整止损价
        
        Args:
            symbol: 标的代码
            atr: ATR值 (14日平均真实波幅)
            current_price: 当前价格
            
        Returns:
            新的止损价或 None
        """
        if symbol not in self.stop_losses:
            return None
        
        stop_loss = self.stop_losses[symbol]
        
        # 计算基于ATR的止损距离
        atr_stop_distance = atr * self.config.vol_multiple
        new_stop_price = current_price - atr_stop_distance
        
        # 限制在合理范围
        min_stop = current_price * (1 - self.config.max_vol_stop_pct)
        max_stop = current_price * (1 - self.config.min_vol_stop_pct)
        new_stop_price = max(min_stop, min(new_stop_price, max_stop))
        
        # 只上调止损价 (更严格)
        if new_stop_price > stop_loss.stop_price:
            stop_loss.stop_price = new_stop_price
            return new_stop_price
        
        return None
    
    # ==================== 批量管理 ====================
    
    def get_active_stop_losses(self) -> List[PositionStopLoss]:
        """获取所有活跃的止损"""
        return [sl for sl in self.stop_losses.values() if sl.status == StopLossStatus.ACTIVE]
    
    def cancel_stop_loss(self, symbol: str) -> bool:
        """取消止损"""
        if symbol in self.stop_losses:
            self.stop_losses[symbol].status = StopLossStatus.CANCELLED
            del self.stop_losses[symbol]
            return True
        return False
    
    def update_take_profit(
        self,
        symbol: str,
        new_take_profit: float
    ) -> bool:
        """更新止盈价"""
        if symbol in self.stop_losses:
            self.stop_losses[symbol].take_profit_price = new_take_profit
            return True
        return False
    
    # ==================== 统计和报告 ====================
    
    def get_stop_loss_summary(self) -> Dict:
        """获取止损摘要"""
        active = self.get_active_stop_losses()
        
        if not active:
            return {
                'total_active': 0,
                'total_triggered': len(self.triggered_history),
                'trigger_rate': 0.0,
                'avg_loss_pct': 0.0,
                'avg_profit_pct': 0.0
            }
        
        # 计算触发统计
        triggered_stops = [sl for sl in self.triggered_history]
        trigger_rate = len(triggered_stops) / (len(triggered_stops) + len(active)) if (len(triggered_stops) + len(active)) > 0 else 0
        
        # 平均盈亏
        losses = [sl.triggered_price for sl in triggered_stops if sl.triggered_price and sl.triggered_price < sl.entry_price]
        profits = [sl.triggered_price for sl in triggered_stops if sl.triggered_price and sl.triggered_price > sl.entry_price]
        
        avg_loss = sum((sl.entry_price - sl.triggered_price) / sl.entry_price 
                      for sl in triggered_stops if sl.triggered_price and sl.triggered_price < sl.entry_price) / len(losses) if losses else 0
        avg_profit = sum((sl.triggered_price - sl.entry_price) / sl.entry_price 
                        for sl in triggered_stops if sl.triggered_price and sl.triggered_price > sl.entry_price) / len(profits) if profits else 0
        
        return {
            'total_active': len(active),
            'total_triggered': len(self.triggered_history),
            'trigger_rate': trigger_rate,
            'avg_loss_pct': avg_loss,
            'avg_profit_pct': avg_profit,
            'stop_types': {
                'fixed': sum(1 for sl in active if sl.stop_type == StopLossType.FIXED_PERCENT),
                'trailing': sum(1 for sl in active if sl.stop_type == StopLossType.TRAILING),
                'volatility': sum(1 for sl in active if sl.stop_type == StopLossType.VOLATILITY),
                'time': sum(1 for sl in active if sl.stop_type == StopLossType.TIME_BASED)
            }
        }
    
    def get_risk_exposure(self) -> Dict[str, float]:
        """获取风险敞口 (各标的距离止损的幅度)"""
        exposure = {}
        for symbol, stop_loss in self.stop_losses.items():
            if stop_loss.status == StopLossStatus.ACTIVE:
                # 距离止损的百分比
                risk_distance = (stop_loss.highest_price - stop_loss.stop_price) / stop_loss.highest_price
                exposure[symbol] = risk_distance
        return exposure


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建止损管理器
    config = StopLossConfig(
        fixed_stop_loss_pct=0.08,
        trailing_stop_pct=0.10,
        max_holding_days=30
    )
    slm = StopLossManager(config)
    
    # 创建止损
    entry_date = datetime.now()
    slm.create_stop_loss(
        symbol="AAPL",
        entry_price=150.0,
        entry_date=entry_date,
        stop_type=StopLossType.TRAILING
    )
    
    # 更新价格
    for i in range(10):
        price = 150.0 * (1 + 0.02 * i)  # 价格上涨
        trigger = slm.update_price("AAPL", price, entry_date + timedelta(days=i))
        if trigger:
            print(f"触发：{trigger}")
    
    print(f"止损摘要：{slm.get_stop_loss_summary()}")
