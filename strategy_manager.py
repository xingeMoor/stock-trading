#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略管理服务 - Q脑系统
运行在5002端口
提供策略列表、详情、操作等功能
"""

import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__, template_folder='templates')

# 数据库连接
def get_db_connection():
    conn = sqlite3.connect('backtest_db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

# 初始化数据库（如果不存在）
def init_db():
    conn = get_db_connection()
    # 创建策略表
    conn.execute('''CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT DEFAULT 'inactive',
        parameters TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 创建回测结果表
    conn.execute('''CREATE TABLE IF NOT EXISTS backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        initial_capital REAL,
        final_capital REAL,
        total_return REAL,
        sharpe_ratio REAL,
        max_drawdown REAL,
        win_rate REAL,
        total_trades INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
    )''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """策略列表页面"""
    conn = get_db_connection()
    search_query = request.args.get('search', '')
    strategy_type = request.args.get('type', '')
    
    query = "SELECT * FROM strategies WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND name LIKE ?"
        params.append(f'%{search_query}%')
        
    if strategy_type:
        query += " AND type = ?"
        params.append(strategy_type)
    
    query += " ORDER BY created_at DESC"
    
    strategies = conn.execute(query, params).fetchall()
    conn.close()
    
    # 获取所有策略类型用于筛选
    strategy_types = ['均值回归', '动量策略', '网格交易', '趋势跟踪', '套利策略']
    
    return render_template('strategies.html', 
                          strategies=strategies, 
                          search_query=search_query,
                          selected_type=strategy_type,
                          strategy_types=strategy_types)

@app.route('/strategy/<int:strategy_id>')
def strategy_detail(strategy_id):
    """策略详情页面"""
    conn = get_db_connection()
    
    # 获取策略信息
    strategy = conn.execute('SELECT * FROM strategies WHERE id = ?', (strategy_id,)).fetchone()
    
    # 获取最新的回测结果
    backtest_result = conn.execute(
        'SELECT * FROM backtest_results WHERE strategy_id = ? ORDER BY created_at DESC LIMIT 1', 
        (strategy_id,)
    ).fetchone()
    
    # 获取所有回测结果用于图表
    backtest_results = conn.execute(
        'SELECT * FROM backtest_results WHERE strategy_id = ? ORDER BY created_at ASC', 
        (strategy_id,)
    ).fetchall()
    
    conn.close()
    
    if not strategy:
        return "策略不存在", 404
    
    return render_template('strategy_detail.html', 
                          strategy=dict(strategy), 
                          backtest_result=dict(backtest_result) if backtest_result else None,
                          backtest_results=[dict(r) for r in backtest_results])

@app.route('/api/strategies', methods=['GET'])
def api_strategies():
    """获取策略列表API"""
    conn = get_db_connection()
    strategies = conn.execute('SELECT * FROM strategies ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return jsonify([dict(s) for s in strategies])

@app.route('/api/strategies', methods=['POST'])
def api_create_strategy():
    """创建新策略API"""
    data = request.json
    name = data.get('name')
    strategy_type = data.get('type')
    parameters = json.dumps(data.get('parameters', {}))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO strategies (name, type, parameters) VALUES (?, ?, ?)',
        (name, strategy_type, parameters)
    )
    strategy_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': strategy_id, 'message': '策略创建成功'})

@app.route('/api/strategy/<int:strategy_id>', methods=['PUT'])
def api_update_strategy(strategy_id):
    """更新策略API"""
    data = request.json
    name = data.get('name')
    strategy_type = data.get('type')
    status = data.get('status')
    parameters = json.dumps(data.get('parameters', {}))
    
    conn = get_db_connection()
    conn.execute(
        '''UPDATE strategies SET name=?, type=?, status=?, parameters=?, updated_at=CURRENT_TIMESTAMP 
           WHERE id=?''',
        (name, strategy_type, status, parameters, strategy_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': '策略更新成功'})

@app.route('/api/strategy/<int:strategy_id>', methods=['DELETE'])
def api_delete_strategy(strategy_id):
    """删除策略API"""
    conn = get_db_connection()
    conn.execute('DELETE FROM strategies WHERE id = ?', (strategy_id,))
    conn.execute('DELETE FROM backtest_results WHERE strategy_id = ?', (strategy_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': '策略删除成功'})

@app.route('/api/strategy/<int:strategy_id>/toggle', methods=['POST'])
def api_toggle_strategy(strategy_id):
    """启停策略API"""
    conn = get_db_connection()
    strategy = conn.execute('SELECT status FROM strategies WHERE id = ?', (strategy_id,)).fetchone()
    
    if strategy:
        new_status = 'active' if strategy['status'] != 'active' else 'inactive'
        conn.execute('UPDATE strategies SET status=? WHERE id=?', (new_status, strategy_id))
        conn.commit()
        conn.close()
        return jsonify({'status': new_status})
    else:
        conn.close()
        return jsonify({'error': '策略不存在'}), 404

@app.route('/api/backtest_results/<int:strategy_id>')
def api_backtest_results(strategy_id):
    """获取策略的回测结果API"""
    conn = get_db_connection()
    results = conn.execute(
        'SELECT * FROM backtest_results WHERE strategy_id = ? ORDER BY created_at DESC', 
        (strategy_id,)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(r) for r in results])

@app.route('/api/create_backtest_result', methods=['POST'])
def api_create_backtest_result():
    """创建回测结果API"""
    data = request.json
    strategy_id = data.get('strategy_id')
    result_data = data.get('result', {})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO backtest_results (
            strategy_id, start_date, end_date, initial_capital, final_capital, 
            total_return, sharpe_ratio, max_drawdown, win_rate, total_trades
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        strategy_id,
        result_data.get('start_date'),
        result_data.get('end_date'),
        result_data.get('initial_capital'),
        result_data.get('final_capital'),
        result_data.get('total_return'),
        result_data.get('sharpe_ratio'),
        result_data.get('max_drawdown'),
        result_data.get('win_rate'),
        result_data.get('total_trades')
    ))
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': result_id, 'message': '回测结果创建成功'})

if __name__ == '__main__':
    init_db()  # 初始化数据库
    print("策略管理服务启动中...")
    print("访问地址: http://localhost:5002")
    app.run(host='0.0.0.0', port=5002, debug=True)