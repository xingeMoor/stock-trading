#!/bin/bash
# 配置 OpenClaw 飞书集成

CONFIG_FILE="$HOME/.openclaw/openclaw.json"

echo "📝 配置 OpenClaw 飞书集成..."
echo ""

# 备份原配置
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d%H%M%S)"
    echo "✓ 已备份原配置"
fi

# 使用 jq 添加飞书配置
if command -v jq &> /dev/null; then
    jq '.plugins.entries.feishu = {
        "enabled": true,
        "config": {
            "channels": {
                "feishu": {
                    "enabled": true,
                    "appId": "cli_a928f3f8fb391bcb",
                    "appSecret": "K2ZFIbQ16II8KrcUwBMgEbOMqBH3P7sy",
                    "domain": "feishu",
                    "connectionMode": "websocket"
                }
            }
        }
    }' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    echo "✓ 飞书配置已添加到 $CONFIG_FILE"
else
    echo "❌ 需要安装 jq: brew install jq"
    exit 1
fi

echo ""
echo "📋 配置内容:"
jq '.plugins.entries.feishu' "$CONFIG_FILE"
echo ""
echo "⚠️  请重启 OpenClaw Gateway 使配置生效:"
echo "   openclaw gateway restart"
echo ""
