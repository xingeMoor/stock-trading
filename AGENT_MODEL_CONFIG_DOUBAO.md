# Q脑 Agent - 豆包模型配置方案
# 版本: 20260301-v5
# API Key: 09fb81b5-5151-4e50-9eb4-2ef06ecf4a7f

## ✅ 已测试通过的模型

| 模型 | 状态 | 说明 |
|------|------|------|
| Doubao-Seed-2.0-Code | ✅ | 前端出众，多语言适配 |
| Doubao-Seed-Code | ✅ | 代码生成、任务调度 |
| Kimi-K2.5 | ✅ | 前端代码质量强化 |
| GLM-4.7 | ✅ | 代码生成、调试 |

---

## 🤖 Agent模型分配 (推荐)

### 工程开发层

| Agent | 角色 | 推荐模型 | 理由 |
|-------|------|---------|------|
| **Dev** 💻 | 后端开发 | Doubao-Seed-2.0-Code | 多语言适配，代码能力强 |
| **Pixel** 🎨 | UI/前端 | Doubao-Seed-2.0-Code / Kimi-K2.5 | 前端出众 |
| **Testy** 🧪 | 测试 | Doubao-Seed-2.0-Code | 代码生成精准 |
| **Archie** 🏗️ | 架构师 | GLM-4.7 | 全链路理解 |

### 量化金融层

| Agent | 角色 | 推荐模型 | 理由 |
|-------|------|---------|------|
| **Factor** 📊 | 因子分析 | Doubao-Seed-Code | 数据分析能力 |
| **Trader** 💹 | 交易执行 | Doubao-Seed-Code | 逻辑协同 |
| **Risk** 🛡️ | 风控 | GLM-4.7 | 复杂规则处理 |
| **Senti** 📰 | 舆情分析 | Kimi-K2.5 | 文本理解强 |
| **Funda** 📈 | 基本面 | GLM-4.7 | 财务分析 |
| **Guard** 🔒 | 防守审核 | Deepseek-V3.2 | 推理能力 |

### 桥梁协调层

| Agent | 角色 | 推荐模型 | 理由 |
|-------|------|---------|------|
| **Backer** 📉 | 回测系统 | Doubao-Seed-2.0-Code | 系统开发 |
| **Strategist** 🎯 | 策略沟通 | Kimi-K2-thinking | 复杂推理 |

### 管理监控层

| Agent | 角色 | 推荐模型 | 理由 |
|-------|------|---------|------|
| **PM** 📋 | 项目管理 | Doubao-Seed-Code | 任务调度 |
| **Ops** 🔧 | 运维 | Doubao-Seed-Code | 自动化脚本 |

---

## 📋 OpenClaw配置示例

```yaml
# ~/.openclaw/config.yaml

models:
  providers:
    volcengine:
      baseUrl: https://ark.cn-beijing.volces.com/api/coding/v3
      apiKey: 09fb81b5-5151-4e50-9eb4-2ef06ecf4a7f
      api: openai-completions
      models:
        - id: Doubao-Seed-2.0-Code
          name: Doubao-Seed-2.0-Code
          reasoning: false
          input: [text]
          contextWindow: 200000
          maxTokens: 8192
        - id: Doubao-Seed-Code
          name: Doubao-Seed-Code
          reasoning: false
          input: [text]
          contextWindow: 200000
          maxTokens: 8192
        - id: Kimi-K2.5
          name: Kimi-K2.5
          reasoning: false
          input: [text]
          contextWindow: 200000
          maxTokens: 8192
        - id: GLM-4.7
          name: GLM-4.7
          reasoning: false
          input: [text]
          contextWindow: 200000
          maxTokens: 8192
        - id: Deepseek-V3.2
          name: Deepseek-V3.2
          reasoning: false
          input: [text]
          contextWindow: 200000
          maxTokens: 8192
        - id: Kimi-K2-thinking
          name: Kimi-K2-thinking
          reasoning: true
          input: [text]
          contextWindow: 200000
          maxTokens: 8192

agents:
  # 编码Agent使用Doubao-Seed-2.0-Code
  developer:
    model: volcengine/Doubao-Seed-2.0-Code
  
  designer:
    model: volcengine/Kimi-K2.5
  
  tester:
    model: volcengine/Doubao-Seed-2.0-Code
  
  architect:
    model: volcengine/GLM-4.7
  
  # 金融Agent
  factor:
    model: volcengine/Doubao-Seed-Code
  
  trader:
    model: volcengine/Doubao-Seed-Code
  
  risk:
    model: volcengine/GLM-4.7
  
  # 其他Agent...
```

---

## 🚀 使用方式

启动Agent时指定模型:
```bash
openclaw agent run --model volcengine/Doubao-Seed-2.0-Code
```

或在配置文件中设置默认模型。

---

*配置时间: 2026-03-01 22:05 by 小七*
