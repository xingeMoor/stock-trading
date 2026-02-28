"""
本地数据湖 - Data Lake
核心功能:
1. SQLite历史数据存储 (3-5年数据)
2. 数据预热机制 (开盘前预加载)
3. 增量更新 (只更新最新数据)
4. 多源数据融合与校验
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import hashlib

# 数据库路径
DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'lake')
os.makedirs(DB_DIR, exist_ok=True)

class DataLake:
    """
    本地数据湖
    
    设计原则:
    - 按市场分库 (a_share.db / us_stock.db)
    - 按表存储不同粒度数据 (daily / weekly / monthly)
    - 元数据记录更新时间和来源
    """
    
    def __init__(self):
        self.connections = {}
        
    def _get_db_path(self, market: str) -> str:
        """获取数据库路径"""
        db_name = f"{market.lower().replace(' ', '_')}.db"
        return os.path.join(DB_DIR, db_name)
    
    def _get_connection(self, market: str) -> sqlite3.Connection:
        """获取数据库连接"""
        if market not in self.connections:
            db_path = self._get_db_path(market)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections[market] = conn
            self._init_tables(market)
        return self.connections[market]
    
    def _init_tables(self, market: str):
        """初始化数据表"""
        conn = self.connections[market]
        cursor = conn.cursor()
        
        # K线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kline_daily (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                amount REAL,
                change_pct REAL,
                turnover REAL,
                updated_at TEXT,
                source TEXT,
                PRIMARY KEY (symbol, date)
            )
        ''')
        
        # 实时行情快照表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS realtime_snapshots (
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL,
                open REAL,
                high REAL,
                low REAL,
                volume INTEGER,
                bid REAL,
                ask REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        # 元数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                market_cap REAL,
                first_date TEXT,
                last_date TEXT,
                total_records INTEGER,
                last_updated TEXT,
                data_source TEXT
            )
        ''')
        
        # 更新日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                update_type TEXT,
                start_date TEXT,
                end_date TEXT,
                records_count INTEGER,
                update_time TEXT,
                status TEXT,
                message TEXT
            )
        ''')
        
        conn.commit()
    
    def save_kline(self, market: str, symbol: str, df: pd.DataFrame, source: str = "api"):
        """
        保存K线数据
        
        Args:
            market: 市场 (A股/US)
            symbol: 股票代码
            df: DataFrame包含OHLCV数据
            source: 数据来源
        """
        if df.empty:
            return
        
        conn = self._get_connection(market)
        
        # 标准化数据
        df = df.copy()
        df['symbol'] = symbol
        df['updated_at'] = datetime.now().isoformat()
        df['source'] = source
        
        # 确保列名正确
        column_mapping = {
            '日期': 'date',
            'date': 'date',
            '开盘': 'open',
            'open': 'open',
            '收盘': 'close',
            'close': 'close',
            '最高': 'high',
            'high': 'high',
            '最低': 'low',
            'low': 'low',
            '成交量': 'volume',
            'volume': 'volume',
            '成交额': 'amount',
            'amount': 'amount',
            '涨跌幅': 'change_pct',
            'change_pct': 'change_pct',
            '换手率': 'turnover',
            'turnover': 'turnover'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 选择需要的列
        required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 
                        'volume', 'amount', 'change_pct', 'turnover', 'updated_at', 'source']
        
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
        
        df = df[required_cols]
        
        # 使用REPLACE INTO实现upsert
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute('''
                REPLACE INTO kline_daily 
                (symbol, date, open, high, low, close, volume, amount, 
                 change_pct, turnover, updated_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(row))
        
        conn.commit()
        
        # 更新元数据
        self._update_metadata(market, symbol, df)
        
        print(f"   ✅ {symbol}: 保存 {len(df)} 条记录")
    
    def _update_metadata(self, market: str, symbol: str, df: pd.DataFrame):
        """更新元数据"""
        conn = self._get_connection(market)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO metadata
            (symbol, first_date, last_date, total_records, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            symbol,
            df['date'].min() if not df.empty else None,
            df['date'].max() if not df.empty else None,
            len(df),
            datetime.now().isoformat()
        ))
        
        conn.commit()
    
    def get_kline(self, market: str, symbol: str, 
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        查询K线数据
        
        Returns:
            DataFrame with OHLCV data
        """
        conn = self._get_connection(market)
        
        query = "SELECT * FROM kline_daily WHERE symbol = ?"
        params = [symbol]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params)
        
        return df
    
    def get_data_range(self, market: str, symbol: str) -> Dict[str, Any]:
        """获取数据时间范围"""
        conn = self._get_connection(market)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as count
            FROM kline_daily WHERE symbol = ?
        ''', (symbol,))
        
        row = cursor.fetchone()
        return {
            'first_date': row['first_date'],
            'last_date': row['last_date'],
            'count': row['count']
        }
    
    def incremental_update(self, market: str, symbol: str, 
                          fetch_func, **fetch_kwargs) -> int:
        """
        增量更新数据
        
        Args:
            market: 市场
            symbol: 股票代码
            fetch_func: 数据获取函数
            fetch_kwargs: 传递给fetch_func的参数
        
        Returns:
            新增记录数
        """
        print(f"\n🔄 增量更新 {symbol}...")
        
        # 检查现有数据范围
        existing = self.get_data_range(market, symbol)
        
        if existing['last_date']:
            # 从最后一天的下一天开始更新
            last_date = datetime.strptime(existing['last_date'], '%Y-%m-%d')
            start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
            end_date = datetime.now().strftime('%Y%m%d')
            
            if start_date > end_date:
                print(f"   ⏭️  数据已是最新 ({existing['last_date']})")
                return 0
            
            print(f"   📅 更新范围: {start_date} ~ {end_date}")
        else:
            # 全新下载，获取3年历史
            start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y%m%d')
            end_date = datetime.now().strftime('%Y%m%d')
            print(f"   📅 全新下载: {start_date} ~ {end_date}")
        
        # 获取新数据
        try:
            df = fetch_func(symbol, start_date, end_date, **fetch_kwargs)
            
            if df is not None and not df.empty:
                self.save_kline(market, symbol, df, source="incremental_update")
                
                # 记录更新日志
                self._log_update(market, symbol, start_date, end_date, len(df), "success")
                
                return len(df)
            else:
                print(f"   ⚠️  无新数据")
                return 0
                
        except Exception as e:
            print(f"   ❌ 更新失败: {e}")
            self._log_update(market, symbol, start_date, end_date, 0, "failed", str(e))
            return 0
    
    def _log_update(self, market: str, symbol: str, start: str, end: str, 
                   count: int, status: str, message: str = ""):
        """记录更新日志"""
        conn = self._get_connection(market)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO update_log
            (symbol, update_type, start_date, end_date, records_count, update_time, status, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, 'incremental', start, end, count, 
              datetime.now().isoformat(), status, message))
        
        conn.commit()
    
    def warmup_cache(self, symbols: List[str], market: str = "A股"):
        """
        数据预热 - 开盘前加载常用数据到内存
        
        Args:
            symbols: 需要预热的股票列表
            market: 市场
        """
        print(f"\n🔥 数据预热 ({market})...")
        print(f"   预热标的: {len(symbols)} 只")
        
        warmed_data = {}
        
        for symbol in symbols:
            # 加载最近60天数据
            df = self.get_kline(market, symbol, 
                               start_date=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'))
            
            if not df.empty:
                warmed_data[symbol] = df
                print(f"   ✅ {symbol}: {len(df)} 天数据")
            else:
                print(f"   ⚠️  {symbol}: 无数据")
        
        print(f"   🔥 预热完成: {len(warmed_data)} 只")
        
        return warmed_data
    
    def batch_download(self, symbols: List[str], market: str, 
                       fetch_func, max_workers: int = 5):
        """
        批量下载历史数据
        
        Args:
            symbols: 股票代码列表
            market: 市场
            fetch_func: 数据获取函数
            max_workers: 并发数
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print(f"\n📥 批量下载 {market} 数据...")
        print(f"   标的数量: {len(symbols)}")
        
        def download_one(symbol):
            try:
                count = self.incremental_update(market, symbol, fetch_func)
                return symbol, count, "success"
            except Exception as e:
                return symbol, 0, f"error: {e}"
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(download_one, sym): sym for sym in symbols}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    sym, count, status = result
                    if status == "success":
                        print(f"   ✅ {sym}: +{count} 条")
                    else:
                        print(f"   ❌ {sym}: {status}")
                except Exception as e:
                    print(f"   ❌ {symbol}: {e}")
        
        # 统计
        success_count = sum(1 for r in results if r[2] == "success")
        total_new = sum(r[1] for r in results)
        
        print(f"\n📊 下载完成: {success_count}/{len(symbols)} 成功")
        print(f"   新增数据: {total_new} 条")
        
        return results
    
    def get_stats(self, market: str) -> Dict[str, Any]:
        """获取数据湖统计信息"""
        conn = self._get_connection(market)
        cursor = conn.cursor()
        
        # 总股票数
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM kline_daily")
        total_symbols = cursor.fetchone()[0]
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM kline_daily")
        total_records = cursor.fetchone()[0]
        
        # 日期范围
        cursor.execute("SELECT MIN(date), MAX(date) FROM kline_daily")
        row = cursor.fetchone()
        
        # 最近更新
        cursor.execute("SELECT MAX(update_time) FROM update_log WHERE status = 'success'")
        last_update = cursor.fetchone()[0]
        
        return {
            'market': market,
            'total_symbols': total_symbols,
            'total_records': total_records,
            'date_range': f"{row[0]} ~ {row[1]}" if row[0] else None,
            'last_update': last_update
        }


def test_data_lake():
    """测试数据湖"""
    print("🧪 测试本地数据湖\n")
    
    lake = DataLake()
    
    # 测试1: 保存模拟数据
    print("1️⃣  测试保存数据...")
    mock_df = pd.DataFrame({
        'date': ['2026-02-26', '2026-02-27', '2026-02-28'],
        'open': [10.0, 10.5, 11.0],
        'high': [10.8, 11.2, 11.5],
        'low': [9.8, 10.3, 10.8],
        'close': [10.5, 11.0, 11.3],
        'volume': [10000, 15000, 12000],
        'amount': [105000, 165000, 135600],
        'change_pct': [2.5, 4.8, 2.7],
        'turnover': [5.2, 7.8, 6.2]
    })
    
    lake.save_kline("A股", "000001", mock_df, source="test")
    print("   ✅ 保存成功")
    
    # 测试2: 查询数据
    print("\n2️⃣  测试查询数据...")
    df = lake.get_kline("A股", "000001")
    print(f"   ✅ 查询到 {len(df)} 条记录")
    print(f"   📊 最新收盘价: ¥{df['close'].iloc[-1]:.2f}")
    
    # 测试3: 数据范围
    print("\n3️⃣  测试数据范围...")
    range_info = lake.get_data_range("A股", "000001")
    print(f"   📅 范围: {range_info['first_date']} ~ {range_info['last_date']}")
    print(f"   📈 总数: {range_info['count']} 条")
    
    # 测试4: 统计信息
    print("\n4️⃣  测试统计信息...")
    stats = lake.get_stats("A股")
    print(f"   📊 {stats}")
    
    print("\n✅ 数据湖测试完成!")


if __name__ == "__main__":
    test_data_lake()
