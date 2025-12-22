# 🐟 摸鱼遥控车 (MoYu Robot)

基于 MCP (Model Context Protocol) 的智能机器人控制平台，支持 AI 控制、Web 遥控、手势控制和人脸追踪。

## ✨ 功能特性

- 🤖 **MCP AI 控制**: 通过 MCP 协议与 AI 模型（如 Claude）集成，实现自然语言控制
- 🌐 **Web 控制界面**: 响应式 Web 界面，支持桌面和移动设备
- 🎮 **多种控制模式**:
  - 手柄模式：方向键/WASD 控制
  - 手势模式：MediaPipe 手势识别
  - 人脸追踪：自动追踪人脸
- 📹 **实时视频推流**: 支持多摄像头视频流
- 🔗 **远程连接**: WebSocket 管道支持远程 AI 控制

## 📁 项目结构

```
moyurobot/
├── src/
│   └── moyurobot/
│       ├── core/           # 核心服务
│       │   ├── config.py   # 配置管理
│       │   └── robot_service.py  # 机器人服务
│       ├── mcp/            # MCP 相关
│       │   ├── server.py   # MCP 服务器
│       │   └── pipe.py     # WebSocket 管道
│       ├── web/            # Web 控制器
│       │   ├── controller.py
│       │   ├── templates/  # HTML 模板
│       │   └── static/     # 静态资源
│       └── tools/          # 工具模块
├── config/                 # 配置文件
│   ├── default.json       # 默认配置
│   └── mcp_config.json    # MCP 配置
├── scripts/               # 启动脚本
│   ├── start_all.sh      # 一键启动
│   ├── start_mcp.sh      # MCP 服务
│   ├── start_web.sh      # Web 服务
│   └── start_pipe.sh     # 管道服务
└── tests/                 # 测试文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
cd /Users/zhengbo.zb/workspaces/moyurobot

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 2. 启动服务

#### 一键启动所有服务
```bash
./scripts/start_all.sh
```

#### 单独启动 Web 控制器
```bash
./scripts/start_web.sh
# 访问 http://localhost:8080
# 默认密码: moyu123
```

#### 单独启动 MCP 服务器
```bash
./scripts/start_mcp.sh
```

#### 启动远程管道
```bash
export MCP_ENDPOINT="wss://your-server.com/ws"
./scripts/start_pipe.sh
```

## 🎮 使用说明

### Web 控制

1. 打开浏览器访问 `http://localhost:8080`
2. 输入密码登录（默认: `moyu123`）
3. 选择控制模式：
   - **手柄模式**: 使用方向按钮或键盘控制
   - **手势模式**: 开启摄像头，使用手势控制
   - **人脸追踪**: 机器人自动追踪人脸

### 键盘快捷键

| 按键 | 功能 |
|------|------|
| W / ↑ | 前进 |
| S / ↓ | 后退 |
| A / ← | 左移 |
| D / → | 右移 |
| Q | 左转 |
| E | 右转 |
| Space | 停止 |
| + | 加速 |
| - | 减速 |

### 手势控制

| 手势 | 功能 |
|------|------|
| ✋ 张开手掌 | 停止 |
| ✊ 握拳 | 关闭夹爪 |
| ☝️ 竖起食指 | 前进 |
| 👍 竖起大拇指 | 打开夹爪 |

### MCP AI 控制

配置 Claude Desktop 或其他 MCP 客户端：

```json
{
    "mcpServers": {
        "moyu-robot": {
            "command": "python",
            "args": ["-m", "moyurobot.mcp.server"],
            "cwd": "/Users/zhengbo.zb/workspaces/moyurobot/src"
        }
    }
}
```

## ⚙️ 配置

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WEB_PASSWORD` | Web 登录密码 | `moyu123` |
| `MCP_ENDPOINT` | 远程 MCP 端点 | - |
| `FLASK_SECRET_KEY` | Flask 密钥 | 随机生成 |

### 配置文件

编辑 `config/default.json` 自定义配置：

```json
{
    "robot": {
        "linear_speed": 0.2,
        "angular_speed": 30.0
    },
    "web": {
        "port": 8080
    }
}
```

## 🔧 开发

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black src/
isort src/
```

## 📝 许可证

MIT License

## 🙏 致谢

- [LeRobot](https://github.com/huggingface/lerobot) - 机器人控制框架
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP 协议实现
- [MediaPipe](https://mediapipe.dev/) - 手势识别

