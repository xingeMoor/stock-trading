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
    从 OpenClaw Gateway 获取真实的 subagents 状态
    
    使用 openclaw gateway call status --json 命令
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
        # 使用 openclaw gateway call status 获取会话信息
        result = subprocess.run(
            ['openclaw', 'gateway', 'call', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                all_agents = []
                
                # 从 sessions.recent 中获取所有会话
                sessions = data.get('sessions', {})
                recent_sessions = sessions.get('recent', [])
                
                for session in recent_sessions:
                    session_key = session.get('key', '')
                    
                    # 只处理 subagent 会话
                    if 'subagent' not in session_key:
                        continue
                    
                    # 提取 label（从 session key 中提取）
                    # 格式: agent:main:subagent:uuid
                    parts = session_key.split(':')
                    uuid_part = parts[-1] if len(parts) > 3 else ''
                    
                    # 根据 session key 推断 label
                    label = infer_label_from_session(session_key, session)
                    
                    # 判断状态：如果有 updatedAt 且时间较近，认为是活跃的
                    updated_at = session.get('updatedAt', 0)
                    age_ms = session.get('age', 0)
                    
                    # 如果更新时间在5分钟内，认为是 running
                    if age_ms < 300000:  # 5分钟
                        status = 'running'
                    else:
                        status = 'completed'
                    
                    # 获取模型信息
                    model = session.get('model', '')
                    if model and not model.startswith('bailian/'):
                        model = f'bailian/{model}'
                    
                    all_agents.append({
                        "session_id": session_key,
                        "session_uuid": session.get('sessionId', ''),
                        "label": label,
                        "status": status,
                        "model": model,
                        "task": '',  # 从 session 无法直接获取任务描述
                        "input_tokens": session.get('inputTokens', 0),
                        "output_tokens": session.get('outputTokens', 0),
                        "total_tokens": session.get('totalTokens', 0),
                        "percent_used": session.get('percentUsed', 0),
                        "updated_at": updated_at,
                        "age_ms": age_ms,
                        "last_active": datetime.fromtimestamp(updated_at / 1000).isoformat() if updated_at else datetime.now().isoformat()
                    })
                
                return all_agents
                
            except json.JSONDecodeError as e:
                logger.error(f"解析 JSON 失败：{e}")
                return []
        
        logger.warning("OpenClaw gateway status 命令无输出")
        return []
        
    except subprocess.TimeoutExpired:
        logger.error("获取 OpenClaw subagents 超时")
        return []
    except Exception as e:
        logger.error(f"获取 OpenClaw subagents 失败：{e}")
        return []


def infer_label_from_session(session_key: str, session: Dict) -> str:
    """根据 session key 和 session 信息推断 Agent label"""
    # 已知的 session key 到 label 的映射
    known_mappings = {
        'c9599a81-800f-477c-8ffc-aaa03d911fed': 'PM-Master',
        'd2660e65-ab04-4c72-8443-295c9314f37f': 'Dev-5002Create',
        '2ccce32f-d134-41f0-b222-b1ea5382f364': 'XHS-Reviewer',
        '925b3dad-aea9-41ef-8388-b69ab94d2bc2': 'XHS-Writer',
        '16a8d581-d0f6-46df-8f6b-eea06d358952': 'Senti-Monitor',
        '9196ad5a-8ad6-4eff-b8da-9606d222b83d': 'Dev-5005Fix',
        'ef1774ae-d9cb-4a94-aa54-4c291205ea0d': 'Dev-5002Fix',
        'b06155c0-0e43-47cc-8814-9c786f1c2b6e': 'Ops-Deploy',
        '58a4e691-61a9-4e3c-94f4-de89f24b5cd9': 'Pixel-5007Fix',
    }
    
    # 从 session key 中提取 UUID
    parts = session_key.split(':')
    if len(parts) >= 4:
        uuid = parts[-1]
        if uuid in known_mappings:
            return known_mappings[uuid]
    
    # 根据模型推断
    model = session.get('model', '')
    if 'qwen3-coder' in model:
        return 'Dev'
    elif 'qwen3.5' in model:
        return 'PM'
    elif 'kimi' in model:
        return 'Ops'
    elif 'glm' in model:
        return 'Reviewer'
    elif 'MiniMax' in model:
        return 'Writer'
    
    return 'Unknown'


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
        age_ms = oc_agent.get('age_ms', 0)
        
        # 将 OpenClaw 状态映射到本地状态
        local_status = map_openclaw_status(status)
        
        # 计算运行时长（毫秒转秒）
        running_duration = age_ms // 1000 if age_ms > 0 else 0
        
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
    
    now = datetime.now()
    
    cursor.execute('''
        UPDATE agent_tasks 
        SET status = 'completed', completed_at = ?, result_summary = ?, quality_score = ?
        WHERE task_id = ?
    ''', (now, result_summary, quality_score, task_id))
    
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


def fail_task(task_id: str, error_message: str = ""):
    """标记任务失败"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now()
    
    cursor.execute('''
        UPDATE agent_tasks 
        SET status = 'failed', completed_at = ?, result_summary = ?
        WHERE task_id = ?
    ''', (now, error_message, task_id))
    
    # 获取 agent_id 并更新状态
    cursor.execute('SELECT agent_id FROM agent_tasks WHERE task_id = ?', (task_id,))
    row = cursor.fetchone()
    if row:
        agent_id = row[0]
        cursor.execute('''
            UPDATE agents SET status = 'error', current_task = NULL
            WHERE agent_id = ?
        ''', (agent_id,))
    
    conn.commit()
    conn.close()


def add_agent_log(agent_id: str, log_type: str, message: str, details: str = None):
    """添加 Agent 日志"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO agent_logs (agent_id, log_type, message, details)
        VALUES (?, ?, ?, ?)
    ''', (agent_id, log_type, message, details))
    
    conn.commit()
    conn.close()


def get_agent_logs(agent_id: str, limit: int = 50) -> List[Dict]:
    """获取 Agent 日志"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT log_type, message, details, created_at
        FROM agent_logs
        WHERE agent_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (agent_id, limit))
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'log_type': row[0],
            'message': row[1],
            'details': row[2],
            'created_at': row[3]
        })
    
    conn.close()
    return logs


if __name__ == '__main__':
    # 测试代码
    init_agent_db()
    
    print("=== 同步 OpenClaw Agents ===")
    sync_openclaw_agents()
    
    print("\n=== 所有 Agents ===")
    agents = get_all_agents()
    for agent in agents:
        print(f"{agent['emoji']} {agent['name']} ({agent['layer']}) - {agent['status']}")
        if agent['current_task']:
            print(f"   任务: {agent['current_task']}")
        if agent['model']:
            print(f"   模型: {agent['model']}")
    
    print("\n=== Dashboard 统计 ===")
    stats = get_dashboard_stats()
    print(f"总 Agent 数: {stats['total_agents']}")
    print(f"运行中: {stats['active_agents']}")
    print(f"空闲: {stats['idle_agents']}")
    print(f"异常: {stats['error_agents']}")
