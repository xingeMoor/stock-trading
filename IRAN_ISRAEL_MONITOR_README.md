# 伊朗 - 以色列冲突舆情监控系统

## 📋 系统概述

本系统用于 7×24 小时持续监控"美国以色列攻打伊朗"相关舆情，包括：
- 中英文新闻和社交媒体监控
- 情感分析和趋势追踪
- 美股/A 股市场影响评估
- 实时警报和报告生成

## 🚀 快速启动

### 启动监控
```bash
cd /Users/gexin/.openclaw/workspace
./iran_israel_monitor_start.sh
```

### 查看状态
```bash
./iran_israel_monitor_status.sh
```

### 停止监控
```bash
./iran_israel_monitor_stop.sh
```

## 📊 监控配置

### 监控关键词 (16 个)
**英文**:
- Iran Israel attack
- US Iran military
- Middle East conflict
- Iran war
- Israel Iran strike
- Iran oil
- Middle East crisis
- Iran US tension

**中文**:
- 美国以色列攻打伊朗
- 伊朗局势
- 中东冲突
- 伊朗战争
- 以伊冲突
- 伊朗油价
- 中东危机
- 美伊紧张

### 监控股票 (24 只)
**美股 - 能源**: XOM, CVX, COP, SLB  
**美股 - 军工**: LMT, RTX, NOC, GD  
**美股 - 航空**: DAL, UAL, AAL  
**美股 - 航运**: FDX, UPS  
**A 股 - 石油**: 601857.SS, 600028.SS, 000825.SZ  
**A 股 - 军工**: 600760.SS, 000768.SZ, 600893.SS  
**A 股 - 黄金**: 600547.SS, 601899.SS  
**A 股 - 航空**: 601111.SS, 600029.SS, 601021.SS  

### 大宗商品 (5 种)
- WTI 原油 (CL=F)
- Brent 原油 (BZ=F)
- 黄金 (GC=F)
- 天然气 (NG=F)
- 铜 (HG=F)

## 📁 文件结构

```
/Users/gexin/.openclaw/workspace/
├── sentiment_iran_israel_analysis.md    # 舆情分析报告
├── iran_israel_sentiment_monitor.py     # 监控主程序
├── iran_israel_monitor_start.sh         # 启动脚本
├── iran_israel_monitor_stop.sh          # 停止脚本
├── iran_israel_monitor_status.sh        # 状态检查脚本
├── iran_israel_cron_config.txt          # Cron 配置
├── sentiment_iran_israel_db.sqlite      # 舆情数据库
└── logs/
    ├── iran_israel_monitor_*.log        # 监控日志
    └── iran_israel_monitor.pid          # 进程 PID
```

## 📈 数据分析

### 查看数据库
```bash
# 查看最新舆情统计
sqlite3 sentiment_iran_israel_db.sqlite "SELECT * FROM heat_statistics ORDER BY timestamp DESC LIMIT 5;"

# 查看警报
sqlite3 sentiment_iran_israel_db.sqlite "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 10;"

# 查看舆情数据
sqlite3 sentiment_iran_israel_db.sqlite "SELECT keyword, sentiment_label, sentiment_score FROM sentiment_data ORDER BY timestamp DESC LIMIT 20;"
```

### 查看日志
```bash
# 实时查看日志
tail -f logs/iran_israel_monitor_*.log

# 查看最近 100 行
tail -100 logs/iran_israel_monitor_*.log
```

## 🚨 警报系统

系统会自动检测以下情况并发出警报：

1. **情感突变警报 (HIGH)**: 负面情绪占比 > 60%
2. **声量暴增警报 (MEDIUM)**: 单轮采集数据 > 100 条
3. **系统错误警报 (CRITICAL)**: 监控系统出错

警报会记录在数据库 `alerts` 表中。

## ⏰ 7×24 小时运行

### 方式一：后台进程 (推荐)
```bash
./iran_israel_monitor_start.sh
```
进程会持续运行，每 5 分钟执行一轮监控。

### 方式二：Cron 守护
将 `iran_israel_cron_config.txt` 中的配置添加到 crontab：
```bash
crontab -e
# 粘贴 iran_israel_cron_config.txt 内容
```

Cron 会每分钟检查进程状态，确保监控不中断。

## 📊 报告生成

### 查看最新报告
```bash
cat sentiment_iran_israel_analysis.md
```

### 报告内容
- 事件热度趋势
- 情感倾向分析
- 主要舆论观点
- 美股/A 股影响评估
- 风险预警
- 监控状态

## 🔧 自定义配置

### 修改监控股票
编辑 `iran_israel_sentiment_monitor.py` 中的 `FOCUS_STOCKS` 列表。

### 修改监控关键词
编辑 `iran_israel_sentiment_monitor.py` 中的 `MONITOR_KEYWORDS` 字典。

### 修改监控频率
编辑 `iran_israel_sentiment_monitor.py` 中的 `check_interval` 变量（默认 300 秒）。

## 📝 注意事项

1. **API 限制**: 当前使用模拟数据，实际使用需配置新闻 API
2. **磁盘空间**: 日志文件会持续增长，建议定期清理
3. **数据库备份**: 定期备份 `sentiment_iran_israel_db.sqlite`
4. **进程监控**: 使用 `./iran_israel_monitor_status.sh` 定期检查

## 🆘 故障排除

### 进程意外停止
```bash
# 查看最后日志
tail -100 logs/iran_israel_monitor_*.log

# 重启监控
./iran_israel_monitor_start.sh
```

### 数据库错误
```bash
# 备份数据库
cp sentiment_iran_israel_db.sqlite sentiment_iran_israel_db.sqlite.bak

# 重新初始化
rm sentiment_iran_israel_db.sqlite
python3 -c "import sqlite3; conn = sqlite3.connect('sentiment_iran_israel_db.sqlite'); conn.close()"
```

### 日志文件过大
```bash
# 清理 7 天前的日志
find logs -name "*iran_israel*.log" -mtime +7 -delete
```

## 📞 技术支持

系统由 Q 脑舆情监控系统自动生成和维护。

---

**最后更新**: 2026-03-02  
**版本**: v1.0
