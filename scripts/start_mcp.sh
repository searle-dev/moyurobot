#!/bin/bash

# MCP 服务器启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT/src"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "🤖 启动 MCP 服务器..."
echo "项目路径: $PROJECT_ROOT"

python -m moyurobot.mcp.server
