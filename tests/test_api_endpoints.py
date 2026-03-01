"""
API 端点测试套件
测试 Q 脑量化交易系统的 REST API 端点

测试范围:
- Web Dashboard API (端口 5001, 5005, 5006)
- 数据接口测试
- 错误处理测试

使用 pytest 框架，支持 CI/CD 集成
"""
import pytest
import requests
import json
from typing import Dict, Any, List


# ============ 配置 ============
BASE_URLS = {
    "trading_monitor": "http://localhost:5001",
    "backtest_dashboard": "http://localhost:5005",
    "system_status": "http://localhost:5006",
}

TIMEOUT = 10  # 请求超时时间（秒）


# ============ Fixtures ============
@pytest.fixture(scope="module")
def api_urls():
    """提供 API URL 的 fixture"""
    return BASE_URLS


@pytest.fixture(scope="function")
def session():
    """创建 requests session"""
    session = requests.Session()
    yield session
    session.close()


# ============ 辅助函数 ============
def validate_json_response(response: requests.Response, required_fields: List[str]) -> Dict[str, Any]:
    """
    验证 JSON 响应
    
    Args:
        response: HTTP 响应
        required_fields: 必需字段列表
    
    Returns:
        dict: 解析后的 JSON 数据
    
    Raises:
        AssertionError: 如果验证失败
    """
    assert response.status_code == 200, f"HTTP {response.status_code}: {response.text}"
    assert "application/json" in response.headers.get("Content-Type", ""), "不是 JSON 格式"
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        pytest.fail(f"JSON 解析失败：{e}")
    
    missing_fields = [field for field in required_fields if field not in data]
    assert not missing_fields, f"缺少必需字段：{missing_fields}"
    
    return data


# ============ System Status API 测试 ============
class TestSystemStatusAPI:
    """测试系统状态监控 API"""
    
    def test_api_status_endpoint(self, session):
        """测试 /api/status 端点"""
        url = f"{BASE_URLS['system_status']}/api/status"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            data = validate_json_response(response, ["tools", "stats", "feishu"])
            
            # 验证 tools 结构
            assert isinstance(data["tools"], list), "tools 应该是列表"
            if data["tools"]:
                tool = data["tools"][0]
                assert "name" in tool, "工具缺少 name 字段"
                assert "status" in tool, "工具缺少 status 字段"
                assert "response_time" in tool, "工具缺少 response_time 字段"
            
            # 验证 stats 结构
            stats = data["stats"]
            assert "total" in stats, "stats 缺少 total 字段"
            assert "normal" in stats, "stats 缺少 normal 字段"
            assert "error" in stats, "stats 缺少 error 字段"
            
            # 验证 feishu 结构
            feishu = data["feishu"]
            assert "webhook" in feishu, "feishu 缺少 webhook 字段"
            assert "app" in feishu, "feishu 缺少 app 字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")
    
    def test_api_tool_history_endpoint(self, session):
        """测试 /api/tool-history/<tool_name> 端点"""
        tool_name = "Alpha Vantage"
        url = f"{BASE_URLS['system_status']}/api/tool-history/{tool_name}"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            data = validate_json_response(response, ["tool_name", "history"])
            
            assert data["tool_name"] == tool_name, f"tool_name 不匹配：{data['tool_name']}"
            assert isinstance(data["history"], list), "history 应该是列表"
            
            if data["history"]:
                entry = data["history"][0]
                assert "time" in entry, "历史记录缺少 time 字段"
                assert "response_time" in entry, "历史记录缺少 response_time 字段"
                assert "status" in entry, "历史记录缺少 status 字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")
    
    def test_api_status_response_time(self, session):
        """测试 /api/status 响应时间"""
        url = f"{BASE_URLS['system_status']}/api/status"
        
        try:
            import time
            start = time.time()
            response = session.get(url, timeout=TIMEOUT)
            elapsed = (time.time() - start) * 1000
            
            assert response.status_code == 200
            assert elapsed < 1000, f"响应时间过长：{elapsed:.2f}ms"
            
            print(f"✓ /api/status 响应时间：{elapsed:.2f}ms")
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ Backtest Dashboard API 测试 ============
class TestBacktestDashboardAPI:
    """测试回测分析面板 API"""
    
    def test_api_batches_endpoint(self, session):
        """测试 /api/batches 端点"""
        url = f"{BASE_URLS['backtest_dashboard']}/api/batches"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            data = validate_json_response(response, [])  # 返回的是列表
            
            assert isinstance(data, list), "应该返回批次列表"
            
            if data:
                batch = data[0]
                assert "batch_id" in batch, "批次缺少 batch_id 字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_api_batch_detail_endpoint(self, session):
        """测试 /api/batch/<batch_id> 端点"""
        # 先获取批次列表
        try:
            batches_response = session.get(
                f"{BASE_URLS['backtest_dashboard']}/api/batches",
                timeout=TIMEOUT
            )
            batches = batches_response.json()
            
            if batches:
                batch_id = batches[0]["batch_id"]
                url = f"{BASE_URLS['backtest_dashboard']}/api/batch/{batch_id}"
                
                response = session.get(url, timeout=TIMEOUT)
                data = validate_json_response(response, ["results", "sectors"])
                
                assert isinstance(data["results"], list), "results 应该是列表"
                assert isinstance(data["sectors"], dict), "sectors 应该是字典"
            else:
                pytest.skip("没有可用的批次数据")
                
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_api_compare_endpoint(self, session):
        """测试 /api/compare 端点"""
        url = f"{BASE_URLS['backtest_dashboard']}/api/compare"
        
        try:
            # 不带参数的比较（应该返回空或错误）
            response = session.get(url, timeout=TIMEOUT)
            # 不应该返回 500
            assert response.status_code != 500, "服务器内部错误"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")


# ============ Trading Monitor API 测试 ============
class TestTradingMonitorAPI:
    """测试模拟交易监控 API"""
    
    def test_main_page(self, session):
        """测试主页面"""
        url = f"{BASE_URLS['trading_monitor']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            assert "<!DOCTYPE html>" in response.text
            
        except requests.exceptions.ConnectionError:
            pytest.skip("模拟交易监控服务未运行")


# ============ 错误处理测试 ============
class TestErrorHandling:
    """测试 API 错误处理"""
    
    def test_invalid_tool_name(self, session):
        """测试无效工具名称"""
        url = f"{BASE_URLS['system_status']}/api/tool-history/NonExistentTool_12345"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            # 应该返回 200（可能返回空历史）或 404，但不应该 500
            assert response.status_code != 500, "服务器内部错误"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")
    
    def test_malformed_batch_id(self, session):
        """测试格式错误的批次 ID"""
        url = f"{BASE_URLS['backtest_dashboard']}/api/batch/invalid-@#$-id"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            # 应该返回 400 或 404，但不应该 500
            assert response.status_code in [200, 400, 404, 405], (
                f"意外状态码：{response.status_code}"
            )
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_nonexistent_endpoint(self, session):
        """测试不存在的端点"""
        url = f"{BASE_URLS['system_status']}/api/nonexistent_endpoint_xyz"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            # 应该返回 404 或 405
            assert response.status_code in [404, 405], (
                f"期望 404 或 405, 实际：{response.status_code}"
            )
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")
    
    def test_method_not_allowed(self, session):
        """测试方法不允许"""
        url = f"{BASE_URLS['system_status']}/api/status"
        
        try:
            # 尝试 POST 请求（应该只支持 GET）
            response = session.post(url, timeout=TIMEOUT)
            assert response.status_code in [405, 404, 200], (
                f"意外状态码：{response.status_code}"
            )
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 数据验证测试 ============
class TestDataValidation:
    """测试数据验证"""
    
    def test_status_data_types(self, session):
        """测试状态数据类型正确性"""
        url = f"{BASE_URLS['system_status']}/api/status"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            data = response.json()
            
            # 验证 stats 字段类型
            stats = data["stats"]
            assert isinstance(stats["total"], int), "total 应该是整数"
            assert isinstance(stats["normal"], int), "normal 应该是整数"
            
            # 验证 tools 数据类型
            for tool in data["tools"]:
                assert isinstance(tool["response_time"], (int, float)), (
                    "response_time 应该是数字"
                )
                assert tool["status"] in ["normal", "warning", "error"], (
                    f"无效状态：{tool['status']}"
                )
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")
    
    def test_tool_history_data_types(self, session):
        """测试工具历史数据类型"""
        url = f"{BASE_URLS['system_status']}/api/tool-history/Test"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            data = response.json()
            
            for entry in data["history"]:
                assert isinstance(entry["response_time"], (int, float)), (
                    "response_time 应该是数字"
                )
                assert entry["status"] in ["normal", "warning", "error"], (
                    f"无效状态：{entry['status']}"
                )
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 性能测试 ============
class TestPerformance:
    """测试 API 性能"""
    
    def test_api_response_time_baseline(self, session):
        """测试 API 响应时间基线"""
        import time
        
        endpoints = [
            f"{BASE_URLS['system_status']}/api/status",
            f"{BASE_URLS['backtest_dashboard']}/api/batches",
        ]
        
        for url in endpoints:
            try:
                start = time.time()
                response = session.get(url, timeout=TIMEOUT)
                elapsed = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    assert elapsed < 2000, f"{url} 响应时间过长：{elapsed:.2f}ms"
                    print(f"✓ {url} 响应时间：{elapsed:.2f}ms")
                
            except requests.exceptions.ConnectionError:
                pass  # 服务未运行，跳过
    
    def test_concurrent_api_requests(self, session):
        """测试并发 API 请求"""
        import concurrent.futures
        
        url = f"{BASE_URLS['system_status']}/api/status"
        
        def make_request():
            try:
                response = session.get(url, timeout=TIMEOUT)
                return response.status_code == 200
            except:
                return False
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(5)]
                results = [f.result() for f in futures]
            
            success_count = sum(results)
            # 至少 80% 成功
            assert success_count >= 4, f"并发成功率过低：{success_count}/5"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 安全性测试 ============
class TestSecurity:
    """测试基本安全性"""
    
    def test_no_sensitive_data_exposure(self, session):
        """测试不暴露敏感数据"""
        url = f"{BASE_URLS['system_status']}/api/status"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            data = response.json()
            
            # 检查是否暴露敏感信息
            response_text = response.text.lower()
            sensitive_patterns = [
                "password",
                "secret",
                "token=",
                "api_key=",
                "private_key",
            ]
            
            for pattern in sensitive_patterns:
                assert pattern not in response_text, (
                    f"可能暴露敏感信息：{pattern}"
                )
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 主入口 ============
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
