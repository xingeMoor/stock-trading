"""
Massive API 数据缓存管理器
支持SQLite缓存，提供TTL过期机制
"""
import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import threading


class CacheTTL(Enum):
    """缓存过期时间配置 (秒)"""
    DAILY_DATA = 86400      # 日线数据: 1天
    MINUTE_DATA = 3600      # 分钟线数据: 1小时
    SNAPSHOT = 60           # 快照数据: 1分钟
    QUOTE = 30              # 报价数据: 30秒
    TRADE = 10              # 成交数据: 10秒
    INDICATOR = 3600        # 技术指标: 1小时
    TICKER_DETAILS = 604800 # 股票详情: 7天
    MARKET_STATUS = 60      # 市场状态: 1分钟
    DEFAULT = 3600          # 默认: 1小时


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    endpoint: str
    symbol: Optional[str]
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class MassiveCache:
    """
    Massive API 数据缓存管理器
    
    使用SQLite作为后端存储，支持:
    - TTL自动过期
    - 按endpoint/symbol查询
    - 统计信息
    - 线程安全
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化缓存管理器
        
        Args:
            db_path: SQLite数据库路径，默认为 ~/.massive_cache/cache.db
        """
        if db_path is None:
            cache_dir = os.path.expanduser("~/.massive_cache")
            os.makedirs(cache_dir, exist_ok=True)
            db_path = os.path.join(cache_dir, "cache.db")
        
        self._db_path = db_path
        self._lock = threading.RLock()
        self._local_cache: Dict[str, CacheEntry] = {}
        self._local_cache_max_size = 1000
        
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    endpoint TEXT NOT NULL,
                    symbol TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoint ON cache_entries(endpoint)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol ON cache_entries(symbol)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires ON cache_entries(expires_at)
            """)
            
            conn.commit()
    
    def _generate_key(self, endpoint: str, symbol: Optional[str], params: Dict[str, Any]) -> str:
        """
        生成缓存key
        
        Format: massive:{endpoint}:{symbol}:{params_hash}
        """
        # 将参数排序后序列化，确保相同参数生成相同key
        params_str = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:16]
        
        symbol_part = symbol.upper() if symbol else "NONE"
        return f"massive:{endpoint}:{symbol_part}:{params_hash}"
    
    def _get_ttl(self, endpoint: str) -> int:
        """根据endpoint获取对应的TTL"""
        endpoint_lower = endpoint.lower()
        
        if 'agg' in endpoint_lower or 'candle' in endpoint_lower:
            # K线数据根据timespan判断
            if 'minute' in endpoint_lower or 'min' in endpoint_lower:
                return CacheTTL.MINUTE_DATA.value
            return CacheTTL.DAILY_DATA.value
        
        if 'snapshot' in endpoint_lower:
            return CacheTTL.SNAPSHOT.value
        
        if 'quote' in endpoint_lower:
            return CacheTTL.QUOTE.value
        
        if 'trade' in endpoint_lower:
            return CacheTTL.TRADE.value
        
        if any(indicator in endpoint_lower for indicator in ['sma', 'ema', 'macd', 'rsi', 'stoch', 'cci', 'adx', 'williams']):
            return CacheTTL.INDICATOR.value
        
        if 'ticker_detail' in endpoint_lower:
            return CacheTTL.TICKER_DETAILS.value
        
        if 'market_status' in endpoint_lower:
            return CacheTTL.MARKET_STATUS.value
        
        return CacheTTL.DEFAULT.value
    
    def get(self, endpoint: str, symbol: Optional[str] = None, 
            params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        从缓存获取数据
        
        Args:
            endpoint: API端点名称
            symbol: 股票代码
            params: 请求参数
            
        Returns:
            缓存数据或None（未命中或已过期）
        """
        params = params or {}
        key = self._generate_key(endpoint, symbol, params)
        
        with self._lock:
            # 先检查本地内存缓存
            if key in self._local_cache:
                entry = self._local_cache[key]
                if not entry.is_expired():
                    return entry.data
                else:
                    del self._local_cache[key]
            
            # 查询数据库
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        "SELECT data, expires_at FROM cache_entries WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        data_json, expires_at_str = row
                        expires_at = datetime.fromisoformat(expires_at_str)
                        
                        if datetime.now() <= expires_at:
                            # 更新访问统计
                            conn.execute(
                                """UPDATE cache_entries 
                                   SET access_count = access_count + 1,
                                       last_accessed = CURRENT_TIMESTAMP
                                   WHERE key = ?""",
                                (key,)
                            )
                            conn.commit()
                            
                            data = json.loads(data_json)
                            
                            # 放入本地缓存
                            self._add_to_local_cache(key, data, expires_at, endpoint, symbol)
                            
                            return data
                        else:
                            # 删除过期数据
                            conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                            conn.commit()
            except Exception as e:
                # 缓存错误不应影响主流程
                pass
        
        return None
    
    def set(self, endpoint: str, symbol: Optional[str] = None,
            params: Optional[Dict[str, Any]] = None, 
            data: Any = None, ttl: Optional[int] = None) -> bool:
        """
        设置缓存数据
        
        Args:
            endpoint: API端点名称
            symbol: 股票代码
            params: 请求参数
            data: 要缓存的数据
            ttl: 自定义过期时间(秒)，默认根据endpoint自动选择
            
        Returns:
            是否成功
        """
        params = params or {}
        key = self._generate_key(endpoint, symbol, params)
        
        if ttl is None:
            ttl = self._get_ttl(endpoint)
        
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=ttl)
        
        try:
            data_json = json.dumps(data, default=str)
            
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO cache_entries 
                       (key, data, created_at, expires_at, endpoint, symbol)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (key, data_json, created_at.isoformat(), expires_at.isoformat(), 
                     endpoint, symbol)
                )
                conn.commit()
            
            # 同时更新本地缓存
            with self._lock:
                self._add_to_local_cache(key, data, expires_at, endpoint, symbol)
            
            return True
        except Exception as e:
            # 缓存错误不应影响主流程
            return False
    
    def _add_to_local_cache(self, key: str, data: Any, expires_at: datetime,
                           endpoint: str, symbol: Optional[str]):
        """添加到本地内存缓存"""
        # 如果缓存已满，移除最旧的条目
        if len(self._local_cache) >= self._local_cache_max_size:
            oldest_key = min(self._local_cache.keys(), 
                           key=lambda k: self._local_cache[k].created_at)
            del self._local_cache[oldest_key]
        
        self._local_cache[key] = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.now(),
            expires_at=expires_at,
            endpoint=endpoint,
            symbol=symbol
        )
    
    def invalidate(self, endpoint: Optional[str] = None, 
                   symbol: Optional[str] = None) -> int:
        """
        使缓存失效
        
        Args:
            endpoint: 指定端点，为None则匹配所有
            symbol: 指定股票代码，为None则匹配所有
            
        Returns:
            删除的条目数
        """
        with self._lock:
            # 清理本地缓存
            keys_to_remove = [
                k for k, v in self._local_cache.items()
                if (endpoint is None or v.endpoint == endpoint) and
                   (symbol is None or v.symbol == symbol)
            ]
            for k in keys_to_remove:
                del self._local_cache[k]
            
            # 清理数据库
            try:
                with sqlite3.connect(self._db_path) as conn:
                    if endpoint and symbol:
                        cursor = conn.execute(
                            "DELETE FROM cache_entries WHERE endpoint = ? AND symbol = ?",
                            (endpoint, symbol)
                        )
                    elif endpoint:
                        cursor = conn.execute(
                            "DELETE FROM cache_entries WHERE endpoint = ?",
                            (endpoint,)
                        )
                    elif symbol:
                        cursor = conn.execute(
                            "DELETE FROM cache_entries WHERE symbol = ?",
                            (symbol,)
                    )
                    else:
                        cursor = conn.execute("DELETE FROM cache_entries")
                    
                    conn.commit()
                    return cursor.rowcount
            except Exception:
                return 0
    
    def clear_expired(self) -> int:
        """
        清理所有过期缓存
        
        Returns:
            删除的条目数
        """
        now = datetime.now().isoformat()
        
        with self._lock:
            # 清理本地缓存
            expired_keys = [
                k for k, v in self._local_cache.items() 
                if v.is_expired()
            ]
            for k in expired_keys:
                del self._local_cache[k]
            
            # 清理数据库
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM cache_entries WHERE expires_at < ?",
                        (now,)
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception:
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            with sqlite3.connect(self._db_path) as conn:
                # 总条目数
                cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
                total_count = cursor.fetchone()[0]
                
                # 过期条目数
                now = datetime.now().isoformat()
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache_entries WHERE expires_at < ?",
                    (now,)
                )
                expired_count = cursor.fetchone()[0]
                
                # 按endpoint统计
                cursor = conn.execute(
                    "SELECT endpoint, COUNT(*) FROM cache_entries GROUP BY endpoint"
                )
                endpoint_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 数据库大小
                db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
                
                return {
                    "total_entries": total_count,
                    "expired_entries": expired_count,
                    "active_entries": total_count - expired_count,
                    "local_cache_entries": len(self._local_cache),
                    "endpoint_distribution": endpoint_stats,
                    "db_size_bytes": db_size,
                    "db_size_mb": round(db_size / (1024 * 1024), 2)
                }
        except Exception as e:
            return {"error": str(e)}
    
    def get_cache_info(self, endpoint: str, symbol: Optional[str] = None,
                      params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """获取特定缓存条目的信息"""
        params = params or {}
        key = self._generate_key(endpoint, symbol, params)
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    """SELECT created_at, expires_at, access_count, last_accessed 
                       FROM cache_entries WHERE key = ?""",
                    (key,)
                )
                row = cursor.fetchone()
                
                if row:
                    created_at, expires_at, access_count, last_accessed = row
                    expires_dt = datetime.fromisoformat(expires_at)
                    is_expired = datetime.now() > expires_dt
                    
                    return {
                        "key": key,
                        "created_at": created_at,
                        "expires_at": expires_at,
                        "is_expired": is_expired,
                        "access_count": access_count,
                        "last_accessed": last_accessed
                    }
        except Exception:
            pass
        
        return None


# 全局缓存实例
cache = MassiveCache()
