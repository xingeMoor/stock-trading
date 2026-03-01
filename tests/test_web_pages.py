"""
Web 页面测试套件
测试 Q 脑量化交易系统的 Web 服务可用性和前端展示逻辑

测试范围:
- http://localhost:5001 (模拟交易监控)
- http://localhost:5005 (回测分析面板)
- http://localhost:5006 (系统状态监控)

使用 pytest 框架，支持 CI/CD 集成
"""
import pytest
import requests
import re
from typing import Dict, Any


# ============ 配置 ============
BASE_URLS = {
    "trading_monitor": "http://localhost:5001",
    "backtest_dashboard": "http://localhost:5005",
    "system_status": "http://localhost:5006",
}

TIMEOUT = 10  # 请求超时时间（秒）


# ============ Fixtures ============
@pytest.fixture(scope="module")
def service_urls():
    """提供服务 URL 的 fixture"""
    return BASE_URLS


@pytest.fixture(scope="function")
def session():
    """创建 requests session"""
    session = requests.Session()
    yield session
    session.close()


# ============ 辅助函数 ============
def check_service_health(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """
    检查服务健康状态
    
    Returns:
        dict: {
            "available": bool,
            "status_code": int,
            "response_time": float,
            "error": str or None
        }
    """
    import time
    result = {
        "available": False,
        "status_code": None,
        "response_time": None,
        "error": None
    }
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        result["response_time"] = (time.time() - start_time) * 1000  # ms
        result["status_code"] = response.status_code
        result["available"] = response.status_code == 200
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"ConnectionError: {str(e)}"
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result


def validate_html_content(html: str, required_elements: list) -> Dict[str, bool]:
    """
    验证 HTML 内容是否包含必需元素
    
    Args:
        html: HTML 内容
        required_elements: 必需包含的元素列表（可以是标签或文本）
    
    Returns:
        dict: {element: found}
    """
    results = {}
    for element in required_elements:
        # 检查是否是正则表达式
        if element.startswith("regex:"):
            pattern = element[6:]
            results[element] = bool(re.search(pattern, html, re.IGNORECASE))
        else:
            results[element] = element.lower() in html.lower()
    return results


# ============ 服务可用性测试 ============
class TestServiceAvailability:
    """测试 Web 服务的基本可用性"""
    
    @pytest.mark.parametrize("service_name,url", BASE_URLS.items())
    def test_service_responds(self, service_name, url):
        """测试服务是否响应"""
        result = check_service_health(url)
        
        assert result["available"], (
            f"服务 {service_name} ({url}) 不可用:\n"
            f"  错误：{result['error']}"
        )
    
    @pytest.mark.parametrize("service_name,url", BASE_URLS.items())
    def test_service_returns_200(self, service_name, url):
        """测试服务返回 200 状态码"""
        result = check_service_health(url)
        
        if result["available"]:
            assert result["status_code"] == 200, (
                f"服务 {service_name} 返回状态码 {result['status_code']}, 期望 200"
            )
    
    @pytest.mark.parametrize("service_name,url", BASE_URLS.items())
    def test_service_response_time(self, service_name, url):
        """测试服务响应时间（性能基线）"""
        result = check_service_health(url)
        
        if result["available"]:
            # 响应时间应该小于 2 秒
            assert result["response_time"] < 2000, (
                f"服务 {service_name} 响应时间过长：{result['response_time']:.2f}ms"
            )
            print(f"✓ {service_name} 响应时间：{result['response_time']:.2f}ms")


# ============ 页面渲染测试 ============
class TestPageRendering:
    """测试页面渲染正确性"""
    
    def test_trading_monitor_page(self, session):
        """测试模拟交易监控页面渲染"""
        url = f"{BASE_URLS['trading_monitor']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            
            # 验证页面必需元素
            required_elements = [
                "模拟交易监控",
                "持仓",
                "交易记录",
                "资金曲线",
                "<!DOCTYPE html>",
                "<html",
                "<head>",
                "<body>",
            ]
            
            validation = validate_html_content(response.text, required_elements)
            missing = [elem for elem, found in validation.items() if not found]
            
            assert not missing, f"页面缺少必需元素：{missing}"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("模拟交易监控服务未运行")
    
    def test_backtest_dashboard_page(self, session):
        """测试回测分析面板页面渲染"""
        url = f"{BASE_URLS['backtest_dashboard']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            
            # 验证页面必需元素
            required_elements = [
                "回测结果分析面板",
                "批次",
                "策略",
                "收益率",
                "<!DOCTYPE html>",
                "<html",
                "Chart.js",  # 应该包含图表库
            ]
            
            validation = validate_html_content(response.text, required_elements)
            missing = [elem for elem, found in validation.items() if not found]
            
            assert not missing, f"页面缺少必需元素：{missing}"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_system_status_page(self, session):
        """测试系统状态监控页面渲染"""
        url = f"{BASE_URLS['system_status']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            
            # 验证页面必需元素
            required_elements = [
                "系统状态监控",
                "工具状态",
                "飞书",
                "响应时间",
                "<!DOCTYPE html>",
                "<html",
                "Chart.js",  # 应该包含图表库
            ]
            
            validation = validate_html_content(response.text, required_elements)
            missing = [elem for elem, found in validation.items() if not found]
            
            assert not missing, f"页面缺少必需元素：{missing}"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 数据展示准确性测试 ============
class TestDataDisplay:
    """测试数据展示准确性"""
    
    def test_trading_monitor_stats(self, session):
        """测试交易监控页面统计数据展示"""
        url = f"{BASE_URLS['trading_monitor']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            html = response.text
            
            # 验证统计数据存在
            assert "总资金" in html or "total_value" in html.lower(), "缺少总资金数据"
            assert "收益率" in html or "return" in html.lower(), "缺少收益率数据"
            assert "仓位" in html or "position" in html.lower(), "缺少仓位数据"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("模拟交易监控服务未运行")
    
    def test_backtest_dashboard_data(self, session):
        """测试回测面板数据展示"""
        url = f"{BASE_URLS['backtest_dashboard']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            html = response.text
            
            # 验证回测数据存在
            assert "批次" in html or "batch" in html.lower(), "缺少批次数据"
            assert "夏普比率" in html or "sharpe" in html.lower() or "策略" in html, "缺少策略性能数据"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_system_status_data(self, session):
        """测试系统状态面板数据展示"""
        url = f"{BASE_URLS['system_status']}/"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            html = response.text
            
            # 验证状态数据存在
            assert "工具状态" in html or "tools" in html.lower(), "缺少工具状态"
            assert "正常" in html or "normal" in html.lower() or "状态" in html, "缺少状态指示"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 交互功能测试 ============
class TestInteractiveFeatures:
    """测试页面交互功能"""
    
    def test_backtest_api_batches_endpoint(self, session):
        """测试回测面板的批次 API"""
        url = f"{BASE_URLS['backtest_dashboard']}/api/batches"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            assert "application/json" in response.headers.get("Content-Type", "")
            
            # 验证返回 JSON 格式
            data = response.json()
            assert isinstance(data, list), "API 应该返回批次列表"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_system_status_api_endpoint(self, session):
        """测试系统状态 API"""
        url = f"{BASE_URLS['system_status']}/api/status"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            assert "application/json" in response.headers.get("Content-Type", "")
            
            # 验证返回 JSON 结构
            data = response.json()
            assert "tools" in data, "缺少 tools 字段"
            assert "stats" in data, "缺少 stats 字段"
            assert "feishu" in data, "缺少 feishu 字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")
    
    def test_system_status_tool_history_api(self, session):
        """测试工具历史数据 API"""
        url = f"{BASE_URLS['system_status']}/api/tool-history/Alpha Vantage"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            assert response.status_code == 200
            
            # 验证返回数据结构
            data = response.json()
            assert "tool_name" in data, "缺少 tool_name 字段"
            assert "history" in data, "缺少 history 字段"
            assert isinstance(data["history"], list), "history 应该是列表"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 错误处理测试 ============
class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_batch_id(self, session):
        """测试无效批次 ID 的处理"""
        url = f"{BASE_URLS['backtest_dashboard']}/api/batch/invalid_id_12345"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            # 应该返回空列表或错误信息，但不应该 500
            assert response.status_code != 500, "服务器内部错误"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("回测分析面板服务未运行")
    
    def test_nonexistent_endpoint(self, session):
        """测试不存在端点的处理"""
        url = f"{BASE_URLS['system_status']}/api/nonexistent"
        
        try:
            response = session.get(url, timeout=TIMEOUT)
            # 应该返回 404 而不是 500
            assert response.status_code in [404, 405], f"期望 404 或 405, 实际：{response.status_code}"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 并发测试 ============
class TestConcurrency:
    """测试并发访问"""
    
    def test_concurrent_requests(self, session):
        """测试并发请求处理"""
        import concurrent.futures
        
        url = f"{BASE_URLS['system_status']}/api/status"
        
        def make_request():
            try:
                response = session.get(url, timeout=TIMEOUT)
                return response.status_code == 200
            except:
                return False
        
        try:
            # 并发 10 个请求
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]
            
            success_count = sum(results)
            assert success_count >= 8, f"并发请求成功率过低：{success_count}/10"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("系统状态监控服务未运行")


# ============ 主入口 ============
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
