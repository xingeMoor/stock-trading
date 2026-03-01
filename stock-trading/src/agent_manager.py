"""
Agent Manager V2 - 支持 OpenClaw Subagents 同步

功能:
1. 与 OpenClaw subagents API 同步真实 Agent 状态
2. 显示模型信息、任务名称、运行时长、最后活跃时间
3. 支持本地数据库持久化

作者：小七
版本：2.0
创建日期：2026-03-01
"""
import sqlite3
import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'agent_registry.db'


class AgentStatus(Enum):
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    COMPLETED = "completed" # 已完成
    ERROR = "error"         # 错误
    OFFLINE = "offline"     # 离线


AGENT_INFO = {
    # 工程层
    "architect": {"name": "Archie", "emoji": "🏗️", "layer": "工程层", "desc": "系统架构设计"},
    "developer": {"name": "Dev", "emoji": "💻", "layer": "工程层", "desc": "代码开发实现"},
    "tester": {"name": "Testy", "emoji": "🧪", "layer": "工程层", "desc": "质量保证测试"},
    "designer": {"name": "Pixel", "emoji": "🎨", "layer": "工程层", "desc": "UI/UX 设计"},
    
    # 金融层
    "factor": {"name": "Factor", "emoji": "📊", "layer": "金融层", "desc": "因子分析挖掘"},
    "sentiment": {"name": "Senti", "emoji": "📰", "layer": "金融层", "desc": "舆情情绪分析"},
    "fundamental": {"name": "Funda", "emoji": "📈", "layer": "金融层", "desc": "基本面研究"},
    "trader": {"name": "Trader", "emoji": "💹", "layer": "金融层", "desc": "交易信号执行"},
    "risk": {"name": "Risk", "emoji": "🛡️", "layer": "金融层", "desc": "风险控制管理"},
    "guard": {"name": "Guard", "emoji": "🔒", "layer": "金融层", "desc": "防守审核复核"},
    
    # 桥梁层
    "backtest": {"name": "Backer", "emoji": "📉", "layer": "桥梁层", "desc": "回测系统设计"},
    "strategist": {"name": "Strategist", "emoji": "🎯", "layer": "桥梁层", "desc": "策略沟通协调"},
    
    # 管理层
    "pm": {"name": "PM", "emoji": "📋", "layer": "管理层", "desc": "项目管理协调"},
    "ops": {"name": "Ops", "emoji": "🔧", "layer": "管理层", "desc": "运维监控告警"},
}


def init_agent_db():
    """初始化 Agent 数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Agent 注册表 - 增加模型、运行时长字段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            emoji TEXT,
            layer TEXT,
            description TEXT,
            status TEXT DEFAULT 'idle',
            current_task TEXT,
            model TEXT,
            running_duration_seconds INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            openclaw_session_id TEXT
        )
    ''')
    
    # 任务记录表 - 增加模型字段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            agent_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            model TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            result_summary TEXT,
            quality_score INTEGER,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    # 工作日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            log_type TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    # 性能统计表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            date DATE NOT NULL,
            tasks_total INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            tasks_failed INTEGER DEFAULT 0,
            avg_response_time_ms INTEGER,
            quality_avg_score REAL,
            UNIQUE(agent_id, date),
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    conn.commit()
    
    # 初始化所有 Agent
    for role, info in AGENT_INFO.items():
        cursor.execute('''
            INSERT OR IGNORE INTO agents (agent_id, role, name, emoji, layer, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (role, role, info['name'], info['emoji'], info['layer'], info['desc'], 'idle'))
    
    conn.commit()
    conn.close()
    logger.info("✅ Agent 数据库初始化完成")


def get_openclaw_subagents() -> List[Dict]:
    """
    从 OpenClaw 获取真实的 subagents 状态
    
    使用 openclaw 命令行工具或 subagents API
    返回格式:
    [
        {
            "session_id": "agent:main:subagent:xxx",
            "label": "PM-Master",
            "status": "running",
            "model": "bailian/qwen3.5-plus",
            "task": "任务描述",
            "created_at": "2026-03-01T12:00:00",
            "last_active": "2026-03-01T12:05:00"
        }
    ]
    """
    try:
        # 方法 1: 使用 openclaw 命令行工具
        result = subprocess.run(
            ['openclaw', 'agents', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # 尝试解析 JSON 输出
            try:
                data = json.loads(result.stdout)
                # 新的格式包含 active 和 recent 字段
                if isinstance(data, dict) and 'active' in data:
                    all_agents = []
                    
                    # 处理活跃 agents
                    for agent in data.get('active', []):
                        all_agents.append({
                            "session_id": agent.get('sessionKey', ''),
                            "run_id": agent.get('runId', ''),
                            "label": agent.get('label', ''),
                            "status": agent.get('status', 'idle'),
                            "model": agent.get('model', ''),
                            "task": agent.get('task', '')[:100] + '...' if len(agent.get('task', '')) > 100 else agent.get('task', ''),
                            "runtime_ms": agent.get('runtimeMs', 0),
                            "started_at": datetime.fromtimestamp(agent.get('startedAt', 0) / 1000).isoformat() if agent.get('startedAt') else datetime.now().isoformat(),
                            "last_active": datetime.now().isoformat()
                        })
                    
                    # 处理最近完成的 agents
                    for agent in data.get('recent', []):
                        all_agents.append({
                            "session_id": agent.get('sessionKey', ''),
                            "run_id": agent.get('runId', ''),
                            "label": agent.get('label', ''),
                            "status": agent.get('status', 'completed'),
                            "model": agent.get('model', ''),
                            "task": agent.get('task', '')[:100] + '...' if len(agent.get('task', '')) > 100 else agent.get('task', ''),
                            "runtime_ms": agent.get('runtimeMs', 0),
                            "started_at": datetime.fromtimestamp(agent.get('startedAt', 0) / 1000).isoformat() if agent.get('startedAt') else datetime.now().isoformat(),
                            "ended_at": datetime.fromtimestamp(agent.get('endedAt', 0) / 1000).isoformat() if agent.get('endedAt') else None,
                            "last_active": datetime.fromtimestamp(agent.get('endedAt', 0) / 1000).isoformat() if agent.get('endedAt') else datetime.now().isoformat()
                        })
                    
                    return all_agents
                elif isinstance(data, list):
                    return data
                else:
                    return []
            except json.JSONDecodeError:
                # 如果不是 JSON，尝试解析文本格式
                return parse_subagents_text(result.stdout)
        
        # 方法 2: 如果命令行不可用，返回空列表 (使用本地状态)
        logger.warning("OpenClaw agents 命令不可用，使用本地状态")
        return []
        
    except subprocess.TimeoutExpired:
        logger.error("获取 OpenClaw subagents 超时")
        return []
    except Exception as e:
        logger.error(f"获取 OpenClaw subagents 失败：{e}")
        return []


def parse_subagents_text(text: str) -> List[Dict]:
    """解析 subagents 文本输出"""
    subagents = []
    lines = text.strip().split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # 尝试解析常见格式
        # 例如："c9599a81-800f-477c-8ffc-aaa03d911fed | PM-Master | running | bailian/qwen3.5-plus"
        parts = line.split('|')
        if len(parts) >= 4:
            subagents.append({
                "session_id": parts[0].strip(),
                "label": parts[1].strip(),
                "status": parts[2].strip(),
                "model": parts[3].strip(),
                "task": parts[4].strip() if len(parts) > 4 else "",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            })
    
    return subagents


def sync_openclaw_agents():
    """
    同步 OpenClaw subagents 状态到本地数据库
    
    将 OpenClaw 的真实 Agent 状态映射到本地 Agent 角色
    """
    openclaw_agents = get_openclaw_subagents()
    
    if not openclaw_agents:
        logger.info("没有 OpenClaw subagents 可同步")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建 label 到 agent_id 的映射（支持多种命名格式）
    label_to_agent = {
        # PM
        'PM-Master': 'pm',
        'PM': 'pm',
        # 工程层
        'Architect': 'architect',
        'Archie': 'architect',
        'Developer': 'developer',
        'Dev': 'developer',
        'Tester': 'tester',
        'Testy': 'tester',
        'Designer': 'designer',
        'Pixel': 'designer',
        'Pixel-5007Fix': 'designer',
        # 金融层
        'Factor': 'factor',
        'Sentiment': 'sentiment',
        'Senti': 'sentiment',
        'Senti-Monitor': 'sentiment',
        'Fundamental': 'fundamental',
        'Funda': 'fundamental',
        'Trader': 'trader',
        'Trader-Exec': 'trader',
        'Risk': 'risk',
        'Guard': 'guard',
        # 桥梁层
        'Backtest': 'backtest',
        'Backer': 'backtest',
        'Strategist': 'strategist',
        # 管理层
        'Ops': 'ops',
        'Ops-Deploy': 'ops',
        # 其他
        'XHS-Writer': 'designer',
        'XHS-Reviewer': 'guard',
        'Dev-5002Fix': 'developer',
        'Dev-5005Fix': 'developer',
        'Dev-5002Create': 'developer',
    }
    
    synced_count = 0
    
    for oc_agent in openclaw_agents:
        session_id = oc_agent.get('session_id', '')
        label = oc_agent.get('label', '')
        status = oc_agent.get('status', 'idle')
        model = oc_agent.get('model', '')
        task = oc_agent.get('task', '')
        last_active = oc_agent.get('last_active', datetime.now().isoformat())
        runtime_ms = oc_agent.get('runtime_ms', 0)
        
        # 将 OpenClaw 状态映射到本地状态
        local_status = map_openclaw_status(status)
        
        # 计算运行时长（优先使用runtime_ms）
        if runtime_ms > 0:
            running_duration = runtime_ms // 1000
        else:
            created_at = oc_agent.get('created_at', datetime.now().isoformat())
            running_duration = calculate_duration_seconds(created_at, last_active, local_status)
        
        # 尝试匹配本地 Agent
        agent_id = label_to_agent.get(label)
        
        if agent_id:
            # 更新现有 Agent
            cursor.execute('''
                UPDATE agents 
                SET status = ?, current_task = ?, model = ?, 
                    running_duration_seconds = ?, last_active = ?,
                    openclaw_session_id = ?
                WHERE agent_id = ?
            ''', (local_status, task, model, running_duration, last_active, session_id, agent_id))
            
            logger.info(f"同步 Agent {agent_id} ({label}): {local_status} - {task[:50] if task else '无任务'}")
            synced_count += 1
        else:
            # 如果无法匹配，记录日志
            logger.debug(f"未找到匹配的 Agent: {label}")
    
    conn.commit()
    conn.close()
    logger.info(f"✅ 同步了 {synced_count}/{len(openclaw_agents)} 个 OpenClaw subagents")


def map_openclaw_status(oc_status: str) -> str:
    """将 OpenClaw 状态映射到本地状态"""
    status_map = {
        'running': AgentStatus.RUNNING.value,
        'completed': AgentStatus.COMPLETED.value,
        'error': AgentStatus.ERROR.value,
        'idle': AgentStatus.IDLE.value,
        'offline': AgentStatus.OFFLINE.value,
    }
    return status_map.get(oc_status.lower(), AgentStatus.IDLE.value)


def calculate_duration_seconds(start_str: str, end_str: str, status: str) -> int:
    """计算运行时长 (秒)"""
    try:
        start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        
        if status == AgentStatus.RUNNING.value:
            end = datetime.now()
        else:
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        return int((end - start).total_seconds())
    except Exception:
        return 0


def format_duration(seconds: int) -> str:
    """格式化运行时长"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分钟"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟"


def get_all_agents() -> List[Dict]:
    """获取所有 Agent 信息 (包含 OpenClaw 同步的状态)"""
    # 先同步 OpenClaw 状态
    sync_openclaw_agents()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT agent_id, role, name, emoji, layer, description, status, 
               current_task, last_active, model, running_duration_seconds
        FROM agents
        ORDER BY layer, name
    ''')
    
    agents = []
    for row in cursor.fetchall():
        duration_seconds = row[10] or 0
        agents.append({
            'agent_id': row[0],
            'role': row[1],
            'name': row[2],
            'emoji': row[3],
            'layer': row[4],
            'description': row[5],
            'status': row[6],
            'current_task': row[7],
            'last_active': row[8],
            'model': row[9] or '-',
            'running_duration': format_duration(duration_seconds) if duration_seconds > 0 else '-',
            'running_duration_seconds': duration_seconds
        })
    
    conn.close()
    return agents


def get_agent_tasks(agent_id: str = None, status: str = None, limit: int = 50) -> List[Dict]:
    """获取任务列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT t.task_id, t.agent_id, a.name as agent_name, a.emoji,
               t.title, t.status, t.priority, t.started_at, t.completed_at, 
               t.quality_score, t.model
        FROM agent_tasks t
        JOIN agents a ON t.agent_id = a.agent_id
        WHERE 1=1
    '''
    params = []
    
    if agent_id:
        query += ' AND t.agent_id = ?'
        params.append(agent_id)
    
    if status:
        query += ' AND t.status = ?'
        params.append(status)
    
    query += ' ORDER BY t.started_at DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    
    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            'task_id': row[0],
            'agent_id': row[1],
            'agent_name': row[2],
            'agent_emoji': row[3],
            'title': row[4],
            'status': row[5],
            'priority': row[6],
            'started_at': row[7],
            'completed_at': row[8],
            'quality_score': row[9],
            'model': row[10] or '-'
        })
    
    conn.close()
    return tasks


def get_dashboard_stats() -> Dict:
    """获取 Dashboard 统计数据"""
    # 先同步 OpenClaw 状态
    sync_openclaw_agents()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Agent 状态统计
    cursor.execute('''
        SELECT status, COUNT(*) FROM agents GROUP BY status
    ''')
    status_counts = dict(cursor.fetchall())
    
    # 今日任务统计
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT status, COUNT(*) FROM agent_tasks
        WHERE date(started_at) = ?
        GROUP BY status
    ''', (today,))
    today_tasks = dict(cursor.fetchall())
    
    # 各层级 Agent 数量
    cursor.execute('''
        SELECT layer, COUNT(*) FROM agents GROUP BY layer
    ''')
    layer_counts = dict(cursor.fetchall())
    
    # 按模型统计
    cursor.execute('''
        SELECT model, COUNT(*) FROM agents 
        WHERE model IS NOT NULL AND model != '' 
        GROUP BY model
    ''')
    model_counts = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'agent_status': status_counts,
        'today_tasks': today_tasks,
        'layer_distribution': layer_counts,
        'model_distribution': model_counts,
        'total_agents': sum(status_counts.values()),
        'active_agents': status_counts.get('running', 0),
        'error_agents': status_counts.get('error', 0),
        'idle_agents': status_counts.get('idle', 0)
    }


def register_task(agent_id: str, title: str, description: str = "", 
                  priority: str = "medium", model: str = "") -> str:
    """注册新任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{agent_id}"
    now = datetime.now()
    
    cursor.execute('''
        INSERT INTO agent_tasks (task_id, agent_id, title, description, priority, model, status, started_at)
        VALUES (?, ?, ?, ?, ?, ?, 'running', ?)
    ''', (task_id, agent_id, title, description, priority, model, now))
    
    cursor.execute('''
        UPDATE agents SET status = 'running', current_task = ?, last_active = ?, model = ?
        WHERE agent_id = ?
    ''', (title, now, model, agent_id))
    
    conn.commit()
    conn.close()
    
    return task_id


def complete_task(task_id: str, result_summary: str = "", quality_score: int = None):
    """完成任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE agent_tasks 
        SET status = 'completed', completed_at = ?, result_summary = ?, quality_score = ?
        WHERE task_id = ?
    ''', (datetime.now(), result_summary, quality_score, task_id))
    
    # 获取 agent_id 并更新状态
    cursor.execute('SELECT agent_id FROM agent_tasks WHERE task_id = ?', (task_id,))
    row = cursor.fetchone()
    if row:
        agent_id = row[0]
        cursor.execute('''
            UPDATE agents SET status = 'idle', current_task = NULL
            WHERE agent_id = ?
        ''', (agent_id,))
    
    conn.commit()
    conn.close()


def log_activity(agent_id: str, log_type: str, message: str, details: dict = None):
    """记录 Agent 活动日志"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO agent_logs (agent_id, log_type, message, details)
        VALUES (?, ?, ?, ?)
    ''', (agent_id, log_type, message, json.dumps(details) if details else None))
    
    cursor.execute('''
        UPDATE agents SET last_active = ?
        WHERE agent_id = ?
    ''', (datetime.now(), agent_id))
    
    conn.commit()
    conn.close()


# 测试函数
def test_sync():
    """测试同步功能"""
    print("\n=== 测试 OpenClaw Subagents 同步 ===")
    
    # 初始化数据库
    init_agent_db()
    
    # 获取 OpenClaw subagents
    oc_agents = get_openclaw_subagents()
    print(f"\nOpenClaw Subagents: {len(oc_agents)}")
    for agent in oc_agents:
        print(f"  - {agent.get('label', 'Unknown')}: {agent.get('status', 'unknown')} @ {agent.get('model', 'N/A')}")
    
    # 同步
    sync_openclaw_agents()
    
    # 获取所有 Agent
    print("\n本地 Agent 状态:")
    agents = get_all_agents()
    for agent in agents:
        print(f"  {agent['emoji']} {agent['name']}: {agent['status']} - {agent['current_task'] or '无任务'}")
        if agent['model'] != '-':
            print(f"      模型：{agent['model']} | 时长：{agent['running_duration']}")
    
    # 统计数据
    print("\nDashboard 统计:")
    stats = get_dashboard_stats()
    print(f"  总 Agent 数：{stats['total_agents']}")
    print(f"  运行中：{stats['active_agents']}")
    print(f"  空闲：{stats['idle_agents']}")
    print(f"  异常：{stats['error_agents']}")
    if stats['model_distribution']:
        print(f"  模型分布：{stats['model_distribution']}")


if __name__ == '__main__':
    test_sync()
