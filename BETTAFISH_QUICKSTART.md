# 🐠 BettaFish 舆情系统 - 快速启动指南

## ✅ 已完成

- [x] GitHub 仓库克隆：`/Users/gexin/.openclaw/workspace/BettaFish`
- [x] 配置文件创建：`.env` (从示例复制)
- [x] 集成文档编写：`BettaFish_Integration_Guide.md`
- [x] 启动脚本创建：`start_bettafish_simple.sh`

## ⚠️ 注意事项

**Python 版本**: 当前系统 Python 3.9.6，BettaFish 部分依赖需要 Python 3.10+

**解决方案**:
1. 使用简化模式（仅报告生成）- 推荐
2. 升级 Python 到 3.10+
3. 使用 Docker 运行（如果有 Docker）

## 🔧 快速配置 (3 步)

### 步骤 1: 配置 API Key

编辑 `/Users/gexin/.openclaw/workspace/BettaFish/.env`:

```bash
# 使用阿里云百炼 API（推荐）
INSIGHT_ENGINE_API_KEY=sk-你的 API 密钥
INSIGHT_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
INSIGHT_ENGINE_MODEL_NAME=qwen-plus

QUERY_ENGINE_API_KEY=sk-你的 API 密钥
QUERY_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QUERY_ENGINE_MODEL_NAME=qwen-plus

REPORT_ENGINE_API_KEY=sk-你的 API 密钥
REPORT_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REPORT_ENGINE_MODEL_NAME=qwen-max
```

### 步骤 2: 启动服务

```bash
cd /Users/gexin/.openclaw/workspace/BettaFish
bash ../start_bettafish_simple.sh
```

### 步骤 3: 测试运行

```bash
# 访问 Web 界面
open http://localhost:5000

# 或命令行测试
python3 report_engine_only.py --query "美国以色列攻打伊朗"
```

## 📊 与 Q 脑系统集成

### 方案 A: API 调用（推荐）

Q 脑系统通过 HTTP API 调用 BettaFish:

```python
# 在 Q 脑系统中调用
import requests

def analyze_sentiment(query: str):
    response = requests.post('http://localhost:5000/analyze', json={
        'query': query,
        'depth': 'shallow'  # 快速模式
    })
    return response.json()

# 使用
result = analyze_sentiment("美国以色列攻打伊朗")
```

### 方案 B: 报告文件共享

BettaFish 生成的报告保存在 `final_reports/` 目录，Q 脑系统可以直接读取：

```python
# 读取最新报告
import glob
reports = glob.glob('BettaFish/final_reports/*.html')
latest_report = max(reports)
```

### 方案 C: 数据库集成

将 BettaFish 分析结果写入 Q 脑数据库：

```sql
INSERT INTO sentiment_analysis (
    query, 
    sentiment_score, 
    report_path, 
    created_at
) VALUES (
    '美国以色列攻打伊朗',
    -0.65,
    'BettaFish/final_reports/report_20260302.html',
    datetime('now')
);
```

## 🔄 持续监控配置

### Cron 定时任务

编辑 crontab (`crontab -e`):

```bash
# 每小时执行一次舆情分析
0 * * * * cd /Users/gexin/.openclaw/workspace/BettaFish && python3 report_engine_only.py --query "中东局势 伊朗 以色列" --output ../logs/bettafish_$(date +\%Y\%m\%d_\%H\%M\%S).json

# 每天早上 8 点生成日报
0 8 * * * cd /Users/gexin/.openclaw/workspace/BettaFish && python3 report_engine_only.py --query "美股 市场舆情" --depth deep
```

### 监控脚本

创建 `bettafish_monitor.py`:

```python
#!/usr/bin/env python3
"""BettaFish 舆情监控脚本"""
import subprocess
import datetime

keywords = [
    "美国 以色列 伊朗",
    "中东局势",
    "石油 价格",
    "军工 股票"
]

for keyword in keywords:
    subprocess.run([
        'python3', 'report_engine_only.py',
        '--query', keyword,
        '--depth', 'shallow'
    ], cwd='/Users/gexin/.openclaw/workspace/BettaFish')
```

## 📈 预期输出

BettaFish 生成的报告包含：

1. **舆情概览** - 事件热度、传播趋势
2. **情感分析** - 正面/负面/中性比例
3. **关键观点** - 主要舆论观点总结
4. **来源分析** - 媒体来源分布
5. **影响评估** - 对市场/行业的潜在影响

## 🎯 当前优先级

1. **高**: 配置 API Key 并启动服务
2. **中**: 集成到 Q 脑 5009 端口页面
3. **低**: 配置定时任务自动运行

---

**文档创建时间**: 2026-03-02 07:38  
**状态**: 等待 API Key 配置
