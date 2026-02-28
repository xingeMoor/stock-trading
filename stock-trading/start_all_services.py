#!/usr/bin/env python3
"""
统一启动脚本 - 启动所有网页服务
"""
import subprocess
import sys
import os

services = [
    ("模拟交易监控", "web_dashboard.py", 5001),
    ("回测结果监控", "backtest_dashboard.py", 5002),
    ("实盘持仓监控", "real_positions_dashboard.py", 5003),
    ("定时任务配置", "schedule_dashboard.py", 5004),
]

print("\n" + "="*60)
print("🚀 启动量化交易监控系统")
print("="*60)

processes = []

for i, (name, script, port) in enumerate(services):
    print(f"\n📊 启动 {name} (端口 {port})...")
    
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), script)]
    
    process = subprocess.Popen(cmd)
    processes.append((name, process))
    
    print(f"✓ {name} 已启动")

print("\n" + "="*60)
print("✅ 所有服务已启动")
print("="*60)
print("\n访问地址:")
for name, _, port in services:
    print(f"  - {name}: http://localhost:{port}")

print("\n按 Ctrl+C 停止所有服务\n")

try:
    for _, process in processes:
        process.wait()
except KeyboardInterrupt:
    print("\n\n⏹️  停止所有服务...")
    for name, process in processes:
        process.terminate()
        print(f"✓ {name} 已停止")
    print("\n所有服务已停止")
