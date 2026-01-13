from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import base64
import eventlet
from meter_detector import MeterDetector
from config import Config

eventlet.monkey_patch()

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化检测器
detector = MeterDetector()

# 模拟视频源（实际项目中替换为真实摄像头）
class VideoSimulator:
    def __init__(self):
        self.frame_count = 0
        
    def get_frame(self):
        """生成模拟仪表图像"""
        # 创建空白图像
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame.fill(240)  # 浅灰色背景
        
        # 绘制模拟仪表
        for i in range(2):
            center_x = 200 + i * 250
            center_y = 240
            radius = 100
            
            # 绘制仪表外圈
            cv2.circle(frame, (center_x, center_y), radius, (0, 0, 0), 3)
            
            # 绘制刻度
            for angle in range(0, 270, 30):
                rad = np.deg2rad(angle - 45)  # 从-45°开始
                x1 = int(center_x + (radius - 10) * np.cos(rad))
                y1 = int(center_y + (radius - 10) * np.sin(rad))
                x2 = int(center_x + radius * np.cos(rad))
                y2 = int(center_y + radius * np.sin(rad))
                cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 0), 2)
            
            # 绘制模拟指针（角度会变化）
            pointer_angle = (self.frame_count * 2 + i * 120) % 270 - 45
            rad = np.deg2rad(pointer_angle)
            x_end = int(center_x + (radius - 20) * np.cos(rad))
            y_end = int(center_y + (radius - 20) * np.sin(rad))
            cv2.line(frame, (center_x, center_y), (x_end, y_end), (0, 0, 255), 3)
            
            # 绘制仪表中心
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # 添加仪表标签
            cv2.putText(frame, f"Meter-{i+1}", 
                       (center_x - 40, center_y + radius + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        self.frame_count += 1
        return frame

video_sim = VideoSimulator()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    return jsonify({
        "status": "running",
        "version": "1.0",
        "meters_detected": 2,
        "processing_fps": 5,
        "last_update": "2024-01-01 12:00:00"
    })

@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    print('客户端已连接')
    emit('connection_response', {'data': 'Connected to meter reading system'})

@socketio.on('start_monitoring')
def handle_start_monitoring():
    """开始监控"""
    print('开始监控仪表...')
    
    while True:
        try:
            # 获取模拟帧
            frame = video_sim.get_frame()
            
            # 处理帧数据
            result = detector.process_frame(frame)
            
            # 添加时间戳
            import datetime
            result['timestamp'] = datetime.datetime.now().strftime("%H:%M:%S")
            
            # 转换为base64用于前端显示
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            result['frame'] = frame_base64
            
            # 发送到前端
            socketio.emit('meter_data', result)
            
            # 控制发送频率（约5FPS）
            socketio.sleep(0.2)
            
        except Exception as e:
            print(f"处理错误: {e}")
            break

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    print('客户端已断开连接')

if __name__ == '__main__':
    print("🏭 工业仪表读数系统启动")
    print("📡 WebSocket服务运行中...")
    print("🌐 请访问 http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
