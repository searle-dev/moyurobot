#!/bin/bash

# ============================================
# 摸鱼遥控车 - 一键启动脚本
# ============================================

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    
    python -c "import fastmcp" 2>/dev/null || {
        log_warn "FastMCP 未安装，正在安装..."
        pip install fastmcp
    }
}

# 启动 MCP 服务器
start_mcp_server() {
    log_header "启动 MCP 服务器"
    
    cd "$PROJECT_ROOT/src"
    
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    
    python -m moyurobot.mcp.server &
    MCP_PID=$!
    
    log_info "MCP 服务器已启动 (PID: $MCP_PID)"
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

# 启动 MCP 管道（可选）
start_mcp_pipe() {
    if [ -z "$MCP_ENDPOINT" ]; then
        log_warn "未设置 MCP_ENDPOINT，跳过 MCP 管道启动"
        return
    fi
    
    log_header "启动 MCP 管道"
    
    cd "$PROJECT_ROOT/src"
    
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    export MCP_CONFIG="$PROJECT_ROOT/config/mcp_config.json"
    
    python -c "
import asyncio
from moyurobot.mcp.pipe import MCPPipe

pipe = MCPPipe(endpoint_url='$MCP_ENDPOINT')
asyncio.run(pipe.run())
" &
    PIPE_PID=$!
    
    log_info "MCP 管道已启动 (PID: $PIPE_PID)"
}

# 显示使用说明
show_usage() {
    log_header "摸鱼遥控车 - 使用说明"
    
    echo "服务已启动："
    echo "  - MCP 服务器: 通过 stdio 接收 AI 命令"
    echo "  - Web 控制器: http://localhost:8080"
    echo ""
    echo "默认密码: moyu123"
    echo ""
    echo "环境变量:"
    echo "  - WEB_PASSWORD: Web 登录密码"
    echo "  - MCP_ENDPOINT: MCP 管道 WebSocket 地址"
    echo ""
    echo "按 Ctrl+C 停止所有服务"
}

# 主函数
main() {
    log_header "🐟 摸鱼遥控车 启动中..."
    
    check_python
    check_dependencies
    
    # 根据参数启动不同服务
    case "${1:-all}" in
        mcp)
            start_mcp_server
            ;;
        web)
            start_web_controller
            ;;
        pipe)
            start_mcp_pipe
            ;;
        all)
            start_mcp_server
            sleep 1
            start_web_controller
            start_mcp_pipe
            ;;
        *)
            echo "用法: $0 [mcp|web|pipe|all]"
            exit 1
            ;;
    esac
    
    show_usage
    
    # 等待后台进程
    wait
}

main "$@"

