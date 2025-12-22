#!/bin/bash

# Web 控制器启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/src"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
export WEB_PASSWORD="${WEB_PASSWORD:-moyu123}"

echo "🌐 启动 Web 控制器..."
echo "访问地址: http://localhost:8080"
echo "默认密码: moyu123"

python -c "
from moyurobot.web.controller import run_server
run_server(host='0.0.0.0', port=8080, debug=True)
"

