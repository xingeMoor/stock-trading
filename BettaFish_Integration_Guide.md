# BettaFish 舆情系统集成指南

## 📦 项目信息

**GitHub**: https://github.com/666ghj/BettaFish  
**克隆位置**: `/Users/gexin/.openclaw/workspace/BettaFish`  
**克隆时间**: 2026-03-02 07:36

## 🏗️ 系统架构

BettaFish 是一个多 Agent 舆情分析系统，包含 5 个核心 Agent：

| Agent | 功能 | 推荐模型 |
|-------|------|---------|
| Query Agent | 精准信息搜索 | deepseek-chat |
| Media Agent | 多模态内容分析 | gemini-2.5-pro |
| Insight Agent | 私有数据库挖掘 | kimi-k2 |
| Report Agent | 智能报告生成 | gemini-2.5-pro |
| MindSpider Agent | 网络爬虫 | deepseek-chat |

## ⚙️ 配置步骤

### 1. 环境变量配置

编辑 `.env` 文件，配置以下关键参数：

```bash
# 主机配置
HOST=0.0.0.0
PORT=5000

# LLM API 配置（使用阿里云百炼）
INSIGHT_ENGINE_API_KEY=sk-xxx
INSIGHT_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
INSIGHT_ENGINE_MODEL_NAME=qwen-plus

MEDIA_ENGINE_API_KEY=sk-xxx
MEDIA_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MEDIA_ENGINE_MODEL_NAME=qwen-vl-max

QUERY_ENGINE_API_KEY=sk-xxx
QUERY_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QUERY_ENGINE_MODEL_NAME=qwen-plus

REPORT_ENGINE_API_KEY=sk-xxx
REPORT_ENGINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REPORT_ENGINE_MODEL_NAME=qwen-max

# 网络搜索（可选）
TAVILY_API_KEY=your_tavily_key
```

### 2. 依赖安装

```bash
cd /Users/gexin/.openclaw/workspace/BettaFish
pip3 install -r requirements.txt
```

**注意**: 部分包可能需要 Python 3.10+，如遇到兼容性问题：
- 使用虚拟环境：`python3.10 -m venv venv && source venv/bin/activate`
- 或跳过某些非核心依赖

### 3. 启动服务

#### 方式一：Flask Web 应用
```bash
python3 app.py
# 访问 http://localhost:5000
```

#### 方式二：命令行快速分析
```bash
python3 report_engine_only.py --query "美国以色列攻打伊朗"
```

#### 方式三：定时监控任务
```bash
# 创建 cron 任务，每小时执行一次
0 * * * * cd /Users/gexin/.openclaw/workspace/BettaFish && python3 report_engine_only.py --query "中东局势 伊朗 以色列"
```

## 🔗 与 Q 脑系统集成

### 集成方案

1. **数据层集成**: BettaFish 作为舆情数据源，输出 JSON 格式数据到 Q 脑数据库
2. **服务层集成**: BettaFish 作为独立服务运行 (5000 端口)，Q 脑通过 API 调用
3. **展示层集成**: 在 Q 脑 5009 端口页面嵌入 BettaFish 报告

### API 调用示例

```python
import requests

# 调用 BettaFish 进行舆情分析
response = requests.post('http://localhost:5000/analyze', json={
    'query': '美国以色列攻打伊朗',
    'depth': 'deep'  # shallow/deep
})

# 获取分析结果
result = response.json()
print(result['report_url'])  # HTML 报告地址
print(result['sentiment_score'])  # 情感得分
```

### 数据库集成

BettaFish 输出数据结构：
```json
{
  "query": "美国以色列攻打伊朗",
  "timestamp": "2026-03-02T07:40:00Z",
  "sentiment": {
    "positive": 0.15,
    "negative": 0.67,
    "neutral": 0.18
  },
  "sources": [...],
  "key_findings": [...],
  "report_html": "final_reports/report_20260302_074000.html"
}
```

## 📊 监控配置

### 监控关键词列表

```python
monitor_keywords = [
    "美国 以色列 伊朗 攻打",
    "中东局势",
    "伊朗 军事打击",
    "US Israel Iran attack",
    "Middle East conflict",
    "Iran military strike"
]
```

### 监控股票关联

```python
stock_keywords = {
    'AAPL': ['苹果', 'Apple', '供应链'],
    'TSLA': ['特斯拉', 'Tesla', '电动车'],
    'XOM': ['埃克森美孚', '石油', '能源'],
    'LMT': ['洛克希德马丁', '军工', '国防']
}
```

## 🚀 快速启动脚本

创建 `start_bettafish_monitor.sh`:

```bash
#!/bin/bash
cd /Users/gexin/.openclaw/workspace/BettaFish

# 启动 Flask 服务
nohup python3 app.py > logs/bettafish.log 2>&1 &

echo "BettaFish 服务已启动 (PID: $!)"
echo "访问地址：http://localhost:5000"
```

## 📝 下一步行动

1. ✅ 克隆仓库 - 已完成
2. ⏳ 配置环境变量 - 需要 API Key
3. ⏳ 安装依赖 - 部分包需要 Python 3.10+
4. ⏳ 启动服务 - 等待配置完成
5. ⏳ 集成到 Q 脑系统 - 等待服务启动

## 💡 建议

1. **使用阿里云百炼 API** - 兼容 OpenAI 格式，性价比高
2. **先跑通简单查询** - 验证配置后再进行复杂分析
3. **定期生成报告** - 设置 cron 任务每小时执行一次
4. **报告归档** - `final_reports/` 目录自动保存所有报告

---

**更新时间**: 2026-03-02 07:37  
**状态**: 仓库已克隆，等待配置和启动
