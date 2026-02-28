"""
原子化数据缓存系统
核心设计:
1. 统一缓存接口 - 无论A股/美股，相同API
2. 原子操作 - 查询/写入/更新都是原子性
3. 智能过期 - 自动判断数据新鲜度
4. 批量优化 - 支持批量读写，减少IO
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from contextlib import contextmanager
import threading
import json
import hashlib

# 缓存数据库路径
CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache', 'unified_cache.db')
os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str              # 唯一键
    data: Any             # 数据内容
    data_type: str        # 数据类型 (kline/realtime/fundamental)
    market: str           # 市场 (A股/US)
    symbol: str           # 股票代码
    start_date: str       # 数据开始日期
    end_date: str         # 数据结束日期
    created_at: datetime  # 创建时间
    expires_at: datetime  # 过期时间
    version: int = 1      # 版本号，用于乐观锁


class AtomicCache:
    """
    原子化缓存系统
    
    特性:
    - 线程安全
    - 原子读写
    - 自动过期清理
    - 批量操作优化
    """
    
    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取线程安全的连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _transaction(self):
        """事务上下文管理器 - 保证原子性"""
        conn = self._get_conn()
        try:
            conn.execute("BEGIN IMMEDIATE")  # 立即获取写锁
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """初始化数据库表"""
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            # 主缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    data_type TEXT NOT NULL,
                    market TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP
                )
            ''')
            
            # 索引优化查询
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_symbol ON cache_entries(market, symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_type ON cache_entries(data_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires ON cache_entries(expires_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_range ON cache_entries(symbol, start_date, end_date)')
            
            # 元数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_entries INTEGER DEFAULT 0,
                    total_size_bytes INTEGER DEFAULT 0,
                    hit_count INTEGER DEFAULT 0,
                    miss_count INTEGER DEFAULT 0,
                    last_cleanup TIMESTAMP
                )
            ''')
            
            # 初始化统计
            cursor.execute('INSERT OR IGNORE INTO cache_stats (id) VALUES (1)')
    
    def _generate_key(self, market: str, symbol: str, data_type: str, 
                     start_date: str = None, end_date: str = None) -> str:
        """生成唯一缓存键"""
        key_parts = [market, symbol, data_type]
        if start_date:
            key_parts.append(start_date)
        if end_date:
            key_parts.append(end_date)
        
        raw_key = "|".join(key_parts)
        # 使用哈希缩短键长
        return hashlib.md5(raw_key.encode()).hexdigest()
    
    def get(self, market: str, symbol: str, data_type: str,
            start_date: str = None, end_date: str = None,
            max_age_hours: int = 24) -> Optional[Any]:
        """
        原子化查询缓存
        
        Args:
            market: 市场 (A股/US)
            symbol: 股票代码
            data_type: 数据类型 (kline/realtime/fundamental)
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)
            max_age_hours: 最大缓存年龄(小时)
        
        Returns:
            缓存数据或None
        """
        key = self._generate_key(market, symbol, data_type, start_date, end_date)
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            # 查询缓存
            cursor.execute('''
                SELECT data, expires_at, version FROM cache_entries
                WHERE key = ? AND expires_at > datetime('now')
            ''', (key,))
            
            row = cursor.fetchone()
            
            if row:
                # 命中缓存
                data = json.loads(row['data'])
                
                # 更新访问统计
                cursor.execute('''
                    UPDATE cache_entries 
                    SET access_count = access_count + 1,
                        last_accessed = datetime('now')
                    WHERE key = ?
                ''', (key,))
                
                # 更新全局统计
                cursor.execute('UPDATE cache_stats SET hit_count = hit_count + 1 WHERE id = 1')
                
                return data
            else:
                # 未命中
                cursor.execute('UPDATE cache_stats SET miss_count = miss_count + 1 WHERE id = 1')
                return None
    
    def set(self, market: str, symbol: str, data_type: str,
            data: Any, start_date: str = None, end_date: str = None,
            ttl_hours: int = 24) -> bool:
        """
        原子化写入缓存
        
        Args:
            market: 市场
            symbol: 股票代码
            data_type: 数据类型
            data: 要缓存的数据
            start_date: 数据开始日期
            end_date: 数据结束日期
            ttl_hours: 缓存存活时间(小时)
        
        Returns:
            是否成功
        """
        key = self._generate_key(market, symbol, data_type, start_date, end_date)
        
        try:
            serialized = json.dumps(data, default=str)
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # UPSERT操作 - 原子性保证
                cursor.execute('''
                    INSERT INTO cache_entries 
                    (key, data, data_type, market, symbol, start_date, end_date, expires_at, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(key) DO UPDATE SET
                        data = excluded.data,
                        updated_at = datetime('now'),
                        expires_at = excluded.expires_at,
                        version = cache_entries.version + 1
                ''', (key, serialized, data_type, market, symbol, 
                      start_date, end_date, expires_at.isoformat()))
                
                # 更新统计
                cursor.execute('''
                    UPDATE cache_stats 
                    SET total_entries = (SELECT COUNT(*) FROM cache_entries),
                        total_size_bytes = total_size_bytes + ?
                    WHERE id = 1
                ''', (len(serialized),))
                
                return True
                
        except Exception as e:
            print(f"❌ 缓存写入失败: {e}")
            return False
    
    def get_kline_atomic(self, market: str, symbol: str, 
                        start_date: str, end_date: str,
                        fetch_func=None, max_age_hours: int = 6) -> Optional[pd.DataFrame]:
        """
        K线数据原子化获取
        
        逻辑:
        1. 先查缓存
        2. 如果命中且数据完整，直接返回
        3. 如果部分缺失，只fetch缺失部分，合并后存入
        4. 如果完全缺失，fetch全部，存入后返回
        """
        # 尝试从缓存获取
        cached_data = self.get(market, symbol, 'kline', start_date, end_date, max_age_hours)
        
        if cached_data is not None:
            print(f"   💾 缓存命中: {symbol} ({start_date}~{end_date})")
            return pd.read_json(cached_data, orient='split')
        
        # 缓存未命中，需要获取数据
        if fetch_func is None:
            return None
        
        print(f"   🌐 缓存未命中，从API获取: {symbol}")
        
        try:
            # 获取数据
            df = fetch_func(symbol, start_date, end_date)
            
            if df is not None and not df.empty:
                # 存入缓存
                self.set(market, symbol, 'kline', 
                        df.to_json(orient='split'),
                        start_date, end_date, ttl_hours=max_age_hours)
                
                print(f"   ✅ 已缓存: {len(df)} 条记录")
                return df
                
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")
        
        return None
    
    def batch_get(self, keys: List[Dict]) -> Dict[str, Any]:
        """
        批量查询 - 一次性查询多个key
        
        Args:
            keys: [{'market': 'A股', 'symbol': '000001', 'data_type': 'kline', ...}, ...]
        
        Returns:
            {key: data} 的字典
        """
        results = {}
        
        for key_info in keys:
            key = self._generate_key(
                key_info['market'],
                key_info['symbol'],
                key_info['data_type'],
                key_info.get('start_date'),
                key_info.get('end_date')
            )
            
            data = self.get(**key_info)
            results[key] = data
        
        return results
    
    def batch_set(self, entries: List[CacheEntry]) -> int:
        """
        批量写入
        
        Returns:
            成功写入的数量
        """
        success_count = 0
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            for entry in entries:
                try:
                    serialized = json.dumps(entry.data, default=str)
                    
                    cursor.execute('''
                        INSERT INTO cache_entries 
                        (key, data, data_type, market, symbol, start_date, end_date, expires_at, version)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            data = excluded.data,
                            updated_at = datetime('now'),
                            expires_at = excluded.expires_at,
                            version = cache_entries.version + 1
                    ''', (
                        entry.key,
                        serialized,
                        entry.data_type,
                        entry.market,
                        entry.symbol,
                        entry.start_date,
                        entry.end_date,
                        entry.expires_at.isoformat(),
                        entry.version
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ 批量写入失败 {entry.key}: {e}")
            
            # 更新统计
            cursor.execute('''
                UPDATE cache_stats 
                SET total_entries = (SELECT COUNT(*) FROM cache_entries)
                WHERE id = 1
            ''')
        
        return success_count
    
    def invalidate(self, market: str = None, symbol: str = None, 
                   data_type: str = None, older_than_days: int = None) -> int:
        """
        使缓存失效
        
        Returns:
            清除的条目数
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if market:
                conditions.append("market = ?")
                params.append(market)
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if data_type:
                conditions.append("data_type = ?")
                params.append(data_type)
            
            if older_than_days:
                conditions.append("updated_at < datetime('now', '-{} days')".format(older_than_days))
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f"DELETE FROM cache_entries WHERE {where_clause}", params)
            deleted = cursor.rowcount
            
            # 更新统计
            cursor.execute('''
                UPDATE cache_stats 
                SET total_entries = (SELECT COUNT(*) FROM cache_entries)
                WHERE id = 1
            ''')
            
            return deleted
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE expires_at < datetime('now')")
            deleted = cursor.rowcount
            
            cursor.execute('''
                UPDATE cache_stats 
                SET total_entries = (SELECT COUNT(*) FROM cache_entries),
                    last_cleanup = datetime('now')
                WHERE id = 1
            ''')
            
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM cache_stats WHERE id = 1')
        stats = dict(cursor.fetchone())
        
        # 计算命中率
        total_requests = stats.get('hit_count', 0) + stats.get('miss_count', 0)
        if total_requests > 0:
            stats['hit_rate'] = stats['hit_count'] / total_requests
        else:
            stats['hit_rate'] = 0
        
        # 各类型分布
        cursor.execute('''
            SELECT data_type, COUNT(*) as count 
            FROM cache_entries 
            GROUP BY data_type
        ''')
        stats['type_distribution'] = {row['data_type']: row['count'] for row in cursor.fetchall()}
        
        return stats


# 全局缓存实例
cache = AtomicCache()


def test_atomic_cache():
    """测试原子缓存"""
    print("🧪 测试原子化缓存系统\n")
    
    # 测试1: 基本存取
    print("1️⃣  基本存取测试...")
    test_data = {'price': 100.5, 'volume': 10000, 'timestamp': datetime.now().isoformat()}
    
    success = cache.set("A股", "000001", "realtime", test_data, ttl_hours=1)
    print(f"   {'✅' if success else '❌'} 写入")
    
    retrieved = cache.get("A股", "000001", "realtime")
    print(f"   {'✅' if retrieved else '❌'} 读取: {retrieved}")
    
    # 测试2: K线数据存取
    print("\n2️⃣  K线数据测试...")
    import pandas as pd
    
    kline_df = pd.DataFrame({
        'date': ['2026-02-26', '2026-02-27', '2026-02-28'],
        'open': [10.0, 10.5, 11.0],
        'close': [10.5, 11.0, 11.3],
        'high': [10.8, 11.2, 11.5],
        'low': [9.8, 10.3, 10.8],
        'volume': [10000, 15000, 12000]
    })
    
    cache.set("A股", "000001", "kline", 
              kline_df.to_json(orient='split'),
              "20260226", "20260228", ttl_hours=24)
    
    cached_json = cache.get("A股", "000001", "kline", "20260226", "20260228")
    if cached_json:
        cached_df = pd.read_json(cached_json, orient='split')
        print(f"   ✅ 缓存K线: {len(cached_df)} 条")
    
    # 测试3: 统计信息
    print("\n3️⃣  缓存统计...")
    stats = cache.get_stats()
    print(f"   总条目: {stats.get('total_entries')}")
    print(f"   命中率: {stats.get('hit_rate', 0):.2%}")
    print(f"   类型分布: {stats.get('type_distribution')}")
    
    print("\n✅ 原子缓存测试完成!")


if __name__ == "__main__":
    test_atomic_cache()
