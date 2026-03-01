#!/bin/bash
# QBrain 部署脚本
# 用途: 本地手动部署或作为GitHub Actions的备用方案

set -e

# 配置变量
SERVER_IP="47.253.133.165"
SERVER_USER="root"
PROJECT_DIR="/opt/qbrain"
REPO_URL=""  # 填写你的GitHub仓库地址
BRANCH="main"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
QBrain 部署脚本

用法: ./deploy.sh [选项]

选项:
    -h, --help          显示帮助信息
    -i, --init          初始化服务器（首次部署）
    -d, --deploy        执行部署（默认）
    -s, --status        检查服务状态
    -l, --logs          查看实时日志
    -b, --backup        创建备份
    -r, --rollback      回滚到上一个版本
    --password PASS     使用密码认证（不推荐）
    --key FILE          使用SSH密钥文件

示例:
    ./deploy.sh                         # 默认部署
    ./deploy.sh -i                      # 初始化服务器
    ./deploy.sh --key ~/.ssh/id_rsa     # 使用指定密钥
    ./deploy.sh -s                      # 检查状态
EOF
}

# 检查依赖
check_dependencies() {
    local deps=("ssh" "scp")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "缺少依赖: $dep"
            exit 1
        fi
    done
}

# 初始化服务器
init_server() {
    log_info "初始化服务器..."
    
    if [ -z "$REPO_URL" ]; then
        log_error "请先在脚本中设置 REPO_URL 变量"
        exit 1
    fi
    
    ssh "$SERVER_USER@$SERVER_IP" "
        set -e
        echo '📁 创建项目目录...'
        sudo mkdir -p $PROJECT_DIR
        cd $PROJECT_DIR
        
        if [ ! -d .git ]; then
            echo '📥 克隆代码仓库...'
            git clone $REPO_URL .
        fi
        
        echo '🔧 安装Python依赖...'
        pip3 install -r requirements.txt || pip install -r requirements.txt
        
        echo '✅ 初始化完成!'
        echo ''
        echo '下一步:'
        echo '  1. 配置环境变量 (.env文件)'
        echo '  2. 创建systemd服务'
        echo '  3. 启动服务'
    "
}

# 执行部署
do_deploy() {
    log_info "开始部署到 $SERVER_IP..."
    
    ssh "$SERVER_USER@$SERVER_IP" "
        set -e
        echo '=========================================='
        echo '🎯 QBrain 部署脚本'
        echo '⏰ 时间: \$(date "+%Y-%m-%d %H:%M:%S")'
        echo '=========================================='
        
        cd $PROJECT_DIR || {
            echo '❌ 项目目录不存在'
            exit 1
        }
        
        echo '📥 拉取最新代码...'
        git fetch origin
        git reset --hard origin/$BRANCH
        
        echo '🔧 安装依赖...'
        if [ -f requirements.txt ]; then
            pip3 install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt --quiet
        fi
        
        echo '🔄 重启服务...'
        # 查找并重启qbrain相关服务
        services=\$(systemctl list-units --type=service --state=running | grep qbrain | awk '{print \$1}')
        if [ -n \"\$services\" ]; then
            for service in \$services; do
                echo "   重启: \$service"
                sudo systemctl restart "\$service" || echo "   ⚠️ 跳过: \$service"
            done
        else
            echo '   ⚠️ 未找到qbrain服务，跳过重启'
        fi
        
        echo '✅ 部署完成!'
        echo '=========================================='
    "
    
    log_success "部署成功!"
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    
    ssh "$SERVER_USER@$SERVER_IP" "
        echo '📊 QBrain 服务状态'
        echo '=========================================='
        
        # 检查qbrain服务
        services=\$(systemctl list-units --type=service | grep qbrain | awk '{print \$1}')
        if [ -n \"\$services\" ]; then
            for service in \$services; do
                status=\$(systemctl is-active "\$service")
                if [ \"\$status\" = "active" ]; then
                    echo \"✅ \$service: 运行中\"
                else
                    echo \"❌ \$service: \$status\"
                fi
            done
        else
            echo '⚠️ 未找到qbrain服务'
        fi
        
        echo ''
        echo '🖥️ 系统资源'
        echo '------------------------------------------'
        echo \"CPU: \$(top -bn1 | grep load | awk '{printf \"%.2f%%\", \$(NF-2)}')\"
        echo \"内存: \$(free -m | awk 'NR==2{printf \"%.2f%%\", \$3*100/\$2 }')\"
        echo \"磁盘: \$(df -h | awk '\$NF==\"/\"{printf \"%s\", \$5}')\"
        
        echo ''
        echo '🌐 端口监听 (5001-5009)'
        echo '------------------------------------------'
        ss -tlnp | grep -E ':(500[1-9])' || echo '无监听端口'
    "
}

# 查看日志
view_logs() {
    log_info "查看日志..."
    
    ssh "$SERVER_USER@$SERVER_IP" "
        echo '📜 最近50行日志'
        echo '=========================================='
        
        # 尝试不同的日志位置
        if [ -f /var/log/qbrain.log ]; then
            tail -n 50 /var/log/qbrain.log
        elif [ -f $PROJECT_DIR/logs/app.log ]; then
            tail -n 50 $PROJECT_DIR/logs/app.log
        else
            # 从journalctl获取
            journalctl -u qbrain-* --no-pager -n 50 2>/dev/null || echo '未找到日志文件'
        fi
    "
}

# 主函数
main() {
    # 默认操作
    local action="deploy"
    local use_password=false
    local ssh_key=""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -i|--init)
                action="init"
                shift
                ;;
            -d|--deploy)
                action="deploy"
                shift
                ;;
            -s|--status)
                action="status"
                shift
                ;;
            -l|--logs)
                action="logs"
                shift
                ;;
            --password)
                use_password=true
                shift
                ;;
            --key)
                ssh_key="$2"
                shift 2
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查依赖
    check_dependencies
    
    # 配置SSH
    if [ "$use_password" = true ]; then
        log_warn "使用密码认证，请输入密码:"
        read -s SSHPASS
        export SSHPASS
        SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=no"
        SCP_CMD="sshpass -e scp -o StrictHostKeyChecking=no"
    elif [ -n "$ssh_key" ]; then
        SSH_CMD="ssh -i $ssh_key -o StrictHostKeyChecking=no"
        SCP_CMD="scp -i $ssh_key -o StrictHostKeyChecking=no"
    else
        SSH_CMD="ssh -o StrictHostKeyChecking=no"
        SCP_CMD="scp -o StrictHostKeyChecking=no"
    fi
    
    # 执行操作
    case $action in
        init)
            init_server
            ;;
        deploy)
            do_deploy
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        *)
            log_error "未知操作: $action"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
