"""
Configuration - Cấu hình ứng dụng (FastAPI + Multiprocessing)
Tập hợp tất cả các settings cho development và production
"""

import os

# Project root directory
basedir = os.path.abspath(os.path.dirname(__file__))

# ==================== SERVER ====================
HOST = '0.0.0.0'
PORT = 8000
RELOAD = False
LOG_LEVEL = 'info'

# ==================== DATABASE ====================
SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "database", "trash_classification.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False

# ==================== UPLOADS ====================
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# ==================== AI/ML ====================
MODEL_PATH = os.path.join(basedir, 'best.pt')
MODEL_SECONDARY_PATH = os.path.join(basedir, 'best2.pt')  # YOLO2 model
BUFFER_SIZE = 5  # Nhận 5 ảnh trước khi inference

# ==================== MULTIPROCESSING ====================
# Tiến trình chính (Primary Classification) - YOLO1: 38 loại rác
PRIMARY_PROCESS_WORKERS = 2  # Số workers cho tiến trình chính

# Tiến trình phụ (Secondary Verification) - YOLO2: Kiểm tra nước
SECONDARY_PROCESS_WORKERS = 1  # Số workers cho tiến trình phụ

# Queue settings
QUEUE_TIMEOUT = 5  # Timeout khi lấy dữ liệu từ queue (seconds)
MAX_QUEUE_SIZE = 100  # Tối đa bao nhiêu items trong queue

# Weight threshold (grams) - Dùng để kiểm tra có nước
WEIGHT_THRESHOLD = {
    'bottle': 50,  # Chai nhựa: nếu > 50g thì có nước
    'can': 30,     # Lon: nếu > 30g thì có nước
    'glass': 100,  # Thủy tinh: nếu > 100g thì có nước
    'default': 50  # Mặc định cho các loại khác
}

# ==================== FASTAPI ====================
SECRET_KEY = 'trash-classification-secret-2024'  # Thay đổi trong production
DEBUG = False
TESTING = False

# CORS settings
CORS_ORIGINS = ["*"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# ==================== WEBSOCKET ====================
WEBSOCKET_RECONNECT_INTERVAL = 5
WEBSOCKET_MAX_CONNECTIONS = 10
WEBSOCKET_PING_INTERVAL = 30

# ==================== DIRECTORIES ====================
# Create directories if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)
os.makedirs(os.path.join(basedir, 'logs'), exist_ok=True)

# ==================== PERFORMANCE - YOLO1 (Primary) ====================
YOLO1_CONF = 0.4  # Confidence threshold (0-1)
YOLO1_IMGSZ = 416  # Input image size
YOLO1_DEVICE = 'cpu'  # 'cpu' hoặc 'cuda' (nếu GPU available)

# ==================== PERFORMANCE - YOLO2 (Secondary) ====================
YOLO2_CONF = 0.5  # Confidence threshold cao hơn vì chỉ kiểm tra nước
YOLO2_IMGSZ = 320  # Lightweight - size nhỏ hơn
YOLO2_DEVICE = 'cpu'  # 'cpu' hoặc 'cuda'

# Image compression
COMPOSITE_SIZE = (600, 400)  # Width x Height
COMPOSITE_QUALITY = 85  # JPEG quality (0-100)

# Database optimization
DB_POOL_SIZE = 10
DB_POOL_RECYCLE = 3600  # Recycle connections after 1 hour

# ==================== FEATURES ====================
ENABLE_AUTO_CLEANUP = True  # Auto delete old records
CLEANUP_DAYS = 30  # Delete records older than 30 days
CLEANUP_INTERVAL = 86400  # Check every 24 hours

# ==================== LOGGING ====================
LOG_FILE = os.path.join(basedir, 'logs', 'app.log')
