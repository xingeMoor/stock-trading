# Web 测试报告

**生成时间:** 2026-03-01  
**测试框架:** pytest  
**测试工程师:** Q 脑 Web-Test-Agent  

---

## 📋 测试概览

### 测试范围

本次测试覆盖 Q 脑量化交易系统的三个核心 Web 服务：

| 服务名称 | 端口 | 功能描述 |
|---------|------|---------|
| 模拟交易监控 | 5001 | 实时监控股票交易、持仓和资金曲线 |
| 回测分析面板 | 5005 | 展示策略回测结果和多策略对比分析 |
| 系统状态监控 | 5006 | 监控系统工具状态、API 健康和飞书集成 |

### 测试类型

1. **服务可用性测试** - 验证 Web 服务是否正常响应
2. **API 端点测试** - 测试 REST API 的功能和数据格式
3. **前端展示测试** - 验证页面渲染和数据展示正确性
4. **错误处理测试** - 测试异常情况下的错误处理
5. **性能测试** - 测量响应时间和并发能力
6. **安全性测试** - 检查敏感数据泄露

---

## 📁 交付物

### 测试文件

| 文件 | 路径 | 描述 |
|-----|------|------|
| Web 页面测试 | `tests/test_web_pages.py` | 测试 Web 页面渲染和交互功能 |
| API 端点测试 | `tests/test_api_endpoints.py` | 测试 REST API 端点 |
| 健康检查脚本 | `src/api_health_checker.py` | 定时检测 API 健康状态 |
| pytest 配置 | `pytest.ini` | pytest 配置文件 |
| 测试配置 | `tests/conftest.py` | 全局 fixtures 和配置 |

### 测试统计

| 测试文件 | 测试类 | 测试用例数 |
|---------|--------|-----------|
| test_web_pages.py | 6 | ~25 |
| test_api_endpoints.py | 8 | ~20 |
| **总计** | **14** | **~45** |

---

## 🔧 使用说明

### 运行所有测试

```bash
cd /Users/gexin/.openclaw/workspace
pytest
```

### 运行特定测试文件

```bash
# Web 页面测试
pytest tests/test_web_pages.py -v

# API 端点测试
pytest tests/test_api_endpoints.py -v
```

### 运行特定测试类

```bash
# 服务可用性测试
pytest tests/test_web_pages.py::TestServiceAvailability -v

# API 性能测试
pytest tests/test_api_endpoints.py::TestPerformance -v
```

### 运行特定测试用例

```bash
# 测试系统状态 API
pytest tests/test_api_endpoints.py::TestSystemStatusAPI::test_api_status_endpoint -v

# 测试页面渲染
pytest tests/test_web_pages.py::TestPageRendering::test_system_status_page -v
```

### 带参数运行

```bash
# 自定义服务 URL
pytest --service-url=http://localhost

# 自定义超时时间
pytest --timeout=30
```

### 生成测试报告

```bash
# HTML 报告（需要 pytest-html 插件）
pytest --html=reports/test_report.html

# JSON 报告（需要 pytest-json 插件）
pytest --json=reports/test_report.json

# 覆盖率报告（需要 pytest-cov 插件）
pytest --cov=src --cov-report=html
```

---

## 🏃 运行健康检查脚本

### 运行一次检查

```bash
python src/api_health_checker.py --once
```

### 持续监控（每 5 分钟）

```bash
python src/api_health_checker.py
```

### 自定义参数

```bash
# 自定义检查间隔（秒）
python src/api_health_checker.py --interval=60

# 自定义超时时间
python src/api_health_checker.py --timeout=5

# 组合参数
python src/api_health_checker.py --interval=120 --timeout=15
```

### 后台运行

```bash
# 使用 nohup
nohup python src/api_health_checker.py > logs/health_checker.log 2>&1 &

# 使用 screen
screen -S health_checker
python src/api_health_checker.py
# Ctrl+A, D 分离会话

# 使用 systemd（生产环境推荐）
sudo systemctl start api-health-checker
```

---

## 📊 测试覆盖

### Web 页面测试覆盖

#### 服务可用性 (TestServiceAvailability)
- ✅ 服务响应测试
- ✅ HTTP 200 状态码验证
- ✅ 响应时间基线测试

#### 页面渲染 (TestPageRendering)
- ✅ 模拟交易监控页面
- ✅ 回测分析面板页面
- ✅ 系统状态监控页面
- ✅ HTML 结构验证
- ✅ 必需元素检查

#### 数据展示 (TestDataDisplay)
- ✅ 交易统计数据
- ✅ 回测结果数据
- ✅ 系统状态数据

#### 交互功能 (TestInteractiveFeatures)
- ✅ 批次 API 端点
- ✅ 状态 API 端点
- ✅ 工具历史 API

#### 错误处理 (TestErrorHandling)
- ✅ 无效批次 ID
- ✅ 不存在端点
- ✅ 方法不允许

#### 并发测试 (TestConcurrency)
- ✅ 并发请求处理

### API 端点测试覆盖

#### System Status API (TestSystemStatusAPI)
- ✅ `/api/status` - 获取系统状态
- ✅ `/api/tool-history/<tool_name>` - 获取工具历史
- ✅ 响应时间测试

#### Backtest Dashboard API (TestBacktestDashboardAPI)
- ✅ `/api/batches` - 获取批次列表
- ✅ `/api/batch/<batch_id>` - 获取批次详情
- ✅ `/api/compare` - 对比多个批次

#### Trading Monitor API (TestTradingMonitorAPI)
- ✅ 主页面渲染

#### 错误处理 (TestErrorHandling)
- ✅ 无效工具名称
- ✅ 格式错误的批次 ID
- ✅ 不存在端点
- ✅ 方法不允许

#### 数据验证 (TestDataValidation)
- ✅ 数据类型验证
- ✅ 数据格式验证

#### 性能测试 (TestPerformance)
- ✅ 响应时间基线
- ✅ 并发请求

#### 安全性 (TestSecurity)
- ✅ 敏感数据泄露检查

---

## 🎯 CI/CD 集成

### GitHub Actions

创建 `.github/workflows/test.yml`:

```yaml
name: Web Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      # 启动测试服务（如果需要）
      trading-monitor:
        image: qbrain/trading-monitor:latest
        ports:
          - 5001:5001
      backtest-dashboard:
        image: qbrain/backtest-dashboard:latest
        ports:
          - 5005:5005
      system-status:
        image: qbrain/system-status:latest
        ports:
          - 5006:5006
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Wait for services
      run: |
        for port in 5001 5005 5006; do
          for i in {1..30}; do
            curl -s http://localhost:$port && break
            sleep 1
          done
        done
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml --cov-report=html
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### GitLab CI

创建 `.gitlab-ci.yml`:

```yaml
stages:
  - test

web_tests:
  stage: test
  image: python:3.10
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=src --cov-report=xml
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
  only:
    - main
    - develop
    - merge_requests
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install pytest pytest-cov'
                sh 'pytest --cov=src --cov-report=xml'
            }
            post {
                always {
                    junit 'reports/*.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }
    }
}
```

---

## 📈 监控告警

### 健康检查脚本功能

1. **定时检测** - 每 5 分钟自动检测所有 API
2. **日志记录** - 详细记录每次检测结果
3. **状态跟踪** - 跟踪服务连续失败次数
4. **告警通知** - 达到阈值时发送告警
5. **报告生成** - 生成 JSON 格式健康报告

### 日志文件

- **位置:** `logs/api_health_check.log`
- **格式:** `YYYY-MM-DD HH:MM:SS - APIHealthChecker - LEVEL - message`

### 状态报告

- **位置:** `logs/api_health_status.json`
- **内容:**
  ```json
  {
    "timestamp": "2026-03-01 23:30:00",
    "services": {
      "trading_monitor": {
        "name": "模拟交易监控",
        "url": "http://localhost:5001",
        "available": true,
        "last_check": "2026-03-01 23:30:00",
        "consecutive_failures": 0,
        "avg_response_time": 125.5,
        "last_error": null
      }
    },
    "summary": {
      "total": 3,
      "available": 3,
      "unavailable": 0
    }
  }
  ```

### 告警配置

在 `src/api_health_checker.py` 中修改:

```python
@dataclass
class Config:
    ALERT_THRESHOLD = 2      # 连续失败 2 次告警
    ALERT_COOLDOWN = 600     # 告警间隔 10 分钟
```

### 集成飞书告警

修改 `_send_feishu_alert` 方法:

```python
def _send_feishu_alert(self, message: str):
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if webhook_url:
        requests.post(
            webhook_url,
            json={
                "msg_type": "text",
                "content": {"text": message}
            }
        )
```

---

## 🔍 故障排查

### 常见问题

#### 1. 服务未运行

```bash
# 检查服务状态
curl http://localhost:5001
curl http://localhost:5005
curl http://localhost:5006

# 启动服务
cd stock-trading
python web_dashboard.py &
python backtest_dashboard_v2.py &
python system_status_dashboard.py &
```

#### 2. 测试跳过

如果看到 `SKIP` 标记，表示服务未运行:

```
tests/test_web_pages.py::TestServiceAvailability::test_service_responds SKIPPED
```

解决方法：先启动对应的 Web 服务。

#### 3. 超时错误

增加超时时间:

```bash
pytest --timeout=30
```

或修改测试文件中的 `TIMEOUT` 常量。

#### 4. 依赖缺失

```bash
pip install pytest requests
```

---

## 📝 后续改进

### 短期优化

- [ ] 添加更多 API 端点测试
- [ ] 集成飞书告警功能
- [ ] 添加视觉回归测试
- [ ] 增加负载测试

### 长期规划

- [ ] 自动化测试流水线
- [ ] 性能基准测试
- [ ] 安全渗透测试
- [ ] 用户行为模拟测试

---

## 📞 联系方式

**测试工程师:** Q 脑 Web-Test-Agent  
**项目:** Q 脑量化交易系统  
**文档版本:** 1.0  

---

*最后更新：2026-03-01*
