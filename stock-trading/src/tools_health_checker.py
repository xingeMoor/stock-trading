"""
Tools 健康检查模块
检测美股/A股数据源和飞书通知系统的可用性
"""
import sqlite3
import requests
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import akshare as ak

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools_monitor.db')

def init_database():
    """初始化监控数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tools注册表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tools_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT UNIQUE NOT NULL,
            tool_type TEXT NOT NULL,
            endpoint TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tools状态历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tools_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id INTEGER,
            status TEXT NOT NULL,
            response_time INTEGER,
            error_msg TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tool_id) REFERENCES tools_registry(id)
        )
    ''')
    
    # 飞书状态表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feishu_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            response_time INTEGER,
            error_msg TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 告警历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            tool_name TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acknowledged BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    
    # 初始化工具列表
    tools = [
        ('Massive API', 'US', 'https://api.massive.com/v1/health', '美股数据API'),
        ('akshare A股', 'A股', 'akshare.stock_zh_a_spot', 'A股数据接口'),
        ('akshare 港股', '港股', 'akshare.stock_hk_ggt_components_em', '港股数据接口'),
        ('akshare 基金', '基金', 'akshare.fund_etf_spot_em', '基金数据接口'),
    ]
    
    for name, type_, endpoint, desc in tools:
        cursor.execute('''
            INSERT OR IGNORE INTO tools_registry (tool_name, tool_type, endpoint, description)
            VALUES (?, ?, ?, ?)
        ''', (name, type_, endpoint, desc))
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def check_massive_api() -> Dict:
    """检测Massive API状态"""
    start_time = time.time()
    try:
        from config import MASSIVE_API_KEY
        headers = {'Authorization': f'Bearer {MASSIVE_API_KEY}'}
        response = requests.get(
            'https://api.massive.com/v1/reference/supported',
            headers=headers,
            timeout=10
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            return {
                'status': 'up',
                'response_time_ms': elapsed_ms,
                'error_msg': None
            }
        else:
            return {
                'status': 'down',
                'response_time_ms': elapsed_ms,
                'error_msg': f'HTTP {response.status_code}: {response.text[:100]}'
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'status': 'down',
            'response_time_ms': elapsed_ms,
            'error_msg': str(e)[:200]
        }

def check_akshare_a_stock() -> Dict:
    """检测akshare A股接口"""
    start_time = time.time()
    try:
        # 尝试获取A股实时行情
        df = ak.stock_zh_a_spot_em()
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if df is not None and len(df) > 0:
            return {
                'status': 'up',
                'response_time_ms': elapsed_ms,
                'error_msg': None,
                'data_count': len(df)
            }
        else:
            return {
                'status': 'down',
                'response_time_ms': elapsed_ms,
                'error_msg': '返回数据为空'
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'status': 'down',
            'response_time_ms': elapsed_ms,
            'error_msg': str(e)[:200]
        }

def check_akshare_etf() -> Dict:
    """检测akshare ETF接口"""
    start_time = time.time()
    try:
        df = ak.fund_etf_spot_em()
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if df is not None and len(df) > 0:
            return {
                'status': 'up',
                'response_time_ms': elapsed_ms,
                'error_msg': None,
                'data_count': len(df)
            }
        else:
            return {
                'status': 'down',
                'response_time_ms': elapsed_ms,
                'error_msg': '返回数据为空'
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'status': 'down',
            'response_time_ms': elapsed_ms,
            'error_msg': str(e)[:200]
        }

def check_feishu_webhook() -> Dict:
    """检测飞书Webhook"""
    start_time = time.time()
    try:
        from dotenv import load_dotenv
        load_dotenv()
        webhook = os.getenv('FEISHU_WEBHOOK')
        
        if not webhook:
            return {
                'status': 'down',
                'response_time_ms': 0,
                'error_msg': '未配置 FEISHU_WEBHOOK'
            }
        
        # 发送测试消息
        payload = {"msg_type": "text", "content": {"text": "健康检查"}}
        response = requests.post(webhook, json=payload, timeout=10)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                return {
                    'status': 'up',
                    'response_time_ms': elapsed_ms,
                    'error_msg': None
                }
            else:
                return {
                    'status': 'down',
                    'response_time_ms': elapsed_ms,
                    'error_msg': result.get('msg', '未知错误')
                }
        else:
            return {
                'status': 'down',
                'response_time_ms': elapsed_ms,
                'error_msg': f'HTTP {response.status_code}'
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'status': 'down',
            'response_time_ms': elapsed_ms,
            'error_msg': str(e)[:200]
        }

def check_feishu_app() -> Dict:
    """检测飞书自建应用"""
    start_time = time.time()
    try:
        from feishu_notification import get_access_token
        token = get_access_token()
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if token:
            return {
                'status': 'up',
                'response_time_ms': elapsed_ms,
                'error_msg': None
            }
        else:
            return {
                'status': 'down',
                'response_time_ms': elapsed_ms,
                'error_msg': '无法获取access token'
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'status': 'down',
            'response_time_ms': elapsed_ms,
            'error_msg': str(e)[:200]
        }

def run_health_check():
    """运行完整健康检查"""
    print(f"\n{'='*60}")
    print(f"🔍 系统健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查各工具状态
    checks = [
        ('Massive API', check_massive_api),
        ('akshare A股', check_akshare_a_stock),
        ('akshare 基金', check_akshare_etf),
    ]
    
    for tool_name, check_func in checks:
        result = check_func()
        
        # 获取tool_id
        cursor.execute('SELECT id FROM tools_registry WHERE tool_name = ?', (tool_name,))
        row = cursor.fetchone()
        if row:
            tool_id = row[0]
            cursor.execute('''
                INSERT INTO tools_status (tool_id, status, response_time, error_msg)
                VALUES (?, ?, ?, ?)
            ''', (tool_id, result['status'], result.get('response_time_ms', 0), result['error_msg']))
        
        status_icon = '✅' if result['status'] == 'up' else '❌'
        print(f"{status_icon} {tool_name}: {result['status']} ({result['response_time_ms']}ms)")
        if result['error_msg']:
            print(f"   错误: {result['error_msg']}")
    
    # 检查飞书状态
    print("\n📨 飞书状态:")
    
    feishu_checks = [
        ('webhook', check_feishu_webhook),
        ('app', check_feishu_app),
    ]
    
    for check_type, check_func in feishu_checks:
        result = check_func()
        cursor.execute('''
            INSERT INTO feishu_status (check_type, status, response_time, error_msg)
            VALUES (?, ?, ?, ?)
        ''', (check_type, result['status'], result.get('response_time_ms', 0), result['error_msg']))
        
        status_icon = '✅' if result['status'] == 'up' else '❌'
        print(f"{status_icon} {check_type}: {result['status']} ({result['response_time_ms']}ms)")
        if result['error_msg']:
            print(f"   错误: {result['error_msg']}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print("✅ 健康检查完成，结果已保存到数据库")
    print('='*60)

def get_tools_summary() -> Dict:
    """获取工具状态摘要"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取最新状态
    cursor.execute('''
        SELECT t.tool_name, t.tool_type, s.status, s.response_time_ms, s.checked_at
        FROM tools_registry t
        LEFT JOIN (
            SELECT tool_id, status, response_time_ms, checked_at,
                   ROW_NUMBER() OVER (PARTITION BY tool_id ORDER BY checked_at DESC) as rn
            FROM tools_status
        ) s ON t.id = s.tool_id AND s.rn = 1
    ''')
    
    tools = []
    for row in cursor.fetchall():
        tools.append({
            'name': row[0],
            'type': row[1],
            'status': row[2] or 'unknown',
            'response_time': row[3] or 0,
            'checked_at': row[4]
        })
    
    # 获取飞书状态
    cursor.execute('''
        SELECT check_type, status, response_time_ms, checked_at
        FROM feishu_status
        WHERE checked_at = (SELECT MAX(checked_at) FROM feishu_status WHERE check_type = feishu_status.check_type)
    ''')
    
    feishu = {}
    for row in cursor.fetchall():
        feishu[row[0]] = {
            'status': row[1],
            'response_time': row[2],
            'checked_at': row[3]
        }
    
    conn.close()
    
    return {
        'tools': tools,
        'feishu': feishu,
        'total_tools': len(tools),
        'up_count': sum(1 for t in tools if t['status'] == 'up'),
        'down_count': sum(1 for t in tools if t['status'] == 'down')
    }

if __name__ == '__main__':
    init_database()
    run_health_check()
