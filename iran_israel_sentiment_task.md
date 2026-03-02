# 伊朗 - 以色列 - 美国 舆情分析专项任务

## 任务背景
近期中东局势紧张，美国以色列可能对伊朗采取军事行动，这对全球金融市场（尤其是美股/A 股）可能产生重大影响。

## 分析目标
1. **舆情热度分析** - 过去 48 小时该事件的讨论热度趋势
2. **情感倾向分析** - 正面/负面/中性情绪分布
3. **主要观点总结** - 各方立场和核心观点
4. **市场影响评估** - 对美股/A 股的潜在影响

## 数据源
- 国际新闻：Reuters, Bloomberg, CNN, BBC
- 社交媒体：Twitter, Reddit (r/geopolitics, r/worldnews)
- 中文媒体：微博，知乎，微信公众号
- 财经媒体：Finviz, Seeking Alpha, 雪球，东方财富

## 关键搜索词
### 英文
- "US Israel Iran attack"
- "Middle East conflict"
- "Iran military strike"
- "Israel Iran tension"
- "US military action Iran"

### 中文
- "美国 以色列 伊朗 攻打"
- "中东局势"
- "伊朗 军事打击"
- "以伊冲突"
- "中东 战争"

## 输出要求
1. 舆情分析报告 (markdown 格式)
2. 情感分析数据 (JSON 格式)
3. 市场影响评估 (包含具体板块和股票)
4. 实时告警机制 (重大舆情变化时通知)

## 执行时间
- **首次分析**: 立即执行
- **持续监控**: 7×24 小时
- **更新频率**: 每 30 分钟更新一次

## 负责人
- 舆情 Agent (Senti)
- 协助：Dev-Agent (API 集成)
