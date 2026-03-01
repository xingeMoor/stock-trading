"""
回测数据库管理
存储回测结果，支持策略对比分析
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'backtest.db')


class BacktestDatabase:
    """回测数据库"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据表"""
        cursor = self.conn.cursor()
        
        # 回测批次表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_batches (
                batch_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                strategy_name TEXT NOT NULL,
                strategy_params TEXT,  -- JSON
                market TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_stocks INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary_stats TEXT  -- JSON
            )
        ''')
        
        # 个股回测结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                sector TEXT,
                initial_value REAL,
                final_value REAL,
                total_return REAL,
                annualized_return REAL,
                volatility REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                trades_count INTEGER,
                win_rate REAL,
                daily_values TEXT,  -- JSON array
                trades TEXT,  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES backtest_batches(batch_id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch ON backtest_results(batch_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON backtest_results(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sector ON backtest_results(sector)')
        
        self.conn.commit()
    
    def save_backtest_batch(
        self,
        batch_id: str,
        name: str,
        strategy_name: str,
        market: str,
        start_date: str,
        end_date: str,
        results: List[Dict],
        description: str = "",
        strategy_params: Dict = None
    ) -> bool:
        """保存回测批次"""
        try:
            cursor = self.conn.cursor()
            
            # 计算汇总统计
            returns = [r['total_return'] for r in results if 'error' not in r]
            summary = {
                'avg_return': round(sum(returns)/len(returns), 2) if returns else 0,
                'median_return': round(sorted(returns)[len(returns)//2], 2) if returns else 0,
                'best_return': round(max(returns), 2) if returns else 0,
                'worst_return': round(min(returns), 2) if returns else 0,
                'positive_count': sum(1 for r in returns if r > 0),
                'negative_count': sum(1 for r in returns if r < 0),
            }
            
            # 插入批次记录
            cursor.execute('''
                INSERT OR REPLACE INTO backtest_batches
                (batch_id, name, description, strategy_name, strategy_params, market,
                 start_date, end_date, total_stocks, summary_stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch_id,
                name,
                description,
                strategy_name,
                json.dumps(strategy_params or {}),
                market,
                start_date,
                end_date,
                len(results),
                json.dumps(summary)
            ))
            
            # 插入个股结果
            for result in results:
                if 'error' in result:
                    continue
                
                cursor.execute('''
                    INSERT INTO backtest_results
                    (batch_id, symbol, sector, initial_value, final_value,
                     total_return, annualized_return, volatility, sharpe_ratio,
                     max_drawdown, trades_count, win_rate, daily_values, trades)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    batch_id,
                    result.get('symbol'),
                    result.get('sector', 'Unknown'),
                    result.get('initial_value'),
                    result.get('final_value'),
                    result.get('total_return'),
                    result.get('annualized_return'),
                    result.get('volatility'),
                    result.get('sharpe_ratio'),
                    result.get('max_drawdown'),
                    result.get('trades_count'),
                    result.get('win_rate'),
                    json.dumps(result.get('daily_values', [])),
                    json.dumps(result.get('trades', []))
                ))
            
            self.conn.commit()
            print(f"✅ 已保存回测批次: {batch_id} ({len(results)} 只股票)")
            return True
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            self.conn.rollback()
            return False
    
    def get_all_batches(self) -> List[Dict]:
        """获取所有回测批次"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT batch_id, name, strategy_name, market, start_date, end_date,
                   total_stocks, created_at, summary_stats
            FROM backtest_batches
            ORDER BY created_at DESC
        ''')
        
        batches = []
        for row in cursor.fetchall():
            batches.append({
                'batch_id': row['batch_id'],
                'name': row['name'],
                'strategy_name': row['strategy_name'],
                'market': row['market'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'total_stocks': row['total_stocks'],
                'created_at': row['created_at'],
                'summary': json.loads(row['summary_stats'] or '{}')
            })
        
        return batches
    
    def get_batch_results(self, batch_id: str) -> List[Dict]:
        """获取指定批次的详细结果"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM backtest_results
            WHERE batch_id = ?
            ORDER BY total_return DESC
        ''', (batch_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row['symbol'],
                'sector': row['sector'],
                'total_return': row['total_return'],
                'annualized_return': row['annualized_return'],
                'sharpe_ratio': row['sharpe_ratio'],
                'max_drawdown': row['max_drawdown'],
                'trades_count': row['trades_count'],
                'win_rate': row['win_rate'],
            })
        
        return results
    
    def get_batch_comparison(self, batch_ids: List[str]) -> Dict[str, Any]:
        """对比多个批次"""
        cursor = self.conn.cursor()
        
        comparison = {}
        for batch_id in batch_ids:
            cursor.execute('''
                SELECT b.name, b.strategy_name, b.summary_stats,
                       AVG(r.total_return) as avg_return,
                       AVG(r.sharpe_ratio) as avg_sharpe,
                       AVG(r.max_drawdown) as avg_dd
                FROM backtest_batches b
                LEFT JOIN backtest_results r ON b.batch_id = r.batch_id
                WHERE b.batch_id = ?
                GROUP BY b.batch_id
            ''', (batch_id,))
            
            row = cursor.fetchone()
            if row:
                comparison[batch_id] = {
                    'name': row['name'],
                    'strategy': row['strategy_name'],
                    'summary': json.loads(row['summary_stats'] or '{}'),
                    'avg_return': round(row['avg_return'], 2) if row['avg_return'] else 0,
                    'avg_sharpe': round(row['avg_sharpe'], 2) if row['avg_sharpe'] else 0,
                    'avg_drawdown': round(row['avg_dd'], 2) if row['avg_dd'] else 0,
                }
        
        return comparison
    
    def get_sector_analysis(self, batch_id: str) -> Dict[str, Any]:
        """获取行业分析"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT sector,
                   COUNT(*) as count,
                   AVG(total_return) as avg_return,
                   AVG(sharpe_ratio) as avg_sharpe,
                   AVG(max_drawdown) as avg_dd
            FROM backtest_results
            WHERE batch_id = ?
            GROUP BY sector
            ORDER BY avg_return DESC
        ''', (batch_id,))
        
        sectors = {}
        for row in cursor.fetchall():
            sectors[row['sector']] = {
                'count': row['count'],
                'avg_return': round(row['avg_return'] or 0, 2),
                'avg_sharpe': round(row['avg_sharpe'] or 0, 2),
                'avg_drawdown': round(row['avg_dd'] or 0, 2),
            }
        
        return sectors
    
    def delete_batch(self, batch_id: str) -> bool:
        """删除批次"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM backtest_results WHERE batch_id = ?', (batch_id,))
            cursor.execute('DELETE FROM backtest_batches WHERE batch_id = ?', (batch_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False


def test_backtest_db():
    """测试回测数据库"""
    print("🧪 测试回测数据库\n")
    
    db = BacktestDatabase()
    
    # 模拟保存一个批次
    batch_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    results = [
        {'symbol': 'AAPL', 'sector': 'Technology', 'total_return': 15.5, 'sharpe_ratio': 1.2},
        {'symbol': 'MSFT', 'sector': 'Technology', 'total_return': 20.3, 'sharpe_ratio': 1.5},
        {'symbol': 'JPM', 'sector': 'Financial', 'total_return': 8.7, 'sharpe_ratio': 0.8},
    ]
    
    print("1️⃣  保存测试批次...")
    success = db.save_backtest_batch(
        batch_id=batch_id,
        name="测试策略",
        strategy_name="MA_Crossover",
        market="US",
        start_date="2024-01-01",
        end_date="2024-12-31",
        results=results
    )
    
    if success:
        print("   ✅ 保存成功")
        
        print("\n2️⃣  查询所有批次...")
        batches = db.get_all_batches()
        print(f"   找到 {len(batches)} 个批次")
        
        print("\n3️⃣  查询批次详情...")
        details = db.get_batch_results(batch_id)
        print(f"   包含 {len(details)} 条记录")
        
        print("\n4️⃣  行业分析...")
        sectors = db.get_sector_analysis(batch_id)
        for sector, stats in sectors.items():
            print(f"   {sector}: {stats['avg_return']:+.2f}%")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_backtest_db()
