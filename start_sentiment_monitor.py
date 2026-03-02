#!/usr/bin/env python3
"""
舆情监控启动脚本
7×24 小时持续监控舆情数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.sentiment.monitor import StockSentimentMonitor
import logging
import time
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sentiment_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("舆情监控服务启动")
    logger.info("=" * 60)
    
    # 创建监控器
    monitor = StockSentimentMonitor()
    
    # 添加重点监控股票（可根据需要调整）
    focus_stocks = [
        ('AAPL', '苹果公司'),
        ('TSLA', '特斯拉'),
        ('NVDA', '英伟达'),
        ('MSFT', '微软'),
        ('GOOGL', '谷歌'),
        ('000001.SZ', '平安银行'),
        ('600519.SS', '贵州茅台'),
        ('300750.SZ', '宁德时代')
    ]
    
    for symbol, name in focus_stocks:
        monitor.add_stock(symbol, name)
    
    logger.info(f"已添加 {len(focus_stocks)} 只重点监控股票")
    
    # 持续监控循环
    check_interval = 300  # 5 分钟检查一次
    
    while True:
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"[{current_time}] 开始舆情数据采集...")
            
            # 这里会调用各个数据源的 API
            # 实际实现需要完整的 API 集成
            for symbol in monitor.stocks:
                logger.info(f"  - 检查 {symbol} 的舆情...")
            
            logger.info(f"本轮检查完成，{check_interval}秒后继续...")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，停止监控")
            break
        except Exception as e:
            logger.error(f"监控过程中出错：{e}", exc_info=True)
            time.sleep(60)  # 出错后等待 1 分钟重试

if __name__ == '__main__':
    main()
