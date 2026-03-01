# 豆包Seed模型配置
# API Key: 09fb81b5-5151-4e50-9eb4-2ef06ecf4a7f

## 模型列表

| 模型ID | 名称 | 说明 |
|--------|------|------|
| Doubao-Seed-2.0-Code | 豆包Seed 2.0编程 | 前端出众，多语言适配 |
| Doubao-Seed-Code | 豆包Seed编程 | 代码生成、任务调度 |
| Kimi-K2.5 | Moonshot AI | 前端代码质量强化 |
| GLM-4.7 | 智谱AI | 代码生成、调试 |
| Deepseek-V3.2 | 深度求索 | 推理与代码开发 |
| Kimi-K2-thinking | Moonshot MoE | 复杂代码开发、Agent任务 |

## OpenClaw配置

```yaml
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
          cost:
            input: 0
            output: 0
            cacheRead: 0
            cacheWrite: 0
          contextWindow: 200000
          maxTokens: 8192
        - id: Doubao-Seed-Code
          name: Doubao-Seed-Code
          reasoning: false
          input: [text]
          cost:
            input: 0
            output: 0
            cacheRead: 0
            cacheWrite: 0
          contextWindow: 200000
          maxTokens: 8192
        - id: Kimi-K2.5
          name: Kimi-K2.5
          reasoning: false
          input: [text]
          cost:
            input: 0
            output: 0
            cacheRead: 0
            cacheWrite: 0
          contextWindow: 200000
          maxTokens: 8192
        - id: GLM-4.7
          name: GLM-4.7
          reasoning: false
          input: [text]
          cost:
            input: 0
            output: 0
            cacheRead: 0
            cacheWrite: 0
          contextWindow: 200000
          maxTokens: 8192
        - id: Deepseek-V3.2
          name: Deepseek-V3.2
          reasoning: false
          input: [text]
          cost:
            input: 0
            output: 0
            cacheRead: 0
            cacheWrite: 0
          contextWindow: 200000
          maxTokens: 8192
        - id: Kimi-K2-thinking
          name: Kimi-K2-thinking
          reasoning: true
          input: [text]
          cost:
            input: 0
            output: 0
            cacheRead: 0
            cacheWrite: 0
          contextWindow: 200000
          maxTokens: 8192

auth:
  profiles:
    volcengine:default:
      provider: volcengine
      mode: api_key

agents:
  defaults:
    model:
      primary: volcengine/Doubao-Seed-2.0-Code
    models:
      volcengine/Doubao-Seed-2.0-Code:
        alias: volcengine
    workspace: /Users/gexin/.openclaw/workspace
    compaction:
      mode: safeguard
    maxConcurrent: 4
    subagents:
      maxConcurrent: 8
```

## Agent模型分配建议

| Agent类型 | 推荐模型 |
|-----------|---------|
| 编码Agent (Dev, Testy) | Doubao-Seed-2.0-Code |
| 前端Agent (Pixel) | Doubao-Seed-2.0-Code / Kimi-K2.5 |
| 架构Agent (Archie) | GLM-4.7 / Deepseek-V3.2 |
| 金融Agent (Factor, Trader) | Doubao-Seed-Code |
| 分析Agent (Senti, Funda) | Kimi-K2-thinking |
