"""
批量回测引擎 V2.0
支持A股+美股，最近2年历史数据，并发执行
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import json

from backtest_engine import BacktestEngine
from atomic_cache import cache


class BatchBacktestRunner:
    """
    批量回测运行器
    
    特性:
    - A股+美股双市场支持
    - 并发执行提高效率
    - 统一结果汇总
    - 绩效对比分析
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.results = []
        
    def run_batch(
        self,
        symbols: List[str],
        market: str,
        start_date: str,
        end_date: str,
        strategy_mode: str = "balanced",
        initial_capital: float = 100000
    ) -> Dict[str, Any]:
        """
        执行批量回测
        
        Args:
            symbols: 股票代码列表
            market: A股/US
            start_date: YYYYMMDD
            end_date: YYYYMMDD
            strategy_mode: 策略模式
            initial_capital: 初始资金
        
        Returns:
            汇总报告
        """
        print(f"\n🚀 批量回测启动")
        print(f"{'='*70}")
        print(f"市场: {market}")
        print(f"标的数量: {len(symbols)}")
        print(f"回测周期: {start_date} ~ {end_date}")
        print(f"策略模式: {strategy_mode}")
        print(f"并发数: {self.max_workers}")
        print(f"{'='*70}\n")
        
        self.results = []
        completed = 0
        failed = 0
        
        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_symbol = {
                executor.submit(
                    self._run_single_backtest,
                    symbol, market, start_date, end_date, 
                    strategy_mode, initial_capital
                ): symbol for symbol in symbols
            }
            
            # 收集结果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result and 'error' not in result:
                        self.results.append(result)
                        completed += 1
                        status = "✅"
                    else:
                        failed += 1
                        status = "❌"
                except Exception as e:
                    failed += 1
                    status = "❌"
                    print(f"   {status} {symbol}: {e}")
                    continue
                
                # 进度显示
                total = completed + failed
                if total % 5 == 0 or total == len(symbols):
                    print(f"   进度: {total}/{len(symbols)} ({completed}成功 {failed}失败)")
        
        # 生成汇总报告
        report = self._generate_summary_report(market, start_date, end_date)
        
        print(f"\n✅ 批量回测完成!")
        print(f"   成功: {completed} | 失败: {failed}")
        
        return report
    
    def _run_single_backtest(
        self,
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        strategy_mode: str,
        initial_capital: float
    ) -> Optional[Dict]:
        """执行单个回测"""
        try:
            engine = BacktestEngine(initial_capital=initial_capital)
            result = engine.run_backtest(
                symbols=[symbol],
                market=market,
                start_date=start_date,
                end_date=end_date,
                strategy_mode=strategy_mode
            )
            
            if 'error' not in result:
                result['symbol'] = symbol
                result['market'] = market
                return result
            else:
                return {'symbol': symbol, 'error': result['error']}
                
        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}
    
    def _generate_summary_report(
        self,
        market: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """生成汇总报告"""
        if not self.results:
            return {'error': '无有效回测结果'}
        
        # 提取关键指标
        returns = [r['summary']['total_return'] for r in self.results if 'summary' in r]
        sharpe_ratios = [r['summary']['sharpe_ratio'] for r in self.results if 'summary' in r]
        max_drawdowns = [r['summary']['max_drawdown'] for r in self.results if 'summary' in r]
        
        # 统计分布
        report = {
            'meta': {
                'market': market,
                'start_date': start_date,
                'end_date': end_date,
                'total_symbols': len(self.results),
                'generated_at': datetime.now().isoformat()
            },
            'performance_distribution': {
                'return': {
                    'mean': round(sum(returns) / len(returns), 2) if returns else 0,
                    'median': round(sorted(returns)[len(returns)//2], 2) if returns else 0,
                    'best': round(max(returns), 2) if returns else 0,
                    'worst': round(min(returns), 2) if returns else 0,
                    'positive_count': sum(1 for r in returns if r > 0),
                    'negative_count': sum(1 for r in returns if r < 0)
                },
                'sharpe_ratio': {
                    'mean': round(sum(sharpe_ratios) / len(sharpe_ratios), 2) if sharpe_ratios else 0,
                    'best': round(max(sharpe_ratios), 2) if sharpe_ratios else 0
                },
                'max_drawdown': {
                    'mean': round(sum(max_drawdowns) / len(max_drawdowns), 2) if max_drawdowns else 0,
                    'worst': round(min(max_drawdowns), 2) if max_drawdowns else 0
                }
            },
            'top_performers': self._get_top_performers(5),
            'bottom_performers': self._get_bottom_performers(5),
            'all_results': self.results
        }
        
        return report
    
    def _get_top_performers(self, n: int) -> List[Dict]:
        """获取表现最好的N个"""
        sorted_results = sorted(
            self.results,
            key=lambda x: x.get('summary', {}).get('total_return', -999),
            reverse=True
        )
        return [
            {
                'symbol': r.get('symbol'),
                'return': r['summary']['total_return'],
                'sharpe': r['summary']['sharpe_ratio'],
                'max_dd': r['summary']['max_drawdown']
            }
            for r in sorted_results[:n] if 'summary' in r
        ]
    
    def _get_bottom_performers(self, n: int) -> List[Dict]:
        """获取表现最差的N个"""
        sorted_results = sorted(
            self.results,
            key=lambda x: x.get('summary', {}).get('total_return', 999)
        )
        return [
            {
                'symbol': r.get('symbol'),
                'return': r['summary']['total_return'],
                'sharpe': r['summary']['sharpe_ratio'],
                'max_dd': r['summary']['max_drawdown']
            }
            for r in sorted_results[:n] if 'summary' in r
        ]
    
    def save_report(self, report: Dict, output_dir: str = None):
        """保存报告到文件"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'backtest_results')
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_backtest_{report['meta']['market']}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 报告已保存: {filepath}")
        return filepath
    
    def print_summary(self, report: Dict):
        """打印汇总报告"""
        print("\n" + "="*70)
        print("📊 批量回测汇总报告")
        print("="*70)
        
        meta = report['meta']
        print(f"\n回测信息:")
        print(f"   市场: {meta['market']}")
        print(f"   周期: {meta['start_date']} ~ {meta['end_date']}")
        print(f"   标的: {meta['total_symbols']} 只")
        
        dist = report['performance_distribution']
        print(f"\n收益分布:")
        print(f"   平均收益: {dist['return']['mean']:+.2f}%")
        print(f"   中位数: {dist['return']['median']:+.2f}%")
        print(f"   最佳: {dist['return']['best']:+.2f}%")
        print(f"   最差: {dist['return']['worst']:+.2f}%")
        print(f"   正收益: {dist['return']['positive_count']} 只")
        print(f"   负收益: {dist['return']['negative_count']} 只")
        
        print(f"\n风险指标:")
        print(f"   平均夏普: {dist['sharpe_ratio']['mean']:.2f}")
        print(f"   平均最大回撤: {dist['max_drawdown']['mean']:.2f}%")
        
        print(f"\n🏆 TOP5 表现:")
        for i, p in enumerate(report['top_performers'], 1):
            print(f"   {i}. {p['symbol']}: {p['return']:+.2f}% (夏普{p['sharpe']:.2f})")
        
        print(f"\n⚠️  BOTTOM5 表现:")
        for i, p in enumerate(report['bottom_performers'], 1):
            print(f"   {i}. {p['symbol']}: {p['return']:+.2f}% (回撤{p['max_dd']:.2f}%)")


# 预定义的股票池
STOCK_UNIVERSE = {
    "A股": {
        "ETF": [
            "510300",  # 沪深300
            "510050",  # 上证50
            "159915",  # 创业板
            "588000",  # 科创50
            "512760",  # 芯片
            "515030",  # 新能源
            "512010",  # 医药
            "159928",  # 消费
            "512690",  # 酒
            "510880",  # 红利
        ],
        "个股": [
            "000001",  # 平安银行
            "000858",  # 五粮液
            "002594",  # 比亚迪
            "600519",  # 贵州茅台
            "300750",  # 宁德时代
            "601012",  # 隆基绿能
            "603288",  # 海天味业
            "600036",  # 招商银行
        ]
    },
    "US": {
        "ETF": [
            "SPY",   # 标普500
            "QQQ",   # 纳斯达克100
            "IWM",   # 罗素2000
            "VTI",   # 全市场
            "VWO",   # 新兴市场
        ],
        "个股": [
            "AAPL",  # 苹果
            "MSFT",  # 微软
            "GOOGL", # 谷歌
            "AMZN",  # 亚马逊
            "TSLA",  # 特斯拉
            "NVDA",  # 英伟达
            "META",  # Meta
            "NFLX",  # 奈飞
        ]
    }
}


def run_quick_test():
    """快速测试 - 使用少量标的"""
    print("🧪 批量回测快速测试\n")
    
    runner = BatchBacktestRunner(max_workers=2)
    
    # 测试A股ETF
    symbols = STOCK_UNIVERSE["A股"]["ETF"][:3]
    
    report = runner.run_batch(
        symbols=symbols,
        market="A股",
        start_date="20250101",
        end_date="20250228",
        strategy_mode="balanced"
    )
    
    if 'error' not in report:
        runner.print_summary(report)
    else:
        print(f"❌ {report['error']}")


if __name__ == "__main__":
    run_quick_test()
