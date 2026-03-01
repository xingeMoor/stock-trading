# Q 脑量化交易系统 - 作战指挥图
# 最后更新：2026-03-01 23:25
# 版本：20260301-v6 - P3 系统重构全面开战

## 🎯 统帅：小七 (Q 宝) - qwen3.5-plus

---

## 📊 军团状态 (9 个 Agent)

### ✅ 已完成 (1/9)
| Agent | 模型 | 任务 | 成果 | 提交 |
|-------|------|------|------|------|
| Factor-选股引擎 | doubao-seed-2.0-code | 四层漏斗筛选 | A 股 0.7%/美股 0.3% 入选率 | c04beef |

### 🔄 开发中 (3/9)
| Agent | 模型 | 任务 | 耗时 | 状态 |
|-------|------|------|------|------|
| Dev-数据层 | doubao-seed-2.0-code | 统一数据接口 | 13 分钟 | 🔄 进行中 |
| Risk-风控层 | doubao-seed-2.0-code | Kelly 仓位管理 | 12 分钟 | 🔄 进行中 |
| Backer-回测 | doubao-seed-2.0-code | ETF 批量回测 | 12 分钟 | 🔄 进行中 |

### 🔄 测试中 (3/9)
| Agent | 模型 | 任务 | 耗时 | 状态 |
|-------|------|------|------|------|
| Testy-单元测试 | doubao-seed-2.0-code | 模块单元测试 | 刚启动 | 🆕 |
| Testy-Web 测试 | doubao-seed-2.0-code | Web+API 测试 | 刚启动 | 🆕 |
| Testy-舆情测试 | doubao-seed-2.0-code | 舆情 API 测试 | 刚启动 | 🆕 |

### ⏳ 待命 (2/9)
| Agent | 模型 | 任务 | 状态 |
|-------|------|------|------|
| Archie-架构师 | qwen3.5-plus | 代码审核 | ⏳ 等待中 (已达 5/5 Agent 上限) |
| Ops-运维 | doubao-seed-2.0-code | 部署脚本 | ⏳ 等待中 |

---

## 🎯 作战阶段

### 阶段 1: 并行开发 (23:10 - 23:40) ✅ 进行中
- [x] 选股引擎完成 ✅
- [ ] 数据层重构 (预计 23:40)
- [ ] 风控执行层 (预计 23:40)
- [ ] 回测验证 (预计 23:40)

### 阶段 2: 全面测试 (23:40 - 00:10) 🔄 准备中
- [ ] 单元测试 (覆盖率 > 80%)
- [ ] Web 页面测试 (5001/5005/5006 端口)
- [ ] API 端点测试
- [ ] 舆情 API 测试
- [ ] API 定时检测脚本

### 阶段 3: 架构审核 (00:10 - 00:20) ⏳ 待命
- [ ] 代码质量审核
- [ ] 架构整合
- [ ] 性能优化建议

### 阶段 4: 合并部署 (00:20 - 00:30) ⏳ 待命
- [ ] 代码合并到 main
- [ ] 阿里云部署
- [ ] 生产环境验证

---

## 📁 预计交付清单

### 核心模块
- [x] src/stock_screener.py (选股引擎) ✅
- [x] src/filters/*.py (四层筛选器) ✅
- [ ] src/data_provider.py (数据接口)
- [ ] src/data_cache.py (缓存层)
- [ ] src/risk_manager.py (风控管理)
- [ ] src/position_manager.py (仓位管理)
- [ ] src/order_executor.py (订单执行)
- [ ] src/batch_backtester.py (批量回测)

### 测试文件
- [ ] tests/test_data_provider.py
- [ ] tests/test_screener.py
- [ ] tests/test_risk_manager.py
- [ ] tests/test_backtester.py
- [ ] tests/test_web_pages.py
- [ ] tests/test_api_endpoints.py
- [ ] tests/test_sentiment_api.py

### 工具脚本
- [ ] src/api_health_checker.py (API 定时检测)
- [ ] src/sentiment_api_tester.py (舆情 API 检测)

### 文档报告
- [ ] code_review_report.md
- [ ] web_test_report.md
- [ ] sentiment_test_report.md
- [ ] coverage_report.md
- [ ] integration_guide.md

---

## ⏰ 时间线

```
23:10 ─┬─ 启动 4 个开发 Agent ✅
       │
23:15 ─┼─ Factor-Agent 完成 (选股引擎) ✅
       │
23:25 ─┼─ 启动 3 个测试 Agent ✅
       │
23:40 ─┼─ 预计开发 Agent 全部完成
       │
23:50 ─┼─ 预计测试 Agent 完成
       │
00:00 ─┼─ 架构审核完成
       │
00:10 ─┴─ 合并部署完成
```

---

## 🎯 成功标准

- [ ] 所有模块通过单元测试 (覆盖率 > 80%)
- [ ] Web 服务 100% 可用 (5001/5005/5006)
- [ ] API 端点测试通过率 > 95%
- [ ] 舆情 API 响应时间 < 500ms
- [ ] 代码审核无重大问题
- [ ] 部署后服务正常运行

---

## 📢 通讯协议

- 各 Agent 完成后自动汇报
- 遇到问题立即上报
- 每 15 分钟同步一次进度
- 紧急问题直接@统帅

---

**统帅指令**: 各军团按计划推进，保持通讯畅通，确保质量第一！🚀
