#!/bin/bash
# QBrain Deployment Script
# Usage: ./scripts/deploy.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_PATH="${DEPLOY_PATH:-/opt/qbrain}"
LOG_FILE="/var/log/qbrain-deploy.log"
ENVIRONMENT="${1:-production}"
BACKUP_DIR="/opt/backups/qbrain"

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Pre-deployment checks
pre_deploy_checks() {
    log "🔍 Running pre-deployment checks..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        warning "Not running as root. Some operations may fail."
    fi
    
    # Check if deploy directory exists
    if [ ! -d "$DEPLOY_PATH" ]; then
        error "Deploy path does not exist: $DEPLOY_PATH"
    fi
    
    # Check disk space
    DISK_USAGE=$(df -h "$DEPLOY_PATH" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        error "Disk usage is at ${DISK_USAGE}%. Please free up space before deploying."
    fi
    
    # Check if git repo
    if [ ! -d "$DEPLOY_PATH/.git" ]; then
        error "Not a git repository: $DEPLOY_PATH"
    fi
    
    success "Pre-deployment checks passed"
}

# Create backup
create_backup() {
    log "💾 Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="qbrain-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    tar -czf "$BACKUP_DIR/$BACKUP_NAME" \
        -C "$DEPLOY_PATH" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='venv' \
        --exclude='node_modules' \
        . 2>/dev/null || warning "Backup creation had some warnings"
    
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/qbrain-*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
    
    success "Backup created: $BACKUP_DIR/$BACKUP_NAME"
}

# Update code
update_code() {
    log "📥 Updating code from repository..."
    
    cd "$DEPLOY_PATH"
    
    # Fetch latest changes
    git fetch origin
    
    # Get current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log "Current branch: $CURRENT_BRANCH"
    
    # Stash any local changes
    git stash push -m "Auto-stash before deploy $(date)" 2>/dev/null || true
    
    # Reset to origin
    git reset --hard "origin/$CURRENT_BRANCH"
    
    success "Code updated to latest commit: $(git rev-parse --short HEAD)"
}

# Install dependencies
install_dependencies() {
    log "📦 Installing dependencies..."
    
    cd "$DEPLOY_PATH"
    
    # Python dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
        success "Python dependencies installed"
    fi
    
    # Node.js dependencies (if applicable)
    if [ -f "package.json" ]; then
        npm install --silent 2>/dev/null || warning "npm install failed or not available"
    fi
}

# Run migrations
run_migrations() {
    log "🗄️ Running database migrations..."
    
    cd "$DEPLOY_PATH"
    
    # Run Alembic migrations if config exists
    if [ -f "alembic.ini" ]; then
        alembic upgrade head 2>/dev/null || warning "Alembic migration failed or not configured"
    fi
    
    # Run Django migrations if manage.py exists
    if [ -f "manage.py" ]; then
        python manage.py migrate --noinput 2>/dev/null || warning "Django migration failed or not configured"
    fi
}

# Set permissions
set_permissions() {
    log "🔧 Setting file permissions..."
    
    cd "$DEPLOY_PATH"
    
    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    
    # Set proper ownership (if running as root)
    if [[ $EUID -eq 0 ]]; then
        chown -R www-data:www-data . 2>/dev/null || \
        chown -R qbrain:qbrain . 2>/dev/null || \
        warning "Could not change ownership"
    fi
}

# Restart services
restart_services() {
    log "🔄 Restarting services..."
    
    # Reload systemd
    systemctl daemon-reload
    
    # Try specific services first
    local services=("qbrain-api" "qbrain-worker" "qbrain-scheduler")
    local restarted=()
    
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep -q "^$service"; then
            systemctl restart "$service"
            restarted+=("$service")
            log "Restarted: $service"
        fi
    done
    
    # Fallback to wildcard if no specific services found
    if [ ${#restarted[@]} -eq 0 ]; then
        systemctl restart 'qbrain-*' 2>/dev/null || warning "No qbrain services found to restart"
    fi
    
    success "Services restarted"
}

# Health check
health_check() {
    log "🏥 Running health checks..."
    
    # Check if services are running
    local services=("qbrain-api" "qbrain-worker")
    local failed=()
    
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep -q "^$service"; then
            if ! systemctl is-active --quiet "$service"; then
                failed+=("$service")
                error "Service $service is not running!"
            fi
        fi
    done
    
    # Check API endpoint if configured
    if [ -f "$DEPLOY_PATH/.env" ]; then
        source "$DEPLOY_PATH/.env"
        if [ -n "$API_PORT" ]; then
            if curl -sf "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
                success "API health check passed"
            else
                warning "API health check failed or endpoint not configured"
            fi
        fi
    fi
    
    if [ ${#failed[@]} -eq 0 ]; then
        success "All health checks passed"
    fi
}

# Cleanup old files
cleanup() {
    log "🧹 Cleaning up old files..."
    
    # Clean Python cache
    find "$DEPLOY_PATH" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$DEPLOY_PATH" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean old logs (keep last 30 days)
    find /var/log -name "qbrain-*.log" -mtime +30 -delete 2>/dev/null || true
    
    success "Cleanup completed"
}

# Rollback function
rollback() {
    error "Deployment failed! Initiating rollback..."
    
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/qbrain-*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        log "Restoring from backup: $LATEST_BACKUP"
        cd "$DEPLOY_PATH"
        tar -xzf "$LATEST_BACKUP" --overwrite
        restart_services
        success "Rollback completed"
    else
        error "No backup available for rollback!"
    fi
}

# Main deployment flow
main() {
    log "🚀 Starting deployment to $ENVIRONMENT environment..."
    log "Deploy path: $DEPLOY_PATH"
    
    # Trap errors for rollback
    trap 'rollback' ERR
    
    pre_deploy_checks
    create_backup
    update_code
    install_dependencies
    run_migrations
    set_permissions
    restart_services
    health_check
    cleanup
    
    success "🎉 Deployment completed successfully!"
    log "Deployed commit: $(cd "$DEPLOY_PATH" && git rev-parse --short HEAD)"
    log "Deploy time: $(date)"
}

# Run main function
main "$@"
