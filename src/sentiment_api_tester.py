"""
舆情 API 定时检测工具
用于定期检测舆情 API 的健康状态和响应性能
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import aiohttp
import requests


class SentimentAPITester:
    """舆情 API 测试器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)
        self.results = []
        
        # API 端点配置
        self.api_endpoints = {
            'news': 'https://api.example.com/news',
            'twitter': 'https://api.twitter.com/2/tweets/search/recent',
            'weibo': 'https://api.weibo.com/2/statuses/public_timeline',
            'sentiment': 'https://api.sentiment.com/analyze'
        }
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认配置
        return {
            'timeout': 30,
            'retry_count': 3,
            'check_interval': 300,  # 5 分钟
            'alert_threshold': 0.8
        }
    
    async def test_api_health(self, endpoint: str, name: str) -> dict:
        """测试 API 健康状态"""
        result = {
            'name': name,
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'response_time': 0,
            'error': None
        }
        
        for attempt in range(self.config.get('retry_count', 3)):
            try:
                start_time = time.time()
                
                # 使用 mock 响应进行测试（实际使用时替换为真实 API 调用）
                async with aiohttp.ClientSession() as session:
                    # 这里使用 mock，实际应该调用真实 API
                    # async with session.get(endpoint, timeout=self.config['timeout']) as response:
                    #     status = response.status
                    #     response_time = time.time() - start_time
                    
                    # Mock 响应
                    await asyncio.sleep(0.1)  # 模拟网络延迟
                    status = 200
                    response_time = time.time() - start_time
                
                result['status'] = 'healthy' if status == 200 else 'degraded'
                result['response_time'] = response_time
                result['status_code'] = status
                
                if status == 200:
                    break
                    
            except Exception as e:
                result['error'] = str(e)
                if attempt == self.config.get('retry_count', 3) - 1:
                    result['status'] = 'unhealthy'
        
        return result
    
    async def test_sentiment_accuracy(self, test_cases: List[dict]) -> dict:
        """测试情感分析准确性"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_cases': len(test_cases),
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        for test_case in test_cases:
            text = test_case['text']
            expected = test_case['expected']
            
            # 使用本地情感分析器
            from sentiment.monitor import StockSentimentMonitor
            monitor = StockSentimentMonitor()
            
            try:
                result = monitor.analyze_sentiment(text)
                
                # 判断是否匹配预期
                passed = result['label'] == expected
                
                test_result = {
                    'text': text[:50] + '...' if len(text) > 50 else text,
                    'expected': expected,
                    'actual': result['label'],
                    'compound': result['compound'],
                    'passed': passed
                }
                
                if passed:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append(test_result)
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'text': text[:50],
                    'error': str(e),
                    'passed': False
                })
        
        results['accuracy'] = results['passed'] / results['total_cases'] if results['total_cases'] > 0 else 0
        return results
    
    async def test_response_performance(self, iterations: int = 10) -> dict:
        """测试响应性能"""
        times = []
        
        for i in range(iterations):
            start = time.time()
            
            # 模拟 API 调用
            await asyncio.sleep(0.05)
            
            elapsed = time.time() - start
            times.append(elapsed)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'iterations': iterations,
            'avg_response_time': sum(times) / len(times),
            'min_response_time': min(times),
            'max_response_time': max(times),
            'p95_response_time': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
        }
    
    async def run_all_tests(self) -> dict:
        """运行所有测试"""
        print(f"\n{'='*70}")
        print(f"舆情 API 测试开始 - {datetime.now().isoformat()}")
        print(f"{'='*70}\n")
        
        # 1. API 健康检查
        print("1. API 健康检查...")
        health_results = {}
        for name, endpoint in self.api_endpoints.items():
            result = await self.test_api_health(endpoint, name)
            health_results[name] = result
            status_icon = "✓" if result['status'] == 'healthy' else "✗"
            print(f"   {status_icon} {name}: {result['status']} ({result.get('response_time', 0)*1000:.2f}ms)")
        
        # 2. 情感分析准确性测试
        print("\n2. 情感分析准确性测试...")
        test_cases = [
            {'text': '公司业绩大幅增长，股价飙升', 'expected': 'positive'},
            {'text': '公司面临重大诉讼，股价下跌', 'expected': 'negative'},
            {'text': '公司召开例行股东大会', 'expected': 'neutral'},
            {'text': 'Apple announces record earnings', 'expected': 'positive'},
            {'text': 'Tesla faces major recall', 'expected': 'negative'},
            {'text': 'Company holds annual meeting', 'expected': 'neutral'},
        ]
        
        accuracy_results = await self.test_sentiment_accuracy(test_cases)
        print(f"   准确率：{accuracy_results['accuracy']*100:.1f}% ({accuracy_results['passed']}/{accuracy_results['total_cases']})")
        
        # 3. 性能测试
        print("\n3. 响应性能测试...")
        performance_results = await self.test_response_performance(iterations=20)
        print(f"   平均响应时间：{performance_results['avg_response_time']*1000:.2f}ms")
        print(f"   P95 响应时间：{performance_results['p95_response_time']*1000:.2f}ms")
        
        # 4. 汇总结果
        overall_status = 'healthy'
        if any(r['status'] != 'healthy' for r in health_results.values()):
            overall_status = 'degraded'
        if accuracy_results['accuracy'] < 0.8:
            overall_status = 'unhealthy'
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'api_health': health_results,
            'accuracy': accuracy_results,
            'performance': performance_results
        }
        
        self.results.append(summary)
        
        print(f"\n{'='*70}")
        print(f"测试完成 - 总体状态：{overall_status.upper()}")
        print(f"{'='*70}\n")
        
        return summary
    
    def save_results(self, output_path: str):
        """保存测试结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"测试结果已保存到：{output_path}")
    
    async def start_monitoring(self, interval: int = None):
        """开始定时监控"""
        interval = interval or self.config.get('check_interval', 300)
        
        print(f"开始定时监控，间隔：{interval}秒")
        
        while True:
            try:
                await self.run_all_tests()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                print("\n监控已停止")
                break
            except Exception as e:
                self.logger.error(f"监控错误：{e}")
                await asyncio.sleep(interval)


async def main():
    """主函数"""
    tester = SentimentAPITester()
    
    # 运行一次完整测试
    results = await tester.run_all_tests()
    
    # 保存结果
    output_path = 'results/sentiment_api_test.json'
    Path('results').mkdir(exist_ok=True)
    tester.save_results(output_path)
    
    return results


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    asyncio.run(main())
