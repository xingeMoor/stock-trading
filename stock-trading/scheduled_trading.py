#!/usr/bin/env python3
"""
定时交易任务
美股开盘后每小时执行一次分析和交易

使用系统 cron 或此脚本的循环模式
"""
import sys
import os
import time
import argparse
from datetime import datetime, timedelta
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.paper_trading import PaperTradingRunner
from src.massive_api import get_market_status
from src.trading_db import TradingDatabase


# 配置
SYMBOLS = ["GOOGL", "META", "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "AMZN"]
INITIAL_CAPITAL = 100000.0  # 10 万美元
STRATEGY = "optimized_v2"
POSITION_SIZE = 0.3  # 30% 仓位

# 美股交易时间 (ET 时区)
MARKET_OPEN = 9  # 9:30 AM ET
MARKET_CLOSE = 16  # 4:00 PM ET


def is_market_hours():
    """检查是否在美股交易时间内"""
    now = datetime.now()
    
    # 检查是否是工作日 (周一=0, 周五=4)
    if now.weekday() >= 5:
        return False
    
    # 检查时间 (简化处理，未考虑夏令时)
    hour_et = now.hour - 13  # 北京时间转 ET 时间 (近似)
    
    if hour_et < MARKET_OPEN or hour_et >= MARKET_CLOSE:
        return False
    
    return True


def get_next_run_time():
    """获取下次运行时间"""
    now = datetime.now()
    
    # 如果是周末，下周一开盘
    if now.weekday() >= 5:
        days_until_monday = 7 - now.weekday()
        next_run = now.replace(hour=21, minute=30, second=0, microsecond=0)  # 北京时间 21:30
        next_run += timedelta(days=days_until_monday)
        return next_run
    
    # 如果已过今日收盘，明天开盘
    hour_et = now.hour - 13
    if hour_et >= MARKET_CLOSE:
        next_run = now.replace(hour=21, minute=30, second=0, microsecond=0)
        if now.weekday() == 4:  # 周五
            next_run += timedelta(days=3)
        else:
            next_run += timedelta(days=1)
        return next_run
    
    # 如果还未开盘，今日开盘
    if hour_et < MARKET_OPEN:
        return now.replace(hour=21, minute=30, second=0, microsecond=0)
    
    # 交易时间内，下一小时
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return next_hour


def run_trading_cycle():
    """执行一轮交易"""
    print(f"\n{'='*60}")
    print(f"🤖 执行定时交易任务")
    print(f"{'='*60}")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"股票池：{', '.join(SYMBOLS)}")
    print(f"策略：{STRATEGY}")
    print(f"仓位：{POSITION_SIZE*100:.1f}%")
    
    # 检查市场状态
    market_status = get_market_status()
    print(f"\n市场状态：{market_status.get('status', 'Unknown')}")
    
    if market_status.get('status') == 'closed':
        print("⚠️  市场已关闭，跳过交易")
        return None
    
    # 执行交易
    runner = PaperTradingRunner(
        initial_capital=INITIAL_CAPITAL,
        strategy_name=STRATEGY,
        position_size_pct=POSITION_SIZE
    )
    
    report = runner.execute_daily_trading(SYMBOLS)
    
    # 保存报告
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'scheduled_runs')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'run_{timestamp}.json')
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✓ 报告已保存：{output_file}")
    
    return report


def send_feishu_notification(report):
    """发送飞书通知 (待配置)"""
    # TODO: 配置飞书 webhook
    print("\n📱 飞书通知：待配置 webhook")
    
    if report:
        summary = report.get('account_summary', {})
        trades = report.get('executed_trades', [])
        
        message = f"""
📊 模拟交易执行报告

💰 账户状态:
  总资产：${summary.get('total_value', 0):,.2f}
  总收益：${summary.get('total_return', 0):,.2f} ({summary.get('total_return_pct', 0):+.2f}%)

📝 今日交易：{len(trades)} 笔
"""
        
        for trade in trades:
            arrow = "→" if trade['trade_type'] == 'buy' else "←"
            pnl_str = f" (PnL: ${trade.get('pnl', 0):+.2f})" if trade['trade_type'] == 'sell' else ""
            message += f"  {arrow} {trade['symbol']}: {trade['shares']}股 @ ${trade['price']:.2f}{pnl_str}\n"
        
        print(message)
    
    # TODO: 实际发送
    # requests.post(FEISHU_WEBHOOK, json={"msg_type": "text", "content": {"text": message}})


def run_continuous_mode(interval_minutes=60):
    """连续运行模式"""
    print("\n" + "="*60)
    print("🕐 启动连续交易模式")
    print("="*60)
    print(f"股票池：{', '.join(SYMBOLS)}")
    print(f"执行间隔：{interval_minutes} 分钟")
    print(f"初始资金：${INITIAL_CAPITAL:,.2f}")
    print("\n按 Ctrl+C 停止\n")
    
    while True:
        try:
            # 检查是否交易时间
            if is_market_hours():
                print(f"\n⏰ 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                run_trading_cycle()
            else:
                next_run = get_next_run_time()
                print(f"\n💤 非交易时间，下次执行：{next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 等待
            print(f"⏳ 等待 {interval_minutes} 分钟...")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断，停止服务")
            break
        except Exception as e:
            print(f"\n❌ 错误：{e}")
            print(f"⏳ 1 分钟后重试...")
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description='定时交易任务')
    parser.add_argument('--once', action='store_true', help='只执行一次')
    parser.add_argument('--interval', type=int, default=60, help='执行间隔 (分钟)')
    parser.add_argument('--symbols', type=str, default=','.join(SYMBOLS), help='股票列表')
    parser.add_argument('--capital', type=float, default=INITIAL_CAPITAL, help='初始资金')
    parser.add_argument('--strategy', type=str, default=STRATEGY, help='策略名称')
    parser.add_argument('--position-size', type=float, default=POSITION_SIZE, help='仓位比例')
    
    args = parser.parse_args()
    
    # 更新配置
    global SYMBOLS, INITIAL_CAPITAL, STRATEGY, POSITION_SIZE
    SYMBOLS = [s.strip() for s in args.symbols.split(',')]
    INITIAL_CAPITAL = args.capital
    STRATEGY = args.strategy
    POSITION_SIZE = args.position_size
    
    if args.once:
        # 单次执行
        run_trading_cycle()
    else:
        # 连续运行
        run_continuous_mode(args.interval)


if __name__ == "__main__":
    main()
