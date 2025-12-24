#!/usr/bin/env python
"""
摸鱼遥控车 Web HTTP 控制器

基于 lerobot lekiwi_http_controller 的完整移植版本，包含：
- 排队系统（用户会话管理）
- 手势控制
- 人脸控制
- 视频推流
- 机械臂控制
"""

import logging
import time
import sys
import os
import threading
import uuid

# 添加项目根目录到路径
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
    sys.path.insert(0, project_root)

import cv2
from flask import Flask, jsonify, request, render_template, Response, make_response, redirect, url_for

# 全局变量
app = None
service = None
logger = None
SESSION_COOKIE_NAME = "moyu_user_id"
USERNAME_COOKIE_NAME = "moyu_username"
SESSION_TIMEOUT_SECONDS = 100
VIP_SESSION_TIMEOUT_SECONDS = 600  # VIP 用户超时时间：10 分钟
_active_user = {"id": None, "start_time": 0.0, "username": None, "is_vip": False}
_waiting_users = []
_active_user_lock = threading.Lock()

# 运动控制开关，默认关闭（监控模式）
_movement_enabled = False


def setup_routes():
    """设置HTTP路由"""
    global app, service, logger

    @app.route('/')
    def index():
        """主页面 - 提供简单的控制界面，仅允许一个活跃用户"""
        username = request.cookies.get(USERNAME_COOKIE_NAME)
        if not username:
            return redirect(url_for('login'))

        user_id = request.cookies.get(SESSION_COOKIE_NAME)
        now = time.time()

        with _active_user_lock:
            active_id = _active_user["id"]
            active_start = _active_user["start_time"]
            active_is_vip = _active_user.get("is_vip", False)
            has_active = active_id is not None and active_start > 0
            
            # 根据是否是 VIP 选择超时时间
            timeout_seconds = VIP_SESSION_TIMEOUT_SECONDS if active_is_vip else SESSION_TIMEOUT_SECONDS
            elapsed = now - active_start if has_active else 0
            is_active = has_active and elapsed < timeout_seconds
            current_owner = _active_user.get("username")

            if is_active and user_id != active_id:
                if username and username not in _waiting_users:
                    _waiting_users.append(username)
                waiting_view = [u for u in _waiting_users if u != current_owner]
                remaining_seconds = max(0, int(timeout_seconds - elapsed))
                return (
                    render_template(
                        "waiting.html",
                        current_owner=current_owner,
                        waiting_users=waiting_view,
                        requesting_user=username,
                        remaining_seconds=remaining_seconds,
                        session_timeout=timeout_seconds,
                    ),
                    429,
                    {"Content-Type": "text/html; charset=utf-8"},
                )

            if not is_active:
                user_id = user_id or str(uuid.uuid4())
                _active_user["id"] = user_id
                _active_user["username"] = username
                _active_user["start_time"] = now
                _active_user["is_vip"] = False  # 普通用户
                if username in _waiting_users:
                    _waiting_users.remove(username)
            elif user_id == _active_user["id"]:
                _active_user["username"] = username
                if username in _waiting_users:
                    _waiting_users.remove(username)

        response = make_response(render_template('index.html', username=username))
        response.set_cookie(
            SESSION_COOKIE_NAME,
            user_id,
            max_age=24 * 3600,
            httponly=True,
            samesite='Lax'
        )
        return response

    @app.route('/vip', methods=['GET'])
    def vip():
        """VIP 页面 - 直接进入控制界面，无需等待，10分钟超时"""
        username = request.cookies.get(USERNAME_COOKIE_NAME)
        if not username:
            return redirect(url_for('login'))

        user_id = request.cookies.get(SESSION_COOKIE_NAME) or str(uuid.uuid4())
        now = time.time()

        with _active_user_lock:
            _active_user["id"] = user_id
            _active_user["username"] = username
            _active_user["start_time"] = now
            _active_user["is_vip"] = True
            
            if username in _waiting_users:
                _waiting_users.remove(username)

        response = make_response(render_template('index.html', username=username))
        response.set_cookie(
            SESSION_COOKIE_NAME,
            user_id,
            max_age=24 * 3600,
            httponly=True,
            samesite='Lax'
        )
        return response

    @app.route('/wait', methods=['GET'])
    def wait():
        """等待页面 - 显示排队信息"""
        username = request.cookies.get(USERNAME_COOKIE_NAME)
        if not username:
            return redirect(url_for('login'))
        
        user_id = request.cookies.get(SESSION_COOKIE_NAME)
        now = time.time()
        
        with _active_user_lock:
            active_id = _active_user["id"]
            active_start = _active_user["start_time"]
            active_is_vip = _active_user.get("is_vip", False)
            has_active = active_id is not None and active_start > 0
            
            timeout_seconds = VIP_SESSION_TIMEOUT_SECONDS if active_is_vip else SESSION_TIMEOUT_SECONDS
            elapsed = now - active_start if has_active else 0
            is_active = has_active and elapsed < timeout_seconds
            current_owner = _active_user.get("username")
            
            if is_active and user_id != active_id:
                if username and username not in _waiting_users:
                    _waiting_users.append(username)
            
            waiting_view = [u for u in _waiting_users if u != current_owner]
            remaining_seconds = max(0, int(timeout_seconds - elapsed)) if is_active else 0
        
        return render_template(
            "waiting.html",
            current_owner=current_owner if is_active else None,
            waiting_users=waiting_view,
            requesting_user=username,
            remaining_seconds=remaining_seconds,
            session_timeout=timeout_seconds,
        )
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录页面，要求输入用户名"""
        error = None
        if request.method == 'POST':
            username = (request.form.get('username') or '').strip()
            if not username:
                error = "用户名不能为空"
            else:
                resp = make_response(redirect(url_for('index')))
                resp.set_cookie(
                    USERNAME_COOKIE_NAME,
                    username,
                    max_age=24 * 3600,
                    httponly=False,
                    samesite='Lax'
                )
                return resp

        return render_template('login.html', error=error)

    @app.route('/exit_control', methods=['POST'])
    def exit_control():
        """退出控制 - 清除当前活跃用户，让其他人可以进入"""
        user_id = request.cookies.get(SESSION_COOKIE_NAME)
        username = request.cookies.get(USERNAME_COOKIE_NAME)
        
        with _active_user_lock:
            active_id = _active_user["id"]
            
            if user_id == active_id:
                _active_user["id"] = None
                _active_user["start_time"] = 0.0
                _active_user["username"] = None
                _active_user["is_vip"] = False
                
                if username and username in _waiting_users:
                    _waiting_users.remove(username)
                
                logger.info(f"用户 {username} 已退出控制")
                return jsonify({
                    "success": True,
                    "message": "已退出控制"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "您不是当前活跃用户，无法退出控制"
                }), 403

    @app.route('/session_info', methods=['GET'])
    def session_info():
        """获取当前会话占用信息"""
        user_id = request.cookies.get(SESSION_COOKIE_NAME)
        now = time.time()

        with _active_user_lock:
            active_id = _active_user["id"]
            active_start = _active_user["start_time"]
            active_username = _active_user.get("username")
            active_is_vip = _active_user.get("is_vip", False)
            waiting_view = [u for u in _waiting_users if u != active_username]

            has_active = active_id is not None and active_start > 0
            elapsed = now - active_start if has_active else 0
            
            timeout_seconds = VIP_SESSION_TIMEOUT_SECONDS if active_is_vip else SESSION_TIMEOUT_SECONDS
            is_active = has_active and elapsed < timeout_seconds
            remaining = timeout_seconds - elapsed if is_active else 0
            is_current_user = is_active and user_id == active_id

        return jsonify({
            "is_active_user": bool(is_current_user),
            "remaining_seconds": max(0, int(remaining if is_current_user else 0)),
            "current_owner": active_username if is_active else None,
            "session_timeout": timeout_seconds,
            "is_vip": active_is_vip if is_active else False,
            "waiting_users": waiting_view,
        })

    @app.route('/status', methods=['GET'])
    def get_status():
        """获取机器人状态"""
        if service is None:
            return jsonify({
                "connected": False,
                "movement_enabled": _movement_enabled,
                "message": "机器人服务未初始化"
            })
        
        status = service.get_status()
        status['movement_enabled'] = _movement_enabled
        return jsonify(status)

    @app.route('/startmove', methods=['GET', 'POST'])
    def start_move():
        """开启运动控制"""
        global _movement_enabled
        _movement_enabled = True
        logger.info("收到 /startmove 请求，已启用运动控制")
        return jsonify({
            "success": True,
            "message": "运动控制已启用"
        })

    @app.route('/stopmove', methods=['GET', 'POST'])
    def stop_move():
        """关闭运动控制"""
        global _movement_enabled
        _movement_enabled = False
        try:
            if service:
                service.stop_robot()
        except:
            pass
        logger.info("收到 /stopmove 请求，已禁用运动控制")
        return jsonify({
            "success": True,
            "message": "运动控制已禁用"
        })

    @app.route('/control', methods=['POST'])
    def control_robot():
        """控制机器人移动"""
        global _movement_enabled
        
        if not _movement_enabled:
            return jsonify({
                "success": False,
                "message": "当前处于仅监控模式，找摸鱼管理员启用控制模式"
            })

        if service is None:
            return jsonify({
                "success": False,
                "message": "机器人服务未初始化"
            })

        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    "success": False,
                    "message": "请求体不能为空"
                })

            # 处理预定义命令
            if "command" in data:
                duration = data.get("duration", 0)
                if duration > 0:
                    result = service.move_robot_for_duration(data["command"], duration)
                else:
                    result = service.execute_predefined_command(data["command"])
                return jsonify(result)
            
            # 处理机械臂位置控制
            elif any(key.endswith('.pos') for key in data.keys()):
                arm_positions = {k: v for k, v in data.items() if k.endswith('.pos')}
                result = service.set_arm_position(arm_positions)
                return jsonify(result)
            
            # 处理自定义速度
            elif any(key in data for key in ["x_vel", "y_vel", "theta_vel"]):
                duration = data.get("duration", 0)
                if duration > 0:
                    result = service.move_robot_with_custom_speed_for_duration(
                        data.get("x_vel", 0.0),
                        data.get("y_vel", 0.0),
                        data.get("theta_vel", 0.0),
                        duration
                    )
                else:
                    result = service.execute_custom_velocity(
                        data.get("x_vel", 0.0),
                        data.get("y_vel", 0.0),
                        data.get("theta_vel", 0.0)
                    )
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": "无效的命令格式"
                })

        except Exception as e:
            logger.error(f"控制命令执行失败: {e}")
            return jsonify({
                "success": False,
                "message": str(e)
            })
    
    @app.route('/video_feed/<camera>')
    def video_feed(camera):
        """视频流端点"""
        def generate():
            """生成MJPEG视频流"""
            last_frame_time = 0
            min_interval = 0.1
            
            while True:
                try:
                    now = time.time()
                    if now - last_frame_time < min_interval:
                        time.sleep(0.01)
                        continue
                        
                    if service and service.robot and service.robot.is_connected and camera in service.robot.cameras:
                        try:
                            frame = service.robot.cameras[camera].async_read(timeout_ms=100)
                            if frame is not None and frame.size > 0:
                                height, width = frame.shape[:2]
                                new_width = int(width * 0.7)
                                new_height = int(height * 0.7)
                                frame_resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                                
                                # RGB -> BGR
                                frame_encoded_ready = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                                
                                ret, jpeg = cv2.imencode('.jpg', frame_encoded_ready, [cv2.IMWRITE_JPEG_QUALITY, 60])
                                if ret:
                                    jpeg_bytes = jpeg.tobytes()
                                    yield (b'--frame\r\n'
                                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
                                    last_frame_time = time.time()
                                else:
                                    time.sleep(0.05)
                            else:
                                time.sleep(0.05)
                        except Exception as cam_e:
                            logger.debug(f"摄像头 {camera} 读取错误: {cam_e}")
                            time.sleep(0.1)
                    else:
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"视频流错误: {e}")
                    time.sleep(0.1)
        
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/cameras')
    def get_cameras():
        """获取可用的摄像头列表"""
        cameras = []
        camera_status = {}
        
        if service and service.robot and service.robot.is_connected:
            for cam_name, cam in service.robot.cameras.items():
                try:
                    is_connected = cam.is_connected
                    test_frame = None
                    if is_connected:
                        try:
                            test_frame = cam.async_read(timeout_ms=100)
                            frame_available = test_frame is not None and test_frame.size > 0
                        except Exception as e:
                            frame_available = False
                            camera_status[cam_name] = str(e)
                    else:
                        frame_available = False
                        
                    cameras.append({
                        'name': cam_name,
                        'display_name': '前置摄像头' if cam_name == 'front' else '手腕摄像头',
                        'connected': is_connected,
                        'frame_available': frame_available,
                        'frame_shape': test_frame.shape if test_frame is not None else None
                    })
                    
                except Exception as e:
                    cameras.append({
                        'name': cam_name,
                        'display_name': '前置摄像头' if cam_name == 'front' else '手腕摄像头',
                        'connected': False,
                        'frame_available': False,
                        'error': str(e)
                    })
                    camera_status[cam_name] = str(e)
        
        return jsonify({
            'cameras': cameras, 
            'robot_connected': service.robot.is_connected if service and service.robot else False,
            'camera_status': camera_status
        })


def run_server(host="0.0.0.0", port=8080, robot_id="my_awesome_kiwi"):
    """启动HTTP服务器"""
    global app, service, logger
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(current_dir, 'templates')
    static_dir = os.path.join(current_dir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # 设置 secret key
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "moyu_robot_secret_key")
    
    # 创建服务实例
    try:
        from moyurobot.core.robot_service import create_default_service, set_global_service
        service = create_default_service(robot_id)
        set_global_service(service)
    except ImportError as e:
        logger.warning(f"无法导入机器人服务模块: {e}")
        service = None
    except Exception as e:
        logger.warning(f"创建机器人服务失败: {e}")
        service = None
    
    # 设置路由
    setup_routes()
    
    logger.info(f"正在启动摸鱼遥控车 HTTP 控制器，地址: http://{host}:{port}")
    
    # 启动时自动连接机器人
    if service:
        if service.connect():
            logger.info("✓ 机器人连接成功")
        else:
            logger.warning("⚠️ 机器人连接失败，将以离线模式启动HTTP服务")
    
    logger.info("使用浏览器访问控制界面，或通过API发送控制命令")
    
    try:
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        cleanup()


def cleanup():
    """清理资源"""
    global service
    if service:
        service.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="摸鱼遥控车 HTTP 控制器")
    parser.add_argument(
        "--robot-id", 
        type=str, 
        default="my_awesome_kiwi",
        help="机器人 ID 标识符（默认: my_awesome_kiwi）"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="服务器主机地址（默认: 0.0.0.0）"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080,
        help="服务器端口（默认: 8080）"
    )
    
    args = parser.parse_args()
    
    print("=== 摸鱼遥控车 HTTP 控制器 ===")
    print(f"机器人 ID: {args.robot_id}")
    print(f"服务地址: http://{args.host}:{args.port}")
    print("功能特性:")
    print("  - 网页控制界面")
    print("  - REST API 接口")
    print("  - 排队系统")
    print("  - 手势/人脸控制")
    print("  - 键盘控制支持")
    print("按 Ctrl+C 停止服务")
    print("=========================")
    
    try:
        run_server(args.host, args.port, args.robot_id)
    except KeyboardInterrupt:
        print("\n收到键盘中断，正在关闭服务...")
    except Exception as e:
        print(f"\n启动失败: {e}")
