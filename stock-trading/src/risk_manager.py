"""
风险管理系统 - 三层风控体系
1. 盘前风控 (Pre-market)
2. 持仓风控 (In-position)  
3. 日终风控 (Post-daily)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"           # 绿色 - 正常
    MEDIUM = "medium"     # 黄色 - 警告
    HIGH = "high"         # 橙色 - 危险
    CRITICAL = "critical" # 红色 - 紧急


@dataclass
class RiskCheck:
    """风险检查结果"""
    check_name: str
    passed: bool
    level: RiskLevel
    message: str
    value: float
    threshold: float
    action: str  # 建议操作


class RiskManager:
    """
    风险管理器
    
    核心功能:
    - 盘前风险扫描
    - 实时持仓监控
    - 日终风险评估
    - 自动风控触发
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.risk_logs = []
        
    def _default_config(self) -> Dict[str, Any]:
        """默认风控配置"""
        return {
            # 仓位限制
            'max_single_position_pct': 0.20,      # 单票最大20%
            'max_total_position_pct': 0.90,       # 总仓位最大90%
            'min_cash_ratio': 0.10,               # 最低现金10%
            
            # 止损止盈
            'stop_loss_pct': 0.08,                # 止损-8%
            'take_profit_pct': 0.15,              # 止盈+15%
            'trailing_stop_pct': 0.05,            # 移动止损5%
            
            # 波动率控制
            'max_daily_volatility': 0.05,         # 单日最大波动5%
            'max_portfolio_volatility': 0.25,     # 组合年化波动率最大25%
            
            # 集中度限制
            'max_sector_concentration': 0.40,     # 单一行业最大40%
            'max_correlated_positions': 3,        # 相关性高的股票最多3只
            
            # 流动性要求
            'min_daily_volume': 10000000,         # 最小日成交额1000万
            'max_position_size_vs_volume': 0.01,  # 持仓不超过日成交量1%
            
            # 回撤控制
            'max_drawdown_warning': 0.10,         # 回撤10%警告
            'max_drawdown_limit': 0.15,           # 回撤15%强制减仓
            'max_drawdown_stop': 0.20,            # 回撤20%停止交易
        }
    
    # ============ 第一层：盘前风控 ============
    
    def pre_market_check(self, portfolio: Dict, market_data: Dict) -> List[RiskCheck]:
        """
        盘前风险检查
        在每天开盘前执行
        """
        checks = []
        
        # 1. 市场整体风险
        checks.append(self._check_market_risk(market_data))
        
        # 2. 账户状态检查
        checks.append(self._check_account_status(portfolio))
        
        # 3. 隔夜风险检查
        checks.append(self._check_overnight_risk(portfolio, market_data))
        
        # 4. 新闻事件检查
        checks.append(self._check_news_risk(market_data))
        
        return checks
    
    def _check_market_risk(self, market_data: Dict) -> RiskCheck:
        """检查市场风险"""
        vix = market_data.get('vix', 20)  # 恐慌指数
        
        if vix > 30:
            return RiskCheck(
                check_name="市场恐慌指数",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"VIX高达{vix}，市场极度恐慌",
                value=vix,
                threshold=30,
                action="暂停开仓，考虑对冲"
            )
        elif vix > 25:
            return RiskCheck(
                check_name="市场恐慌指数",
                passed=True,
                level=RiskLevel.MEDIUM,
                message=f"VIX为{vix}，市场波动较大",
                value=vix,
                threshold=25,
                action="降低仓位，谨慎操作"
            )
        else:
            return RiskCheck(
                check_name="市场恐慌指数",
                passed=True,
                level=RiskLevel.LOW,
                message=f"VIX正常 ({vix})",
                value=vix,
                threshold=30,
                action="正常交易"
            )
    
    def _check_account_status(self, portfolio: Dict) -> RiskCheck:
        """检查账户状态"""
        total_value = portfolio.get('total_value', 0)
        initial_value = portfolio.get('initial_value', total_value)
        
        if initial_value > 0:
            drawdown = (initial_value - total_value) / initial_value
        else:
            drawdown = 0
        
        max_dd = self.config['max_drawdown_stop']
        warning_dd = self.config['max_drawdown_warning']
        
        if drawdown > max_dd:
            return RiskCheck(
                check_name="账户回撤",
                passed=False,
                level=RiskLevel.CRITICAL,
                message=f"回撤{drawdown*100:.1f}%超过限制{max_dd*100:.0f}%",
                value=drawdown,
                threshold=max_dd,
                action="立即停止所有交易"
            )
        elif drawdown > warning_dd:
            return RiskCheck(
                check_name="账户回撤",
                passed=True,
                level=RiskLevel.MEDIUM,
                message=f"回撤{drawdown*100:.1f}%接近警告线",
                value=drawdown,
                threshold=warning_dd,
                action="降低仓位，加强监控"
            )
        else:
            return RiskCheck(
                check_name="账户回撤",
                passed=True,
                level=RiskLevel.LOW,
                message=f"回撤正常 ({drawdown*100:.1f}%)",
                value=drawdown,
                threshold=warning_dd,
                action="正常交易"
            )
    
    def _check_overnight_risk(self, portfolio: Dict, market_data: Dict) -> RiskCheck:
        """检查隔夜风险"""
        # 检查是否有重大隔夜变动
        overnight_changes = market_data.get('overnight_changes', [])
        
        significant_moves = [
            c for c in overnight_changes 
            if abs(c.get('change_pct', 0)) > 0.05
        ]
        
        if len(significant_moves) > 3:
            return RiskCheck(
                check_name="隔夜大幅波动",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"{len(significant_moves)}只股票隔夜波动超5%",
                value=len(significant_moves),
                threshold=3,
                action="开盘后观察再决策"
            )
        else:
            return RiskCheck(
                check_name="隔夜大幅波动",
                passed=True,
                level=RiskLevel.LOW,
                message="隔夜波动正常",
                value=len(significant_moves),
                threshold=3,
                action="正常交易"
            )
    
    def _check_news_risk(self, market_data: Dict) -> RiskCheck:
        """检查新闻风险"""
        risk_events = market_data.get('risk_events', [])
        
        high_impact = [e for e in risk_events if e.get('impact') == 'high']
        
        if high_impact:
            return RiskCheck(
                check_name="重大新闻事件",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"有{len(high_impact)}个高影响事件",
                value=len(high_impact),
                threshold=0,
                action="关注事件进展，灵活应对"
            )
        else:
            return RiskCheck(
                check_name="重大新闻事件",
                passed=True,
                level=RiskLevel.LOW,
                message="无重大风险事件",
                value=0,
                threshold=0,
                action="正常交易"
            )
    
    # ============ 第二层：持仓风控 ============
    
    def position_risk_check(self, symbol: str, position: Dict, 
                           current_price: float, market_data: Dict) -> List[RiskCheck]:
        """
        持仓风险检查
        对每个持仓实时监控
        """
        checks = []
        
        # 1. 止损检查
        checks.append(self._check_stop_loss(symbol, position, current_price))
        
        # 2. 止盈检查
        checks.append(self._check_take_profit(symbol, position, current_price))
        
        # 3. 移动止损
        checks.append(self._check_trailing_stop(symbol, position, current_price))
        
        # 4. 波动率检查
        checks.append(self._check_volatility(symbol, current_price, market_data))
        
        return checks
    
    def _check_stop_loss(self, symbol: str, position: Dict, current_price: float) -> RiskCheck:
        """检查止损"""
        avg_cost = position.get('avg_cost', current_price)
        if avg_cost <= 0:
            return RiskCheck(
                check_name=f"{symbol} 止损",
                passed=True, level=RiskLevel.LOW,
                message="无持仓", value=0, threshold=0, action="-"
            )
        
        loss_pct = (current_price - avg_cost) / avg_cost
        stop_level = -self.config['stop_loss_pct']
        
        if loss_pct <= stop_level:
            return RiskCheck(
                check_name=f"{symbol} 止损",
                passed=False,
                level=RiskLevel.CRITICAL,
                message=f"亏损{loss_pct*100:.1f}%触及止损线",
                value=loss_pct,
                threshold=stop_level,
                action="立即平仓止损"
            )
        elif loss_pct <= stop_level * 0.7:
            return RiskCheck(
                check_name=f"{symbol} 止损",
                passed=True,
                level=RiskLevel.MEDIUM,
                message=f"亏损{loss_pct*100:.1f}%接近止损线",
                value=loss_pct,
                threshold=stop_level,
                action="密切关注，准备止损"
            )
        else:
            return RiskCheck(
                check_name=f"{symbol} 止损",
                passed=True,
                level=RiskLevel.LOW,
                message=f"亏损可控 ({loss_pct*100:.1f}%)",
                value=loss_pct,
                threshold=stop_level,
                action="持有"
            )
    
    def _check_take_profit(self, symbol: str, position: Dict, current_price: float) -> RiskCheck:
        """检查止盈"""
        avg_cost = position.get('avg_cost', current_price)
        if avg_cost <= 0:
            return RiskCheck(
                check_name=f"{symbol} 止盈",
                passed=True, level=RiskLevel.LOW,
                message="无持仓", value=0, threshold=0, action="-"
            )
        
        profit_pct = (current_price - avg_cost) / avg_cost
        target = self.config['take_profit_pct']
        
        if profit_pct >= target:
            return RiskCheck(
                check_name=f"{symbol} 止盈",
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"盈利{profit_pct*100:.1f}%达到目标",
                value=profit_pct,
                threshold=target,
                action="考虑部分止盈"
            )
        else:
            return RiskCheck(
                check_name=f"{symbol} 止盈",
                passed=True,
                level=RiskLevel.LOW,
                message=f"盈利{profit_pct*100:.1f}%",
                value=profit_pct,
                threshold=target,
                action="持有观望"
            )
    
    def _check_trailing_stop(self, symbol: str, position: Dict, current_price: float) -> RiskCheck:
        """检查移动止损"""
        highest_price = position.get('highest_price', current_price)
        
        if highest_price > 0:
            pullback = (highest_price - current_price) / highest_price
            limit = self.config['trailing_stop_pct']
            
            if pullback >= limit:
                return RiskCheck(
                    check_name=f"{symbol} 移动止损",
                    passed=False,
                    level=RiskLevel.HIGH,
                    message=f"从高点回落{pullback*100:.1f}%",
                    value=pullback,
                    threshold=limit,
                    action="触发移动止损，平仓"
                )
        
        return RiskCheck(
            check_name=f"{symbol} 移动止损",
            passed=True,
            level=RiskLevel.LOW,
            message="未触发",
            value=0,
            threshold=self.config['trailing_stop_pct'],
            action="持有"
        )
    
    def _check_volatility(self, symbol: str, current_price: float, market_data: Dict) -> RiskCheck:
        """检查波动率"""
        daily_change = market_data.get('daily_change', 0)
        limit = self.config['max_daily_volatility']
        
        if abs(daily_change) > limit:
            return RiskCheck(
                check_name=f"{symbol} 日波动",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"日内波动{daily_change*100:.1f}%异常",
                value=daily_change,
                threshold=limit,
                action="考虑减仓或对冲"
            )
        else:
            return RiskCheck(
                check_name=f"{symbol} 日波动",
                passed=True,
                level=RiskLevel.LOW,
                message=f"波动正常 ({daily_change*100:.1f}%)",
                value=daily_change,
                threshold=limit,
                action="正常"
            )
    
    # ============ 第三层：日终风控 ============
    
    def post_daily_check(self, portfolio: Dict, trades: List[Dict]) -> List[RiskCheck]:
        """
        日终风险检查
        收盘后执行，评估当日表现和风险状况
        """
        checks = []
        
        # 1. 日收益检查
        checks.append(self._check_daily_pnl(portfolio))
        
        # 2. 交易频率检查
        checks.append(self._check_trading_frequency(trades))
        
        # 3. 集中度检查
        checks.append(self._check_concentration(portfolio))
        
        # 4. 流动性检查
        checks.append(self._check_liquidity(portfolio))
        
        return checks
    
    def _check_daily_pnl(self, portfolio: Dict) -> RiskCheck:
        """检查日收益"""
        daily_return = portfolio.get('daily_return', 0)
        
        if daily_return < -0.03:  # 单日亏损超3%
            return RiskCheck(
                check_name="日收益",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"单日亏损{daily_return*100:.1f}%",
                value=daily_return,
                threshold=-0.03,
                action="复盘原因，明日谨慎"
            )
        else:
            return RiskCheck(
                check_name="日收益",
                passed=True,
                level=RiskLevel.LOW,
                message=f"日收益正常 ({daily_return*100:.1f}%)",
                value=daily_return,
                threshold=-0.03,
                action="正常"
            )
    
    def _check_trading_frequency(self, trades: List[Dict]) -> RiskCheck:
        """检查交易频率"""
        if len(trades) > 10:  # 单日交易超10次
            return RiskCheck(
                check_name="交易频率",
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"单日交易{len(trades)}次过于频繁",
                value=len(trades),
                threshold=10,
                action="减少过度交易"
            )
        else:
            return RiskCheck(
                check_name="交易频率",
                passed=True,
                level=RiskLevel.LOW,
                message=f"交易频率正常 ({len(trades)}次)",
                value=len(trades),
                threshold=10,
                action="正常"
            )
    
    def _check_concentration(self, portfolio: Dict) -> RiskCheck:
        """检查集中度"""
        positions = portfolio.get('positions', {})
        total_value = portfolio.get('total_value', 1)
        
        if not positions:
            return RiskCheck(
                check_name="持仓集中度",
                passed=True, level=RiskLevel.LOW,
                message="无持仓", value=0, threshold=0.2, action="-"
            )
        
        max_position = max(
            p.get('value', 0) for p in positions.values()
        ) / total_value
        
        limit = self.config['max_single_position_pct']
        
        if max_position > limit:
            return RiskCheck(
                check_name="持仓集中度",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"单票占比{max_position*100:.1f}%过高",
                value=max_position,
                threshold=limit,
                action="明日减仓分散"
            )
        else:
            return RiskCheck(
                check_name="持仓集中度",
                passed=True,
                level=RiskLevel.LOW,
                message=f"持仓分散 ({max_position*100:.1f}%)",
                value=max_position,
                threshold=limit,
                action="正常"
            )
    
    def _check_liquidity(self, portfolio: Dict) -> RiskCheck:
        """检查流动性"""
        cash = portfolio.get('cash', 0)
        total = portfolio.get('total_value', 1)
        cash_ratio = cash / total if total > 0 else 0
        
        min_ratio = self.config['min_cash_ratio']
        
        if cash_ratio < min_ratio:
            return RiskCheck(
                check_name="现金比例",
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"现金比例{cash_ratio*100:.1f}%过低",
                value=cash_ratio,
                threshold=min_ratio,
                action="保留更多现金"
            )
        else:
            return RiskCheck(
                check_name="现金比例",
                passed=True,
                level=RiskLevel.LOW,
                message=f"现金充足 ({cash_ratio*100:.1f}%)",
                value=cash_ratio,
                threshold=min_ratio,
                action="正常"
            )
    
    def generate_risk_report(self, checks: List[RiskCheck]) -> str:
        """生成风险报告"""
        critical = [c for c in checks if c.level == RiskLevel.CRITICAL]
        high = [c for c in checks if c.level == RiskLevel.HIGH]
        medium = [c for c in checks if c.level == RiskLevel.MEDIUM]
        low = [c for c in checks if c.level == RiskLevel.LOW]
        
        report = f"""
🛡️ 风险控制报告
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

风险统计:
   🔴 紧急: {len(critical)} 项
   🟠 高危: {len(high)} 项
   🟡 警告: {len(medium)} 项
   🟢 正常: {len(low)} 项

"""
        
        if critical:
            report += "🔴 紧急处理:\n"
            for c in critical:
                report += f"   ❌ {c.check_name}: {c.message}\n"
                report += f"      → {c.action}\n\n"
        
        if high:
            report += "🟠 高度关注:\n"
            for c in high:
                report += f"   ⚠️  {c.check_name}: {c.message}\n"
                report += f"      → {c.action}\n\n"
        
        if medium:
            report += "🟡 注意事项:\n"
            for c in medium:
                report += f"   ℹ️  {c.check_name}: {c.message}\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return report


def test_risk_manager():
    """测试风控系统"""
    print("🧪 测试风险管理系统\n")
    
    rm = RiskManager()
    
    # 模拟数据
    portfolio = {
        'total_value': 95000,
        'initial_value': 100000,
        'cash': 20000,
        'positions': {
            '000001': {'value': 25000, 'avg_cost': 10},
            '000858': {'value': 30000, 'avg_cost': 150},
            '510300': {'value': 20000, 'avg_cost': 4},
        },
        'daily_return': -0.025
    }
    
    market_data = {
        'vix': 28,
        'overnight_changes': [],
        'risk_events': [],
        'daily_change': 0.02
    }
    
    print("1️⃣  盘前风控检查...")
    pre_checks = rm.pre_market_check(portfolio, market_data)
    for check in pre_checks:
        emoji = "✅" if check.passed else "❌"
        print(f"   {emoji} {check.check_name}: {check.message}")
    
    print("\n2️⃣  持仓风控检查...")
    position_checks = rm.position_risk_check('000001', portfolio['positions']['000001'], 9.2, market_data)
    for check in position_checks:
        emoji = "✅" if check.passed else "❌"
        print(f"   {emoji} {check.check_name}: {check.message}")
    
    print("\n3️⃣  日终风控检查...")
    post_checks = rm.post_daily_check(portfolio, [])
    for check in post_checks:
        emoji = "✅" if check.passed else "❌"
        print(f"   {emoji} {check.check_name}: {check.message}")
    
    print("\n4️⃣  生成风险报告...")
    all_checks = pre_checks + position_checks + post_checks
    report = rm.generate_risk_report(all_checks)
    print(report)
    
    print("✅ 风控系统测试完成!")


if __name__ == "__main__":
    test_risk_manager()
