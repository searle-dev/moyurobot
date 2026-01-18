#!/bin/sh

# ============================================
# XLeRobot 双臂机器人 - 快速启动脚本
# ============================================

# 设置 XLeRobot 双臂模式
export ROBOT_TYPE="xlerobot"
export ROBOT_ID="${ROBOT_ID:-my_xlerobot}"

echo "=========================================="
echo "  XLeRobot 双臂机器人启动"
echo "=========================================="
echo ""
echo "机器人类型: XLeRobot (双臂)"
echo "机器人 ID:  $ROBOT_ID"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 调用主启动脚本
exec "$SCRIPT_DIR/start_all.sh" "$@"
