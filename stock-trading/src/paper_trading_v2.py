"""
模拟交易系统 V2.0
支持双账户模式:
1. 自动选股账户 - Agent全权决策
2. 指定持仓账户 - 用户指定股票池，Agent决定时机和仓位
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from atomic_cache import cache
from data_provider import DataProvider
from factor_engine import FactorEngine
from risk_manager import RiskManager
from llm_strategy_engine import LLMStrategyEngine


class AccountMode(Enum):
    """账户模式"""
    AUTO_SELECT = "auto_select"      # 自动选股
    FIXED_POOL = "fixed_pool"        # 指定持仓


@dataclass
class Position:
    """持仓记录"""
    symbol: str
    shares: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    opened_at: str
    highest_price: float  # 用于移动止损
    

@dataclass
class PaperAccount:
    """模拟账户"""
    account_id: str
    name: str
    mode: AccountMode
    initial_capital: float
    cash: float
    fixed_pool: List[str] = field(default_factory=list)
    positions: Dict[str, Position] = field(default_factory=dict)
    trades_history: List[Dict] = field(default_factory=list)
    daily_values: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_value(self) -> float:
        """总资产"""
        position_value = sum(p.market_value for p in self.positions.values())
        return self.cash + position_value
    
    @property
    def total_return(self) -> float:
        """总收益率"""
        return (self.total_value - self.initial_capital) / self.initial_capital


class PaperTradingSystem:
    """
    模拟交易系统 V2.0
    
    核心功能:
    - 双账户模式支持
    - LLM驱动的交易决策
    - 实时风控监控
    - 完整的交易记录
    """
    
    def __init__(self):
        self.data_provider = DataProvider()
        self.factor_engine = FactorEngine()
        self.risk_manager = RiskManager()
        self.llm_engine = LLMStrategyEngine()
        
        self.accounts: Dict[str, PaperAccount] = {}
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        
    def create_account(
        self,
        name: str,
        mode: AccountMode,
        initial_capital: float = 100000,
        fixed_pool: List[str] = None
    ) -> str:
        """
        创建模拟账户
        
        Args:
            name: 账户名称
            mode: 账户模式
            initial_capital: 初始资金
            fixed_pool: 指定持仓模式的股票池
        
        Returns:
            account_id
        """
        account_id = f"paper_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.accounts)}"
        
        account = PaperAccount(
            account_id=account_id,
            name=name,
            mode=mode,
            initial_capital=initial_capital,
            cash=initial_capital,
            fixed_pool=fixed_pool if fixed_pool else []
        )
        
        self.accounts[account_id] = account
        
        print(f"✅ 创建账户成功")
        print(f"   ID: {account_id}")
        print(f"   名称: {name}")
        print(f"   模式: {'自动选股' if mode == AccountMode.AUTO_SELECT else '指定持仓'}")
        print(f"   初始资金: ¥{initial_capital:,.2f}")
        
        return account_id
    
    def run_daily_trading(self, account_id: str, market: str = "A股"):
        """
        执行每日交易流程
        
        工作流程:
        1. 盘前准备 - 数据获取、风险扫描
        2. LLM决策 - 生成交易信号
        3. 风控检查 - 验证交易合规性
        4. 执行交易 - 模拟成交
        5. 盘后结算 - 更新持仓和价值
        """
        if account_id not in self.accounts:
            print(f"❌ 账户不存在: {account_id}")
            return
        
        account = self.accounts[account_id]
        print(f"\n{'='*70}")
        print(f"📅 日期: {self.current_date}")
        print(f"👤 账户: {account.name} ({account.mode.value})")
        print(f"💰 总资产: ¥{account.total_value:,.2f}")
        print(f"{'='*70}\n")
        
        # ========== 1. 盘前准备 ==========
        print("🔍 1. 盘前准备...")
        
        # 获取市场数据
        market_data = self._get_market_data(market)
        
        # 风控扫描
        portfolio = {
            'total_value': account.total_value,
            'initial_value': account.initial_capital,
            'cash': account.cash,
            'positions': {s: {'value': p.market_value} for s, p in account.positions.items()},
            'daily_return': 0
        }
        
        risk_checks = self.risk_manager.pre_market_check(portfolio, market_data)
        critical_risks = [c for c in risk_checks if not c.passed and c.level.value == 'critical']
        
        if critical_risks:
            print("   ❌ 存在紧急风险，暂停交易:")
            for r in critical_risks:
                print(f"      - {r.message}")
            return
        
        print("   ✅ 盘前检查通过")
        
        # ========== 2. LLM决策 ==========
        print("\n🧠 2. LLM决策分析...")
        
        # 根据模式选择股票池
        if account.mode == AccountMode.AUTO_SELECT:
            # 自动选股：从全市场筛选
            universe = self._get_auto_universe(market)
        else:
            # 指定持仓：从固定池中选择
            universe = account.fixed_pool if hasattr(account, 'fixed_pool') else []
        
        if not universe:
            print("   ⚠️ 无可用标的")
            return
        
        print(f"   📊 分析标的: {len(universe)} 只")
        
        # 为每个标的生成因子
        stock_analysis = []
        for symbol in universe[:10]:  # 限制数量避免超时
            try:
                factors = self.factor_engine.calculate_all_factors(symbol, market)
                if factors:
                    stock_analysis.append({
                        'symbol': symbol,
                        'factors': factors
                    })
            except Exception as e:
                continue
        
        # LLM生成交易决策
        decision = self.llm_engine.generate_decision(stock_analysis, account.positions)
        
        print(f"   💡 决策结果:")
        for action in decision.get('actions', []):
            print(f"      - {action['symbol']}: {action['action']} {action.get('shares', 0)}股")
        
        # ========== 3. 风控检查 ==========
        print("\n🛡️ 3. 风控验证...")
        
        valid_actions = []
        for action in decision.get('actions', []):
            symbol = action['symbol']
            action_type = action['action']
            
            # 检查个股风控
            if symbol in account.positions:
                position = account.positions[symbol]
                current_price = self._get_current_price(symbol, market)
                
                checks = self.risk_manager.position_risk_check(
                    symbol, {'avg_cost': position.avg_cost, 'highest_price': position.highest_price},
                    current_price, market_data
                )
                
                # 如果触发止损，强制卖出
                stop_loss_triggered = any(
                    not c.passed and '止损' in c.check_name 
                    for c in checks
                )
                
                if stop_loss_triggered and action_type != 'sell':
                    print(f"   ⚠️ {symbol} 触发止损，强制卖出")
                    action['action'] = 'sell'
                    action['reason'] = 'stop_loss_triggered'
            
            valid_actions.append(action)
        
        print(f"   ✅ 通过验证: {len(valid_actions)} 个操作")
        
        # ========== 4. 执行交易 ==========
        print("\n💼 4. 执行交易...")
        
        executed_trades = []
        for action in valid_actions:
            trade = self._execute_trade(account, action, market)
            if trade:
                executed_trades.append(trade)
        
        print(f"   ✅ 执行完成: {len(executed_trades)} 笔交易")
        
        # ========== 5. 盘后结算 ==========
        print("\n📊 5. 盘后结算...")
        
        # 更新持仓市值
        for symbol, position in account.positions.items():
            current_price = self._get_current_price(symbol, market)
            if current_price:
                position.current_price = current_price
                position.market_value = position.shares * current_price
                position.unrealized_pnl = (current_price - position.avg_cost) * position.shares
                position.unrealized_pnl_pct = (current_price - position.avg_cost) / position.avg_cost
                
                # 更新最高价（用于移动止损）
                if current_price > position.highest_price:
                    position.highest_price = current_price
        
        # 记录每日净值
        account.daily_values.append({
            'date': self.current_date,
            'total_value': account.total_value,
            'cash': account.cash,
            'position_value': account.total_value - account.cash,
            'return_pct': account.total_return * 100
        })
        
        # 日终风控检查
        post_checks = self.risk_manager.post_daily_check(
            portfolio, account.trades_history[-10:] if len(account.trades_history) > 10 else account.trades_history
        )
        
        print(f"   💰 最新资产: ¥{account.total_value:,.2f}")
        print(f"   📈 累计收益: {account.total_return*100:+.2f}%")
        
        print(f"\n{'='*70}")
        print("✅ 今日交易结束")
        print(f"{'='*70}\n")
    
    def _get_market_data(self, market: str) -> Dict:
        """获取市场数据"""
        return {
            'vix': 20,  # 恐慌指数
            'overnight_changes': [],
            'risk_events': [],
            'daily_change': 0
        }
    
    def _get_auto_universe(self, market: str) -> List[str]:
        """获取自动选股范围"""
        # ETF列表
        etfs = {
            "A股": ["510300", "510050", "159915", "588000", "512760", "515030"],
            "US": ["SPY", "QQQ", "IWM", "VTI"]
        }
        return etfs.get(market, [])
    
    def _get_current_price(self, symbol: str, market: str) -> Optional[float]:
        """获取当前价格"""
        try:
            df = cache.get_kline_atomic(market, symbol, self.current_date, self.current_date)
            if df is not None and not df.empty:
                return float(df['close'].iloc[0])
        except:
            pass
        return None
    
    def _execute_trade(self, account: PaperAccount, action: Dict, market: str) -> Optional[Dict]:
        """执行单笔交易"""
        symbol = action['symbol']
        action_type = action['action']
        
        price = self._get_current_price(symbol, market)
        if not price:
            return None
        
        trade = {
            'time': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action_type,
            'price': price
        }
        
        if action_type == 'buy':
            # 计算买入金额（默认使用20%现金）
            buy_amount = min(account.cash * 0.20, account.cash * 0.95)
            shares = int(buy_amount / price / 100) * 100  # 整手
            
            if shares < 100:
                return None
            
            cost = shares * price * 1.00025  # 含手续费
            
            if cost > account.cash:
                return None
            
            # 更新持仓
            if symbol in account.positions:
                pos = account.positions[symbol]
                total_cost = pos.shares * pos.avg_cost + shares * price
                total_shares = pos.shares + shares
                pos.avg_cost = total_cost / total_shares
                pos.shares = total_shares
            else:
                account.positions[symbol] = Position(
                    symbol=symbol,
                    shares=shares,
                    avg_cost=price,
                    current_price=price,
                    market_value=shares * price,
                    unrealized_pnl=0,
                    unrealized_pnl_pct=0,
                    opened_at=self.current_date,
                    highest_price=price
                )
            
            account.cash -= cost
            trade['shares'] = shares
            trade['cost'] = cost
            
        elif action_type == 'sell':
            if symbol not in account.positions:
                return None
            
            pos = account.positions[symbol]
            shares = pos.shares  # 全仓卖出
            
            proceeds = shares * price * 0.99875  # 扣除手续费和印花税
            realized_pnl = (price - pos.avg_cost) * shares
            
            account.cash += proceeds
            del account.positions[symbol]
            
            trade['shares'] = shares
            trade['proceeds'] = proceeds
            trade['realized_pnl'] = realized_pnl
        
        account.trades_history.append(trade)
        return trade
    
    def get_account_summary(self, account_id: str) -> Dict:
        """获取账户摘要"""
        if account_id not in self.accounts:
            return {'error': '账户不存在'}
        
        account = self.accounts[account_id]
        
        return {
            'account_id': account_id,
            'name': account.name,
            'mode': account.mode.value,
            'total_value': account.total_value,
            'cash': account.cash,
            'position_value': account.total_value - account.cash,
            'total_return': account.total_return * 100,
            'positions_count': len(account.positions),
            'trades_count': len(account.trades_history),
            'positions': [
                {
                    'symbol': p.symbol,
                    'shares': p.shares,
                    'avg_cost': p.avg_cost,
                    'current_price': p.current_price,
                    'market_value': p.market_value,
                    'unrealized_pnl': p.unrealized_pnl,
                    'unrealized_pnl_pct': p.unrealized_pnl_pct * 100
                }
                for p in account.positions.values()
            ]
        }


def test_paper_trading():
    """测试模拟交易"""
    print("🧪 测试模拟交易系统 V2.0\n")
    
    system = PaperTradingSystem()
    
    # 创建自动选股账户
    print("="*70)
    print("创建自动选股账户")
    print("="*70)
    auto_account = system.create_account(
        name="自动选股策略",
        mode=AccountMode.AUTO_SELECT,
        initial_capital=100000
    )
    
    # 创建指定持仓账户
    print("\n" + "="*70)
    print("创建指定持仓账户")
    print("="*70)
    fixed_account = system.create_account(
        name="白马股策略",
        mode=AccountMode.FIXED_POOL,
        initial_capital=100000,
        fixed_pool=["000001", "000858", "600519"]  # 平安银行、五粮液、茅台
    )
    
    print("\n" + "="*70)
    print("账户概览")
    print("="*70)
    
    for acc_id in [auto_account, fixed_account]:
        summary = system.get_account_summary(acc_id)
        print(f"\n👤 {summary['name']} ({summary['mode']})")
        print(f"   总资产: ¥{summary['total_value']:,.2f}")
        print(f"   现金: ¥{summary['cash']:,.2f}")
        print(f"   持仓: {summary['positions_count']} 只")
    
    print("\n✅ 模拟交易系统测试完成!")
    print("\n💡 使用方法:")
    print("   system.run_daily_trading(account_id, 'A股')")


if __name__ == "__main__":
    test_paper_trading()
