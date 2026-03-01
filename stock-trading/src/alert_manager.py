"""
告警管理器
功能:
- 定义不同级别的告警 (info/warning/error/critical)
- 告警抑制 (相同问题5分钟内不重复发送)
- 告警聚合 (批量发送)
- 记录告警历史到数据库
"""
import sqlite3
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import os
import threading


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警对象"""
    id: Optional[int]
    alert_key: str  # 告警唯一标识(用于去重)
    level: str
    title: str
    message: str
    source: str  # 告警来源(模块/工具名)
    metadata: str  # JSON格式的额外信息
    status: str  # pending/sent/suppressed/acknowledged
    created_at: str
    sent_at: Optional[str]
    acknowledged_at: Optional[str]
    acknowledged_by: Optional[str]


class AlertManager:
    """告警管理器"""
    
    # 告警级别对应的emoji
    LEVEL_EMOJI = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🚨"
    }
    
    # 告警级别优先级
    LEVEL_PRIORITY = {
        "info": 1,
        "warning": 2,
        "error": 3,
        "critical": 4
    }
    
    def __init__(self, db_path: str = None, suppression_minutes: int = 5):
        """
        初始化告警管理器
        
        Args:
            db_path: 数据库路径
            suppression_minutes: 告警抑制时间(分钟),默认5分钟
        """
        self.db_path = db_path or self._get_default_db_path()
        self.suppression_seconds = suppression_minutes * 60
        self._lock = threading.Lock()
        self._pending_alerts: List[Alert] = []
        self._batch_timer: Optional[threading.Timer] = None
        self._batch_interval = 30  # 批量发送间隔(秒)
        self._notification_handlers: List[Callable[[Alert], bool]] = []
        
        self._init_db()
    
    def _get_default_db_path(self) -> str:
        """获取默认数据库路径"""
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, 'alerts.db')
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 告警历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_key TEXT NOT NULL,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                acknowledged_at TIMESTAMP,
                acknowledged_by TEXT
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alert_key ON alerts(alert_key)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON alerts(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON alerts(created_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_alert_key(self, level: str, title: str, source: str) -> str:
        """
        生成告警唯一标识
        
        Args:
            level: 告警级别
            title: 告警标题
            source: 告警来源
        
        Returns:
            告警唯一标识(MD5哈希)
        """
        key_string = f"{level}:{title}:{source}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _should_suppress(self, alert_key: str) -> bool:
        """
        检查是否应该抑制该告警
        
        Args:
            alert_key: 告警唯一标识
        
        Returns:
            是否应该抑制
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 查询最近是否有相同告警(包括pending、sent、acknowledged)
        cutoff_time = datetime.now() - timedelta(seconds=self.suppression_seconds)
        cursor.execute('''
            SELECT COUNT(*) FROM alerts 
            WHERE alert_key = ? 
            AND status IN ('pending', 'sent', 'acknowledged')
            AND created_at > ?
        ''', (alert_key, cutoff_time.isoformat()))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def add_notification_handler(self, handler: Callable[[Alert], bool]):
        """
        添加通知处理器
        
        Args:
            handler: 处理函数,接收Alert对象,返回是否成功
        """
        self._notification_handlers.append(handler)
    
    def create_alert(
        self,
        level: str,
        title: str,
        message: str,
        source: str = "",
        metadata: Dict[str, Any] = None,
        immediate: bool = False
    ) -> Optional[Alert]:
        """
        创建告警
        
        Args:
            level: 告警级别 (info/warning/error/critical)
            title: 告警标题
            message: 告警内容
            source: 告警来源
            metadata: 额外元数据
            immediate: 是否立即发送(不等待批量)
        
        Returns:
            创建的告警对象,如果被抑制则返回None
        """
        alert_key = self._generate_alert_key(level, title, source)
        
        # 检查是否需要抑制
        if self._should_suppress(alert_key):
            print(f"🔇 告警被抑制: [{level}] {title}")
            return None
        
        now = datetime.now().isoformat()
        alert = Alert(
            id=None,
            alert_key=alert_key,
            level=level,
            title=title,
            message=message,
            source=source,
            metadata=json.dumps(metadata or {}),
            status="pending",
            created_at=now,
            sent_at=None,
            acknowledged_at=None,
            acknowledged_by=None
        )
        
        # 保存到数据库
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alerts 
                (alert_key, level, title, message, source, metadata, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_key, alert.level, alert.title, alert.message,
                alert.source, alert.metadata, alert.status, alert.created_at
            ))
            alert.id = cursor.lastrowid
            conn.commit()
            conn.close()
        
        print(f"📝 告警已创建: [{level}] {title}")
        
        # 如果是critical级别或immediate为True,立即发送
        if level == "critical" or immediate:
            self._send_alert(alert)
        else:
            # 加入待发送队列
            with self._lock:
                self._pending_alerts.append(alert)
                self._schedule_batch_send()
        
        return alert
    
    def _schedule_batch_send(self):
        """调度批量发送"""
        if self._batch_timer is None or not self._batch_timer.is_alive():
            self._batch_timer = threading.Timer(self._batch_interval, self._batch_send)
            self._batch_timer.daemon = True
            self._batch_timer.start()
    
    def _batch_send(self):
        """批量发送告警"""
        with self._lock:
            if not self._pending_alerts:
                return
            
            # 按级别分组并去重
            alerts_to_send = self._pending_alerts.copy()
            self._pending_alerts.clear()
        
        # 按优先级排序
        alerts_to_send.sort(
            key=lambda a: self.LEVEL_PRIORITY.get(a.level, 0),
            reverse=True
        )
        
        # 合并相同级别的告警
        merged_alerts = self._merge_alerts(alerts_to_send)
        
        # 发送
        for alert in merged_alerts:
            self._send_alert(alert)
    
    def _merge_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """
        合并相同级别的告警
        
        Args:
            alerts: 告警列表
        
        Returns:
            合并后的告警列表
        """
        if len(alerts) <= 3:
            return alerts
        
        # 如果告警数量过多,合并为一条汇总消息
        level_counts = {}
        for alert in alerts:
            level_counts[alert.level] = level_counts.get(alert.level, 0) + 1
        
        summary_parts = []
        for level in ["critical", "error", "warning", "info"]:
            if level in level_counts:
                emoji = self.LEVEL_EMOJI.get(level, "📢")
                summary_parts.append(f"{emoji} {level.upper()}: {level_counts[level]}条")
        
        summary_message = "\n".join([
            "多条告警需要关注:",
            "",
            *summary_parts,
            "",
            f"共计 {len(alerts)} 条告警,请查看详细日志"
        ])
        
        # 创建汇总告警
        summary_alert = Alert(
            id=None,
            alert_key=self._generate_alert_key("warning", "批量告警汇总", "alert_manager"),
            level="warning",
            title="📦 批量告警汇总",
            message=summary_message,
            source="alert_manager",
            metadata=json.dumps({"original_count": len(alerts)}),
            status="pending",
            created_at=datetime.now().isoformat(),
            sent_at=None,
            acknowledged_at=None,
            acknowledged_by=None
        )
        
        return [summary_alert]
    
    def _send_alert(self, alert: Alert) -> bool:
        """
        发送告警
        
        Args:
            alert: 告警对象
        
        Returns:
            是否发送成功
        """
        success = False
        
        # 调用所有通知处理器
        for handler in self._notification_handlers:
            try:
                if handler(alert):
                    success = True
            except Exception as e:
                print(f"❌ 通知处理器失败: {e}")
        
        # 更新数据库状态
        status = "sent" if success else "failed"
        sent_at = datetime.now().isoformat() if success else None
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE alerts 
                SET status = ?, sent_at = ?
                WHERE id = ?
            ''', (status, sent_at, alert.id))
            conn.commit()
            conn.close()
        
        alert.status = status
        alert.sent_at = sent_at
        
        return success
    
    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str = "system"
    ) -> bool:
        """
        确认告警
        
        Args:
            alert_id: 告警ID
            acknowledged_by: 确认人
        
        Returns:
            是否成功
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE alerts 
                SET status = 'acknowledged', 
                    acknowledged_at = ?,
                    acknowledged_by = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), acknowledged_by, alert_id))
            updated = cursor.rowcount > 0
            conn.commit()
            conn.close()
        
        return updated
    
    def get_pending_alerts(self, limit: int = 100) -> List[Alert]:
        """
        获取待处理的告警
        
        Args:
            limit: 限制数量
        
        Returns:
            告警列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM alerts 
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def get_alert_history(
        self,
        level: str = None,
        source: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        获取告警历史
        
        Args:
            level: 告警级别过滤
            source: 来源过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量
        
        Returns:
            告警列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if level:
            query += " AND level = ?"
            params.append(level)
        if source:
            query += " AND source = ?"
            params.append(source)
        if start_time:
            query += " AND created_at >= ?"
            params.append(start_time)
        if end_time:
            query += " AND created_at <= ?"
            params.append(end_time)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取告警统计
        
        Args:
            hours: 统计最近多少小时
        
        Returns:
            统计数据
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # 按级别统计
        cursor.execute('''
            SELECT level, COUNT(*) as count 
            FROM alerts 
            WHERE created_at > ?
            GROUP BY level
        ''', (cutoff_time,))
        
        level_stats = {row['level']: row['count'] for row in cursor.fetchall()}
        
        # 按状态统计
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM alerts 
            WHERE created_at > ?
            GROUP BY status
        ''', (cutoff_time,))
        
        status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # 按来源统计TOP10
        cursor.execute('''
            SELECT source, COUNT(*) as count 
            FROM alerts 
            WHERE created_at > ?
            GROUP BY source
            ORDER BY count DESC
            LIMIT 10
        ''', (cutoff_time,))
        
        source_stats = [
            {"source": row['source'], "count": row['count']}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        total = sum(level_stats.values())
        
        return {
            "total": total,
            "by_level": level_stats,
            "by_status": status_stats,
            "top_sources": source_stats,
            "time_range_hours": hours
        }
    
    def _row_to_alert(self, row: sqlite3.Row) -> Alert:
        """将数据库行转换为Alert对象"""
        return Alert(
            id=row['id'],
            alert_key=row['alert_key'],
            level=row['level'],
            title=row['title'],
            message=row['message'],
            source=row['source'],
            metadata=row['metadata'],
            status=row['status'],
            created_at=row['created_at'],
            sent_at=row['sent_at'],
            acknowledged_at=row['acknowledged_at'],
            acknowledged_by=row['acknowledged_by']
        )
    
    def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        清理旧告警
        
        Args:
            days: 保留多少天的告警
        
        Returns:
            删除的记录数
        """
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM alerts 
                WHERE created_at < ?
            ''', (cutoff_time,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        
        print(f"🧹 清理了 {deleted} 条旧告警记录")
        return deleted


# 全局告警管理器实例
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(db_path: str = None) -> AlertManager:
    """获取全局告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(db_path)
    return _alert_manager


def send_alert(
    level: str,
    title: str,
    message: str,
    source: str = "",
    metadata: Dict[str, Any] = None,
    immediate: bool = False
) -> Optional[Alert]:
    """
    快捷发送告警
    
    Args:
        level: 告警级别
        title: 标题
        message: 内容
        source: 来源
        metadata: 元数据
        immediate: 是否立即发送
    
    Returns:
        创建的告警对象
    """
    manager = get_alert_manager()
    return manager.create_alert(level, title, message, source, metadata, immediate)


if __name__ == "__main__":
    # 测试
    print("🧪 测试告警管理器\n")
    
    manager = AlertManager(suppression_minutes=1)
    
    # 添加测试处理器
    def test_handler(alert: Alert) -> bool:
        print(f"📤 发送告警: [{alert.level}] {alert.title}")
        return True
    
    manager.add_notification_handler(test_handler)
    
    # 测试创建告警
    print("1. 创建普通告警")
    alert1 = manager.create_alert(
        level="warning",
        title="测试告警",
        message="这是一个测试告警",
        source="test"
    )
    
    print("\n2. 创建critical告警(立即发送)")
    alert2 = manager.create_alert(
        level="critical",
        title="严重错误",
        message="系统出现严重错误!",
        source="test",
        immediate=True
    )
    
    print("\n3. 测试告警抑制(相同告警不应重复创建)")
    alert3 = manager.create_alert(
        level="warning",
        title="测试告警",
        message="这是一个测试告警",
        source="test"
    )
    
    print("\n4. 获取告警统计")
    stats = manager.get_stats(hours=1)
    print(f"统计: {json.dumps(stats, indent=2)}")
    
    print("\n✅ 测试完成")
