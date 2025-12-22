#!/bin/bash

# MCP 服务器启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/src"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "🤖 启动 MCP 服务器..."
python -m moyurobot.mcp.server

