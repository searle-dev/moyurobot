#!/bin/bash

# ============================================
# 摸鱼遥控车 - 一键启动脚本
# ============================================

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# 清理函数
cleanup() {
    log_header "正在清理..."
    
    # 终止所有后台进程
    jobs -p | xargs -r kill 2>/dev/null || true
    
    log_info "清理完成"
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 检查 Python 环境
check_python() {
    log_info "检查 Python 环境..."
    
    if ! command -v python &> /dev/null; then
        log_error "未找到 Python，请先安装 Python 3.10+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
    log_info "Python 版本: $PYTHON_VERSION"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    cd "$PROJECT_ROOT"
    
    # 检查关键依赖
    python -c "import flask" 2>/dev/null || {
        log_warn "Flask 未安装，正在安装..."
        pip install flask flask-cors
    }
}

# 启动 Web 控制器
start_web_controller() {
    log_header "启动 Web 控制器"
    
    cd "$PROJECT_ROOT/src"
    
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    export WEB_PASSWORD="${WEB_PASSWORD:-moyu123}"
    
    python -c "
from moyurobot.web.controller import run_server
run_server(host='0.0.0.0', port=8080)
" &
    WEB_PID=$!
    
    log_info "Web 控制器已启动 (PID: $WEB_PID)"
    log_info "访问地址: http://localhost:8080"
}

# 显示使用说明
show_usage() {
    log_header "摸鱼遥控车 - 使用说明"
    
    echo "服务已启动："
    echo "  - Web 控制器: http://localhost:8080"
    echo ""
    echo "默认密码: moyu123"
    echo ""
    echo "环境变量:"
    echo "  - WEB_PASSWORD: Web 登录密码"
    echo ""
    echo "按 Ctrl+C 停止所有服务"
}

# 主函数
main() {
    log_header "🐟 摸鱼遥控车 启动中..."
    
    log_info "项目路径: $PROJECT_ROOT"
    
    check_python
    check_dependencies
    
    start_web_controller
    
    show_usage
    
    # 等待后台进程
    wait
}

main "$@"
