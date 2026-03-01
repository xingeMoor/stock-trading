#!/usr/bin/env python3
"""
Tools状态监控系统 - 数据库模块
创建和管理SQLite数据库表结构
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

# 数据库文件路径
DB_PATH = Path(__file__).parent / "tools_monitor.db"


def init_database():
    """初始化数据库，创建所有必要的表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. tools_registry 表 - 注册所有工具
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tools_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL UNIQUE,
            tool_type TEXT NOT NULL CHECK(tool_type IN ('美股', 'A股', '飞书')),
            endpoint TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. tools_status 表 - 记录状态历史
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tools_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('up', 'down')),
            response_time REAL,
            error_msg TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tool_id) REFERENCES tools_registry(id)
        )
    """)

    # 3. feishu_status 表 - 飞书状态监控
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feishu_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_type TEXT NOT NULL CHECK(check_type IN ('webhook', 'app')),
            status TEXT NOT NULL CHECK(status IN ('up', 'down')),
            response_time REAL,
            error_msg TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引以优化查询性能
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tools_status_tool_id 
        ON tools_status(tool_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tools_status_checked_at 
        ON tools_status(checked_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_feishu_status_checked_at 
        ON feishu_status(checked_at)
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


def register_default_tools():
    """注册默认的工具配置"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    default_tools = [
        # 美股数据工具
        ("massive_api", "美股", "https://api.massive.com/v1/health", "Massive API - 美股数据源"),
        ("yahoo_finance", "美股", "https://finance.yahoo.com", "Yahoo Finance备用数据源"),

        # A股数据工具
        ("akshare_stock", "A股", "https://www.akshare.xyz/api/stock_zh_a_spot", "AKShare A股实时行情"),
        ("akshare_index", "A股", "https://www.akshare.xyz/api/index_zh_a_hist", "AKShare A股指数数据"),

        # 飞书相关
        ("feishu_webhook", "飞书", "https://open.feishu.cn/open-apis/bot/v2/hook", "飞书Webhook机器人"),
        ("feishu_app_api", "飞书", "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal", "飞书自建应用API"),
    ]

    for tool_name, tool_type, endpoint, description in default_tools:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO tools_registry (tool_name, tool_type, endpoint, description)
                VALUES (?, ?, ?, ?)
            """, (tool_name, tool_type, endpoint, description))
        except sqlite3.Error as e:
            print(f"⚠️ 注册工具失败 {tool_name}: {e}")

    conn.commit()
    conn.close()
    print("✅ 默认工具注册完成")


def get_all_tools():
    """获取所有已注册的工具"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools_registry")
    tools = cursor.fetchall()
    conn.close()
    return tools


def get_tool_by_name(tool_name):
    """根据名称获取工具信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools_registry WHERE tool_name = ?", (tool_name,))
    tool = cursor.fetchone()
    conn.close()
    return tool


def record_tool_status(tool_id, status, response_time=None, error_msg=None):
    """记录工具状态到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tools_status (tool_id, status, response_time, error_msg, checked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (tool_id, status, response_time, error_msg, datetime.now()))
    conn.commit()
    conn.close()


def record_feishu_status(check_type, status, response_time=None, error_msg=None):
    """记录飞书状态到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO feishu_status (check_type, status, response_time, error_msg, checked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (check_type, status, response_time, error_msg, datetime.now()))
    conn.commit()
    conn.close()


def get_latest_status(limit=100):
    """获取最新的状态记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, r.tool_name, r.tool_type 
        FROM tools_status s
        JOIN tools_registry r ON s.tool_id = r.id
        ORDER BY s.checked_at DESC
        LIMIT ?
    """, (limit,))
    records = cursor.fetchall()
    conn.close()
    return records


def get_feishu_latest_status(limit=50):
    """获取飞书最新的状态记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM feishu_status
        ORDER BY checked_at DESC
        LIMIT ?
    """, (limit,))
    records = cursor.fetchall()
    conn.close()
    return records


if __name__ == "__main__":
    # 如果直接运行此脚本，初始化数据库
    init_database()
    register_default_tools()
    print("\n📊 已注册的工具列表:")
    for tool in get_all_tools():
        print(f"  - {tool[1]} ({tool[2]}): {tool[3]}")
