#!/bin/bash
# 小红书内容管理系统 - 定时任务配置脚本

echo "📕 配置小红书内容管理定时任务"
echo "================================"
echo ""

# 检查 crontab 是否可用
if ! command -v crontab &> /dev/null; then
    echo "❌ crontab 未安装"
    exit 1
fi

# 显示当前 crontab
echo "📋 当前定时任务:"
crontab -l 2>/dev/null || echo "(无)"
echo ""

# 创建新的 cron 配置
CRON_FILE="/tmp/xiaohongshu_cron_$$"

# 读取现有配置
crontab -l 2>/dev/null > "$CRON_FILE" || true

# 添加新任务
cat >> "$CRON_FILE" << 'EOF'

# 小红书内容管理 - 每日自动生成 (08:00)
0 8 * * * cd /Users/gexin/.openclaw/workspace && /usr/bin/python3 daily_content_generator.py >> /Users/gexin/.openclaw/workspace/logs/xiaohongshu_daily.log 2>&1

# 小红书管理面板 - 健康检查 (每 5 分钟)
*/5 * * * * curl -s http://localhost:5010 > /dev/null || (echo "小红书管理面板异常" | mail -s "告警" admin@example.com)
EOF

# 安装新的 crontab
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo "✅ 定时任务配置完成！"
echo ""
echo "📋 新增任务:"
echo "  1. 每日 08:00 - 自动生成小红书内容"
echo "  2. 每 5 分钟 - 管理面板健康检查"
echo ""
echo "📝 查看配置:"
echo "  crontab -l"
echo ""
echo "📄 日志文件:"
echo "  /Users/gexin/.openclaw/workspace/logs/xiaohongshu_daily.log"
echo ""
