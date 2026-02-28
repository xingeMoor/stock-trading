#!/usr/bin/env python3
"""
量化交易系统 - 统一入口
一键启动完整交易流程
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
import argparse

# 导入所有模块
from data_provider import DataProvider
from data_lake import DataLake
from atomic_cache import cache
from factor_engine import FactorEngine
from llm_strategy_engine import LLMStrategyEngine
from backtest_engine import BacktestEngine
from batch_backtest_v2 import BatchBacktestRunner, STOCK_UNIVERSE
from risk_manager import RiskManager
from paper_trading_v2 import PaperTradingSystem, AccountMode
from polymarket_client import get_market_sentiment

try:
    from data_warmer import DataWarmer
except ImportError:
    DataWarmer = None


class QuantSystem:
    """
    量化交易系统主控
    
    整合所有模块，提供统一操作界面
    """
    
    def __init__(self):
        print("🚀 初始化量化交易系统...")
        
        self.data_provider = DataProvider()
        self.data_lake = DataLake()
        self.factor_engine = FactorEngine()
        self.risk_manager = RiskManager()
        self.paper_system = PaperTradingSystem()
        
        print("✅ 系统初始化完成\n")
    
    def cmd_warmup(self):
        """数据预热"""
        print("🔥 执行数据预热...")
        warmer = DataWarmer()
        
        # A股核心ETF
        warmer.warm_daily()
        
        print("\n✅ 数据预热完成!")
    
    def cmd_backtest(self, market: str = "A股", mode: str = "balanced"):
        """批量回测"""
        print(f"📊 启动批量回测 ({market})...")
        
        runner = BatchBacktestRunner(max_workers=4)
        
        symbols = STOCK_UNIVERSE[market]["ETF"]
        
        report = runner.run_batch(
            symbols=symbols,
            market=market,
            start_date="20240101",
            end_date="20250228",
            strategy_mode=mode
        )
        
        runner.print_summary(report)
        runner.save_report(report)
        
        return report
    
    def cmd_paper_create(self, name: str, mode: str, capital: float = 100000, pool: list = None):
        """创建模拟账户"""
        print(f"👤 创建模拟账户: {name}")
        
        account_mode = AccountMode.AUTO_SELECT if mode == "auto" else AccountMode.FIXED_POOL
        
        account_id = self.paper_system.create_account(
            name=name,
            mode=account_mode,
            initial_capital=capital,
            fixed_pool=pool or []
        )
        
        return account_id
    
    def cmd_paper_trade(self, account_id: str, market: str = "A股"):
        """执行模拟交易"""
        print(f"💼 执行模拟交易...")
        self.paper_system.run_daily_trading(account_id, market)
    
    def cmd_paper_status(self, account_id: str):
        """查看账户状态"""
        summary = self.paper_system.get_account_summary(account_id)
        
        print(f"\n{'='*70}")
        print(f"📊 账户概览: {summary['name']}")
        print(f"{'='*70}")
        print(f"模式: {summary['mode']}")
        print(f"总资产: ¥{summary['total_value']:,.2f}")
        print(f"现金: ¥{summary['cash']:,.2f}")
        print(f"持仓市值: ¥{summary['position_value']:,.2f}")
        print(f"累计收益: {summary['total_return']:+.2f}%")
        print(f"持仓数量: {summary['positions_count']} 只")
        print(f"交易次数: {summary['trades_count']} 次")
        
        if summary['positions']:
            print(f"\n📈 当前持仓:")
            for p in summary['positions']:
                emoji = "🟢" if p['unrealized_pnl'] > 0 else "🔴"
                print(f"   {emoji} {p['symbol']}: {p['shares']}股 "
                      f"成本¥{p['avg_cost']:.2f} 现价¥{p['current_price']:.2f} "
                      f"盈亏{p['unrealized_pnl_pct']:+.2f}%")
    
    def cmd_sentiment(self):
        """获取市场情绪"""
        print("🌍 获取Polymarket市场情绪...")
        sentiment = get_market_sentiment(limit=50)
        
        if 'error' not in sentiment:
            print(f"\n📊 市场情绪报告")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"综合评分: {sentiment['overall_score']} ({sentiment['interpretation']})")
            print(f"经济情绪: {sentiment['economy_score']:+.2f}")
            print(f"美联储预期: {sentiment['fed_score']:+.2f}")
            print(f"加密情绪: {sentiment['crypto_score']:+.2f}")
            
            if sentiment['top_markets']:
                print(f"\n🔥 热门市场:")
                for m in sentiment['top_markets'][:5]:
                    print(f"   - {m['title'][:40]}... ({m['probability']:.1%})")
        else:
            print(f"❌ {sentiment['error']}")
    
    def cmd_risk_check(self, account_id: str):
        """风险检查"""
        print("🛡️ 执行风险检查...")
        
        summary = self.paper_system.get_account_summary(account_id)
        
        portfolio = {
            'total_value': summary['total_value'],
            'initial_value': 100000,
            'cash': summary['cash'],
            'positions': {p['symbol']: {'value': p['market_value']} for p in summary['positions']},
            'daily_return': 0
        }
        
        market_data = {'vix': 20, 'overnight_changes': [], 'risk_events': []}
        
        checks = self.risk_manager.pre_market_check(portfolio, market_data)
        report = self.risk_manager.generate_risk_report(checks)
        
        print(report)
    
    def interactive(self):
        """交互模式"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║               🎯 量化交易系统 - 交互控制台                     ║
╠══════════════════════════════════════════════════════════════╣
║  命令:                                                        ║
║    warmup          - 数据预热                                 ║
║    backtest        - 批量回测                                 ║
║    paper create    - 创建模拟账户                             ║
║    paper trade     - 执行模拟交易                             ║
║    paper status    - 查看账户状态                             ║
║    sentiment       - 市场情绪                                 ║
║    risk            - 风险检查                                 ║
║    help            - 显示帮助                                 ║
║    quit            - 退出                                     ║
╚══════════════════════════════════════════════════════════════╝
""")
        
        current_account = None
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd == "quit":
                    print("👋 再见!")
                    break
                
                elif cmd == "help":
                    print("可用命令: warmup, backtest, paper create/trade/status, sentiment, risk, quit")
                
                elif cmd == "warmup":
                    self.cmd_warmup()
                
                elif cmd == "backtest":
                    market = input("市场 (A股/US) [A股]: ").strip() or "A股"
                    self.cmd_backtest(market)
                
                elif cmd == "paper create":
                    name = input("账户名称: ").strip()
                    mode = input("模式 (auto/fixed) [auto]: ").strip() or "auto"
                    current_account = self.cmd_paper_create(name, mode)
                
                elif cmd == "paper trade":
                    if not current_account:
                        current_account = input("账户ID: ").strip()
                    self.cmd_paper_trade(current_account)
                
                elif cmd == "paper status":
                    if not current_account:
                        current_account = input("账户ID: ").strip()
                    self.cmd_paper_status(current_account)
                
                elif cmd == "sentiment":
                    self.cmd_sentiment()
                
                elif cmd == "risk":
                    if not current_account:
                        current_account = input("账户ID: ").strip()
                    self.cmd_risk_check(current_account)
                
                else:
                    print("未知命令，输入 help 查看帮助")
                    
            except KeyboardInterrupt:
                print("\n👋 再见!")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='量化交易系统')
    parser.add_argument('command', nargs='?', help='命令 (interactive, warmup, backtest, paper, sentiment)')
    parser.add_argument('--market', default='A股', help='市场 (A股/US)')
    parser.add_argument('--mode', default='balanced', help='策略模式')
    
    args = parser.parse_args()
    
    system = QuantSystem()
    
    if not args.command or args.command == "interactive":
        system.interactive()
    elif args.command == "warmup":
        system.cmd_warmup()
    elif args.command == "backtest":
        system.cmd_backtest(args.market, args.mode)
    elif args.command == "sentiment":
        system.cmd_sentiment()
    else:
        print(f"未知命令: {args.command}")


if __name__ == "__main__":
    main()
