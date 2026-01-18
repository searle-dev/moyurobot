#!/bin/sh

# ============================================
# LeKiwi 单臂机器人 - 快速启动脚本
# ============================================

# 设置 LeKiwi 单臂模式
export ROBOT_TYPE="lekiwi"
export ROBOT_ID="${ROBOT_ID:-my_awesome_kiwi}"

echo "=========================================="
echo "  LeKiwi 单臂机器人启动"
echo "=========================================="
echo ""
echo "机器人类型: LeKiwi (单臂)"
echo "机器人 ID:  $ROBOT_ID"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 调用主启动脚本
exec "$SCRIPT_DIR/start_all.sh" "$@"
