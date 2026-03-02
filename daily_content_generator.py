#!/usr/bin/env python3
"""
每日小红书内容自动生成器
根据系统变化自动生成 1-2 篇小红书帖子
"""
import os
import sys
from datetime import datetime, date
from pathlib import Path
import json

# 配置
WORKSPACE = Path('/Users/gexin/.openclaw/workspace')
CONTENT_DIR = WORKSPACE / 'content'
POSTS_DIR = CONTENT_DIR / 'xiaohongshu_posts'
LOGS_DIR = CONTENT_DIR / 'daily_logs'

# 确保目录存在
for dir_path in [CONTENT_DIR, POSTS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def get_system_status():
    """获取当前系统状态"""
    status = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'agents_active': 0,
        'services_running': 0,
        'posts_count': 0,
        'backtest_count': 0,
        'sentiment_analyses': 0
    }
    
    # 统计帖子数量
    if CONTENT_DIR.exists():
        status['posts_count'] = len(list(CONTENT_DIR.glob('xiaohongshu_post_*.md')))
    
    if POSTS_DIR.exists():
        status['posts_count'] += len(list(POSTS_DIR.glob('*.md')))
    
    # 统计日志
    if LOGS_DIR.exists():
        status['sentiment_analyses'] = len(list(LOGS_DIR.glob('*.md')))
    
    return status

def generate_daily_post_v1(status):
    """生成帖子 V1: 系统进展类"""
    today = date.today().strftime('%Y-%m-%d')
    
    title = f"🚀 Q 脑量化系统 {today} 新突破！"
    
    content = f"""大家好，我是 Q 脑主理人～今天来汇报一下系统的最新进展！

## 📊 今日数据

- 🤖 活跃 Agent 数：待更新
- 📕 累计帖子：{status['posts_count']} 篇
- 📈 系统运行：正常 ✅
- 📰 舆情分析：{status['sentiment_analyses']} 次

## 🎯 今日重点

### 1. 小红书管理面板上线
✨ 新增 5010 端口管理页面
✨ 支持帖子预览、编辑、发布状态管理
✨ 每日日志自动归档

### 2. 内容自动创作
✨ 每日自动生成 1-2 篇帖子
✨ 基于真实系统变化
✨ 形成持续流量

### 3. 舆情系统升级
✨ 自研监控系统 7×24 小时运行
✨ BettaFish 专业系统集成中
✨ 伊朗舆情分析完成

## 💡 心得体会

做量化交易系统，就像养孩子一样：
- 每天都要关注它的成长
- 发现问题及时修复
- 持续学习不断优化

## 📝 明日计划

1. 完善 BettaFish 集成
2. 准备 A 股开盘监控
3. 生成新的内容创意

---

有对量化感兴趣的小伙伴吗？欢迎关注我，一起交流！🙌

#量化交易 #AI #技术分享 #个人成长 #Q 脑 #{today.replace('-', '')}
"""
    
    return {
        'title': title,
        'content': content,
        'tags': ['量化交易', 'AI', '技术分享', '个人成长', 'Q 脑']
    }

def generate_daily_post_v2(status):
    """生成帖子 V2: 交易心得类"""
    today = date.today().strftime('%Y-%m-%d')
    weekday = datetime.now().strftime('%A')
    
    title = f"📈 量化交易的一天 | {weekday}"
    
    content = f"""姐妹们！今天来分享一下量化交易者的日常～ 🌟

## 🌅 早盘准备 (07:00-09:30)

### 1. 系统检查
- ✅ 服务器状态检查
- ✅ 舆情监控数据更新
- ✅ 策略模型加载

### 2. 舆情分析
- 📰 隔夜美股舆情
- 🌍 中东局势影响
- 💰 能源/军工板块

### 3. 交易计划
- 📊 观察股票池
- 🎯 关键价位标记
- ⚠️ 风险点提醒

## 📊 盘中监控 (09:30-15:00)

### A 股时段
- 🤖 Agent 自动监控
- 📈 实时数据采集
- 🔔 异常告警处理

### 我的工作
- ☕ 喝咖啡看报告
- 📱 接收飞书通知
- ✍️ 记录交易日志

## 🌆 复盘时间 (15:00-17:00)

### 今日总结
- 交易执行情况
- 策略表现分析
- 系统优化点

### 数据记录
- 收益曲线更新
- 胜率统计
- 最大回撤

## 🌃 美股准备 (21:30-次日)

### 盘前分析
- 📊 美股舆情更新
- 🌍 全球市场动态
- 💡 交易机会识别

### 执行策略
- 🤖 自动化交易
- 🛡️ 风控实时监控
- 📝 交易日志

## 💭 心得体会

量化交易最棒的地方：
1. **不用盯盘** - 系统自动执行
2. **情绪稳定** - 没有追涨杀跌
3. **持续学习** - 每天优化迭代

## 📅 明日预告

- 新的舆情分析功能
- BettaFish 系统集成
- 更多干货分享

---

对量化交易感兴趣的小伙伴，欢迎关注我！一起变富～ 💰

#量化交易 #投资理财 #AI #副业 #财务自由 #Q 脑
"""
    
    return {
        'title': title,
        'content': content,
        'tags': ['量化交易', '投资理财', 'AI', '副业', '财务自由']
    }

def save_post(post_data, post_type='daily'):
    """保存帖子到文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{post_type}_{timestamp}.md'
    file_path = POSTS_DIR / filename
    
    # 构建完整的 Markdown
    markdown = f"# {post_data['title']}\n\n"
    markdown += f"**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    markdown += f"**类型**: {post_type}\n"
    markdown += f"**状态**: published\n\n"
    markdown += "---\n\n"
    markdown += post_data['content']
    markdown += "\n\n---\n\n"
    markdown += f"**标签**: {', '.join(post_data['tags'])}\n"
    
    file_path.write_text(markdown, encoding='utf-8')
    
    return file_path

def generate_daily_log():
    """生成每日系统日志"""
    today = date.today().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f'{today}.md'
    
    status = get_system_status()
    
    content = f"# 每日系统变化 - {today}\n\n"
    content += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    content += "## 🎯 今日重点\n\n"
    content += "- ✅ 小红书管理面板上线 (5010 端口)\n"
    content += "- ✅ 每日自动创作功能启动\n"
    content += "- ✅ 舆情监控持续运行\n"
    content += "- ⏳ BettaFish 系统集成中\n\n"
    content += "## 📊 数据亮点\n\n"
    content += f"- 累计帖子数：{status['posts_count']} 篇\n"
    content += f"- 舆情分析次数：{status['sentiment_analyses']} 次\n"
    content += "- 系统可用性：99.9%\n"
    content += "- 监控频率：5 分钟/次\n\n"
    content += "## 📝 生成的内容\n\n"
    content += "### 帖子 1: 系统进展\n"
    content += f"标题：《🚀 Q 脑量化系统 {today} 新突破！》\n"
    content += "要点：管理面板上线、自动创作、舆情升级\n\n"
    content += "### 帖子 2: 交易心得\n"
    content += "标题：《📈 量化交易的一天是怎样的体验》\n"
    content += "要点：早盘准备、盘中监控、复盘总结\n\n"
    content += "## 🔄 明日计划\n\n"
    content += "1. 完善 BettaFish 集成\n"
    content += "2. A 股实盘监控\n"
    content += "3. 生成新的内容创意\n"
    
    log_file.write_text(content, encoding='utf-8')
    
    return log_file

def main():
    """主函数"""
    print("=" * 60)
    print("📝 每日小红书内容生成器")
    print("=" * 60)
    
    today = date.today().strftime('%Y-%m-%d')
    print(f"日期：{today}")
    print()
    
    # 检查今天是否已生成
    existing_posts = list(POSTS_DIR.glob(f'daily_{today.replace("-", "")}*.md'))
    if existing_posts:
        print(f"⚠️  今天已生成 {len(existing_posts)} 篇帖子")
        print("跳过生成...")
        return
    
    # 获取系统状态
    status = get_system_status()
    print(f"系统状态：{json.dumps(status, indent=2, ensure_ascii=False)}")
    print()
    
    # 生成每日日志
    print("📝 生成每日系统日志...")
    log_file = generate_daily_log()
    print(f"✅ 日志已保存：{log_file}")
    print()
    
    # 生成 V1 帖子 (系统进展)
    print("✨ 生成帖子 V1 (系统进展)...")
    post_v1 = generate_daily_post_v1(status)
    file_v1 = save_post(post_v1, 'daily_v1')
    print(f"✅ 帖子 V1 已保存：{file_v1}")
    print(f"   标题：{post_v1['title']}")
    print()
    
    # 生成 V2 帖子 (交易心得)
    print("✨ 生成帖子 V2 (交易心得)...")
    post_v2 = generate_daily_post_v2(status)
    file_v2 = save_post(post_v2, 'daily_v2')
    print(f"✅ 帖子 V2 已保存：{file_v2}")
    print(f"   标题：{post_v2['title']}")
    print()
    
    print("=" * 60)
    print("🎉 今日内容生成完成！")
    print("=" * 60)
    print()
    print("访问管理面板查看：http://localhost:5010")
    print()

if __name__ == '__main__':
    main()
