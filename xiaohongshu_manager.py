#!/usr/bin/env python3
"""
小红书内容管理面板
展示所有小红书帖子，支持预览、编辑、发布状态管理
"""
from flask import Flask, render_template_string, jsonify, request
import os
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# 配置
CONTENT_DIR = Path('/Users/gexin/.openclaw/workspace/content')
POSTS_DIR = CONTENT_DIR / 'xiaohongshu_posts'
DAILY_LOG_DIR = CONTENT_DIR / 'daily_logs'

# 确保目录存在
CONTENT_DIR.mkdir(exist_ok=True)
POSTS_DIR.mkdir(exist_ok=True)
DAILY_LOG_DIR.mkdir(exist_ok=True)

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小红书内容管理 - Q 脑</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #ff6b6b 0%, #ff8787 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            background: white;
            padding: 30px 40px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            margin-bottom: 30px;
        }
        .header h1 {
            color: #ff6b6b;
            font-size: 32px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .header p { color: #666; font-size: 16px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
            color: #ff6b6b;
            margin-bottom: 5px;
        }
        .stat-label { color: #888; font-size: 14px; }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .posts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }
        .post-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .post-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .post-header {
            background: linear-gradient(135deg, #ff6b6b, #ff8787);
            color: white;
            padding: 20px;
        }
        .post-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .post-meta {
            font-size: 12px;
            opacity: 0.9;
        }
        .post-body {
            padding: 20px;
        }
        .post-preview {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
            max-height: 100px;
            overflow: hidden;
            margin-bottom: 15px;
        }
        .tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 15px;
        }
        .tag {
            background: #fff0f0;
            color: #ff6b6b;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
        }
        .post-actions {
            display: flex;
            gap: 10px;
            padding: 0 20px 20px;
        }
        .btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #ff6b6b, #ff8787);
            color: white;
        }
        .btn-primary:hover {
            transform: scale(1.05);
        }
        .btn-secondary {
            background: #f0f0f0;
            color: #666;
        }
        .btn-secondary:hover {
            background: #e0e0e0;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-draft { background: #fff3cd; color: #856404; }
        .status-published { background: #d4edda; color: #155724; }
        .status-scheduled { background: #cce5ff; color: #004085; }
        .create-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #ff6b6b, #ff8787);
            color: white;
            border: none;
            font-size: 30px;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(255,107,107,0.4);
            transition: all 0.3s;
        }
        .create-btn:hover {
            transform: scale(1.1) rotate(90deg);
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: white;
            padding: 40px;
            border-radius: 20px;
            max-width: 800px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        .modal-header h2 { color: #ff6b6b; }
        .close-btn {
            background: none;
            border: none;
            font-size: 30px;
            cursor: pointer;
            color: #999;
        }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 600;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #ff6b6b;
        }
        textarea.form-control {
            min-height: 200px;
            resize: vertical;
        }
        .daily-log-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .daily-log-section h2 {
            color: #ff6b6b;
            margin-bottom: 20px;
        }
        .log-timeline {
            border-left: 3px solid #ff6b6b;
            padding-left: 20px;
        }
        .log-item {
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #f0f0f0;
        }
        .log-item:last-child {
            border-bottom: none;
        }
        .log-date {
            color: #ff6b6b;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .log-content { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                <span>📕</span>
                小红书内容管理
            </h1>
            <p>Q 脑量化交易系统 - 内容创作与发布管理平台</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalPosts">0</div>
                <div class="stat-label">总帖子数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="publishedPosts">0</div>
                <div class="stat-label">已发布</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="draftPosts">0</div>
                <div class="stat-label">草稿</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="logsCount">0</div>
                <div class="stat-label">每日日志</div>
            </div>
        </div>

        <div class="daily-log-section">
            <h2>📝 每日系统变化日志</h2>
            <div class="log-timeline" id="logTimeline">
                <!-- 日志内容 -->
            </div>
        </div>

        <h2 style="color: #ff6b6b; margin-bottom: 20px;">📕 帖子列表</h2>
        <div class="posts-grid" id="postsGrid">
            <!-- 帖子卡片 -->
        </div>
    </div>

    <button class="create-btn" onclick="showCreateModal()">+</button>

    <!-- 预览模态框 -->
    <div class="modal" id="previewModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>📕 帖子预览</h2>
                <button class="close-btn" onclick="closeModal('previewModal')">&times;</button>
            </div>
            <div id="previewContent"></div>
        </div>
    </div>

    <!-- 创建模态框 -->
    <div class="modal" id="createModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>✨ 创建新帖子</h2>
                <button class="close-btn" onclick="closeModal('createModal')">&times;</button>
            </div>
            <form id="createForm" onsubmit="createPost(event)">
                <div class="form-group">
                    <label>标题</label>
                    <input type="text" class="form-control" id="postTitle" required 
                           placeholder="输入吸引人的标题...">
                </div>
                <div class="form-group">
                    <label>标签 (用逗号分隔)</label>
                    <input type="text" class="form-control" id="postTags" 
                           placeholder="AI 量化，技术分享，个人成长">
                </div>
                <div class="form-group">
                    <label>内容</label>
                    <textarea class="form-control" id="postContent" required 
                              placeholder="输入帖子内容..."></textarea>
                </div>
                <div class="form-group">
                    <label>状态</label>
                    <select class="form-control" id="postStatus">
                        <option value="draft">草稿</option>
                        <option value="published">已发布</option>
                        <option value="scheduled">计划发布</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">
                    创建帖子
                </button>
            </form>
        </div>
    </div>

    <script>
        // 加载帖子数据
        async function loadPosts() {
            const response = await fetch('/api/posts');
            const posts = await response.json();
            
            document.getElementById('totalPosts').textContent = posts.length;
            document.getElementById('publishedPosts').textContent = 
                posts.filter(p => p.status === 'published').length;
            document.getElementById('draftPosts').textContent = 
                posts.filter(p => p.status === 'draft').length;
            
            const grid = document.getElementById('postsGrid');
            grid.innerHTML = posts.map(post => `
                <div class="post-card">
                    <div class="post-header">
                        <div class="post-title">${post.title}</div>
                        <div class="post-meta">
                            ${post.created_at} · 
                            <span class="status-badge status-${post.status}">
                                ${getStatusText(post.status)}
                            </span>
                        </div>
                    </div>
                    <div class="post-body">
                        <div class="post-preview">${post.preview}</div>
                        <div class="tags">
                            ${post.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                        <div class="post-actions">
                            <button class="btn btn-primary" 
                                    onclick="previewPost('${post.file}')">
                                预览
                            </button>
                            <button class="btn btn-secondary" 
                                    onclick="editPost('${post.file}')">
                                编辑
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        // 加载每日日志
        async function loadLogs() {
            const response = await fetch('/api/logs');
            const logs = await response.json();
            
            document.getElementById('logsCount').textContent = logs.length;
            
            const timeline = document.getElementById('logTimeline');
            timeline.innerHTML = logs.map(log => `
                <div class="log-item">
                    <div class="log-date">📅 ${log.date}</div>
                    <div class="log-content">${log.content}</div>
                </div>
            `).join('');
        }

        function getStatusText(status) {
            const map = {
                'draft': '草稿',
                'published': '已发布',
                'scheduled': '计划发布'
            };
            return map[status] || status;
        }

        function showCreateModal() {
            document.getElementById('createModal').classList.add('active');
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('active');
        }

        async function previewPost(filename) {
            const response = await fetch(`/api/posts/${filename}`);
            const post = await response.json();
            
            document.getElementById('previewContent').innerHTML = `
                <div style="line-height: 1.8;">
                    <h3 style="color: #ff6b6b; margin-bottom: 15px;">${post.title}</h3>
                    <div style="white-space: pre-wrap;">${post.content}</div>
                </div>
            `;
            document.getElementById('previewModal').classList.add('active');
        }

        function editPost(filename) {
            // 编辑功能
            alert('编辑功能开发中...');
        }

        async function createPost(event) {
            event.preventDefault();
            
            const title = document.getElementById('postTitle').value;
            const tags = document.getElementById('postTags').value.split(',').map(t => t.trim());
            const content = document.getElementById('postContent').value;
            const status = document.getElementById('postStatus').value;
            
            const response = await fetch('/api/posts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title, tags, content, status})
            });
            
            if (response.ok) {
                alert('帖子创建成功！');
                closeModal('createModal');
                loadPosts();
            } else {
                alert('创建失败，请重试');
            }
        }

        // 页面加载时初始化
        loadPosts();
        loadLogs();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """获取所有帖子"""
    posts = []
    
    if POSTS_DIR.exists():
        for file in POSTS_DIR.glob('*.md'):
            try:
                content = file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                # 提取标题 (第一个 # 开头的行)
                title = "未命名"
                for line in lines:
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                
                # 提取标签 (包含 # 的行)
                tags = []
                for line in lines:
                    if line.startswith('#') and not line.startswith('# '):
                        extracted = [t.strip() for t in line.split() if t.startswith('#')]
                        tags.extend(extracted)
                
                # 预览 (前 100 字)
                preview_lines = [l for l in lines if not l.startswith('#')]
                preview = ' '.join(preview_lines)[:200] + '...'
                
                # 状态
                status = 'draft'
                if '已发布' in content or 'published' in content.lower():
                    status = 'published'
                
                posts.append({
                    'file': file.name,
                    'title': title,
                    'tags': tags[:5],  # 限制标签数量
                    'preview': preview,
                    'status': status,
                    'created_at': datetime.fromtimestamp(
                        file.stat().st_mtime
                    ).strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                print(f"Error reading {file}: {e}")
    
    # 也读取根目录的帖子
    if CONTENT_DIR.exists():
        for file in CONTENT_DIR.glob('xiaohongshu_post_*.md'):
            try:
                content = file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                title = "未命名"
                for line in lines:
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                
                tags = []
                for line in lines:
                    if line.startswith('#') and not line.startswith('# '):
                        extracted = [t.strip() for t in line.split() if t.startswith('#')]
                        tags.extend(extracted)
                
                preview_lines = [l for l in lines if not l.startswith('#')]
                preview = ' '.join(preview_lines)[:200] + '...'
                
                status = 'published'  # 默认已发布
                
                posts.append({
                    'file': file.name,
                    'title': title,
                    'tags': tags[:5],
                    'preview': preview,
                    'status': status,
                    'created_at': datetime.fromtimestamp(
                        file.stat().st_mtime
                    ).strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                print(f"Error reading {file}: {e}")
    
    return jsonify(sorted(posts, key=lambda x: x['created_at'], reverse=True))

@app.route('/api/posts/<filename>', methods=['GET'])
def get_post(filename):
    """获取单个帖子详情"""
    # 先查 posts 目录，再查根目录
    file_path = POSTS_DIR / filename
    if not file_path.exists():
        file_path = CONTENT_DIR / filename
    
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        return jsonify({
            'filename': filename,
            'content': content,
            'path': str(file_path)
        })
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/posts', methods=['POST'])
def create_post():
    """创建新帖子"""
    data = request.json
    title = data.get('title', '新帖子')
    tags = data.get('tags', [])
    content = data.get('content', '')
    status = data.get('status', 'draft')
    
    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'post_{timestamp}.md'
    file_path = POSTS_DIR / filename
    
    # 构建 Markdown 内容
    markdown_content = f"# {title}\n\n"
    markdown_content += f"**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    markdown_content += f"**状态**: {status}\n\n"
    markdown_content += f"**标签**: {', '.join(tags)}\n\n"
    markdown_content += "---\n\n"
    markdown_content += content
    markdown_content += "\n\n---\n\n"
    markdown_content += "#标签\n"
    for tag in tags:
        if not tag.startswith('#'):
            tag = '#' + tag
        markdown_content += f"{tag} "
    
    # 写入文件
    file_path.write_text(markdown_content, encoding='utf-8')
    
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取每日系统变化日志"""
    logs = []
    
    if DAILY_LOG_DIR.exists():
        for file in sorted(DAILY_LOG_DIR.glob('*.md'), reverse=True):
            try:
                content = file.read_text(encoding='utf-8')
                logs.append({
                    'date': file.stem,
                    'content': content[:500] + '...' if len(content) > 500 else content,
                    'full_path': str(file)
                })
            except Exception as e:
                print(f"Error reading {file}: {e}")
    
    return jsonify(logs[:10])  # 返回最近 10 条

@app.route('/api/generate-daily', methods=['POST'])
def generate_daily():
    """生成每日小红书内容"""
    from datetime import date
    
    today = date.today().strftime('%Y-%m-%d')
    log_file = DAILY_LOG_DIR / f'{today}.md'
    
    # 检查是否已生成
    if log_file.exists():
        return jsonify({'error': 'Today\'s log already exists'}), 400
    
    # 生成每日日志内容
    content = f"# 每日系统变化 - {today}\n\n"
    content += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    content += "## 🎯 今日重点\n\n"
    content += "- 系统运行正常\n"
    content += "- 新增功能：自动内容生成\n"
    content += "- 舆情监控：7×24 小时运行\n\n"
    content += "## 📊 数据亮点\n\n"
    content += "- 监控股票数：8 只\n"
    content += "- 舆情更新频率：5 分钟/次\n"
    content += "- 系统可用性：99.9%\n\n"
    content += "## 💡 内容创意\n\n"
    content += "### 帖子 1: 系统进展\n"
    content += "标题：《Q 脑量化系统今日新突破！》\n"
    content += "要点：\n"
    content += "- 小红书管理面板上线\n"
    content += "- 每日自动创作功能\n"
    content += "- 舆情分析系统升级\n\n"
    content += "### 帖子 2: 交易心得\n"
    content += "标题：《量化交易的一天是怎样的体验》\n"
    content += "要点：\n"
    content += "- 早盘准备工作\n"
    content += "- 系统自动监控\n"
    content += "- 复盘与优化\n\n"
    
    log_file.write_text(content, encoding='utf-8')
    
    return jsonify({
        'success': True,
        'log_file': str(log_file),
        'message': 'Daily log generated successfully'
    })

if __name__ == '__main__':
    print("=" * 60)
    print("📕 小红书内容管理面板")
    print("=" * 60)
    print("访问地址：http://localhost:5010")
    print("帖子目录：", POSTS_DIR)
    print("日志目录：", DAILY_LOG_DIR)
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5010, debug=False)
