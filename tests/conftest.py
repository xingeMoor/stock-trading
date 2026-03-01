"""
pytest 配置文件
提供全局的 fixtures 和配置
"""
import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    """pytest 配置钩子"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
    config.addinivalue_line(
        "markers", "web: marks tests as web page tests"
    )


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--service-url",
        action="store",
        default="http://localhost",
        help="Base URL for services"
    )
    
    parser.addoption(
        "--timeout",
        action="store",
        default=10,
        type=int,
        help="Request timeout in seconds"
    )


@pytest.fixture(scope="session")
def pytestconfig():
    """提供 pytest 配置"""
    return pytest.config


@pytest.fixture
def service_url(request):
    """提供服务 URL"""
    return request.config.getoption("--service-url")


@pytest.fixture
def timeout(request):
    """提供超时配置"""
    return request.config.getoption("--timeout")
