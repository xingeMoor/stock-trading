"""
交易记录数据库
使用 SQLite 存储模拟交易和实盘交易记录
"""
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trading.db')


@dataclass
class TradeRecord:
    """交易记录"""
    id: Optional[int]
    symbol: str
    trade_date: str
    trade_type: str  # buy/sell
    strategy: str  # 策略名称
    price: float
    shares: int
    value: float
    commission: float
    pnl: float  # 仅卖出时有值
    confidence: float  # 决策置信度
    reasoning: str  # 决策理由
    created_at: str
    updated_at: str


@dataclass
class PositionRecord:
    """持仓记录"""
    id: Optional[int]
    symbol: str
    shares: int
    average_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_date: str
    updated_at: str


@dataclass
class DailySnapshot:
    """每日账户快照"""
    id: Optional[int]
    snapshot_date: str
    total_capital: float
    cash: float
    position_value: float
    total_value: float
    daily_return: float
    daily_return_pct: float
    total_return: float
    total_return_pct: float
    created_at: str


class TradingDatabase:
    """交易数据库管理类"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self):
        """初始化数据表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                price REAL NOT NULL,
                shares INTEGER NOT NULL,
                value REAL NOT NULL,
                commission REAL NOT NULL,
                pnl REAL DEFAULT 0,
                confidence REAL NOT NULL,
                reasoning TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 持仓记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                shares INTEGER NOT NULL,
                average_cost REAL NOT NULL,
                current_price REAL NOT NULL,
                market_value REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                unrealized_pnl_pct REAL NOT NULL,
                entry_date TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 每日快照表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL UNIQUE,
                total_capital REAL NOT NULL,
                cash REAL NOT NULL,
                position_value REAL NOT NULL,
                total_value REAL NOT NULL,
                daily_return REAL NOT NULL,
                daily_return_pct REAL NOT NULL,
                total_return REAL NOT NULL,
                total_return_pct REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_date ON daily_snapshots(snapshot_date)')
        
        conn.commit()
        conn.close()
    
    # ==================== 交易记录 ====================
    
    def add_trade(self, symbol: str, trade_type: str, price: float, shares: int,
                  strategy: str, confidence: float, reasoning: str,
                  commission: float = 0.0, pnl: float = 0.0,
                  trade_date: str = None) -> int:
        """
        添加交易记录
        
        Returns:
            交易记录 ID
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        value = price * shares
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades 
            (symbol, trade_date, trade_type, strategy, price, shares, value, 
             commission, pnl, confidence, reasoning, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, trade_date, trade_type, strategy, price, shares, value,
              commission, pnl, confidence, reasoning, now, now))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def get_trades(self, symbol: str = None, start_date: str = None, 
                   end_date: str = None, limit: int = 100) -> List[Dict]:
        """获取交易记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM trades WHERE 1=1'
        params = []
        
        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol)
        
        if start_date:
            query += ' AND trade_date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND trade_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY trade_date DESC, id DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_trade_history(self, symbol: str) -> List[Dict]:
        """获取单只股票的完整交易历史"""
        return self.get_trades(symbol=symbol, limit=1000)
    
    # ==================== 持仓记录 ====================
    
    def update_position(self, symbol: str, shares: int, average_cost: float,
                        current_price: float, entry_date: str = None):
        """更新持仓记录"""
        if entry_date is None:
            entry_date = datetime.now().strftime('%Y-%m-%d')
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        market_value = shares * current_price
        unrealized_pnl = (current_price - average_cost) * shares
        unrealized_pnl_pct = (current_price - average_cost) / average_cost * 100 if average_cost > 0 else 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO positions 
            (id, symbol, shares, average_cost, current_price, market_value,
             unrealized_pnl, unrealized_pnl_pct, entry_date, updated_at)
            VALUES (
                (SELECT id FROM positions WHERE symbol = ?),
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (symbol, symbol, shares, average_cost, current_price, market_value,
              unrealized_pnl, unrealized_pnl_pct, entry_date, now))
        
        conn.commit()
        conn.close()
    
    def get_positions(self) -> List[Dict]:
        """获取所有持仓"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM positions ORDER BY symbol')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """获取单只股票持仓"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM positions WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def clear_position(self, symbol: str):
        """清除持仓（卖出后）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
        conn.commit()
        conn.close()
    
    # ==================== 每日快照 ====================
    
    def add_snapshot(self, total_capital: float, cash: float, position_value: float,
                     prev_total_value: float = None, snapshot_date: str = None):
        """添加每日账户快照"""
        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_value = cash + position_value
        
        # 计算收益
        if prev_total_value is None:
            # 尝试获取前一天的快照
            prev = self.get_prev_snapshot(snapshot_date)
            prev_total_value = prev['total_value'] if prev else total_capital
        
        daily_return = total_value - prev_total_value
        daily_return_pct = daily_return / prev_total_value * 100 if prev_total_value > 0 else 0
        total_return = total_value - total_capital
        total_return_pct = total_return / total_capital * 100
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_snapshots 
            (id, snapshot_date, total_capital, cash, position_value, total_value,
             daily_return, daily_return_pct, total_return, total_return_pct, created_at)
            VALUES (
                (SELECT id FROM daily_snapshots WHERE snapshot_date = ?),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (snapshot_date, snapshot_date, total_capital, cash, position_value,
              total_value, daily_return, daily_return_pct, total_return, 
              total_return_pct, now))
        
        conn.commit()
        conn.close()
    
    def get_snapshots(self, start_date: str = None, end_date: str = None, 
                      limit: int = 100) -> List[Dict]:
        """获取每日快照"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM daily_snapshots WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND snapshot_date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND snapshot_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY snapshot_date DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_prev_snapshot(self, date: str) -> Optional[Dict]:
        """获取指定日期之前的快照"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM daily_snapshots 
            WHERE snapshot_date < ? 
            ORDER BY snapshot_date DESC 
            LIMIT 1
        ''', (date,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """获取最新快照"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM daily_snapshots 
            ORDER BY snapshot_date DESC 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # ==================== 统计查询 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取交易统计"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 总交易次数
        cursor.execute('SELECT COUNT(*) as count FROM trades')
        total_trades = cursor.fetchone()['count']
        
        # 买入/卖出次数
        cursor.execute('SELECT trade_type, COUNT(*) as count FROM trades GROUP BY trade_type')
        type_counts = {row['trade_type']: row['count'] for row in cursor.fetchall()}
        
        # 平均盈亏
        cursor.execute('''
            SELECT AVG(pnl) as avg_pnl, SUM(pnl) as total_pnl 
            FROM trades WHERE trade_type = 'sell'
        ''')
        pnl_stats = cursor.fetchone()
        
        # 胜率
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                COUNT(*) as total
            FROM trades WHERE trade_type = 'sell'
        ''')
        win_stats = cursor.fetchone()
        win_rate = win_stats['wins'] / win_stats['total'] * 100 if win_stats['total'] > 0 else 0
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'buy_count': type_counts.get('buy', 0),
            'sell_count': type_counts.get('sell', 0),
            'avg_pnl': pnl_stats['avg_pnl'] or 0,
            'total_pnl': pnl_stats['total_pnl'] or 0,
            'win_count': win_stats['wins'],
            'win_rate': round(win_rate, 2)
        }
    
    def get_symbol_statistics(self, symbol: str) -> Dict[str, Any]:
        """获取单只股票的统计"""
        trades = self.get_trade_history(symbol)
        
        buy_trades = [t for t in trades if t['trade_type'] == 'buy']
        sell_trades = [t for t in trades if t['trade_type'] == 'sell']
        
        total_pnl = sum(t['pnl'] for t in sell_trades)
        winning_trades = sum(1 for t in sell_trades if t['pnl'] > 0)
        win_rate = winning_trades / len(sell_trades) * 100 if sell_trades else 0
        
        return {
            'symbol': symbol,
            'total_trades': len(trades),
            'buy_count': len(buy_trades),
            'sell_count': len(sell_trades),
            'total_pnl': total_pnl,
            'win_count': winning_trades,
            'win_rate': round(win_rate, 2)
        }
    
    def export_to_csv(self, output_path: str):
        """导出交易记录到 CSV"""
        import csv
        
        trades = self.get_trades(limit=10000)
        
        if not trades:
            return
        
        with open(output_path, 'w', newline='') as f:
            fieldnames = trades[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trades)
        
        print(f"✓ 已导出 {len(trades)} 条交易记录到：{output_path}")
    
    def close_all(self):
        """关闭所有持仓（清仓）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM positions')
        conn.commit()
        conn.close()
        
        print("✓ 已清空所有持仓记录")


if __name__ == "__main__":
    # 测试
    db = TradingDatabase()
    
    # 添加测试交易
    trade_id = db.add_trade(
        symbol="GOOGL",
        trade_type="buy",
        price=185.50,
        shares=50,
        strategy="relaxed_v2",
        confidence=0.75,
        reasoning="RSI 超卖 + MACD 金叉 + 趋势向上"
    )
    print(f"✓ 添加交易记录 ID: {trade_id}")
    
    # 更新持仓
    db.update_position(
        symbol="GOOGL",
        shares=50,
        average_cost=185.50,
        current_price=188.20
    )
    print("✓ 更新持仓记录")
    
    # 获取统计
    stats = db.get_statistics()
    print(f"\n📊 交易统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 获取持仓
    positions = db.get_positions()
    print(f"\n📈 当前持仓:")
    for pos in positions:
        print(f"  {pos['symbol']}: {pos['shares']}股, 盈亏：${pos['unrealized_pnl']:.2f}")
