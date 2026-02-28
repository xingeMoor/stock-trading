"""
批量回测脚本
回测多个股票并保存结果
"""
import sys
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.backtest import backtest_strategy
from strategies.optimized_v2_strategy import optimized_v2_strategy

# 热门股票列表 (按行业分类)
STOCKS_BY_SECTOR = {
    "科技": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD", "INTC", "CSCO", "ORCL", "ADBE",
             "CRM", "AVGO", "QCOM", "TXN", "IBM", "NOW", "INTU", "AMAT", "LRCX", "KLAC"],
    "半导体": ["NVDA", "AMD", "INTC", "TSM", "AVGO", "QCOM", "TXN", "AMAT", "LRCX", "KLAC",
               "MU", "MRVL", "NXPI", "MCHP", "ADI", "SWKS", "QRVO", "MPWR", "ENPH", "ON"],
    "电商": ["AMZN", "BABA", "JD", "PDD", "MELI", "SE", "CPNG", "ETSY", "EBAY", "W"],
    "金融": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V",
             "MA", "PYPL", "SQ", "COIN", "SOFI"],
    "医疗": ["JNJ", "UNH", "PFE", "MRK", "ABBV", "TMO", "ABT", "DHR", "BMY", "LLY",
             "AMGN", "GILD", "VRTX", "REGN", "ZTS", "MRNA", "BNTX", "ISRG", "SYK", "BSX"],
    "消费": ["TSLA", "NKE", "MCD", "SBUX", "KO", "PEP", "WMT", "COST", "HD", "LOW",
             "TGT", "DG", "DLTR", "ROST", "TJX", "CMG", "YUM", "DPZ", "LULU", "ULTA"],
    "能源": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
             "BKR", "DVN", "FANG", "HES", "KMI"],
    "工业": ["CAT", "BA", "HON", "UNP", "UPS", "RTX", "LMT", "GE", "MMM", "DE",
             "GD", "NOC", "FDX", "NSC", "CSX", "WM", "RSG", "EMR", "ETN", "PH"],
    "通信": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA"],
    "房地产": ["AMT", "PLD", "CCI", "EQIX", "PSA", "WELL", "DLR", "O", "SBAC", "SPG"],
    "公用事业": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ED"]
}


def run_backtest(symbol, start_date, end_date):
    """执行单只股票回测"""
    print(f"📊 回测 {symbol}...")
    
    try:
        result = backtest_strategy(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            strategy_func=optimized_v2_strategy,
            verbose=False
        )
        
        if 'error' not in result:
            # 保存结果
            output_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"backtest_{symbol}_{start_date}_{end_date}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"  ✓ {symbol}: +{result.get('total_return', 0):.2f}% (Sharpe: {result.get('sharpe_ratio', 0):.2f})")
            return {'symbol': symbol, 'status': 'success', 'result': result}
        else:
            print(f"  ✗ {symbol}: {result.get('error')}")
            return {'symbol': symbol, 'status': 'error', 'error': result.get('error')}
            
    except Exception as e:
        print(f"  ✗ {symbol}: 异常 - {e}")
        return {'symbol': symbol, 'status': 'error', 'error': str(e)}


def run_batch_backtest(symbols=None, start_date='2024-01-01', end_date='2026-02-28', 
                       max_workers=5, sectors=None):
    """
    批量回测
    
    Args:
        symbols: 股票列表 (可选，不提供则使用预定义列表)
        start_date: 开始日期
        end_date: 结束日期
        max_workers: 并发数
        sectors: 行业列表 (可选)
    """
    print("\n" + "="*60)
    print("🚀 批量回测启动")
    print("="*60)
    print(f"回测周期：{start_date} 至 {end_date}")
    
    # 确定股票列表
    if symbols:
        stock_list = symbols
    elif sectors:
        stock_list = []
        for sector in sectors:
            stock_list.extend(STOCKS_BY_SECTOR.get(sector, []))
    else:
        # 默认回测所有行业
        stock_list = []
        for stocks in STOCKS_BY_SECTOR.values():
            stock_list.extend(stocks)
        
        # 去重
        stock_list = list(set(stock_list))
    
    print(f"股票数量：{len(stock_list)}")
    print(f"并发数：{max_workers}")
    print("="*60 + "\n")
    
    # 并发执行
    results = []
    start_time = datetime.now()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_backtest, symbol, start_date, end_date): symbol
            for symbol in stock_list
        }
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            results.append(result)
            
            # 进度显示
            if completed % 10 == 0:
                print(f"\n⏳ 进度：{completed}/{len(stock_list)}")
    
    # 统计结果
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    # 保存总结
    summary = {
        'start_date': start_date,
        'end_date': end_date,
        'total_stocks': len(stock_list),
        'successful': successful,
        'failed': failed,
        'duration_seconds': duration,
        'completed_at': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'results': results
    }
    
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    
    summary_file = os.path.join(output_dir, f'summary_{start_date}_{end_date}.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 回测完成")
    print("="*60)
    print(f"总股票数：{len(stock_list)}")
    print(f"成功：{successful}")
    print(f"失败：{failed}")
    print(f"耗时：{duration:.1f}秒")
    print(f"总结文件：{summary_file}")
    print("="*60 + "\n")
    
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='批量回测')
    parser.add_argument('--symbols', type=str, help='股票列表 (逗号分隔)')
    parser.add_argument('--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2026-02-28', help='结束日期')
    parser.add_argument('--workers', type=int, default=5, help='并发数')
    parser.add_argument('--sectors', type=str, help='行业列表 (逗号分隔)')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',') if args.symbols else None
    sectors = args.sectors.split(',') if args.sectors else None
    
    run_batch_backtest(
        symbols=symbols,
        start_date=args.start,
        end_date=args.end,
        max_workers=args.workers,
        sectors=sectors
    )
