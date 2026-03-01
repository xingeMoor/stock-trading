"""
仓位管理模块 - Position Manager
负责计算最优仓位、控制集中度和动态调整

核心功能:
- Kelly公式计算最优仓位
- 最大仓位限制
- 集中度控制
- 动态仓位调整
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PositionType(Enum):
    """仓位类型"""
    LONG = "long"
    SHORT = "short"


@dataclass
class PositionConfig:
    """仓位配置"""
    max_position_pct: float = 0.25  # 单个标的最大仓位 25%
    max_total_exposure: float = 1.0  # 最大总敞口 100%
    max_sector_exposure: float = 0.4  # 最大行业敞口 40%
    kelly_fraction: float = 0.25  # Kelly分数 (0.25 = 1/4 Kelly)
    min_position_pct: float = 0.02  # 最小仓位 2%
    max_positions: int = 20  # 最大持仓数量


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    market_value: float
    weight: float  # 占组合权重
    sector: str
    position_type: PositionType


class PositionManager:
    """
    仓位管理器
    
    使用Kelly公式和现代投资组合理论进行仓位管理
    """
    
    def __init__(self, config: Optional[PositionConfig] = None):
        self.config = config or PositionConfig()
        self.positions: Dict[str, Position] = {}
        self.cash_balance: float = 0.0
        self.total_portfolio_value: float = 0.0
        
    def update_portfolio_value(self, total_value: float, cash: float):
        """更新组合总值和现金"""
        self.total_portfolio_value = total_value
        self.cash_balance = cash
        
    def add_position(self, position: Position):
        """添加或更新持仓"""
        self.positions[position.symbol] = position
        
    def remove_position(self, symbol: str):
        """移除持仓"""
        if symbol in self.positions:
            del self.positions[symbol]
    
    # ==================== Kelly公式计算 ====================
    
    def calculate_kelly_fraction(
        self, 
        win_rate: float, 
        avg_win: float, 
        avg_loss: float
    ) -> float:
        """
        计算Kelly最优仓位比例
        
        Kelly公式: f* = (p * b - q) / b
        其中:
        - p = 胜率
        - q = 1 - p = 败率
        - b = 盈亏比 = 平均盈利 / 平均亏损
        
        Args:
            win_rate: 胜率 (0-1)
            avg_win: 平均盈利比例 (如 0.15 表示 15%)
            avg_loss: 平均亏损比例 (如 0.08 表示 8%)
            
        Returns:
            Kelly最优仓位比例 (0-1)
        """
        if avg_loss <= 0:
            return 0.0
            
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss
        
        # Kelly公式
        kelly = (p * b - q) / b
        
        # 应用Kelly分数 (降低风险)
        adjusted_kelly = kelly * self.config.kelly_fraction
        
        # 限制在合理范围
        kelly_pct = max(0.0, min(adjusted_kelly, self.config.max_position_pct))
        
        return kelly_pct
    
    def calculate_kelly_from_returns(
        self,
        returns: List[float]
    ) -> float:
        """
        从历史收益率序列计算Kelly比例
        
        Args:
            returns: 历史收益率列表 (如 [0.05, -0.03, 0.08, ...])
            
        Returns:
            Kelly最优仓位比例
        """
        if not returns or len(returns) < 10:
            return 0.0
            
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]
        
        if not wins or not losses:
            return 0.0
            
        win_rate = len(wins) / len(returns)
        avg_win = sum(wins) / len(wins)
        avg_loss = abs(sum(losses) / len(losses))
        
        return self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
    
    # ==================== 仓位限制检查 ====================
    
    def check_position_limit(
        self, 
        symbol: str, 
        proposed_weight: float,
        sector: str
    ) -> Tuple[bool, str]:
        """
        检查仓位是否超出限制
        
        Returns:
            (是否允许, 原因)
        """
        # 检查单个标的仓位限制
        if proposed_weight > self.config.max_position_pct:
            return False, f"超出单标的最大仓位限制 ({self.config.max_position_pct:.1%})"
        
        # 检查最小仓位
        if proposed_weight < self.config.min_position_pct and proposed_weight > 0:
            return False, f"低于最小仓位限制 ({self.config.min_position_pct:.1%})"
        
        # 检查行业集中度
        sector_exposure = self._calculate_sector_exposure(sector)
        if sector_exposure + proposed_weight > self.config.max_sector_exposure:
            return False, f"超出行业最大敞口限制 ({self.config.max_sector_exposure:.1%})"
        
        # 检查总仓位
        total_exposure = self._calculate_total_exposure()
        if total_exposure + proposed_weight > self.config.max_total_exposure:
            return False, f"超出总敞口限制 ({self.config.max_total_exposure:.1%})"
        
        # 检查持仓数量
        if symbol not in self.positions and len(self.positions) >= self.config.max_positions:
            return False, f"超出最大持仓数量限制 ({self.config.max_positions})"
        
        return True, "通过检查"
    
    def _calculate_sector_exposure(self, sector: str) -> float:
        """计算行业总敞口"""
        total = 0.0
        for pos in self.positions.values():
            if pos.sector == sector:
                total += pos.weight
        return total
    
    def _calculate_total_exposure(self) -> float:
        """计算总敞口"""
        return sum(pos.weight for pos in self.positions.values())
    
    # ==================== 集中度控制 ====================
    
    def calculate_concentration_metrics(self) -> Dict[str, float]:
        """
        计算集中度指标
        
        Returns:
            集中度指标字典
        """
        if not self.positions:
            return {
                'hhi': 0.0,
                'top5_concentration': 0.0,
                'effective_positions': 0.0,
                'sector_concentration': 0.0
            }
        
        weights = [pos.weight for pos in self.positions.values()]
        
        # HHI指数 (Herfindahl-Hirschman Index)
        hhi = sum(w ** 2 for w in weights)
        
        # 前5大持仓集中度
        sorted_weights = sorted(weights, reverse=True)
        top5_concentration = sum(sorted_weights[:5])
        
        # 有效持仓数量 (1/HHI)
        effective_positions = 1.0 / hhi if hhi > 0 else 0.0
        
        # 行业集中度 (最大行业权重)
        sector_weights = {}
        for pos in self.positions.values():
            sector_weights[pos.sector] = sector_weights.get(pos.sector, 0) + pos.weight
        sector_concentration = max(sector_weights.values()) if sector_weights else 0.0
        
        return {
            'hhi': hhi,
            'top5_concentration': top5_concentration,
            'effective_positions': effective_positions,
            'sector_concentration': sector_concentration
        }
    
    def check_concentration_risk(self) -> Dict[str, bool]:
        """
        检查集中度风险
        
        Returns:
            风险检查结果
        """
        metrics = self.calculate_concentration_metrics()
        
        return {
            'hhi_risk': metrics['hhi'] > 0.25,  # HHI > 0.25 表示集中度高
            'top5_risk': metrics['top5_concentration'] > 0.6,  # 前5大 > 60%
            'diversification_risk': metrics['effective_positions'] < 5,  # 有效持仓 < 5
            'sector_risk': metrics['sector_concentration'] > self.config.max_sector_exposure
        }
    
    # ==================== 动态仓位调整 ====================
    
    def calculate_dynamic_position_size(
        self,
        symbol: str,
        signal_strength: float,
        volatility: float,
        market_regime: str = 'normal'
    ) -> float:
        """
        计算动态仓位大小
        
        Args:
            symbol: 标的代码
            signal_strength: 信号强度 (-1 到 1)
            volatility: 波动率 (年化)
            market_regime: 市场状态 ('normal', 'high_vol', 'crisis')
            
        Returns:
            建议仓位比例
        """
        # 基础仓位 (基于Kelly)
        base_position = self.config.max_position_pct * abs(signal_strength)
        
        # 波动率调整 (高波动降低仓位)
        vol_adjustment = 1.0
        if volatility > 0.5:  # 年化波动率 > 50%
            vol_adjustment = 0.5
        elif volatility > 0.3:  # 年化波动率 > 30%
            vol_adjustment = 0.75
        
        # 市场状态调整
        regime_adjustment = {
            'normal': 1.0,
            'high_vol': 0.7,
            'crisis': 0.3
        }.get(market_regime, 1.0)
        
        # 计算最终仓位
        position_size = base_position * vol_adjustment * regime_adjustment
        
        # 应用限制
        position_size = max(0, min(position_size, self.config.max_position_pct))
        
        # 检查仓位限制
        allowed, reason = self.check_position_limit(
            symbol, 
            position_size,
            self.positions.get(symbol, Position('', 0, 0, 0, 0, 0, '', PositionType.LONG)).sector
        )
        
        if not allowed:
            # 如果超限，返回允许的最大值
            current_weight = self.positions.get(symbol, Position('', 0, 0, 0, 0, 0, '', PositionType.LONG)).weight
            max_allowed = self.config.max_position_pct - current_weight
            position_size = max(0, max_allowed)
        
        return position_size
    
    def rebalance_portfolio(
        self,
        target_weights: Dict[str, float]
    ) -> List[Dict]:
        """
        再平衡组合到目标权重
        
        Args:
            target_weights: 目标权重字典 {symbol: weight}
            
        Returns:
            交易指令列表
        """
        trades = []
        
        for symbol, target_weight in target_weights.items():
            current_pos = self.positions.get(symbol)
            current_weight = current_pos.weight if current_pos else 0.0
            
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.001:  # 差异超过 0.1% 才交易
                trade_value = weight_diff * self.total_portfolio_value
                trades.append({
                    'symbol': symbol,
                    'action': 'buy' if weight_diff > 0 else 'sell',
                    'weight_change': weight_diff,
                    'trade_value': trade_value
                })
        
        return trades
    
    def get_risk_summary(self) -> Dict:
        """获取仓位风险摘要"""
        concentration = self.calculate_concentration_metrics()
        concentration_risks = self.check_concentration_risk()
        
        return {
            'total_exposure': self._calculate_total_exposure(),
            'num_positions': len(self.positions),
            'cash_weight': self.cash_balance / self.total_portfolio_value if self.total_portfolio_value > 0 else 0,
            'concentration_metrics': concentration,
            'concentration_risks': concentration_risks,
            'config': {
                'max_position_pct': self.config.max_position_pct,
                'max_total_exposure': self.config.max_total_exposure,
                'max_sector_exposure': self.config.max_sector_exposure,
                'kelly_fraction': self.config.kelly_fraction
            }
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建仓位管理器
    config = PositionConfig(
        max_position_pct=0.20,
        kelly_fraction=0.25
    )
    pm = PositionManager(config)
    
    # 计算Kelly仓位
    kelly = pm.calculate_kelly_fraction(
        win_rate=0.55,
        avg_win=0.12,
        avg_loss=0.06
    )
    print(f"Kelly最优仓位：{kelly:.2%}")
    
    # 从历史收益计算
    returns = [0.05, -0.03, 0.08, 0.02, -0.04, 0.06, 0.01, -0.02, 0.07, 0.03]
    kelly_hist = pm.calculate_kelly_from_returns(returns)
    print(f"历史Kelly仓位：{kelly_hist:.2%}")
