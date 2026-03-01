# Web 测试快速指南

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install pytest requests pytest-cov
```

### 2. 运行所有测试

```bash
cd /Users/gexin/.openclaw/workspace
pytest
```

### 3. 运行特定测试

```bash
# Web 页面测试
pytest tests/test_web_pages.py -v

# API 端点测试
pytest tests/test_api_endpoints.py -v
```

## 📊 测试服务

测试覆盖以下 Web 服务：

| 服务 | 端口 | 状态 |
|-----|------|------|
| 模拟交易监控 | 5001 | 需要启动 |
| 回测分析面板 | 5005 | 需要启动 |
| 系统状态监控 | 5006 | 需要启动 |

### 启动服务

```bash
cd stock-trading

# 后台启动所有服务
python web_dashboard.py &
python backtest_dashboard_v2.py &
python system_status_dashboard.py &
```

## 🔍 运行健康检查

```bash
# 运行一次检查
python3 src/api_health_checker.py --once

# 持续监控（每 5 分钟）
python3 src/api_health_checker.py
```

## 📁 文件结构

```
workspace/
├── tests/
│   ├── conftest.py           # pytest 配置
│   ├── test_web_pages.py     # Web 页面测试
│   └── test_api_endpoints.py # API 端点测试
├── src/
│   └── api_health_checker.py # 健康检查脚本
├── pytest.ini                # pytest 配置
└── web_test_report.md        # 完整测试报告
```

## 📈 测试结果

- **总测试用例**: ~45 个
- **测试类**: 14 个
- **覆盖范围**: 服务可用性、API 功能、错误处理、性能、安全

## ⚠️ 注意事项

1. 测试前确保 Web 服务已启动
2. 如果服务未运行，测试会自动跳过 (SKIP)
3. 健康检查脚本会记录日志到 `logs/api_health_check.log`

## 📖 详细文档

查看完整测试报告：[web_test_report.md](web_test_report.md)
