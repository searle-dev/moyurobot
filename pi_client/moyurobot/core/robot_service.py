#!/usr/bin/env python
"""
机器人服务模块

提供对 LeKiwi 和 XLeRobot 机器人的统一控制接口
支持单臂（LeKiwi）和双臂（XLeRobot）配置
"""

import logging
import os
import platform
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List

import numpy as np

# 从 config 模块导入配置类（避免重复定义）
from moyurobot.core.config import RobotServiceConfig, RobotType

logger = logging.getLogger(__name__)


# XLeRobot 双臂机械臂关节定义
XLEROBOT_LEFT_ARM_JOINTS = [
    "left_shoulder_pan.pos",
    "left_shoulder_lift.pos",
    "left_elbow_flex.pos",
    "left_wrist_flex.pos",
    "left_wrist_roll.pos",
    "left_gripper.pos",
]

XLEROBOT_RIGHT_ARM_JOINTS = [
    "right_shoulder_pan.pos",
    "right_shoulder_lift.pos",
    "right_elbow_flex.pos",
    "right_wrist_flex.pos",
    "right_wrist_roll.pos",
    "right_gripper.pos",
]

# LeKiwi 单臂机械臂关节定义
LEKIWI_ARM_JOINTS = [
    "arm_shoulder_pan.pos",
    "arm_shoulder_lift.pos",
    "arm_elbow_flex.pos",
    "arm_wrist_flex.pos",
    "arm_wrist_roll.pos",
    "arm_gripper.pos",
]


def find_camera_by_name(camera_name: str) -> Optional[str]:
    """根据设备名称查找摄像头设备路径
    
    通过读取 /sys/class/video4linux/ 目录下的设备信息文件来获取设备名称
    
    Args:
        camera_name: 摄像头设备名称，例如 "USB Camera" 或 "T1 Webcam"
        
    Returns:
        设备路径，例如 "/dev/video3"，如果未找到则返回 None
    """
    if platform.system() != "Linux":
        return None
    
    sys_video_path = Path("/sys/class/video4linux")
    
    if not sys_video_path.exists():
        logger.warning("/sys/class/video4linux 目录不存在")
        return None
    
    try:
        device_map = {}
        
        for video_dir in sorted(sys_video_path.glob("video*")):
            name_file = video_dir / "name"
            if not name_file.exists():
                continue
            
            try:
                with open(name_file, 'r') as f:
                    device_name = f.read().strip()
                
                if not device_name:
                    continue
                
                video_num = video_dir.name.replace("video", "")
                if not video_num.isdigit():
                    continue
                
                device_path = f"/dev/video{video_num}"
                
                if not Path(device_path).exists():
                    continue
                
                if device_name not in device_map:
                    device_map[device_name] = []
                device_map[device_name].append(device_path)
                
            except (IOError, OSError) as e:
                logger.debug(f"读取设备 {video_dir.name} 信息失败: {e}")
                continue
        
        for device_name, paths in device_map.items():
            if camera_name.lower() in device_name.lower():
                if paths:
                    device_path = paths[0]
                    logger.info(f"找到摄像头设备: {device_name} -> {device_path}")
                    return device_path
        
        available_names = list(device_map.keys())
        logger.warning(f"未找到名称为 '{camera_name}' 的摄像头设备。可用设备: {available_names}")
        return None
        
    except Exception as e:
        logger.error(f"查找摄像头设备时出错: {e}")
        return None


class RobotService:
    """机器人控制服务

    提供统一的机器人控制接口，可被 HTTP 控制器、MCP 服务等复用
    支持 LeKiwi（单臂）和 XLeRobot（双臂）机器人
    """

    def __init__(self, config: RobotServiceConfig):
        self.config = config
        self.robot = None
        self._robot_class = None
        self._robot_config_class = None

        # 运行状态
        self.running = False
        self.last_command_time = 0

        # 根据机器人类型初始化动作字典
        self.current_action = self._init_action_dict()

        self.control_thread = None
        self._lock = threading.Lock()

        # 延迟导入标记
        self._lerobot_imported = False
        self._xlerobot_imported = False

    def _init_action_dict(self) -> Dict[str, Any]:
        """根据机器人类型初始化动作字典"""
        # 基础移动动作（所有机器人通用）
        action = {
            "x.vel": 0.0,
            "y.vel": 0.0,
            "theta.vel": 0.0,
        }

        if self.config.is_xlerobot():
            # XLeRobot 双臂配置
            for joint in XLEROBOT_LEFT_ARM_JOINTS:
                action[joint] = 0
            for joint in XLEROBOT_RIGHT_ARM_JOINTS:
                action[joint] = 0
        else:
            # LeKiwi 单臂配置（默认）
            for joint in LEKIWI_ARM_JOINTS:
                action[joint] = 0

        return action

    def get_arm_joints(self, arm: str = "default") -> List[str]:
        """获取指定机械臂的关节列表

        Args:
            arm: 机械臂标识 - "left", "right", "default"（单臂时使用）

        Returns:
            关节名称列表
        """
        if self.config.is_xlerobot():
            if arm == "left":
                return XLEROBOT_LEFT_ARM_JOINTS
            elif arm == "right":
                return XLEROBOT_RIGHT_ARM_JOINTS
            else:
                return XLEROBOT_LEFT_ARM_JOINTS + XLEROBOT_RIGHT_ARM_JOINTS
        else:
            return LEKIWI_ARM_JOINTS
        
    def _import_lerobot(self):
        """延迟导入 lerobot 模块（LeKiwi）"""
        if self._lerobot_imported:
            return True

        try:
            from lerobot.robots.lekiwi.config_lekiwi import LeKiwiConfig
            from lerobot.robots.lekiwi.lekiwi import LeKiwi
            from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
            from lerobot.cameras.configs import Cv2Rotation

            self._robot_class = LeKiwi
            self._robot_config_class = LeKiwiConfig
            self._camera_config_class = OpenCVCameraConfig
            self._cv2_rotation = Cv2Rotation
            self._lerobot_imported = True
            return True

        except ImportError as e:
            logger.error(f"无法导入 lerobot 模块: {e}")
            logger.error("请确保已安装 lerobot[lekiwi] 依赖")
            return False

    def _import_xlerobot(self):
        """延迟导入 xlerobot/lerobot 模块（XLeRobot 双臂机器人）

        XLeRobot 基于 LeRobot 框架，使用相同的摄像头配置类，
        但使用不同的机器人配置和控制类。
        """
        if self._xlerobot_imported:
            return True

        try:
            # XLeRobot 使用 LeRobot 的基础设施
            from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
            from lerobot.cameras.configs import Cv2Rotation

            self._camera_config_class = OpenCVCameraConfig
            self._cv2_rotation = Cv2Rotation

            # 尝试导入 XLeRobot 专用模块
            try:
                # XLeRobot 可能有自己的配置类
                from lerobot.robots.xlerobot.config_xlerobot import XLeRobotConfig
                from lerobot.robots.xlerobot.xlerobot import XLeRobot
                self._robot_class = XLeRobot
                self._robot_config_class = XLeRobotConfig
                logger.info("已加载 XLeRobot 专用模块")
            except ImportError:
                # 如果没有专用模块，尝试使用 LeKiwi 作为基础（XLeRobot 兼容 LeKiwi）
                logger.warning("XLeRobot 专用模块未找到，尝试使用兼容模式...")
                try:
                    from lerobot.robots.lekiwi.config_lekiwi import LeKiwiConfig
                    from lerobot.robots.lekiwi.lekiwi import LeKiwi
                    self._robot_class = LeKiwi
                    self._robot_config_class = LeKiwiConfig
                    logger.info("使用 LeKiwi 兼容模式运行 XLeRobot")
                except ImportError:
                    logger.error("无法导入 LeKiwi 兼容模块")
                    return False

            self._xlerobot_imported = True
            return True

        except ImportError as e:
            logger.error(f"无法导入 xlerobot 模块: {e}")
            logger.error("请确保已安装 lerobot 依赖，并配置好 XLeRobot 文件")
            return False

    def _import_robot_module(self):
        """根据机器人类型导入对应模块"""
        if self.config.is_xlerobot():
            return self._import_xlerobot()
        else:
            return self._import_lerobot()
    
    def _create_robot(self):
        """创建机器人实例"""
        if not self._import_robot_module():
            return None

        # 创建摄像头配置
        cameras_config = self._create_cameras_config()

        # 构建配置参数字典
        config_params = {
            "id": self.config.robot_id,
            "cameras": cameras_config
        }

        # XLeRobot 需要额外的串口配置
        if self.config.is_xlerobot():
            if self.config.port1:
                config_params["port1"] = self.config.port1
            if self.config.port2:
                config_params["port2"] = self.config.port2

        robot_config = self._robot_config_class(**config_params)

        return self._robot_class(robot_config)

    def _create_cameras_config(self) -> Dict[str, Any]:
        """创建摄像头配置

        根据机器人类型（LeKiwi 单臂或 XLeRobot 双臂）创建对应的摄像头配置
        """
        cameras_config = {}

        # 前置摄像头（所有机器人通用）
        front_path = find_camera_by_name(self.config.front_camera_name)
        if front_path is None:
            front_path = "/dev/video0"
            logger.warning(f"未找到 '{self.config.front_camera_name}'，使用默认路径: {front_path}")

        cameras_config["front"] = self._camera_config_class(
            index_or_path=front_path,
            fps=30,
            width=640,
            height=480,
            rotation=self._cv2_rotation.NO_ROTATION
        )

        if self.config.is_xlerobot():
            # XLeRobot 双臂配置：左右手腕各一个摄像头
            left_wrist_path = find_camera_by_name(self.config.left_wrist_camera_name)
            if left_wrist_path is None:
                left_wrist_path = "/dev/video2"
                logger.warning(f"未找到 '{self.config.left_wrist_camera_name}'，使用默认路径: {left_wrist_path}")

            right_wrist_path = find_camera_by_name(self.config.right_wrist_camera_name)
            if right_wrist_path is None:
                right_wrist_path = "/dev/video4"
                logger.warning(f"未找到 '{self.config.right_wrist_camera_name}'，使用默认路径: {right_wrist_path}")

            cameras_config["left_wrist"] = self._camera_config_class(
                index_or_path=left_wrist_path,
                fps=30,
                width=640,
                height=480,
                rotation=self._cv2_rotation.ROTATE_180
            )

            cameras_config["right_wrist"] = self._camera_config_class(
                index_or_path=right_wrist_path,
                fps=30,
                width=640,
                height=480,
                rotation=self._cv2_rotation.ROTATE_180
            )
        else:
            # LeKiwi 单臂配置：单个手腕摄像头
            wrist_path = find_camera_by_name(self.config.wrist_camera_name)
            if wrist_path is None:
                wrist_path = "/dev/video3"
                logger.warning(f"未找到 '{self.config.wrist_camera_name}'，使用默认路径: {wrist_path}")

            cameras_config["wrist"] = self._camera_config_class(
                index_or_path=wrist_path,
                fps=30,
                width=640,
                height=480,
                rotation=self._cv2_rotation.ROTATE_180
            )

        return cameras_config
    
    def connect(self, calibrate: bool = False) -> bool:
        """连接机器人
        
        Args:
            calibrate: 是否进行校准，默认 False（跳过校准）
        """
        try:
            if self.robot and self.robot.is_connected:
                logger.info("机器人已经连接")
                return True
            
            logger.info("正在连接机器人...")
            
            if self.robot is None:
                self.robot = self._create_robot()
                if self.robot is None:
                    return False
            
            # 跳过校准（calibrate=False）
            self.robot.connect(calibrate=calibrate)
            
            # 读取当前机械臂位置
            current_state = self.robot.get_observation()
            with self._lock:
                for key in self.current_action:
                    if key.endswith('.pos') and key in current_state:
                        self.current_action[key] = current_state[key]
            
            # 启动控制循环
            if not self.running:
                self.running = True
                self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
                self.control_thread.start()
            
            logger.info("✓ 机器人连接成功")
            return True
            
        except Exception as e:
            logger.error(f"机器人连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开机器人连接"""
        try:
            self.running = False
            if self.robot and self.robot.is_connected:
                self.robot.disconnect()
            logger.info("机器人断开连接成功")
        except Exception as e:
            logger.error(f"断开机器人连接失败: {e}")
    
    def is_connected(self) -> bool:
        """检查机器人是否连接"""
        return self.robot is not None and self.robot.is_connected
    
    def get_status(self) -> Dict[str, Any]:
        """获取机器人状态"""
        try:
            with self._lock:
                return {
                    "success": True,
                    "connected": self.is_connected(),
                    "running": self.running,
                    "current_action": self.current_action.copy(),
                    "last_command_time": self.last_command_time
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "connected": False,
                "running": self.running
            }
    
    def execute_predefined_command(self, command: str) -> Dict[str, Any]:
        """执行预定义的移动命令"""
        if not self.is_connected():
            return {
                "success": False,
                "message": "机器人未连接，请检查硬件连接后重启服务"
            }
        
        try:
            with self._lock:
                self.current_action.update({
                    "x.vel": 0.0,
                    "y.vel": 0.0,
                    "theta.vel": 0.0
                })

                if command == "forward":
                    self.current_action["x.vel"] = self.config.linear_speed
                elif command == "backward":
                    self.current_action["x.vel"] = -self.config.linear_speed
                elif command == "left":
                    self.current_action["y.vel"] = self.config.linear_speed
                elif command == "right":
                    self.current_action["y.vel"] = -self.config.linear_speed
                elif command == "rotate_left":
                    self.current_action["theta.vel"] = self.config.angular_speed
                elif command == "rotate_right":
                    self.current_action["theta.vel"] = -self.config.angular_speed
                elif command == "stop":
                    pass
                else:
                    logger.warning(f"未知命令: {command}")
                    return {
                        "success": False,
                        "message": f"未知命令: {command}"
                    }

                self.last_command_time = time.time()
            
            return {
                "success": True,
                "message": f"执行命令: {command}",
                "current_action": self.current_action.copy()
            }

        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def execute_custom_velocity(self, x_vel: float, y_vel: float, theta_vel: float) -> Dict[str, Any]:
        """执行自定义速度命令"""
        if not self.is_connected():
            return {
                "success": False,
                "message": "机器人未连接，请检查硬件连接后重启服务"
            }
        
        try:
            with self._lock:
                self.current_action.update({
                    "x.vel": x_vel,
                    "y.vel": y_vel,
                    "theta.vel": theta_vel
                })
                self.last_command_time = time.time()
            
            return {
                "success": True,
                "message": "自定义速度命令已设置",
                "current_action": self.current_action.copy()
            }
            
        except Exception as e:
            logger.error(f"设置自定义速度失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def move_robot_for_duration(self, command: str, duration: float) -> Dict[str, Any]:
        """移动机器人指定时间"""
        result = self.execute_predefined_command(command)
        if not result["success"]:
            return result
        
        if command != "stop" and duration > 0:
            def stop_after_duration():
                end_time = time.time() + duration
                while time.time() < end_time:
                    with self._lock:
                        self.last_command_time = time.time()
                    time.sleep(0.1)
                self.execute_predefined_command("stop")
            
            stop_thread = threading.Thread(target=stop_after_duration, daemon=True)
            stop_thread.start()
        
        return {
            "success": True,
            "command": command,
            "duration": duration,
            "message": f"机器人{command}移动{duration}秒"
        }
    
    def move_robot_with_custom_speed_for_duration(self, x_vel: float, y_vel: float,
                                                 theta_vel: float, duration: float) -> Dict[str, Any]:
        """使用自定义速度移动机器人指定时间"""
        result = self.execute_custom_velocity(x_vel, y_vel, theta_vel)
        if not result["success"]:
            return result
        
        if duration > 0:
            def stop_after_duration():
                end_time = time.time() + duration
                while time.time() < end_time:
                    with self._lock:
                        self.last_command_time = time.time()
                    time.sleep(0.1)
                self.execute_predefined_command("stop")
            
            stop_thread = threading.Thread(target=stop_after_duration, daemon=True)
            stop_thread.start()
        
        return {
            "success": True,
            "x_vel": x_vel,
            "y_vel": y_vel,
            "theta_vel": theta_vel,
            "duration": duration,
            "message": f"机器人自定义速度移动{duration}秒"
        }
    
    def set_arm_position(self, arm_positions: Dict[str, float]) -> Dict[str, Any]:
        """设置机械臂位置"""
        if not self.is_connected():
            return {
                "success": False,
                "message": "机器人未连接，请检查硬件连接后重启服务"
            }
        
        try:
            if hasattr(self, '_arm_speed_configured') and self._arm_speed_configured == self.config.arm_servo_speed:
                pass
            else:
                self._configure_arm_servo_speed(self.config.arm_servo_speed)
                self._arm_speed_configured = self.config.arm_servo_speed
            
            with self._lock:
                for joint, position in arm_positions.items():
                    if joint in self.current_action:
                        self.current_action[joint] = position
                
                self.last_command_time = time.time()
            
            return {
                "success": True,
                "message": f"机械臂位置已更新（舵机速度: {self.config.arm_servo_speed*100:.0f}%）",
                "arm_positions": arm_positions,
                "servo_speed_percent": self.config.arm_servo_speed * 100,
                "current_action": self.current_action.copy()
            }
            
        except Exception as e:
            logger.error(f"设置机械臂位置失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _configure_arm_servo_speed(self, speed_ratio: float = 0.2):
        """配置机械臂舵机速度"""
        if not self.is_connected():
            return

        speed_ratio = max(0.05, min(1.0, speed_ratio))
        max_speed = 2400
        goal_speed = int(max_speed * speed_ratio)
        max_acceleration = 50
        acceleration = max(5, int(max_acceleration * speed_ratio * 0.5))
        torque_limit = getattr(self.config, 'arm_torque_limit', 600)

        # 根据机器人类型选择机械臂电机前缀
        if self.config.is_xlerobot():
            arm_prefixes = ["left_", "right_"]
        else:
            arm_prefixes = ["arm_"]

        arm_motors = [
            motor for motor in self.robot.bus.motors
            if any(motor.startswith(prefix) for prefix in arm_prefixes)
        ]

        for motor in arm_motors:
            try:
                self.robot.bus.write("Goal_Acc", motor, acceleration)
                self.robot.bus.write("Goal_Speed", motor, goal_speed)
                self.robot.bus.write("P_Coefficient", motor, 8)
                self.robot.bus.write("Torque_Limit", motor, torque_limit)
            except Exception as e:
                logger.warning(f"设置舵机 {motor} 速度/扭矩失败: {e}")

        logger.info(f"机械臂舵机配置已更新: 速度={speed_ratio*100:.0f}%, 扭矩限制={torque_limit}/1000")
    
    def stop_robot(self):
        """停止机器人"""
        return self.execute_predefined_command("stop")
    
    def move(self, x: float, y: float, theta: float):
        """
        移动机器人
        
        Args:
            x: 前后速度 (m/s)
            y: 左右速度 (m/s)
            theta: 旋转速度 (deg/s)
        """
        return self.execute_custom_velocity(x, y, theta)
    
    def reset_arm(self, arm: str = "all"):
        """重置机械臂到初始位置

        Args:
            arm: 机械臂标识 - "left", "right", "all"（默认），单臂机器人忽略此参数
        """
        if self.config.is_xlerobot():
            initial_positions = {}
            if arm in ["left", "all"]:
                initial_positions.update({
                    "left_shoulder_pan.pos": 0,
                    "left_shoulder_lift.pos": 0,
                    "left_elbow_flex.pos": 0,
                    "left_wrist_flex.pos": 0,
                    "left_wrist_roll.pos": 0,
                    "left_gripper.pos": 50,
                })
            if arm in ["right", "all"]:
                initial_positions.update({
                    "right_shoulder_pan.pos": 0,
                    "right_shoulder_lift.pos": 0,
                    "right_elbow_flex.pos": 0,
                    "right_wrist_flex.pos": 0,
                    "right_wrist_roll.pos": 0,
                    "right_gripper.pos": 50,
                })
        else:
            initial_positions = {
                "arm_shoulder_pan.pos": 0,
                "arm_shoulder_lift.pos": 0,
                "arm_elbow_flex.pos": 0,
                "arm_wrist_flex.pos": 0,
                "arm_wrist_roll.pos": 0,
                "arm_gripper.pos": 50,
            }
        return self.set_arm_position(initial_positions)

    def set_gripper(self, value: int, arm: str = "default"):
        """设置夹爪开合度

        Args:
            value: 0-100，0为完全关闭，100为完全打开
            arm: 机械臂标识 - "left", "right", "both"（双臂同时），单臂机器人忽略此参数
        """
        if self.config.is_xlerobot():
            positions = {}
            if arm in ["left", "both", "all"]:
                positions["left_gripper.pos"] = value
            if arm in ["right", "both", "all"]:
                positions["right_gripper.pos"] = value
            if arm == "default":
                # 默认控制双臂
                positions["left_gripper.pos"] = value
                positions["right_gripper.pos"] = value
            return self.set_arm_position(positions)
        else:
            return self.set_arm_position({"arm_gripper.pos": value})

    # ==================== XLeRobot 双臂专用方法 ====================

    def set_left_arm_position(self, arm_positions: Dict[str, float]) -> Dict[str, Any]:
        """设置左臂位置（XLeRobot 专用）

        Args:
            arm_positions: 关节位置字典，键为不带前缀的关节名
                例如: {"shoulder_pan.pos": 0, "gripper.pos": 50}
        """
        if not self.config.is_xlerobot():
            return {
                "success": False,
                "message": "当前机器人不是 XLeRobot 双臂机器人"
            }

        # 添加 left_ 前缀
        prefixed_positions = {
            f"left_{k}": v for k, v in arm_positions.items()
        }
        return self.set_arm_position(prefixed_positions)

    def set_right_arm_position(self, arm_positions: Dict[str, float]) -> Dict[str, Any]:
        """设置右臂位置（XLeRobot 专用）

        Args:
            arm_positions: 关节位置字典，键为不带前缀的关节名
                例如: {"shoulder_pan.pos": 0, "gripper.pos": 50}
        """
        if not self.config.is_xlerobot():
            return {
                "success": False,
                "message": "当前机器人不是 XLeRobot 双臂机器人"
            }

        # 添加 right_ 前缀
        prefixed_positions = {
            f"right_{k}": v for k, v in arm_positions.items()
        }
        return self.set_arm_position(prefixed_positions)

    def set_dual_arm_position(
        self,
        left_positions: Optional[Dict[str, float]] = None,
        right_positions: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """同时设置双臂位置（XLeRobot 专用）

        Args:
            left_positions: 左臂关节位置字典
            right_positions: 右臂关节位置字典
        """
        if not self.config.is_xlerobot():
            return {
                "success": False,
                "message": "当前机器人不是 XLeRobot 双臂机器人"
            }

        combined_positions = {}

        if left_positions:
            for k, v in left_positions.items():
                key = k if k.startswith("left_") else f"left_{k}"
                combined_positions[key] = v

        if right_positions:
            for k, v in right_positions.items():
                key = k if k.startswith("right_") else f"right_{k}"
                combined_positions[key] = v

        return self.set_arm_position(combined_positions)

    def mirror_arm_position(self, source_arm: str = "left") -> Dict[str, Any]:
        """镜像复制一只手臂的位置到另一只手臂（XLeRobot 专用）

        Args:
            source_arm: 源手臂 - "left" 或 "right"
        """
        if not self.config.is_xlerobot():
            return {
                "success": False,
                "message": "当前机器人不是 XLeRobot 双臂机器人"
            }

        with self._lock:
            if source_arm == "left":
                source_joints = XLEROBOT_LEFT_ARM_JOINTS
                target_prefix = "right_"
            else:
                source_joints = XLEROBOT_RIGHT_ARM_JOINTS
                target_prefix = "left_"

            mirror_positions = {}
            for joint in source_joints:
                if joint in self.current_action:
                    # 提取关节名（去掉 left_/right_ 前缀）
                    joint_name = joint.replace("left_", "").replace("right_", "")
                    target_key = f"{target_prefix}{joint_name}"
                    mirror_positions[target_key] = self.current_action[joint]

        return self.set_arm_position(mirror_positions)
    
    def _control_loop(self):
        """机器人控制主循环"""
        logger.info("机器人控制循环已启动")
        
        while self.running and self.is_connected():
            try:
                loop_start_time = time.time()
                
                if (time.time() - self.last_command_time) > self.config.command_timeout_s:
                    with self._lock:
                        self.current_action.update({
                            "x.vel": 0.0,
                            "y.vel": 0.0,
                            "theta.vel": 0.0
                        })

                with self._lock:
                    action_to_send = self.current_action.copy()
                
                self.robot.send_action(action_to_send)
                
                elapsed = time.time() - loop_start_time
                sleep_time = max(1.0 / self.config.max_loop_freq_hz - elapsed, 0)
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"控制循环错误: {e}")
                time.sleep(0.1)

        logger.info("机器人控制循环已停止")


# 全局服务实例
_global_service: Optional[RobotService] = None
_service_lock = threading.Lock()


def get_global_service() -> Optional[RobotService]:
    """获取全局服务实例"""
    global _global_service
    with _service_lock:
        return _global_service


def set_global_service(service: RobotService):
    """设置全局服务实例"""
    global _global_service
    with _service_lock:
        _global_service = service


def create_default_service(
    robot_id: str = "moyu_robot",
    robot_type: str = "lekiwi"
) -> RobotService:
    """创建默认配置的服务实例

    Args:
        robot_id: 机器人 ID
        robot_type: 机器人类型 - "lekiwi"（单臂）或 "xlerobot"（双臂）
    """
    config = RobotServiceConfig(
        robot_id=robot_id,
        robot_type=robot_type,
        linear_speed=0.2,
        angular_speed=30.0,
        arm_servo_speed=0.2,
        command_timeout_s=6,
        max_loop_freq_hz=30
    )
    return RobotService(config)

