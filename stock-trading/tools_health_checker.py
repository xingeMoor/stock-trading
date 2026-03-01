#!/usr/bin/env python3
"""
Tools Health Checker - 检测各种工具和服务的状态
"""

import sqlite3
import requests
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(__file__).parent / "tools_monitor.db"

# API配置
MASSIVE_API_URL = 'https://api.massive.com/v1/market/status'
AKSHARE_TIMEOUT = 10
FEISHU_APP_TOKEN_URL = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
    
    def get_all_tools(self) -> list:
        """获取所有注册的工具"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, tool_name, tool_type, endpoint FROM tools_registry')
        tools = cursor.fetchall()
        conn.close()
        return tools
    
    def record_tool_status(self, tool_id: int, status: str, 
                          response_time: float, error_msg: Optional[str] = None):
        """记录工具状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tools_status (tool_id, status, response_time, error_msg, checked_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (tool_id, status, response_time, error_msg, datetime.now()))
        conn.commit()
        conn.close()
    
    def record_feishu_status(self, check_type: str, status: str,
                            response_time: float, error_msg: Optional[str] = None):
        """记录飞书状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feishu_status (check_type, status, response_time, error_msg, checked_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (check_type, status, response_time, error_msg, datetime.now()))
        conn.commit()
        conn.close()


class HealthChecker:
    """健康检查类"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.retry_count = 3
        self.retry_delay = 2  # 秒
    
    def _retry_wrapper(self, func, *args, **kwargs) -> Tuple[bool, float, Optional[str]]:
        """带重试机制的包装器"""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
                return True, elapsed, None
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{self.retry_count} failed: {last_error}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        
        return False, 0, last_error
    
    def check_massive_api(self) -> Tuple[bool, float, Optional[str]]:
        """检测Massive API (美股数据)"""
        def _check():
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; HealthChecker/1.0)'
            }
            response = requests.get(
                MASSIVE_API_URL,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        return self._retry_wrapper(_check)
    
    def check_akshare_api(self) -> Tuple[bool, float, Optional[str]]:
        """检测akshare A股接口"""
        def _check():
            try:
                import akshare as ak
                # 使用akshare获取上证指数作为健康检查
                df = ak.stock_zh_index_daily(symbol="sh000001")
                if df is None or df.empty:
                    raise Exception("Empty response from akshare")
                return df
            except ImportError:
                raise Exception("akshare module not installed")
        
        return self._retry_wrapper(_check)
    
    def check_feishu_webhook(self, webhook_url: str) -> Tuple[bool, float, Optional[str]]:
        """检测飞书Webhook - 发送测试消息"""
        def _check():
            if not webhook_url:
                raise Exception("Webhook URL not configured")
            
            payload = {
                "msg_type": "text",
                "content": {
                    "text": "Health check ping"
                }
            }
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            if result.get('code') != 0:
                raise Exception(f"Feishu webhook error: {result.get('msg')}")
            return result
        
        return self._retry_wrapper(_check)
    
    def check_feishu_app_api(self, app_id: str, app_secret: str) -> Tuple[bool, float, Optional[str]]:
        """检测飞书自建应用API"""
        def _check():
            if not app_id or not app_secret:
                raise Exception("App credentials not configured")
            
            payload = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            response = requests.post(
                FEISHU_APP_TOKEN_URL,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            if result.get('code') != 0:
                raise Exception(f"Feishu app API error: {result.get('msg')}")
            return result
        
        return self._retry_wrapper(_check)
    
    def check_all_tools(self):
        """检测所有已注册的工具"""
        tools = self.db.get_all_tools()
        
        for tool in tools:
            tool_id, tool_name, tool_type, endpoint = tool
            logger.info(f"Checking tool: {tool_name} ({tool_type})")
            
            try:
                if tool_type == '美股':
                    success, response_time, error = self.check_massive_api()
                elif tool_type == 'A股':
                    success, response_time, error = self.check_akshare_api()
                else:
                    logger.warning(f"Skipping tool type: {tool_type}")
                    continue
                
                status = 'up' if success else 'down'
                self.db.record_tool_status(tool_id, status, response_time, error)
                
                if success:
                    logger.info(f"✓ {tool_name}: UP ({response_time:.2f}ms)")
                else:
                    logger.error(f"✗ {tool_name}: DOWN - {error}")
                    
            except Exception as e:
                logger.exception(f"Error checking {tool_name}")
                self.db.record_tool_status(tool_id, 'down', 0, str(e))
    
    def check_feishu_services(self, webhook_url: str = '', app_id: str = '', app_secret: str = ''):
        """检测飞书服务"""
        # 检测Webhook
        if webhook_url:
            logger.info("Checking Feishu Webhook...")
            success, response_time, error = self.check_feishu_webhook(webhook_url)
            status = 'up' if success else 'down'
            self.db.record_feishu_status('webhook', status, response_time, error)
            
            if success:
                logger.info(f"✓ Feishu Webhook: UP ({response_time:.2f}ms)")
            else:
                logger.error(f"✗ Feishu Webhook: DOWN - {error}")
        
        # 检测App API
        if app_id and app_secret:
            logger.info("Checking Feishu App API...")
            success, response_time, error = self.check_feishu_app_api(app_id, app_secret)
            status = 'up' if success else 'down'
            self.db.record_feishu_status('app', status, response_time, error)
            
            if success:
                logger.info(f"✓ Feishu App API: UP ({response_time:.2f}ms)")
            else:
                logger.error(f"✗ Feishu App API: DOWN - {error}")


def load_config() -> Dict[str, str]:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.json"
    default_config = {
        'feishu_webhook_url': '',
        'feishu_app_id': '',
        'feishu_app_secret': ''
    }
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return {**default_config, **config}
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}")
        return default_config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid config file: {e}")
        return default_config


def run_health_check(check_tools: bool = True, check_feishu: bool = True):
    """运行健康检查"""
    logger.info("=" * 50)
    logger.info("Starting health check...")
    logger.info("=" * 50)
    
    db = DatabaseManager()
    checker = HealthChecker(db)
    config = load_config()
    
    if check_tools:
        checker.check_all_tools()
    
    if check_feishu:
        checker.check_feishu_services(
            webhook_url=config.get('feishu_webhook_url', ''),
            app_id=config.get('feishu_app_id', ''),
            app_secret=config.get('feishu_app_secret', '')
        )
    
    logger.info("=" * 50)
    logger.info("Health check completed")
    logger.info("=" * 50)


if __name__ == '__main__':
    run_health_check()
