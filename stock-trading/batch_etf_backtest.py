#!/usr/bin/env python3
"""
批量ETF回测 - A股热门板块
使用新浪财经数据源
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
import pandas as pd
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 热门ETF列表
ETF_LIST = {
    # 科技类
    "512760": "芯片ETF",
    "515030": "新能源车ETF",
    "159995": "半导体ETF",
    "515050": "5GETF",
    "159819": "人工智能ETF",
    
    # 医药类
    "512010": "医药ETF",
    "512170": "医疗ETF",
    "159992": "创新药ETF",
    
    # 消费类
    "159928": "消费ETF",
    "510150": "消费50ETF",
    "159736": "酒ETF",
    
    # 金融类
    "510300": "沪深300ETF",
    "510050": "上证50ETF",
    "159915": "创业板ETF",
    "588000": "科创50ETF",
    
    # 周期类
    "510880": "红利ETF",
    "159980": "有色ETF",
    "159985": "豆粕ETF",
}

def get_etf_hist_sina(symbol):
    """获取ETF历史数据(新浪财经)"""
    try:
        # 添加交易所前缀
        if not symbol.startswith(('sh', 'sz')):
            prefix = 'sh' if symbol.startswith('5') else 'sz'
            full_symbol = f"{prefix}{symbol}"
        else:
            full_symbol = symbol
            symbol = symbol[2:]
        
        df = ak.fund_etf_hist_sina(symbol=full_symbol)
        return symbol, df
    except Exception as e:
        print(f"❌ {symbol}: {e}")
        return symbol, None

def simple_backtest(df, strategy="ma_cross"):
    """
    简单回测策略
    
    strategy:
    - ma_cross: 均线交叉 (5日上穿20日买入，下穿卖出)
    - rsi: RSI超卖买入，超买卖出
    """
    if df is None or len(df) < 60:
        return None
    
    # 计算指标
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    # 计算RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 信号生成
    if strategy == "ma_cross":
        df['signal'] = 0
        df.loc[df['ma5'] > df['ma20'], 'signal'] = 1  # 买入
        df.loc[df['ma5'] <= df['ma20'], 'signal'] = -1  # 卖出
    elif strategy == "rsi":
        df['signal'] = 0
        df.loc[df['rsi'] < 30, 'signal'] = 1  # 超卖买入
        df.loc[df['rsi'] > 70, 'signal'] = -1  # 超买卖出
    
    # 回测计算
    position = 0
    trades = []
    entry_price = 0
    equity = [100000]  # 初始资金10万
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        if position == 0 and row['signal'] == 1:
            # 买入
            position = 1
            entry_price = row['close']
            trades.append({
                'date': row.get('date', i),
                'type': 'buy',
                'price': entry_price
            })
        elif position == 1 and row['signal'] == -1:
            # 卖出
            exit_price = row['close']
            pnl = (exit_price - entry_price) / entry_price
            trades.append({
                'date': row.get('date', i),
                'type': 'sell',
                'price': exit_price,
                'pnl': pnl
            })
            equity.append(equity[-1] * (1 + pnl))
            position = 0
        else:
            if equity:
                equity.append(equity[-1])
    
    # 计算绩效
    total_return = (equity[-1] - equity[0]) / equity[0] * 100 if len(equity) > 1 else 0
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
    win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0
    
    # 最大回撤
    max_drawdown = 0
    peak = equity[0]
    for val in equity:
        if val > peak:
            peak = val
        drawdown = (peak - val) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'total_return': round(total_return, 2),
        'win_rate': round(win_rate, 2),
        'max_drawdown': round(max_drawdown * 100, 2),
        'trade_count': len(sell_trades),
        'final_equity': round(equity[-1], 2),
        'trades': trades[:10]  # 只保留前10笔交易详情
    }

def analyze_etf(symbol, name):
    """分析单只ETF"""
    print(f"📊 分析 {name} ({symbol})...")
    
    symbol_clean, df = get_etf_hist_sina(symbol)
    if df is None:
        return None
    
    # 基础统计
    latest = df.iloc[-1]
    first = df.iloc[0]
    total_change = (latest['close'] - first['close']) / first['close'] * 100
    
    # 均线策略回测
    result_ma = simple_backtest(df.copy(), "ma_cross")
    
    # RSI策略回测
    result_rsi = simple_backtest(df.copy(), "rsi")
    
    return {
        'symbol': symbol,
        'name': name,
        'data_points': len(df),
        'latest_price': round(latest['close'], 3),
        'total_change': round(total_change, 2),
        'ma_strategy': result_ma,
        'rsi_strategy': result_rsi
    }

def main():
    print("="*60)
    print("🚀 A股ETF批量回测")
    print("="*60)
    print(f"\n回测标的: {len(ETF_LIST)} 只ETF")
    print("策略: 均线交叉 + RSI超买卖")
    print()
    
    results = []
    
    # 串行执行（避免网络并发问题）
    for symbol, name in ETF_LIST.items():
        try:
            result = analyze_etf(symbol, name)
            if result:
                results.append(result)
                
                # 打印简要结果
                ma_ret = result['ma_strategy']['total_return'] if result['ma_strategy'] else 0
                rsi_ret = result['rsi_strategy']['total_return'] if result['rsi_strategy'] else 0
                print(f"   ✅ 均线策略: {ma_ret:+.2f}% | RSI策略: {rsi_ret:+.2f}%")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    # 保存结果
    output_file = f"data/etf_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('data', exist_ok=True)
    
    # 处理日期序列化
    import datetime as dt
    def json_serial(obj):
        if isinstance(obj, (dt.datetime, dt.date, pd.Timestamp)):
            return obj.strftime('%Y-%m-%d')
        raise TypeError(f'Type {type(obj)} not serializable')
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=json_serial)
    
    # 汇总报告
    print("\n" + "="*60)
    print("📈 回测汇总")
    print("="*60)
    
    if results:
        # 按均线策略收益排序
        sorted_by_ma = sorted([r for r in results if r['ma_strategy']], 
                              key=lambda x: x['ma_strategy']['total_return'], reverse=True)
        
        print("\n🏆 均线策略TOP5:")
        for i, r in enumerate(sorted_by_ma[:5], 1):
            ma = r['ma_strategy']
            print(f"   {i}. {r['name']} ({r['symbol']}): {ma['total_return']:+.2f}% | "
                  f"胜率{ma['win_rate']:.0f}% | 回撤{ma['max_drawdown']:.1f}%")
        
        print("\n📉 均线策略BOTTOM5:")
        for i, r in enumerate(sorted_by_ma[-5:], 1):
            ma = r['ma_strategy']
            print(f"   {i}. {r['name']} ({r['symbol']}): {ma['total_return']:+.2f}% | "
                  f"胜率{ma['win_rate']:.0f}% | 回撤{ma['max_drawdown']:.1f}%")
        
        # 平均表现
        avg_ma = sum(r['ma_strategy']['total_return'] for r in results if r['ma_strategy']) / len(results)
        print(f"\n📊 平均收益: {avg_ma:+.2f}%")
        print(f"📁 详细结果已保存: {output_file}")
    
    print("="*60)

if __name__ == "__main__":
    main()
