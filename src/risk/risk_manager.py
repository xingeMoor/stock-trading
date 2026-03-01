"""
风险管理核心模块 - Risk Manager
Q 脑量化交易系统的风控中枢

核心功能:
- Kelly 公式仓位计算
- 多层次风险控制
- 实时风险监控
- 交易前风控检查
- 支持 A 股 T+1 和美股 T+0

Author: Q 脑 Risk-Agent
Date: 2026-03-01
"""

import yaml
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

from .position_manager import PositionManager, PositionConfig, Position, PositionType
from .stop_loss import StopLossManager, StopLossConfig, StopLossType


class MarketType(Enum):
    """市场类型"""
    A_SHARE = "A_SHARE"      # A 股 (T+1)
    US_STOCK = "US_STOCK"    # 美股 (T+0)


class RiskLevel(Enum):
    """风险等级"""
    MINIMAL = "minimal"      # 极低风险 (0-20)
    LOW = "low"              # 低风险 (20-40)
    MEDIUM = "medium"        # 中等风险 (40-60)
    HIGH = "high"            # 高风险 (60-80)
    CRITICAL = "critical"    # 严重风险 (80-100)


class DrawdownLevel(Enum):
    """回撤等级"""
    NORMAL = "normal"        # 正常 (0-5%)
    WARNING = "warning"      # 警告 (5-10%)
    DANGER = "danger"        # 危险 (10-15%)
    CRITICAL = "critical"    # 严重 (>15%)


@dataclass
class RiskConfig:
    """风控配置"""
    # Kelly 参数
    kelly_fraction: float = 0.25
    max_position_pct: float = 0.25
    min_position_pct: float = 0.02
    max_positions: int = 20
    max_sector_exposure: float = 0.40
    
    # 止损参数
    fixed_stop_loss_pct: float = 0.08
    fixed_take_profit_pct: float = 0.20
    trailing_stop_pct: float = 0.10
    max_holding_days: int = 30
    
    # 回撤控制
    max_drawdown_pct: float = 0.15
    max_daily_loss_pct: float = 0.03
    max_consecutive_losses: int = 5
    
    # 市场类型
    market_type: MarketType = MarketType.US_STOCK
    
    # 动态调整
    volatility_adjustment: bool = True
    market_regime: str = 'normal'
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'RiskConfig':
        """从 YAML 配置文件加载"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        kelly_cfg = config.get('kelly', {})
        stop_cfg = config.get('stop_loss', {})
        drawdown_cfg = config.get('drawdown', {})
        dynamic_cfg = config.get('dynamic_adjustment', {})
        global_cfg = config.get('global', {})
        
        return cls(
            kelly_fraction=kelly_cfg.get('fraction', 0.25),
            max_position_pct=kelly_cfg.get('max_position_pct', 0.25),
            min_position_pct=kelly_cfg.get('min_position_pct', 0.02),
            max_positions=kelly_cfg.get('max_positions', 20),
            max_sector_exposure=kelly_cfg.get('max_sector_exposure', 0.40),
            fixed_stop_loss_pct=stop_cfg.get('fixed_stop_loss_pct', 0.08),
            fixed_take_profit_pct=stop_cfg.get('fixed_take_profit_pct', 0.20),
            trailing_stop_pct=stop_cfg.get('trailing_stop_pct', 0.10),
            max_holding_days=stop_cfg.get('max_holding_days', 30),
            max_drawdown_pct=global_cfg.get('max_drawdown_pct', 0.15),
            max_daily_loss_pct=global_cfg.get('max_daily_loss_pct', 0.03),
            max_consecutive_losses=drawdown_cfg.get('max_consecutive_losses', 5),
            market_type=MarketType.US_STOCK,
            volatility_adjustment=dynamic_cfg.get('volatility', {}).get('enabled', True),
            market_regime=dynamic_cfg.get('market_regime', {}).get('current', 'normal')
        )


@dataclass
class TradeRequest:
    """交易请求"""
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: int
    price: Optional[float] = None
    order_type: str = 'MARKET'
    market: MarketType = MarketType.US_STOCK
    sector: str = ''
    signal_strength: float = 0.5
    win_rate: float = 0.5
    avg_win: float = 0.1
    avg_loss: float = 0.05


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    allowed: bool
    reason: str
    suggested_quantity: Optional[int] = None
    risk_level: RiskLevel = RiskLevel.LOW
    warnings: List[str] = field(default_factory=list)


class RiskManager:
    """
    风险管理器
    
    Q 脑风控系统的核心，整合仓位管理、止损控制和回撤监控
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        
        # 初始化子模块
        self.position_config = PositionConfig(
            max_position_pct=self.config.max_position_pct,
            kelly_fraction=self.config.kelly_fraction,
            max_positions=self.config.max_positions,
            max_sector_exposure=self.config.max_sector_exposure,
            min_position_pct=self.config.min_position_pct
        )
        self.position_manager = PositionManager(self.position_config)
        
        self.stop_loss_config = StopLossConfig(
            fixed_stop_loss_pct=self.config.fixed_stop_loss_pct,
            fixed_take_profit_pct=self.config.fixed_take_profit_pct,
            trailing_stop_pct=self.config.trailing_stop_pct,
            max_holding_days=self.config.max_holding_days
        )
        self.stop_loss_manager = StopLossManager(self.stop_loss_config)
        
        # 回撤控制状态
        self.initial_capital: float = 0.0
        self.peak_value: float = 0.0
        self.current_value: float = 0.0
        self.current_drawdown: float = 0.0
        self.leverage_ratio: float = 1.0
        
        # 日盈亏追踪
        self.daily_pnl: float = 0.0
        self.daily_start_value: float = 0.0
        self.last_reset_date: Optional[datetime] = None
        
        # 连续亏损追踪
        self.consecutive_losses: int = 0
        self.loss_history: List[Tuple[datetime, float]] = []
        
        # 交易历史
        self.trade_history: List[Dict] = []
        
    def initialize(self, initial_capital: float):
        """初始化风控系统"""
        self.initial_capital = initial_capital
        self.peak_value = initial_capital
        self.current_value = initial_capital
        self.daily_start_value = initial_capital
        self.last_reset_date = datetime.now()
        
        # 更新仓位管理器的组合价值
        self.position_manager.update_portfolio_value(initial_capital, initial_capital)
    
    def update_portfolio_value(self, current_value: float, current_date: Optional[datetime] = None):
        """
        更新组合价值并计算回撤
        
        Args:
            current_value: 当前组合价值
            current_date: 当前日期
        """
        current_date = current_date or datetime.now()
        
        # 检查是否需要重置日盈亏
        if self.last_reset_date and current_date.date() != self.last_reset_date.date():
            self.daily_pnl = 0.0
            self.daily_start_value = self.current_value
            self.last_reset_date = current_date
        
        # 更新价值
        prev_value = self.current_value
        self.current_value = current_value
        
        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # 计算回撤
        self.current_drawdown = (self.peak_value - self.current_value) / self.peak_value
        
        # 计算日盈亏
        self.daily_pnl = current_value - self.daily_start_value
        
        # 更新仓位管理器
        self.position_manager.update_portfolio_value(current_value, current_value * 0.1)  # 假设 10% 现金
    
    # ==================== Kelly 仓位计算 ====================
    
    def calculate_kelly_position(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        signal_strength: float = 1.0,
        volatility: Optional[float] = None
    ) -> float:
        """
        计算 Kelly 最优仓位
        
        Args:
            win_rate: 胜率 (0-1)
            avg_win: 平均盈利比例
            avg_loss: 平均亏损比例
            signal_strength: 信号强度 (0-1)
            volatility: 年化波动率
            
        Returns:
            建议仓位比例 (0-1)
        """
        # 基础 Kelly 计算
        base_kelly = self.position_manager.calculate_kelly_fraction(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss
        )
        
        # 信号强度调整
        adjusted_kelly = base_kelly * signal_strength
        
        # 波动率调整
        if volatility and self.config.volatility_adjustment:
            vol_factor = self._get_volatility_adjustment_factor(volatility)
            adjusted_kelly *= vol_factor
        
        # 市场状态调整
        regime_factor = self._get_market_regime_factor()
        adjusted_kelly *= regime_factor
        
        # 应用回撤调整
        adjusted_kelly *= self.leverage_ratio
        
        # 限制在合理范围
        final_kelly = max(
            self.config.min_position_pct,
            min(adjusted_kelly, self.config.max_position_pct)
        )
        
        return final_kelly
    
    def _get_volatility_adjustment_factor(self, volatility: float) -> float:
        """获取波动率调整因子"""
        if volatility > 0.50:
            return 0.50
        elif volatility > 0.30:
            return 0.75
        return 1.0
    
    def _get_market_regime_factor(self) -> float:
        """获取市场状态调整因子"""
        regime_factors = {
            'normal': 1.0,
            'high_vol': 0.7,
            'crisis': 0.3
        }
        return regime_factors.get(self.config.market_regime, 1.0)
    
    # ==================== 交易前风控检查 ====================
    
    def check_trade(
        self,
        trade_request: TradeRequest
    ) -> RiskCheckResult:
        """
        交易前风控检查
        
        Args:
            trade_request: 交易请求
            
        Returns:
            风控检查结果
        """
        warnings = []
        
        # 1. 检查日亏损限制
        daily_loss_pct = self.daily_pnl / self.daily_start_value if self.daily_start_value > 0 else 0
        if daily_loss_pct <= -self.config.max_daily_loss_pct:
            return RiskCheckResult(
                allowed=False,
                reason=f"触及日亏损限制 (当前：{daily_loss_pct:.2%}, 限制：-{self.config.max_daily_loss_pct:.2%})",
                risk_level=RiskLevel.CRITICAL
            )
        elif daily_loss_pct <= -self.config.max_daily_loss_pct * 0.67:
            warnings.append(f"日亏损接近限制：{daily_loss_pct:.2%}")
        
        # 2. 检查回撤等级
        drawdown_level = self._get_drawdown_level()
        if drawdown_level == DrawdownLevel.CRITICAL:
            return RiskCheckResult(
                allowed=False,
                reason=f"触及最大回撤限制 (当前：{self.current_drawdown:.2%}, 限制：{self.config.max_drawdown_pct:.2%})",
                risk_level=RiskLevel.CRITICAL
            )
        
        # 3. 检查连续亏损
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            return RiskCheckResult(
                allowed=False,
                reason=f"连续亏损次数超限 (当前：{self.consecutive_losses}, 限制：{self.config.max_consecutive_losses})",
                risk_level=RiskLevel.HIGH
            )
        
        # 4. 计算 Kelly 最优仓位
        kelly_pct = self.calculate_kelly_position(
            win_rate=trade_request.win_rate,
            avg_win=trade_request.avg_win,
            avg_loss=trade_request.avg_loss,
            signal_strength=trade_request.signal_strength
        )
        
        # 5. 检查仓位限制
        proposed_weight = (trade_request.quantity * (trade_request.price or 0)) / self.current_value
        allowed, reason = self.position_manager.check_position_limit(
            symbol=trade_request.symbol,
            proposed_weight=proposed_weight,
            sector=trade_request.sector
        )
        
        if not allowed:
            return RiskCheckResult(
                allowed=False,
                reason=reason,
                risk_level=RiskLevel.MEDIUM,
                warnings=warnings
            )
        
        # 6. 检查市场交易时间 (T+1/T+0 规则)
        if not self._check_trading_time(trade_request.market, trade_request.action):
            return RiskCheckResult(
                allowed=False,
                reason=f"非交易时间或违反 T+1 规则 ({trade_request.market.value})",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 7. 计算建议数量
        suggested_quantity = self._calculate_suggested_quantity(
            symbol=trade_request.symbol,
            kelly_pct=kelly_pct,
            current_price=trade_request.price or 0
        )
        
        # 8. 确定风险等级
        risk_level = self._calculate_risk_level()
        
        return RiskCheckResult(
            allowed=True,
            reason="通过风控检查",
            suggested_quantity=suggested_quantity,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def _check_trading_time(self, market: MarketType, action: str) -> bool:
        """检查交易时间和 T+1/T+0 规则"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        current_time = hour * 100 + minute
        
        if market == MarketType.A_SHARE:
            # A 股交易时间：9:30-11:30, 13:00-15:00
            morning = 930 <= current_time <= 1130
            afternoon = 1300 <= current_time <= 1500
            
            if not (morning or afternoon):
                return False
            
            # T+1 检查 (简化版：检查是否是当日买入的持仓)
            if action == 'sell':
                # 实际应用中需要检查持仓的买入日期
                pass
                
        elif market == MarketType.US_STOCK:
            # 美股交易时间 (北京时间): 21:30-04:00
            if hour >= 21 or hour < 4:
                return True
            # 夏令时调整
            if hour >= 20 or hour < 3:
                return True
            
            return False
        
        return True
    
    def _calculate_suggested_quantity(
        self,
        symbol: str,
        kelly_pct: float,
        current_price: float
    ) -> int:
        """计算建议交易数量"""
        if current_price <= 0:
            return 0
        
        # 检查当前持仓
        current_pos = self.position_manager.positions.get(symbol)
        current_weight = current_pos.weight if current_pos else 0.0
        
        # 可增加的仓位
        available_weight = kelly_pct - current_weight
        
        if available_weight <= 0:
            return 0
        
        # 计算价值
        trade_value = available_weight * self.current_value
        
        # 计算数量
        quantity = int(trade_value / current_price)
        
        # 应用最小交易单位 (A 股 100 股，美股 1 股)
        if self.config.market_type == MarketType.A_SHARE:
            quantity = (quantity // 100) * 100
        
        return max(0, quantity)
    
    # ==================== 回撤控制 ====================
    
    def _get_drawdown_level(self) -> DrawdownLevel:
        """获取当前回撤等级"""
        if self.current_drawdown < 0.05:
            return DrawdownLevel.NORMAL
        elif self.current_drawdown < 0.10:
            return DrawdownLevel.WARNING
        elif self.current_drawdown < 0.15:
            return DrawdownLevel.DANGER
        else:
            return DrawdownLevel.CRITICAL
    
    def _update_leverage_ratio(self):
        """根据回撤更新杠杆比率"""
        drawdown_level = self._get_drawdown_level()
        
        if drawdown_level == DrawdownLevel.NORMAL:
            self.leverage_ratio = 1.0
        elif drawdown_level == DrawdownLevel.WARNING:
            self.leverage_ratio = 0.8
        elif drawdown_level == DrawdownLevel.DANGER:
            self.leverage_ratio = 0.5
        else:  # CRITICAL
            self.leverage_ratio = 0.25
    
    def _calculate_risk_level(self) -> RiskLevel:
        """计算综合风险等级"""
        score = 0.0
        
        # 回撤评分 (40%)
        drawdown_score = min(100, (self.current_drawdown / self.config.max_drawdown_pct) * 100)
        score += drawdown_score * 0.4
        
        # 日盈亏评分 (30%)
        daily_pnl_pct = self.daily_pnl / self.daily_start_value if self.daily_start_value > 0 else 0
        daily_score = max(0, min(100, (-daily_pnl_pct / self.config.max_daily_loss_pct) * 100))
        score += daily_score * 0.3
        
        # 集中度评分 (20%)
        concentration = self.position_manager.calculate_concentration_metrics()
        hhi_score = min(100, (concentration['hhi'] / 0.25) * 100)
        score += hhi_score * 0.2
        
        # 连续亏损评分 (10%)
        loss_score = min(100, (self.consecutive_losses / self.config.max_consecutive_losses) * 100)
        score += loss_score * 0.1
        
        # 转换为风险等级
        if score < 20:
            return RiskLevel.MINIMAL
        elif score < 40:
            return RiskLevel.LOW
        elif score < 60:
            return RiskLevel.MEDIUM
        elif score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    # ==================== 持仓管理 ====================
    
    def add_position(
        self,
        symbol: str,
        quantity: int,
        price: float,
        sector: str,
        market: MarketType
    ):
        """添加持仓"""
        market_value = quantity * price
        
        # 计算权重
        weight = market_value / self.current_value if self.current_value > 0 else 0
        
        position = Position(
            symbol=symbol,
            quantity=quantity,
            avg_price=price,
            current_price=price,
            market_value=market_value,
            weight=weight,
            sector=sector,
            position_type=PositionType.LONG
        )
        
        self.position_manager.add_position(position)
        
        # 创建止损
        self.stop_loss_manager.create_stop_loss(
            symbol=symbol,
            entry_price=price,
            entry_date=datetime.now(),
            stop_type=StopLossType.FIXED_PERCENT
        )
        
        # 记录交易
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': 'buy',
            'quantity': quantity,
            'price': price,
            'market': market.value
        })
    
    def remove_position(self, symbol: str, pnl_pct: float):
        """移除持仓"""
        self.position_manager.remove_position(symbol)
        self.stop_loss_manager.cancel_stop_loss(symbol)
        
        # 更新连续亏损计数
        if pnl_pct < 0:
            self.consecutive_losses += 1
            self.loss_history.append((datetime.now(), pnl_pct))
        else:
            self.consecutive_losses = 0
        
        # 清理旧的亏损记录
        self._cleanup_loss_history()
    
    def _cleanup_loss_history(self):
        """清理超过统计窗口的亏损记录"""
        window = timedelta(days=self.config.max_consecutive_losses * 2)
        cutoff = datetime.now() - window
        self.loss_history = [(d, p) for d, p in self.loss_history if d > cutoff]
    
    # ==================== 价格更新和止损检查 ====================
    
    def update_price(
        self,
        symbol: str,
        current_price: float,
        current_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        更新价格并检查止损
        
        Returns:
            如果触发止损，返回触发信息
        """
        current_date = current_date or datetime.now()
        
        # 更新持仓价格
        if symbol in self.position_manager.positions:
            position = self.position_manager.positions[symbol]
            position.current_price = current_price
            position.market_value = position.quantity * current_price
        
        # 检查止损
        trigger_info = self.stop_loss_manager.update_price(
            symbol=symbol,
            current_price=current_price,
            current_date=current_date
        )
        
        if trigger_info:
            # 记录止损触发
            self.trade_history.append({
                'timestamp': current_date,
                'symbol': symbol,
                'action': 'stop_loss',
                'reason': trigger_info['reason'],
                'price': trigger_info['trigger_price'],
                'pnl_pct': trigger_info['pnl_pct']
            })
        
        return trigger_info
    
    # ==================== 组合再平衡 ====================
    
    def rebalance_portfolio(self) -> List[Dict]:
        """
        组合再平衡
        
        Returns:
            交易指令列表
        """
        # 获取当前风险等级
        risk_level = self._calculate_risk_level()
        
        # 根据风险等级调整目标仓位
        target_scale = {
            RiskLevel.MINIMAL: 1.0,
            RiskLevel.LOW: 0.95,
            RiskLevel.MEDIUM: 0.80,
            RiskLevel.HIGH: 0.60,
            RiskLevel.CRITICAL: 0.40
        }.get(risk_level, 1.0)
        
        # 计算目标权重
        target_weights = {}
        for symbol, position in self.position_manager.positions.items():
            target_weight = position.weight * target_scale
            target_weights[symbol] = target_weight
        
        # 生成再平衡交易
        trades = self.position_manager.rebalance_portfolio(target_weights)
        
        return trades
    
    # ==================== 风险报告 ====================
    
    def get_risk_report(self) -> Dict:
        """获取完整风险报告"""
        position_summary = self.position_manager.get_risk_summary()
        stop_loss_summary = self.stop_loss_manager.get_stop_loss_summary()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': self.current_value,
            'initial_capital': self.initial_capital,
            'total_pnl': self.current_value - self.initial_capital,
            'total_pnl_pct': (self.current_value - self.initial_capital) / self.initial_capital if self.initial_capital > 0 else 0,
            
            'drawdown': {
                'current': self.current_drawdown,
                'peak_value': self.peak_value,
                'level': self._get_drawdown_level().value,
                'leverage_ratio': self.leverage_ratio
            },
            
            'daily_pnl': {
                'pnl': self.daily_pnl,
                'pnl_pct': self.daily_pnl / self.daily_start_value if self.daily_start_value > 0 else 0,
                'start_value': self.daily_start_value
            },
            
            'consecutive_losses': self.consecutive_losses,
            'risk_level': self._calculate_risk_level().value,
            
            'position_summary': position_summary,
            'stop_loss_summary': stop_loss_summary,
            
            'config': {
                'max_drawdown': self.config.max_drawdown_pct,
                'max_daily_loss': self.config.max_daily_loss_pct,
                'max_position': self.config.max_position_pct,
                'kelly_fraction': self.config.kelly_fraction,
                'market_type': self.config.market_type.value
            }
        }
    
    def get_risk_summary_string(self) -> str:
        """获取风险摘要字符串"""
        report = self.get_risk_report()
        
        summary = f"""
【Q 脑风控日报】{datetime.now().strftime('%Y-%m-%d %H:%M')}

💰 组合价值：{report['portfolio_value']:,.2f}
📈 总盈亏：{report['total_pnl']:,.2f} ({report['total_pnl_pct']:.2%})

📉 回撤监控:
  当前回撤：{report['drawdown']['current']:.2%}
  回撤等级：{report['drawdown']['level'].upper()}
  杠杆比率：{report['drawdown']['leverage_ratio']:.0%}

📊 日盈亏：{report['daily_pnl']['pnl']:,.2f} ({report['daily_pnl']['pnl_pct']:.2%})

⚠️ 风险等级：{report['risk_level'].upper()}
🔴 连续亏损：{report['consecutive_losses']} 次

📦 持仓数量：{report['position_summary']['num_positions']}
💵 现金占比：{report['position_summary']['cash_weight']:.1%}
"""
        return summary


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建风控管理器
    config = RiskConfig(
        max_position_pct=0.20,
        kelly_fraction=0.25,
        max_drawdown_pct=0.15,
        market_type=MarketType.US_STOCK
    )
    rm = RiskManager(config)
    
    # 初始化
    rm.initialize(1000000)  # 100 万初始资金
    
    # 计算 Kelly 仓位
    kelly = rm.calculate_kelly_position(
        win_rate=0.55,
        avg_win=0.12,
        avg_loss=0.06,
        signal_strength=0.8
    )
    print(f"Kelly 最优仓位：{kelly:.2%}")
    
    # 交易前检查
    trade_request = TradeRequest(
        symbol="AAPL",
        action='buy',
        quantity=100,
        price=150.0,
        sector='Technology',
        signal_strength=0.8,
        win_rate=0.55,
        avg_win=0.12,
        avg_loss=0.06
    )
    
    result = rm.check_trade(trade_request)
    print(f"\n交易检查：{'允许' if result.allowed else '拒绝'}")
    print(f"原因：{result.reason}")
    if result.suggested_quantity:
        print(f"建议数量：{result.suggested_quantity}")
    
    # 获取风险报告
    print(f"\n{rm.get_risk_summary_string()}")
