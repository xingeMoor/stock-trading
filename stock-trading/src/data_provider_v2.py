"""
统一数据接口 v2 - 支持 A 股 + 美股多数据源

功能:
1. 统一接口访问 A 股 (akshare) 和美股 (Massive API) 数据
2. 智能缓存机制 (内存 + SQLite)
3. 自动降级和故障转移
4. 标准化的数据格式

作者：Q 脑量化交易系统
日期：2026-03-01
"""
import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import threading

import pandas as pd

# ============================================================================
# 缓存配置
# ============================================================================

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

DB_PATH = os.path.join(CACHE_DIR, 'data_cache.db')


class CacheTTL:
    """缓存过期时间配置 (秒)"""
    KLINE_DAILY = 3600          # 日线数据：1 小时
    KLINE_MINUTE = 300          # 分钟线数据：5 分钟
    REALTIME = 30               # 实时行情：30 秒
    FUNDAMENTAL = 86400         # 基本面数据：1 天
    SNAPSHOT = 60               # 快照数据：1 分钟
    DEFAULT = 1800              # 默认：30 分钟


@dataclass
class CacheStats:
    """缓存统计信息"""
    total_entries: int = 0
    expired_entries: int = 0
    hit_count: int = 0
    miss_count: int = 0
    db_size_mb: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return self.hit_count / total * 100 if total > 0 else 0.0


# ============================================================================
# 缓存管理器
# ============================================================================

class DataManagerCache:
    """
    数据缓存管理器
    
    支持:
    - 内存缓存 (LRU)
    - SQLite 持久化缓存
    - TTL 自动过期
    - 线程安全
    """
    
    def __init__(self, db_path: str = DB_PATH, max_memory_entries: int = 500):
        self._db_path = db_path
        self._max_memory_entries = max_memory_entries
        self._lock = threading.RLock()
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._stats = CacheStats()
        
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    symbol TEXT,
                    market TEXT,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON data_cache(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market ON data_cache(market)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON data_cache(expires_at)")
            conn.commit()
        finally:
            conn.close()
    
    def _generate_key(self, data_type: str, symbol: str, market: str, 
                      params: Dict[str, Any]) -> str:
        """生成缓存 key"""
        params_str = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:16]
        return f"{market}:{data_type}:{symbol}:{params_hash}"
    
    def get(self, data_type: str, symbol: str, market: str, 
            params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """获取缓存数据"""
        params = params or {}
        key = self._generate_key(data_type, symbol, market, params)
        
        with self._lock:
            # 检查内存缓存
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if datetime.now() < entry['expires_at']:
                    self._stats.hit_count += 1
                    return entry['data']
                else:
                    del self._memory_cache[key]
            
            # 检查数据库缓存
            try:
                conn = sqlite3.connect(self._db_path)
                try:
                    cursor = conn.execute(
                        "SELECT data, expires_at FROM data_cache WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        data_json, expires_at_str = row
                        expires_at = datetime.fromisoformat(expires_at_str)
                        
                        if datetime.now() < expires_at:
                            # 更新命中统计
                            conn.execute(
                                "UPDATE data_cache SET hit_count = hit_count + 1 WHERE key = ?",
                                (key,)
                            )
                            conn.commit()
                            
                            data = json.loads(data_json)
                            
                            # 更新内存缓存
                            self._add_to_memory(key, data, expires_at, data_type, symbol, market)
                            
                            self._stats.hit_count += 1
                            return data
                        else:
                            # 删除过期数据
                            conn.execute("DELETE FROM data_cache WHERE key = ?", (key,))
                            conn.commit()
                finally:
                    conn.close()
            except Exception:
                pass
            
            self._stats.miss_count += 1
            return None
    
    def set(self, data_type: str, symbol: str, market: str, 
            data: Any, ttl: int = CacheTTL.DEFAULT,
            params: Optional[Dict[str, Any]] = None) -> bool:
        """设置缓存数据"""
        params = params or {}
        key = self._generate_key(data_type, symbol, market, params)
        
        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl)
        
        try:
            data_json = json.dumps(data, default=str)
            
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO data_cache 
                       (key, data, data_type, created_at, expires_at, symbol, market)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (key, data_json, data_type, now.isoformat(), 
                     expires_at.isoformat(), symbol, market)
                )
                conn.commit()
            finally:
                conn.close()
            
            # 更新内存缓存
            self._add_to_memory(key, data, expires_at, data_type, symbol, market)
            
            return True
        except Exception as e:
            print(f"⚠️  缓存写入失败：{e}")
            return False
    
    def _add_to_memory(self, key: str, data: Any, expires_at: datetime,
                       data_type: str, symbol: str, market: str):
        """添加到内存缓存"""
        if len(self._memory_cache) >= self._max_memory_entries:
            # LRU: 移除最旧的条目
            oldest_key = min(self._memory_cache.keys(),
                           key=lambda k: self._memory_cache[k]['created_at'])
            del self._memory_cache[oldest_key]
        
        self._memory_cache[key] = {
            'data': data,
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'data_type': data_type,
            'symbol': symbol,
            'market': market
        }
    
    def invalidate(self, symbol: Optional[str] = None, 
                   market: Optional[str] = None,
                   data_type: Optional[str] = None) -> int:
        """使缓存失效"""
        with self._lock:
            # 清理内存缓存
            keys_to_remove = [
                k for k, v in self._memory_cache.items()
                if (symbol is None or v['symbol'] == symbol) and
                   (market is None or v['market'] == market) and
                   (data_type is None or v['data_type'] == data_type)
            ]
            for k in keys_to_remove:
                del self._memory_cache[k]
            
            # 清理数据库
            try:
                conn = sqlite3.connect(self._db_path)
                try:
                    conditions = []
                    params = []
                    
                    if symbol:
                        conditions.append("symbol = ?")
                        params.append(symbol)
                    if market:
                        conditions.append("market = ?")
                        params.append(market)
                    if data_type:
                        conditions.append("data_type = ?")
                        params.append(data_type)
                    
                    if conditions:
                        query = f"DELETE FROM data_cache WHERE {' AND '.join(conditions)}"
                        cursor = conn.execute(query, params)
                        conn.commit()
                        return cursor.rowcount
                finally:
                    conn.close()
            except Exception:
                pass
            
            return 0
    
    def clear_expired(self) -> int:
        """清理过期缓存"""
        now = datetime.now().isoformat()
        
        with self._lock:
            # 清理内存
            expired_keys = [
                k for k, v in self._memory_cache.items()
                if datetime.now() > v['expires_at']
            ]
            for k in expired_keys:
                del self._memory_cache[k]
            
            # 清理数据库
            try:
                conn = sqlite3.connect(self._db_path)
                try:
                    cursor = conn.execute(
                        "DELETE FROM data_cache WHERE expires_at < ?",
                        (now,)
                    )
                    conn.commit()
                    return cursor.rowcount
                finally:
                    conn.close()
            except Exception:
                return 0
    
    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM data_cache")
                total = cursor.fetchone()[0]
                
                now = datetime.now().isoformat()
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM data_cache WHERE expires_at < ?",
                    (now,)
                )
                expired = cursor.fetchone()[0]
                
                db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
                
                self._stats.total_entries = total
                self._stats.expired_entries = expired
                self._stats.db_size_mb = round(db_size / (1024 * 1024), 2)
                
                return self._stats
            finally:
                conn.close()
        except Exception:
            return self._stats


# ============================================================================
# 数据提供者基类
# ============================================================================

class DataProviderBase(ABC):
    """数据提供者基类"""
    
    def __init__(self, cache: DataManagerCache):
        self.cache = cache
        self.market = "UNKNOWN"
    
    @abstractmethod
    def get_kline(self, symbol: str, start: str, end: str, 
                  **kwargs) -> pd.DataFrame:
        """获取 K 线数据"""
        pass
    
    @abstractmethod
    def get_realtime(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情"""
        pass
    
    @abstractmethod
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取基本面数据"""
        pass
    
    def _save_to_cache(self, data_type: str, symbol: str, 
                       data: Any, ttl: int = CacheTTL.DEFAULT,
                       params: Optional[Dict[str, Any]] = None):
        """保存数据到缓存"""
        self.cache.set(data_type, symbol, self.market, data, ttl, params)
    
    def _get_from_cache(self, data_type: str, symbol: str,
                        params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """从缓存获取数据"""
        return self.cache.get(data_type, symbol, self.market, params)


# ============================================================================
# A 股数据提供者
# ============================================================================

class AShareProvider(DataProviderBase):
    """
    A 股数据提供者 - 使用 akshare
    
    文档：https://akshare.xyz/
    安装：pip install akshare
    """
    
    def __init__(self, cache: DataManagerCache):
        super().__init__(cache)
        self.market = "A 股"
        
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            raise ImportError("请安装 akshare: pip install akshare")
    
    def get_kline(self, symbol: str, start: str, end: str,
                  period: str = "daily", adjust: str = "qfq",
                  **kwargs) -> pd.DataFrame:
        """
        获取 A 股 K 线数据
        
        Args:
            symbol: 股票代码，如 "000001"
            start: 开始日期 YYYYMMDD 或 YYYY-MM-DD
            end: 结束日期 YYYYMMDD 或 YYYY-MM-DD
            period: 周期 (daily/weekly/monthly)
            adjust: 复权类型 (qfq/hfq/None)
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, ...
        """
        # 标准化日期格式
        start = start.replace('-', '')
        end = end.replace('-', '')
        
        # 检查缓存
        cache_params = {'period': period, 'adjust': adjust}
        cached = self._get_from_cache('kline', symbol, cache_params)
        if cached is not None:
            df = pd.DataFrame(cached)
            df['date'] = pd.to_datetime(df['date'])
            return df
        
        # 从 akshare 获取
        try:
            df = self.ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                adjust=adjust
            )
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # 确保日期为 datetime 类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 保存到缓存
            self._save_to_cache('kline', symbol, df.to_dict('records'), 
                               CacheTTL.KLINE_DAILY, cache_params)
            
            return df
            
        except Exception as e:
            raise Exception(f"A 股 K 线获取失败：{e}")
    
    def get_realtime(self, symbol: str) -> Dict[str, Any]:
        """获取 A 股实时行情"""
        # 检查缓存
        cached = self._get_from_cache('realtime', symbol)
        if cached is not None:
            return cached
        
        try:
            df = self.ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == symbol]
            
            if stock.empty:
                return {'error': f'股票 {symbol} 未找到', 'market': self.market}
            
            row = stock.iloc[0]
            data = {
                'symbol': symbol,
                'name': row.get('名称', ''),
                'price': float(row.get('最新价', 0)),
                'open': float(row.get('今开', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'prev_close': float(row.get('昨收', 0)),
                'volume': int(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'change': float(row.get('涨跌额', 0)),
                'turnover': float(row.get('换手率', 0)),
                'market': self.market,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存到缓存
            self._save_to_cache('realtime', symbol, data, CacheTTL.REALTIME)
            
            return data
            
        except Exception as e:
            return {'error': str(e), 'market': self.market}
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取 A 股基本面数据"""
        # 检查缓存
        cached = self._get_from_cache('fundamental', symbol)
        if cached is not None:
            return cached
        
        try:
            info = self.ak.stock_individual_info_em(symbol=symbol)
            
            # 转换为字典
            info_dict = {}
            for _, row in info.iterrows():
                if len(row) >= 2:
                    key = row.iloc[0]
                    value = row.iloc[1] if len(row) > 1 else None
                    info_dict[key] = value
            
            data = {
                'symbol': symbol,
                'market_cap': info_dict.get('总市值', 0),
                'float_market_cap': info_dict.get('流通市值', 0),
                'pe_ratio': info_dict.get('市盈率', 0),
                'pb_ratio': info_dict.get('市净率', 0),
                'roe': info_dict.get('ROE', 0),
                'eps': info_dict.get('每股收益', 0),
                'industry': info_dict.get('行业', ''),
                'area': info_dict.get('地区', ''),
                'market': self.market
            }
            
            # 保存到缓存
            self._save_to_cache('fundamental', symbol, data, CacheTTL.FUNDAMENTAL)
            
            return data
            
        except Exception as e:
            return {'error': str(e), 'market': self.market}
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取 A 股股票列表"""
        return self.ak.stock_zh_a_spot_em()
    
    def get_etf_list(self) -> pd.DataFrame:
        """获取 ETF 列表"""
        return self.ak.fund_etf_spot_em()
    
    def get_sector_strength(self) -> pd.DataFrame:
        """获取板块强度"""
        return self.ak.stock_sector_spot()


# ============================================================================
# 美股数据提供者
# ============================================================================

class USStockProvider(DataProviderBase):
    """
    美股数据提供者 - 使用 Massive API
    
    文档：https://massive.com/
    """
    
    def __init__(self, cache: DataManagerCache, api_key: Optional[str] = None):
        super().__init__(cache)
        self.market = "US"
        
        # 从环境变量或参数获取 API Key
        if api_key is None:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('MASSIVE_API_KEY')
        
        if not api_key:
            raise ValueError("MASSIVE_API_KEY 未设置")
        
        self.api_key = api_key
        self._client = None
    
    @property
    def client(self):
        """懒加载 Massive 客户端"""
        if self._client is None:
            try:
                from massive import RESTClient
                self._client = RESTClient(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 massive-api-client: pip install polygon-api-client")
        return self._client
    
    def get_kline(self, symbol: str, start: str, end: str,
                  multiplier: int = 1, timespan: str = "day",
                  **kwargs) -> pd.DataFrame:
        """
        获取美股 K 线数据
        
        Args:
            symbol: 股票代码，如 "AAPL"
            start: 开始日期 YYYY-MM-DD 或 YYYYMMDD
            end: 结束日期 YYYY-MM-DD 或 YYYYMMDD
            multiplier: 时间间隔倍数
            timespan: 时间单位 (minute/hour/day/week/month)
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, ...
        """
        # 标准化日期格式
        if len(start) == 8:
            start = f"{start[:4]}-{start[4:6]}-{start[6:]}"
        if len(end) == 8:
            end = f"{end[:4]}-{end[4:6]}-{end[6:]}"
        
        # 检查缓存
        cache_params = {'multiplier': multiplier, 'timespan': timespan}
        cached = self._get_from_cache('kline', symbol, cache_params)
        if cached is not None:
            df = pd.DataFrame(cached)
            df['date'] = pd.to_datetime(df['date'])
            return df
        
        # 从 Massive API 获取
        try:
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=start,
                to=end,
                limit=5000
            )
            
            agg_list = list(aggs)
            if not agg_list:
                return pd.DataFrame()
            
            # 转换为 DataFrame
            data = []
            for item in agg_list:
                data.append({
                    'date': datetime.fromtimestamp(item.timestamp / 1000),
                    'open': float(item.open),
                    'high': float(item.high),
                    'low': float(item.low),
                    'close': float(item.close),
                    'volume': int(item.volume) if hasattr(item, 'volume') else 0,
                    'vwap': float(item.vwap) if hasattr(item, 'vwap') else None,
                    'transactions': int(item.transactions) if hasattr(item, 'transactions') else 0
                })
            
            df = pd.DataFrame(data)
            
            # 保存到缓存
            ttl = CacheTTL.KLINE_MINUTE if timespan == 'minute' else CacheTTL.KLINE_DAILY
            self._save_to_cache('kline', symbol, df.to_dict('records'), ttl, cache_params)
            
            return df
            
        except Exception as e:
            raise Exception(f"美股 K 线获取失败：{e}")
    
    def get_realtime(self, symbol: str) -> Dict[str, Any]:
        """获取美股实时行情"""
        # 检查缓存
        cached = self._get_from_cache('realtime', symbol)
        if cached is not None:
            return cached
        
        try:
            # 获取快照数据
            snapshot = self.client.get_snapshot_ticker("stocks", symbol)
            
            data = {
                'symbol': symbol,
                'name': snapshot.ticker if hasattr(snapshot, 'ticker') else symbol,
                'price': float(snapshot.last_trade.price) if hasattr(snapshot, 'last_trade') else 0,
                'open': float(snapshot.day.open) if hasattr(snapshot, 'day') else 0,
                'high': float(snapshot.day.high) if hasattr(snapshot, 'day') else 0,
                'low': float(snapshot.day.low) if hasattr(snapshot, 'day') else 0,
                'prev_close': float(snapshot.prev_day.close) if hasattr(snapshot, 'prev_day') else 0,
                'volume': int(snapshot.day.volume) if hasattr(snapshot, 'day') else 0,
                'change': float(snapshot.day.change) if hasattr(snapshot, 'day') else 0,
                'change_pct': float(snapshot.day.change_percent) if hasattr(snapshot, 'day') else 0,
                'market_cap': float(snapshot.market_cap) if hasattr(snapshot, 'market_cap') else None,
                'pe_ratio': float(snapshot.valuations.get('pe', 0)) if hasattr(snapshot, 'valuations') else None,
                'market': self.market,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存到缓存
            self._save_to_cache('realtime', symbol, data, CacheTTL.REALTIME)
            
            return data
            
        except Exception as e:
            return {'error': str(e), 'market': self.market}
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取美股基本面数据"""
        # 检查缓存
        cached = self._get_from_cache('fundamental', symbol)
        if cached is not None:
            return cached
        
        try:
            # 获取股票详情
            details = self.client.get_ticker_details(symbol)
            
            data = {
                'symbol': symbol,
                'name': details.name if hasattr(details, 'name') else symbol,
                'market_cap': float(details.market_cap) if hasattr(details, 'market_cap') else None,
                'shares_outstanding': float(details.shares_outstanding) if hasattr(details, 'shares_outstanding') else None,
                'public_float': float(details.public_float) if hasattr(details, 'public_float') else None,
                'industry': details.sic_description if hasattr(details, 'sic_description') else None,
                'sector': None,  # Massive API 不直接提供
                'employees': details.total_employees if hasattr(details, 'total_employees') else None,
                'headquarters': details.address.city if hasattr(details, 'address') and hasattr(details.address, 'city') else None,
                'founded': details.list_date if hasattr(details, 'list_date') else None,
                'description': details.description if hasattr(details, 'description') else None,
                'homepage': details.homepage_url if hasattr(details, 'homepage_url') else None,
                'market': self.market
            }
            
            # 保存到缓存
            self._save_to_cache('fundamental', symbol, data, CacheTTL.FUNDAMENTAL)
            
            return data
            
        except Exception as e:
            return {'error': str(e), 'market': self.market}
    
    def get_snapshot_all(self) -> List[Dict[str, Any]]:
        """获取所有美股快照"""
        try:
            snapshots = self.client.get_snapshot_all("stocks")
            
            return [
                {
                    'symbol': s.ticker,
                    'price': float(s.last_trade.price),
                    'change_pct': float(s.change_percent),
                    'volume': int(s.day.volume)
                }
                for s in snapshots
            ]
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态"""
        try:
            status = self.client.get_market_status()
            
            return {
                'market': status.market if hasattr(status, 'market') else 'unknown',
                'server_time': status.server_time if hasattr(status, 'server_time') else None,
                'after_hours': status.after_hours if hasattr(status, 'after_hours') else False,
                'early_hours': status.early_hours if hasattr(status, 'early_hours') else False
            }
        except Exception as e:
            return {'error': str(e)}


# ============================================================================
# 统一数据接口
# ============================================================================

class DataProvider:
    """
    统一数据接口
    
    提供单一入口访问 A 股和美股数据，自动选择对应的数据提供者
    """
    
    _instances: Dict[str, DataProviderBase] = {}
    _cache: Optional[DataManagerCache] = None
    
    @classmethod
    def _get_cache(cls) -> DataManagerCache:
        """获取或创建缓存管理器"""
        if cls._cache is None:
            cls._cache = DataManagerCache()
        return cls._cache
    
    @classmethod
    def _get_provider(cls, market: str) -> DataProviderBase:
        """获取市场对应的数据提供者"""
        market = market.upper()
        market_map = {'A 股': 'A 股', 'ASHARE': 'A 股', 'CN': 'A 股', 
                      'US': 'US', 'USA': 'US', '美股': 'US'}
        
        normalized_market = market_map.get(market.upper(), market)
        
        if normalized_market not in cls._instances:
            cache = cls._get_cache()
            
            if normalized_market == 'A 股':
                cls._instances[normalized_market] = AShareProvider(cache)
            elif normalized_market == 'US':
                cls._instances[normalized_market] = USStockProvider(cache)
            else:
                raise ValueError(f"不支持的市场：{market}")
        
        return cls._instances[normalized_market]
    
    @classmethod
    def get_kline(cls, symbol: str, market: str, start: str, end: str,
                  **kwargs) -> pd.DataFrame:
        """
        统一获取 K 线数据
        
        Args:
            symbol: 股票代码
            market: 市场 (A 股/US)
            start: 开始日期
            end: 结束日期
            **kwargs: 额外参数传递给具体提供者
        
        Returns:
            DataFrame with OHLCV data
        """
        provider = cls._get_provider(market)
        return provider.get_kline(symbol, start, end, **kwargs)
    
    @classmethod
    def get_realtime(cls, symbol: str, market: str) -> Dict[str, Any]:
        """统一获取实时行情"""
        provider = cls._get_provider(market)
        return provider.get_realtime(symbol)
    
    @classmethod
    def get_fundamentals(cls, symbol: str, market: str) -> Dict[str, Any]:
        """统一获取基本面数据"""
        provider = cls._get_provider(market)
        return provider.get_fundamentals(symbol)
    
    @classmethod
    def get_cache_stats(cls) -> CacheStats:
        """获取缓存统计"""
        cache = cls._get_cache()
        return cache.get_stats()
    
    @classmethod
    def clear_cache(cls, symbol: Optional[str] = None,
                    market: Optional[str] = None,
                    data_type: Optional[str] = None) -> int:
        """清除缓存"""
        cache = cls._get_cache()
        return cache.invalidate(symbol, market, data_type)


# ============================================================================
# 测试函数
# ============================================================================

def test_data_provider():
    """测试统一数据接口"""
    print("=" * 70)
    print("🧪 测试统一数据接口 v2")
    print("=" * 70)
    
    # 测试 A 股
    print("\n1️⃣  A 股数据测试...")
    try:
        provider = DataProvider._get_provider('A 股')
        
        # 测试 K 线
        print("   📊 获取平安银行 (000001) K 线...")
        df = provider.get_kline('000001', '20250101', '20260228')
        print(f"   ✅ 获取 {len(df)} 条数据")
        print(f"   📈 最新收盘价：¥{df['close'].iloc[-1]:.2f}")
        
        # 测试实时行情
        print("\n   💹 获取实时行情...")
        realtime = provider.get_realtime('000001')
        if 'error' not in realtime:
            print(f"   ✅ {realtime['name']}: ¥{realtime['price']} ({realtime['change_pct']}%)")
        else:
            print(f"   ⚠️  {realtime.get('error', '未知错误')}")
        
        # 测试基本面
        print("\n   📋 获取基本面数据...")
        fundamentals = provider.get_fundamentals('000001')
        if 'error' not in fundamentals:
            print(f"   ✅ 市值：{fundamentals.get('market_cap', 'N/A')}")
            print(f"   ✅ PE: {fundamentals.get('pe_ratio', 'N/A')}")
        else:
            print(f"   ⚠️  {fundamentals.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"   ❌ A 股测试失败：{e}")
    
    # 测试美股
    print("\n2️⃣  美股数据测试...")
    try:
        provider = DataProvider._get_provider('US')
        
        # 测试 K 线
        print("   📊 获取 AAPL K 线...")
        df = provider.get_kline('AAPL', '2025-01-01', '2026-02-28')
        print(f"   ✅ 获取 {len(df)} 条数据")
        print(f"   📈 最新收盘价：${df['close'].iloc[-1]:.2f}")
        
        # 测试实时行情
        print("\n   💹 获取实时行情...")
        realtime = provider.get_realtime('AAPL')
        if 'error' not in realtime:
            print(f"   ✅ {realtime.get('name', 'AAPL')}: ${realtime.get('price', 0):.2f} ({realtime.get('change_pct', 0)}%)")
        else:
            print(f"   ⚠️  {realtime.get('error', '未知错误')}")
        
        # 测试基本面
        print("\n   📋 获取基本面数据...")
        fundamentals = provider.get_fundamentals('AAPL')
        if 'error' not in fundamentals:
            print(f"   ✅ 市值：{fundamentals.get('market_cap', 'N/A')}")
            print(f"   ✅ 员工数：{fundamentals.get('employees', 'N/A')}")
        else:
            print(f"   ⚠️  {fundamentals.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"   ❌ 美股测试失败：{e}")
    
    # 测试缓存
    print("\n3️⃣  缓存统计...")
    stats = DataProvider.get_cache_stats()
    print(f"   📊 缓存条目：{stats.total_entries}")
    print(f"   📊 命中率：{stats.hit_rate:.1f}%")
    print(f"   💾 数据库大小：{stats.db_size_mb} MB")
    
    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    test_data_provider()
