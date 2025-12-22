#!/bin/bash

# Web 控制器启动脚本

# 获取脚本所在目录（兼容不同 shell）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT/src"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
export WEB_PASSWORD="${WEB_PASSWORD:-moyu123}"

echo "🌐 启动 Web 控制器..."
echo "访问地址: http://localhost:8080"
echo "默认密码: moyu123"
echo "项目路径: $PROJECT_ROOT"

python -c "
from moyurobot.web.controller import run_server
run_server(host='0.0.0.0', port=8080, debug=True)
"
