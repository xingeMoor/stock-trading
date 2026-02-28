# Git 工作流指南

## 仓库信息

- **URL**: https://github.com/xingeMoor/stock-trading
- **分支**: main
- **作者**: xingeMoor <shiyi_gx@163.com>

## 日常使用

### 提交修改

```bash
cd /Users/gexin/.openclaw/workspace/stock-trading

# 1. 查看变更
git status

# 2. 添加文件
git add <文件名>          # 添加单个文件
git add .                # 添加所有变更

# 3. 提交
git commit -m "描述你的修改"

# 4. 推送到 GitHub
git push
```

### 查看历史

```bash
git log --oneline        # 简洁日志
git log                  # 详细日志
git diff                 # 查看未提交的变更
```

### 拉取更新

```bash
git pull                 # 拉取并合并远程变更
```

## Commit 规范

格式：`<类型>: <描述>`

**类型**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式 (不影响功能)
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具/配置

**示例**:
```bash
git commit -m "feat: 添加动态 RSI 阈值"
git commit -m "fix: 修复回测未来函数问题"
git commit -m "docs: 更新 README 使用说明"
git commit -m "refactor: 优化策略框架结构"
```

## 安全提醒

### ⚠️ 不要提交敏感信息

以下文件已在 `.gitignore` 中，**不会被提交**:
- `.env` - API Key 等环境变量
- `logs/*.log` - 日志文件
- `data/*.json` - 回测数据

### 如果不小心提交了敏感信息

1. **立即撤销相关的 API Key/Token**
2. 使用 BFG 或 git filter-branch 清理历史:
```bash
# 安装 BFG
brew install bfg

# 清理 .env 文件
bfg --delete-files .env

# 强制推送
git push --force
```

## 当前状态

- ✅ 初始版本已推送 (66 个文件，18874 行代码)
- ✅ API Key 已改为环境变量管理
- ✅ .env 文件已加入 gitignore

## 常用命令速查

```bash
# 查看状态
git status

# 添加所有变更
git add .

# 提交
git commit -m "描述"

# 推送
git push

# 拉取
git pull

# 查看日志
git log --oneline -10

# 撤销未提交的修改
git checkout -- <文件名>

# 撤销已暂存的修改
git reset HEAD <文件名>
```

---

**Last Updated**: 2026-02-28
