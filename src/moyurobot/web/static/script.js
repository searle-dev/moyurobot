/**
 * 摸鱼遥控车 - 控制脚本
 * 
 * 支持功能：
 * - 键盘/按钮控制
 * - 手势识别控制
 * - 人脸追踪控制
 */

// ============== 全局变量 ==============
let currentMode = 'gamepad';
let isMoving = false;
let gestureCamera = null;
let faceCamera = null;
let hands = null;

// 键盘映射
const keyMappings = {
    'KeyW': 'forward',
    'ArrowUp': 'forward',
    'KeyS': 'backward',
    'ArrowDown': 'backward',
    'KeyA': 'left',
    'ArrowLeft': 'left',
    'KeyD': 'right',
    'ArrowRight': 'right',
    'KeyQ': 'rotate_left',
    'KeyE': 'rotate_right',
    'Space': 'stop',
};

// ============== 初始化 ==============
document.addEventListener('DOMContentLoaded', () => {
    initModeSelector();
    initDirectionControls();
    initArmControls();
    initSpeedControls();
    initKeyboardControls();
    initLogout();
    checkConnectionStatus();
    
    // 定期检查连接状态
    setInterval(checkConnectionStatus, 5000);
});

// ============== 模式选择 ==============
function initModeSelector() {
    const modeButtons = document.querySelectorAll('.mode-btn');
    const panels = document.querySelectorAll('.control-panel');
    
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            
            // 切换按钮状态
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 切换面板
            panels.forEach(p => p.classList.remove('active'));
            document.getElementById(`${mode}Panel`).classList.add('active');
            
            // 停止之前的模式
            stopCurrentMode();
            
            // 启动新模式
            currentMode = mode;
            if (mode === 'gesture') {
                startGestureControl();
            } else if (mode === 'face') {
                startFaceTracking();
            }
        });
    });
}

function stopCurrentMode() {
    // 停止手势控制
    if (gestureCamera) {
        gestureCamera.stop();
        gestureCamera = null;
    }
    
    // 停止人脸追踪
    if (faceCamera) {
        faceCamera.stop();
        faceCamera = null;
    }
    
    // 发送停止命令
    sendMoveCommand('stop');
}

// ============== 方向控制 ==============
function initDirectionControls() {
    const dirButtons = document.querySelectorAll('.dir-btn, .rotate-btn');
    
    dirButtons.forEach(btn => {
        const direction = btn.dataset.direction;
        
        // 鼠标事件
        btn.addEventListener('mousedown', () => {
            btn.classList.add('active');
            sendMoveCommand(direction);
        });
        
        btn.addEventListener('mouseup', () => {
            btn.classList.remove('active');
            if (direction !== 'stop') {
                sendMoveCommand('stop');
            }
        });
        
        btn.addEventListener('mouseleave', () => {
            btn.classList.remove('active');
        });
        
        // 触摸事件（移动设备）
        btn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            btn.classList.add('active');
            sendMoveCommand(direction);
        });
        
        btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            btn.classList.remove('active');
            if (direction !== 'stop') {
                sendMoveCommand('stop');
            }
        });
    });
}

// ============== 机械臂控制 ==============
function initArmControls() {
    const armButtons = document.querySelectorAll('.arm-btn');
    
    armButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            sendArmCommand(action);
        });
    });
}

// ============== 速度控制 ==============
function initSpeedControls() {
    const speedUp = document.getElementById('speedUp');
    const speedDown = document.getElementById('speedDown');
    
    speedUp.addEventListener('click', () => sendSpeedCommand('increase'));
    speedDown.addEventListener('click', () => sendSpeedCommand('decrease'));
}

// ============== 键盘控制 ==============
function initKeyboardControls() {
    const activeKeys = new Set();
    
    document.addEventListener('keydown', (e) => {
        if (currentMode !== 'gamepad') return;
        if (e.target.tagName === 'INPUT') return;
        
        const direction = keyMappings[e.code];
        if (direction && !activeKeys.has(e.code)) {
            activeKeys.add(e.code);
            sendMoveCommand(direction);
            
            // 高亮对应按钮
            const btn = document.querySelector(`[data-direction="${direction}"]`);
            if (btn) btn.classList.add('active');
        }
        
        // 速度控制
        if (e.code === 'Equal' || e.code === 'NumpadAdd') {
            sendSpeedCommand('increase');
        } else if (e.code === 'Minus' || e.code === 'NumpadSubtract') {
            sendSpeedCommand('decrease');
        }
    });
    
    document.addEventListener('keyup', (e) => {
        if (currentMode !== 'gamepad') return;
        
        const direction = keyMappings[e.code];
        if (direction && activeKeys.has(e.code)) {
            activeKeys.delete(e.code);
            
            // 取消高亮
            const btn = document.querySelector(`[data-direction="${direction}"]`);
            if (btn) btn.classList.remove('active');
            
            // 如果没有其他按键按下，停止移动
            if (activeKeys.size === 0 && direction !== 'stop') {
                sendMoveCommand('stop');
            }
        }
    });
}

// ============== 登出 ==============
function initLogout() {
    document.getElementById('logoutBtn').addEventListener('click', () => {
        window.location.href = '/logout';
    });
}

// ============== API 调用 ==============
async function sendMoveCommand(direction) {
    try {
        const response = await fetch('/api/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction })
        });
        
        const data = await response.json();
        if (data.speed) {
            updateSpeedDisplay(data.speed);
        }
    } catch (error) {
        console.error('移动命令失败:', error);
    }
}

async function sendArmCommand(action) {
    try {
        await fetch('/api/arm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
    } catch (error) {
        console.error('机械臂命令失败:', error);
    }
}

async function sendSpeedCommand(action) {
    try {
        const response = await fetch('/api/speed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        
        const data = await response.json();
        if (data.speed) {
            updateSpeedDisplay(data.speed);
        }
    } catch (error) {
        console.error('速度命令失败:', error);
    }
}

function updateSpeedDisplay(speedName) {
    const speedLevel = document.getElementById('speedLevel');
    speedLevel.textContent = `速度: ${speedName}`;
}

// ============== 连接状态 ==============
async function checkConnectionStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        const statusEl = document.getElementById('connectionStatus');
        if (data.connected) {
            statusEl.textContent = '● 已连接';
            statusEl.className = 'status connected';
        } else {
            statusEl.textContent = '● 未连接';
            statusEl.className = 'status disconnected';
        }
    } catch (error) {
        const statusEl = document.getElementById('connectionStatus');
        statusEl.textContent = '● 连接错误';
        statusEl.className = 'status disconnected';
    }
}

// ============== 手势控制 ==============
async function startGestureControl() {
    const videoElement = document.getElementById('gestureVideo');
    const canvasElement = document.getElementById('gestureCanvas');
    const canvasCtx = canvasElement.getContext('2d');
    const resultElement = document.getElementById('gestureResult');
    
    // 初始化 MediaPipe Hands
    hands = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
    });
    
    hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
    });
    
    hands.onResults((results) => {
        // 绘制手势
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        
        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            const landmarks = results.multiHandLandmarks[0];
            
            // 绘制手部关键点
            drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, {
                color: '#00FF00',
                lineWidth: 2
            });
            drawLandmarks(canvasCtx, landmarks, {
                color: '#FF0000',
                lineWidth: 1,
                radius: 3
            });
            
            // 识别手势
            const gesture = recognizeGesture(landmarks);
            updateGestureResult(resultElement, gesture);
            
            // 发送手势命令
            sendGestureCommand(gesture, landmarks);
        } else {
            resultElement.querySelector('.gesture-icon').textContent = '✋';
            resultElement.querySelector('.gesture-text').textContent = '等待手势...';
        }
        
        canvasCtx.restore();
    });
    
    // 启动摄像头
    try {
        gestureCamera = new Camera(videoElement, {
            onFrame: async () => {
                canvasElement.width = videoElement.videoWidth;
                canvasElement.height = videoElement.videoHeight;
                await hands.send({ image: videoElement });
            },
            width: 640,
            height: 480
        });
        await gestureCamera.start();
    } catch (error) {
        console.error('摄像头启动失败:', error);
        resultElement.querySelector('.gesture-text').textContent = '摄像头启动失败';
    }
}

function recognizeGesture(landmarks) {
    // 手指伸展检测
    const fingers = {
        thumb: landmarks[4].y < landmarks[3].y,
        index: landmarks[8].y < landmarks[6].y,
        middle: landmarks[12].y < landmarks[10].y,
        ring: landmarks[16].y < landmarks[14].y,
        pinky: landmarks[20].y < landmarks[18].y
    };
    
    const extendedCount = Object.values(fingers).filter(Boolean).length;
    
    // 手势识别
    if (extendedCount === 5) {
        return 'open_palm';  // 张开手掌
    } else if (extendedCount === 0) {
        return 'fist';  // 握拳
    } else if (fingers.index && !fingers.middle && !fingers.ring && !fingers.pinky) {
        return 'pointing_up';  // 竖起食指
    } else if (fingers.thumb && !fingers.index && !fingers.middle && !fingers.ring && !fingers.pinky) {
        return 'thumbs_up';  // 竖起大拇指
    }
    
    return 'unknown';
}

function updateGestureResult(element, gesture) {
    const gestureInfo = {
        'open_palm': { icon: '✋', text: '张开手掌 - 停止' },
        'fist': { icon: '✊', text: '握拳 - 关闭夹爪' },
        'pointing_up': { icon: '☝️', text: '竖起食指 - 前进' },
        'thumbs_up': { icon: '👍', text: '竖起大拇指 - 打开夹爪' },
        'unknown': { icon: '❓', text: '未识别手势' }
    };
    
    const info = gestureInfo[gesture] || gestureInfo['unknown'];
    element.querySelector('.gesture-icon').textContent = info.icon;
    element.querySelector('.gesture-text').textContent = info.text;
}

let lastGesture = null;
let gestureDebounce = null;

async function sendGestureCommand(gesture, landmarks) {
    // 防抖处理
    if (gesture === lastGesture) return;
    
    if (gestureDebounce) {
        clearTimeout(gestureDebounce);
    }
    
    gestureDebounce = setTimeout(async () => {
        lastGesture = gesture;
        
        try {
            await fetch('/api/gesture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gesture, landmarks })
            });
        } catch (error) {
            console.error('手势命令失败:', error);
        }
    }, 200);
}

// ============== 人脸追踪 ==============
async function startFaceTracking() {
    const videoElement = document.getElementById('faceVideo');
    const canvasElement = document.getElementById('faceCanvas');
    const canvasCtx = canvasElement.getContext('2d');
    const resultElement = document.getElementById('faceResult');
    
    // 使用简单的人脸检测 (基于浏览器 API)
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 }
        });
        
        videoElement.srcObject = stream;
        faceCamera = {
            stop: () => {
                stream.getTracks().forEach(track => track.stop());
            }
        };
        
        // 简单的颜色追踪模拟人脸追踪
        const detectFace = () => {
            if (!faceCamera) return;
            
            canvasElement.width = videoElement.videoWidth || 640;
            canvasElement.height = videoElement.videoHeight || 480;
            
            canvasCtx.drawImage(videoElement, 0, 0);
            
            // 这里可以添加更复杂的人脸检测逻辑
            // 目前使用中心点作为示例
            const centerX = 0.5;
            const centerY = 0.5;
            
            // 绘制追踪框
            canvasCtx.strokeStyle = '#00FF00';
            canvasCtx.lineWidth = 3;
            const boxSize = 150;
            canvasCtx.strokeRect(
                (canvasElement.width - boxSize) / 2,
                (canvasElement.height - boxSize) / 2,
                boxSize,
                boxSize
            );
            
            resultElement.querySelector('.face-text').textContent = '人脸追踪中...';
            
            // 发送追踪命令
            sendFaceTrackCommand(centerX, centerY);
            
            requestAnimationFrame(detectFace);
        };
        
        videoElement.onloadedmetadata = () => {
            detectFace();
        };
        
    } catch (error) {
        console.error('摄像头启动失败:', error);
        resultElement.querySelector('.face-text').textContent = '摄像头启动失败';
    }
}

let faceTrackDebounce = null;

async function sendFaceTrackCommand(centerX, centerY) {
    if (faceTrackDebounce) return;
    
    faceTrackDebounce = setTimeout(async () => {
        faceTrackDebounce = null;
        
        try {
            await fetch('/api/face_track', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    center: { x: centerX, y: centerY },
                    frame_size: { width: 640, height: 480 }
                })
            });
        } catch (error) {
            console.error('人脸追踪命令失败:', error);
        }
    }, 100);
}

