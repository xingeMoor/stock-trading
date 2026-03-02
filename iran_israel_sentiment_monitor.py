#!/usr/bin/env python3
"""
伊朗 - 以色列 - 美国冲突专项舆情监控
7×24 小时持续运行
"""
import sys
import os
import logging
import time
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sentiment.monitor import StockSentimentMonitor

# 配置日志
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'iran_israel_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 监控关键词
MONITOR_KEYWORDS = {
    'en': [
        'Iran Israel attack',
        'US Iran military',
        'Middle East conflict',
        'Iran war',
        'Israel Iran strike',
        'Iran oil',
        'Middle East crisis',
        'Iran US tension'
    ],
    'zh': [
        '美国以色列攻打伊朗',
        '伊朗局势',
        '中东冲突',
        '伊朗战争',
        '以伊冲突',
        '伊朗油价',
        '中东危机',
        '美伊紧张'
    ]
}

# 监控股票 (与事件高度相关)
FOCUS_STOCKS = [
    # 美股 - 能源
    ('XOM', '埃克森美孚'),
    ('CVX', '雪佛龙'),
    ('COP', '康菲石油'),
    ('SLB', '斯伦贝谢'),
    # 美股 - 军工
    ('LMT', '洛克希德马丁'),
    ('RTX', '雷神技术'),
    ('NOC', '诺斯罗普格鲁曼'),
    ('GD', '通用动力'),
    # 美股 - 航空 (负面)
    ('DAL', '达美航空'),
    ('UAL', '联合航空'),
    ('AAL', '美国航空'),
    # 美股 - 航运 (负面)
    ('FDX', '联邦快递'),
    ('UPS', '联合包裹'),
    # A 股 - 石油
    ('601857.SS', '中国石油'),
    ('600028.SS', '中国石化'),
    ('000825.SZ', '太钢不锈'),
    # A 股 - 军工
    ('600760.SS', '中航沈飞'),
    ('000768.SZ', '中航西飞'),
    ('600893.SS', '航发动力'),
    # A 股 - 黄金 (避险)
    ('600547.SS', '山东黄金'),
    ('601899.SS', '紫金矿业'),
    # A 股 - 航空 (负面)
    ('601111.SS', '中国国航'),
    ('600029.SS', '南方航空'),
    ('601021.SS', '春秋航空'),
]

# 大宗商品
COMMODITIES = [
    ('CL=F', 'WTI 原油'),
    ('BZ=F', 'Brent 原油'),
    ('GC=F', '黄金'),
    ('NG=F', '天然气'),
    ('HG=F', '铜'),
]


class IranIsraelSentimentMonitor(StockSentimentMonitor):
    """伊朗 - 以色列冲突专项舆情监控器"""
    
    def __init__(self):
        super().__init__()
        self.db_path = Path('sentiment_iran_israel_db.sqlite')
        self.init_database()
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建舆情数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                keyword TEXT NOT NULL,
                language TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                sentiment_label TEXT,
                sentiment_score REAL,
                url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建热度统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS heat_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_mentions INTEGER,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                avg_sentiment REAL,
                top_keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建市场影响表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_impact (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                price REAL,
                change_percent REAL,
                volume INTEGER,
                sentiment_correlation REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建警报表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
        
    def save_sentiment_data(self, data_list):
        """保存舆情数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for data in data_list:
            cursor.execute('''
                INSERT INTO sentiment_data 
                (timestamp, keyword, language, source, title, summary, 
                 sentiment_label, sentiment_score, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp', datetime.now().isoformat()),
                data.get('keyword', ''),
                data.get('language', 'unknown'),
                data.get('source', 'unknown'),
                data.get('title', ''),
                data.get('summary', ''),
                data.get('label', 'neutral'),
                data.get('compound', 0),
                data.get('url', '')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"保存 {len(data_list)} 条舆情数据到数据库")
        
    def save_heat_statistics(self, stats):
        """保存热度统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO heat_statistics 
            (timestamp, total_mentions, positive_count, negative_count, 
             neutral_count, avg_sentiment, top_keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            stats.get('total_mentions', 0),
            stats.get('positive_count', 0),
            stats.get('negative_count', 0),
            stats.get('neutral_count', 0),
            stats.get('avg_sentiment', 0),
            json.dumps(stats.get('top_keywords', []))
        ))
        
        conn.commit()
        conn.close()
        
    def save_market_data(self, symbol, name, price, change_pct, volume):
        """保存市场数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_impact 
            (timestamp, symbol, name, price, change_percent, volume)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            symbol,
            name,
            price,
            change_pct,
            volume
        ))
        
        conn.commit()
        conn.close()
        
    def create_alert(self, alert_type, severity, message):
        """创建警报"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (timestamp, alert_type, severity, message)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            alert_type,
            severity,
            message
        ))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"🚨 警报 [{severity}]: {message}")
        
    def simulate_data_collection(self):
        """模拟数据采集 (实际应调用 API)"""
        # 这里是模拟数据，实际应调用新闻 API
        simulated_news = []
        
        for keyword in MONITOR_KEYWORDS['en'] + MONITOR_KEYWORDS['zh']:
            # 模拟新闻数据
            news_item = {
                'timestamp': datetime.now().isoformat(),
                'keyword': keyword,
                'language': 'en' if keyword in MONITOR_KEYWORDS['en'] else 'zh',
                'source': 'simulated',
                'title': f'Simulated news about {keyword}',
                'summary': f'Simulated summary for {keyword}',
                'label': 'negative',
                'compound': -0.65,
                'url': 'https://example.com'
            }
            simulated_news.append(news_item)
            
        return simulated_news
        
    def generate_report(self):
        """生成分析报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取最新统计
        cursor.execute('''
            SELECT * FROM heat_statistics 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        latest_stats = cursor.fetchone()
        
        # 获取警报数量
        cursor.execute('''
            SELECT COUNT(*) FROM alerts 
            WHERE acknowledged = 0
        ''')
        unack_alerts = cursor.fetchone()[0]
        
        conn.close()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'running',
            'latest_stats': latest_stats,
            'unacknowledged_alerts': unack_alerts,
            'monitor_keywords_count': len(MONITOR_KEYWORDS['en']) + len(MONITOR_KEYWORDS['zh']),
            'monitor_stocks_count': len(FOCUS_STOCKS),
            'monitor_commodities_count': len(COMMODITIES)
        }
        
        return report
        
    def run_monitoring_cycle(self):
        """执行一轮监控"""
        logger.info("=" * 60)
        logger.info(f"开始舆情监控周期 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            # 1. 采集舆情数据
            logger.info("正在采集舆情数据...")
            news_data = self.simulate_data_collection()
            logger.info(f"采集到 {len(news_data)} 条舆情数据")
            
            # 2. 保存到数据库
            if news_data:
                self.save_sentiment_data(news_data)
                
            # 3. 分析情感
            positive_count = sum(1 for n in news_data if n.get('label') == 'positive')
            negative_count = sum(1 for n in news_data if n.get('label') == 'negative')
            neutral_count = sum(1 for n in news_data if n.get('label') == 'neutral')
            
            avg_sentiment = sum(n.get('compound', 0) for n in news_data) / len(news_data) if news_data else 0
            
            # 4. 保存统计
            stats = {
                'total_mentions': len(news_data),
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count,
                'avg_sentiment': avg_sentiment,
                'top_keywords': list(set(n.get('keyword', '') for n in news_data))[:10]
            }
            self.save_heat_statistics(stats)
            
            # 5. 检查警报条件
            if negative_count > len(news_data) * 0.6:  # 负面超过 60%
                self.create_alert(
                    'SENTIMENT_SPIKE',
                    'HIGH',
                    f'负面情绪占比过高：{negative_count/len(news_data)*100:.1f}%'
                )
                
            if len(news_data) > 100:  # 声量过大
                self.create_alert(
                    'VOLUME_SPIKE',
                    'MEDIUM',
                    f'舆情声量激增：{len(news_data)} 条'
                )
                
            # 6. 生成报告
            report = self.generate_report()
            logger.info(f"监控周期完成 - 负面：{negative_count}, 中性：{neutral_count}, 正面：{positive_count}")
            logger.info(f"平均情感得分：{avg_sentiment:.3f}")
            
            return report
            
        except Exception as e:
            logger.error(f"监控周期出错：{e}", exc_info=True)
            self.create_alert(
                'SYSTEM_ERROR',
                'CRITICAL',
                f'监控系统出错：{str(e)}'
            )
            return None


def main():
    """主函数"""
    logger.info("🚀 " + "=" * 58)
    logger.info("伊朗 - 以色列 - 美国冲突舆情监控系统启动")
    logger.info("=" * 60)
    logger.info(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"工作目录：{os.getcwd()}")
    logger.info("=" * 60)
    
    # 创建监控器
    monitor = IranIsraelSentimentMonitor()
    
    # 添加监控股票
    for symbol, name in FOCUS_STOCKS:
        monitor.add_stock(symbol, name)
    
    logger.info(f"✅ 已添加 {len(FOCUS_STOCKS)} 只重点监控股票")
    logger.info(f"✅ 已添加 {len(COMMODITIES)} 种大宗商品监控")
    logger.info(f"✅ 已配置 {len(MONITOR_KEYWORDS['en']) + len(MONITOR_KEYWORDS['zh'])} 个监控关键词")
    logger.info("=" * 60)
    
    # 持续监控循环
    check_interval = 300  # 5 分钟检查一次
    
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            logger.info(f"\n📊 第 {cycle_count} 轮监控")
            
            # 执行监控
            report = monitor.run_monitoring_cycle()
            
            if report:
                logger.info(f"✅ 第 {cycle_count} 轮监控完成")
                logger.info(f"   数据点：{report['latest_stats'][1] if report['latest_stats'] else 0}")
                logger.info(f"   未处理警报：{report['unacknowledged_alerts']}")
            
            # 每 12 轮 (1 小时) 输出一次摘要
            if cycle_count % 12 == 0:
                logger.info("\n" + "=" * 60)
                logger.info("📈 小时摘要")
                logger.info(f"   已完成监控轮次：{cycle_count}")
                logger.info(f"   运行时长：{cycle_count * check_interval / 60:.1f} 分钟")
                logger.info("=" * 60)
            
            # 等待下一轮
            logger.info(f"\n⏳ {check_interval}秒后进行下一轮检查...")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ 收到中断信号，停止监控")
            logger.info(f"总运行轮次：{cycle_count}")
            logger.info(f"总运行时长：{cycle_count * check_interval / 60:.1f} 分钟")
            break
        except Exception as e:
            logger.error(f"❌ 监控循环出错：{e}", exc_info=True)
            logger.info("60 秒后重试...")
            time.sleep(60)


if __name__ == '__main__':
    main()
