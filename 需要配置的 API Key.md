# 🔑 API Key 配置状态

## 当前配置

**API Key**: `sk-sp-a184e2d7f771427a9b0c3c869992ff5a`  
**Base URL**: `https://coding.dashscope.aliyuncs.com/v1` (用户提供)  
**测试状态**: ❌ 401 错误 (API Key 格式问题)

---

## ⚠️ 问题诊断

### 测试 1: coding.dashscope.aliyuncs.com
- **URL**: `https://coding.dashscope.aliyuncs.com/v1/chat/completions`
- **模型**: qwen-plus
- **结果**: ❌ 400 错误 - model not supported

### 测试 2: dashscope.aliyuncs.com (标准端点)
- **URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- **模型**: qwen-plus
- **结果**: ❌ 401 错误 - Incorrect API key provided

---

## 🔍 可能的原因

1. **API Key 格式**: `sk-sp-` 前缀可能是特殊类型的 Key
2. **端点不匹配**: coding 端点可能需要不同的认证方式
3. **账户状态**: API Key 可能未激活或已过期

---

## ✅ 解决方案

### 方案 1: 确认正确的 API Key

请登录阿里云百炼控制台确认：
1. 访问：https://bailian.console.aliyun.com/
2. 进入"API Key 管理"
3. 创建新的 API Key (标准格式)
4. 复制完整的 Key (应该是 `sk-` 开头，不含 `-sp-`)

### 方案 2: 使用 DashScope 原生 SDK

```python
import dashscope

dashscope.api_key = "sk-sp-a184e2d7f771427a9b0c3c869992ff5a"

response = dashscope.Generation.call(
    model='qwen-plus',
    messages=[{'role': 'user', 'content': '你好'}]
)
```

### 方案 3: 继续使用自研舆情系统

当前自研舆情监控系统已运行：
- **PID**: 65987
- **频率**: 每 5 分钟
- **状态**: ✅ 正常运行

---

## 📝 已配置文件

| 文件 | 状态 |
|------|------|
| `BettaFish/.env` | ✅ 已配置 API Key |
| `config/qbrain_config.py` | ✅ 已配置 API Key |

---

## 🎯 下一步

1. **确认 API Key** - 请提供标准的阿里云百炼 API Key
2. **或** - 继续使用自研舆情系统 (已正常运行)
3. **或** - 使用 DashScope SDK 方式集成

---

**更新时间**: 2026-03-02 07:55  
**状态**: 等待确认正确的 API Key
