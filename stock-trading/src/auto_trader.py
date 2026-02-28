"""
自动交易执行器
连接大模型决策 ↔ 实际交易执行
支持模拟盘和实盘
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import sqlite3

from trading_db import TradingDatabase
from data_provider import DataProvider

@dataclass
class TradeOrder:
    """交易订单"""
    symbol: str
    action: str  # buy / sell
    shares: int
    price: float
    order_type: str = "market"  # market / limit
    reason: str = ""  # 大模型决策理由
    confidence: float = 0.0  # 大模型置信度
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AutoTrader:
    """
    自动交易执行器
    
    功能:
    1. 接收大模型交易决策
    2. 风控检查
    3. 计算具体交易数量
    4. 执行交易（模拟/实盘）
    5. 记录和反馈
    """
    
    def __init__(self, 
                 account_id: str = "default",
                 mode: str = "paper",  # paper / real
                 initial_capital: float = 100000.0):
        """
        Args:
            account_id: 账户ID
            mode: 交易模式 (paper=模拟盘, real=实盘)
            initial_capital: 初始资金
        """
        self.account_id = account_id
        self.mode = mode
        self.initial_capital = initial_capital
        
        # 数据库连接
        self.db = TradingDatabase()
        
        # 数据接口
        self.data_provider = DataProvider()
        
        # 加载当前持仓
        self.positions = self._load_positions()
        self.cash = self._load_cash()
        
    def _load_positions(self) -> Dict[str, Dict]:
        """加载当前持仓"""
        positions = {}
        db_positions = self.db.get_positions()
        for pos in db_positions:
            positions[pos['symbol']] = {
                'shares': pos['shares'],
                'average_cost': pos['average_cost'],
                'current_price': pos['current_price']
            }
        return positions
    
    def _load_cash(self) -> float:
        """加载现金余额"""
        latest = self.db.get_latest_snapshot()
        if latest:
            return latest['cash']
        return self.initial_capital
    
    def calculate_position_size(self, 
                                symbol: str,
                                target_weight: float,
                                confidence: float) -> int:
        """
        计算交易股数
        
        Args:
            symbol: 股票代码
            target_weight: 目标仓位比例 (如 0.15 = 15%)
            confidence: 大模型置信度 (0-1)
        
        Returns:
            交易股数
        """
        # 获取当前价格
        realtime = self.data_provider.get_realtime(symbol, 'A股')
        if 'error' in realtime:
            print(f"⚠️  无法获取{symbol}价格")
            return 0
        
        current_price = realtime['price']
        
        # 计算目标市值
        total_value = self._get_total_value()
        target_value = total_value * target_weight * confidence
        
        # 计算当前持仓市值
        current_shares = self.positions.get(symbol, {}).get('shares', 0)
        current_value = current_shares * current_price
        
        # 计算需要调整的市值
        delta_value = target_value - current_value
        
        # 检查可用资金（买入时）
        if delta_value > 0 and delta_value > self.cash:
            delta_value = self.cash * 0.95  # 留5%缓冲
        
        # 计算股数（整手，A股100股一手）
        shares = int(delta_value / current_price / 100) * 100
        
        return shares
    
    def _get_total_value(self) -> float:
        """获取总资产"""
        position_value = sum(
            pos['shares'] * pos['current_price'] 
            for pos in self.positions.values()
        )
        return self.cash + position_value
    
    def risk_check(self, order: TradeOrder) -> Dict[str, Any]:
        """
        风控检查
        
        Returns:
            {'approved': True/False, 'reasons': []}
        """
        reasons = []
        approved = True
        
        # 检查1: 单票仓位上限
        total_value = self._get_total_value()
        order_value = order.shares * order.price
        new_weight = order_value / total_value if total_value > 0 else 0
        
        if new_weight > 0.20:  # 单票不超过20%
            approved = False
            reasons.append(f"单票仓位超限: {new_weight:.1%} > 20%")
        
        # 检查2: 总仓位上限
        if order.action == 'buy':
            new_total_position = (total_value - self.cash + order_value) / total_value
            if new_total_position > 0.90:  # 总仓位不超过90%
                approved = False
                reasons.append(f"总仓位超限: {new_total_position:.1%} > 90%")
        
        # 检查3: 止损检查（卖出时）
        if order.action == 'sell' and order.symbol in self.positions:
            pos = self.positions[order.symbol]
            avg_cost = pos['average_cost']
            if order.price < avg_cost * 0.92:  # 亏损超过8%
                reasons.append(f"⚠️ 触发止损: 亏损{(1-order.price/avg_cost)*100:.1f}%")
                # 止损强制批准
                approved = True
        
        # 检查4: 最低交易金额
        if order_value < 1000:  # 小于1000元不交易
            approved = False
            reasons.append(f"交易金额太小: ¥{order_value:.0f} < ¥1000")
        
        return {
            'approved': approved,
            'reasons': reasons,
            'risk_level': 'high' if not approved else 'medium' if reasons else 'low'
        }
    
    def execute_order(self, order: TradeOrder) -> Dict[str, Any]:
        """
        执行交易订单
        """
        print(f"\n📋 执行订单: {order.action.upper()} {order.symbol}")
        print(f"   股数: {order.shares}, 价格: ¥{order.price:.2f}")
        print(f"   理由: {order.reason[:50]}...")
        
        # 风控检查
        risk_result = self.risk_check(order)
        if not risk_result['approved']:
            print(f"   ❌ 风控拒绝:")
            for reason in risk_result['reasons']:
                print(f"      - {reason}")
            return {
                'status': 'rejected',
                'order': asdict(order),
                'risk_check': risk_result
            }
        
        if risk_result['reasons']:
            print(f"   ⚠️  风险提示:")
            for reason in risk_result['reasons']:
                print(f"      - {reason}")
        
        # 模拟执行
        if self.mode == "paper":
            return self._execute_paper(order)
        else:
            return self._execute_real(order)
    
    def _execute_paper(self, order: TradeOrder) -> Dict[str, Any]:
        """模拟盘执行"""
        try:
            # 计算费用
            commission = order.shares * order.price * 0.00025  # 万2.5佣金
            stamp_tax = order.shares * order.price * 0.001 if order.action == 'sell' else 0  # 卖出印花税
            total_cost = commission + stamp_tax
            
            trade_value = order.shares * order.price
            
            # 更新持仓和现金
            if order.action == 'buy':
                self.cash -= (trade_value + total_cost)
                
                if order.symbol in self.positions:
                    # 加仓，更新成本
                    old_shares = self.positions[order.symbol]['shares']
                    old_cost = self.positions[order.symbol]['average_cost']
                    total_shares = old_shares + order.shares
                    total_cost_basis = old_shares * old_cost + order.shares * order.price
                    self.positions[order.symbol] = {
                        'shares': total_shares,
                        'average_cost': total_cost_basis / total_shares,
                        'current_price': order.price
                    }
                else:
                    self.positions[order.symbol] = {
                        'shares': order.shares,
                        'average_cost': order.price,
                        'current_price': order.price
                    }
                
                pnl = 0
            else:  # sell
                self.cash += (trade_value - total_cost)
                
                if order.symbol in self.positions:
                    old_shares = self.positions[order.symbol]['shares']
                    avg_cost = self.positions[order.symbol]['average_cost']
                    
                    # 计算盈亏
                    pnl = (order.price - avg_cost) * order.shares
                    
                    # 更新持仓
                    remaining = old_shares - order.shares
                    if remaining > 0:
                        self.positions[order.symbol]['shares'] = remaining
                    else:
                        del self.positions[order.symbol]
                else:
                    pnl = 0
            
            # 记录到数据库
            self.db.add_trade(
                symbol=order.symbol,
                trade_type=order.action,
                price=order.price,
                shares=order.shares,
                strategy="LLM_MultiFactor",
                confidence=order.confidence,
                reasoning=order.reason,
                commission=commission,
                pnl=pnl if order.action == 'sell' else 0
            )
            
            # 更新持仓记录
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                self.db.update_position(
                    symbol=order.symbol,
                    shares=pos['shares'],
                    average_cost=pos['average_cost'],
                    current_price=order.price
                )
            
            print(f"   ✅ 模拟交易成功!")
            print(f"   💰 交易金额: ¥{trade_value:,.2f}")
            print(f"   📊 手续费: ¥{total_cost:.2f}")
            if order.action == 'sell' and pnl != 0:
                print(f"   {'🟢' if pnl > 0 else '🔴'} 盈亏: ¥{pnl:,.2f}")
            
            return {
                'status': 'success',
                'order': asdict(order),
                'trade_value': trade_value,
                'cost': total_cost,
                'pnl': pnl if order.action == 'sell' else 0,
                'cash_remaining': self.cash
            }
            
        except Exception as e:
            print(f"   ❌ 执行失败: {e}")
            return {
                'status': 'error',
                'order': asdict(order),
                'error': str(e)
            }
    
    def _execute_real(self, order: TradeOrder) -> Dict[str, Any]:
        """实盘执行（待接入券商API）"""
        print(f"   ⏳ 实盘API接入中...")
        return {
            'status': 'pending',
            'message': '实盘API未接入，请先配置券商接口',
            'order': asdict(order)
        }
    
    def process_llm_decision(self, llm_decision: Dict) -> List[Dict]:
        """
        处理大模型的交易决策
        
        Args:
            llm_decision: 大模型输出的JSON决策
        
        Returns:
            执行结果列表
        """
        results = []
        
        for decision in llm_decision.get('trading_decisions', []):
            symbol = decision['symbol']
            action = decision['action']
            target_weight = decision.get('position_delta', 0)
            confidence = decision.get('confidence', 0.7)
            
            # 跳过hold
            if action == 'hold':
                continue
            
            # 计算交易数量
            shares = self.calculate_position_size(symbol, target_weight, confidence)
            
            if shares == 0:
                print(f"⏭️  {symbol}: 无需交易")
                continue
            
            # 获取当前价格
            realtime = self.data_provider.get_realtime(symbol, 'A股')
            if 'error' in realtime:
                print(f"❌ {symbol}: 无法获取价格")
                continue
            
            price = realtime['price']
            
            # 如果是卖出，确保不超过持仓
            if action == 'sell' and symbol in self.positions:
                max_shares = self.positions[symbol]['shares']
                shares = min(shares, max_shares)
            
            # 创建订单
            order = TradeOrder(
                symbol=symbol,
                action=action,
                shares=shares,
                price=price,
                reason=decision.get('reasoning', ''),
                confidence=confidence
            )
            
            # 执行
            result = self.execute_order(order)
            results.append(result)
        
        return results


def test_auto_trader():
    """测试自动交易器"""
    print("🧪 测试自动交易执行器\n")
    
    # 创建模拟盘交易者
    trader = AutoTrader(
        account_id="test_account",
        mode="paper",
        initial_capital=100000
    )
    
    print(f"💰 初始资金: ¥{trader.initial_capital:,.2f}")
    print(f"💵 当前现金: ¥{trader.cash:,.2f}")
    print(f"📊 当前持仓: {len(trader.positions)} 只\n")
    
    # 模拟大模型决策
    mock_llm_decision = {
        "trading_decisions": [
            {
                "symbol": "512760",
                "action": "buy",
                "position_delta": 0.15,
                "confidence": 0.85,
                "reasoning": "芯片ETF技术形态突破，RSI处于合理区间，政策利好半导体行业"
            },
            {
                "symbol": "510300",
                "action": "buy",
                "position_delta": 0.10,
                "confidence": 0.75,
                "reasoning": "沪深300估值处于历史低位，适合作为底仓配置"
            }
        ]
    }
    
    print("🤖 模拟大模型决策执行:\n")
    results = trader.process_llm_decision(mock_llm_decision)
    
    print(f"\n📈 执行完成: {len(results)} 笔交易")
    print(f"💵 剩余现金: ¥{trader.cash:,.2f}")
    print(f"📊 当前持仓: {len(trader.positions)} 只")
    for sym, pos in trader.positions.items():
        print(f"   - {sym}: {pos['shares']}股, 成本¥{pos['average_cost']:.2f}")


if __name__ == "__main__":
    test_auto_trader()
