#!/usr/bin/env python3
"""
Tools状态监控定时任务调度器
使用APScheduler实现定时健康检查
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 导入健康检查模块
from tools_health_checker import HealthChecker, DatabaseManager, load_config

# 配置日志
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / 'scheduler.log')
    ]
)
logger = logging.getLogger(__name__)


class MonitorScheduler:
    """监控任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.checker = None
        self.db = None
        self.is_running = False
        self.config = {}
        
    async def init(self):
        """初始化组件"""
        self.db = DatabaseManager()
        self.checker = HealthChecker(self.db)
        self.config = load_config()
        
    async def check_all_tools(self):
        """检查所有工具状态（每5分钟）"""
        logger.info("=" * 50)
        logger.info("开始执行Tools健康检查...")
        logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            if not self.checker:
                await self.init()
                
            # 获取所有已注册的工具
            tools = self.db.get_all_tools()
            
            for tool in tools:
                tool_id, tool_name, tool_type, endpoint = tool
                
                # 跳过飞书类型的工具（单独检查）
                if tool_type == '飞书':
                    continue
                
                await self._check_tool_with_retry(tool_id, tool_name, tool_type)
            
            logger.info("Tools健康检查完成")
            
        except Exception as e:
            logger.error(f"Tools健康检查过程中发生错误: {e}")
            
    async def check_feishu(self):
        """检查飞书状态（每10分钟）"""
        logger.info("=" * 50)
        logger.info("开始执行飞书状态检查...")
        logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            if not self.checker:
                await self.init()
            
            webhook_url = self.config.get('feishu_webhook_url', '')
            app_id = self.config.get('feishu_app_id', '')
            app_secret = self.config.get('feishu_app_secret', '')
            
            # 检查Webhook
            if webhook_url:
                await self._check_feishu_webhook_with_retry(webhook_url)
            else:
                logger.warning("飞书Webhook URL未配置，跳过检查")
            
            # 检查App API
            if app_id and app_secret:
                await self._check_feishu_app_with_retry(app_id, app_secret)
            else:
                logger.warning("飞书应用凭证未配置，跳过检查")
            
            logger.info("飞书状态检查完成")
            
        except Exception as e:
            logger.error(f"飞书状态检查过程中发生错误: {e}")
    
    async def _check_tool_with_retry(self, tool_id: int, tool_name: str, tool_type: str, max_retries: int = 3):
        """带重试机制的工具检查"""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[{tool_name}] 第 {attempt} 次尝试...")
                
                if tool_type == '美股':
                    success, response_time, error = self.checker.check_massive_api()
                elif tool_type == 'A股':
                    success, response_time, error = self.checker.check_akshare_api()
                else:
                    logger.warning(f"[{tool_name}] 未知工具类型: {tool_type}")
                    return
                
                status = 'up' if success else 'down'
                self.db.record_tool_status(tool_id, status, response_time, error)
                
                if success:
                    logger.info(f"✓ [{tool_name}] 检查成功 ({response_time:.2f}ms)")
                    return
                else:
                    logger.warning(f"✗ [{tool_name}] 检查失败: {error}")
                    
                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # 指数退避: 2, 4, 8秒
                        logger.info(f"[{tool_name}] 等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[{tool_name}] 已达到最大重试次数 ({max_retries})")
                        
            except Exception as e:
                logger.error(f"[{tool_name}] 检查过程异常: {e}")
                self.db.record_tool_status(tool_id, 'down', 0, str(e))
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"[{tool_name}] 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[{tool_name}] 已达到最大重试次数 ({max_retries})")
    
    async def _check_feishu_webhook_with_retry(self, webhook_url: str, max_retries: int = 3):
        """带重试机制的飞书Webhook检查"""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[飞书Webhook] 第 {attempt} 次尝试...")
                
                success, response_time, error = self.checker.check_feishu_webhook(webhook_url)
                status = 'up' if success else 'down'
                self.db.record_feishu_status('webhook', status, response_time, error)
                
                if success:
                    logger.info(f"✓ [飞书Webhook] 检查成功 ({response_time:.2f}ms)")
                    return
                else:
                    logger.warning(f"✗ [飞书Webhook] 检查失败: {error}")
                    
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.info(f"[飞书Webhook] 等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[飞书Webhook] 已达到最大重试次数 ({max_retries})")
                        
            except Exception as e:
                logger.error(f"[飞书Webhook] 检查过程异常: {e}")
                self.db.record_feishu_status('webhook', 'down', 0, str(e))
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"[飞书Webhook] 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[飞书Webhook] 已达到最大重试次数 ({max_retries})")
    
    async def _check_feishu_app_with_retry(self, app_id: str, app_secret: str, max_retries: int = 3):
        """带重试机制的飞书App API检查"""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[飞书App API] 第 {attempt} 次尝试...")
                
                success, response_time, error = self.checker.check_feishu_app_api(app_id, app_secret)
                status = 'up' if success else 'down'
                self.db.record_feishu_status('app', status, response_time, error)
                
                if success:
                    logger.info(f"✓ [飞书App API] 检查成功 ({response_time:.2f}ms)")
                    return
                else:
                    logger.warning(f"✗ [飞书App API] 检查失败: {error}")
                    
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.info(f"[飞书App API] 等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[飞书App API] 已达到最大重试次数 ({max_retries})")
                        
            except Exception as e:
                logger.error(f"[飞书App API] 检查过程异常: {e}")
                self.db.record_feishu_status('app', 'down', 0, str(e))
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"[飞书App API] 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[飞书App API] 已达到最大重试次数 ({max_retries})")
                    
    def setup_jobs(self):
        """配置定时任务"""
        logger.info("正在配置定时任务...")
        
        # 每5分钟检查一次所有tools
        self.scheduler.add_job(
            self.check_all_tools,
            trigger=IntervalTrigger(minutes=5),
            id='check_all_tools',
            name='检查所有Tools状态',
            replace_existing=True,
            misfire_grace_time=300  # 5分钟的容错时间
        )
        logger.info("已添加任务: 每5分钟检查所有Tools")
        
        # 每10分钟检查一次飞书
        self.scheduler.add_job(
            self.check_feishu,
            trigger=IntervalTrigger(minutes=10),
            id='check_feishu',
            name='检查飞书状态',
            replace_existing=True,
            misfire_grace_time=600  # 10分钟的容错时间
        )
        logger.info("已添加任务: 每10分钟检查飞书状态")
        
    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行中")
            return
            
        # 初始化
        await self.init()
        
        logger.info("=" * 60)
        logger.info("Tools状态监控系统启动")
        logger.info("=" * 60)
        
        # 配置任务
        self.setup_jobs()
        
        # 启动调度器
        self.scheduler.start()
        self.is_running = True
        
        logger.info("调度器已启动")
        logger.info("任务列表:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.name}: {job.trigger}")
        
        # 立即执行一次检查
        logger.info("\n立即执行首次检查...")
        await self.check_all_tools()
        await self.check_feishu()
        
        logger.info("\n系统运行中，按 Ctrl+C 停止...")
        
        # 保持运行
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop()
            
    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
            
        logger.info("\n正在停止调度器...")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("调度器已停止")
        
    async def run_once(self):
        """仅运行一次检查（用于测试）"""
        logger.info("=" * 60)
        logger.info("执行单次检查模式")
        logger.info("=" * 60)
        
        await self.init()
        await self.check_all_tools()
        await self.check_feishu()
        
        logger.info("\n单次检查完成")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tools状态监控调度器')
    parser.add_argument(
        '--once',
        action='store_true',
        help='仅运行一次检查然后退出'
    )
    parser.add_argument(
        '--tools-only',
        action='store_true',
        help='仅检查Tools（不包括飞书）'
    )
    parser.add_argument(
        '--feishu-only',
        action='store_true',
        help='仅检查飞书'
    )
    
    args = parser.parse_args()
    
    scheduler = MonitorScheduler()
    
    try:
        if args.once:
            # 单次运行模式
            asyncio.run(scheduler.run_once())
        else:
            # 持续运行模式
            asyncio.run(scheduler.start())
            
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
