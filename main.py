"""
FastAPI Main Application (ASGI)
================================
Framework: FastAPI (Asynchronous Server Gateway Interface)
Real-time Communication: WebSocket + HTTP/REST API
Architecture: Asyncio + Multiprocessing

Workflow:
  1. ESP32-CAM gửi ảnh qua WebSocket
  2. FastAPI nhận ảnh (non-blocking, async)
  3. Buffer 5 ảnh -> Submit vào Multiprocessing Queue
  4. PRIMARY process: Phân loại 38 loại rác (YOLO1)
  5. SECONDARY process: Xác nhận có nước/không nước (YOLO2)
  6. FastAPI nhận kết quả từ result_queue
  7. Gửi kết quả về ESP32 (JSON: 1-5 code)
  8. Lưu vào database SQLite
"""

import os
import sys
import asyncio
import base64
import json
import cv2
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import *
from models import TrashRecord, init_db, get_session_factory
from services.processor import start_orchestrator, stop_orchestrator, get_orchestrator
from repositories.trash_repository import TrashRepository
from sqlalchemy.orm import Session

# ==================== LIFESPAN & INITIALIZATION ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan context manager - Startup & Shutdown"""
    
    # ===== STARTUP =====
    print("\n" + "="*80)
    print("🗑️  TRASH CLASSIFICATION - FastAPI + Multiprocessing System")
    print("="*80)
    
    # Initialize database
    print("\n[🔧 STARTUP] Khởi tạo Database...")
    try:
        init_db(SQLALCHEMY_DATABASE_URI)
        app.session_factory = get_session_factory(SQLALCHEMY_DATABASE_URI)
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database init error: {e}")
    
    # Start multiprocessing orchestrator
    print("\n[🔧 STARTUP] Khởi động Multiprocessing Orchestrator...")
    try:
        start_orchestrator()
        print("✅ Multiprocessing orchestrator started")
    except Exception as e:
        print(f"❌ Orchestrator start error: {e}")
    
    # Start background batch processor
    print("\n[🔧 STARTUP] Khởi động Background Batch Processor...")
    try:
        asyncio.create_task(process_batches_background())
        print("✅ Background batch processor started")
    except Exception as e:
        print(f"❌ Background processor error: {e}")
    
    print("\n" + "="*80)
    print("✅ SERVER READY!")
    print(f"📌 WebSocket: ws://localhost:{PORT}/ws")
    print(f"📌 API: http://localhost:{PORT}/api")
    print(f"📌 Dashboard: http://localhost:{PORT}/")
    print("="*80 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    print("\n" + "="*80)
    print("🛑 SERVER SHUTTING DOWN...")
    print("="*80)
    
    try:
        stop_orchestrator()
        print("✅ Multiprocessing orchestrator stopped")
    except Exception as e:
        print(f"⚠️  Error stopping orchestrator: {e}")
    
    print("✅ Goodbye!\n")


# ==================== FASTAPI APP INITIALIZATION ====================

app = FastAPI(
    title="🗑️  Trash Classification System",
    description="Real-time Trash Classification with FastAPI + Multiprocessing",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup Jinja2 templates with absolute path
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)

# Database session factory
app.session_factory = None

# ==================== REQUEST/RESPONSE MODELS ====================

class ImageData(BaseModel):
    """Base64 encoded image"""
    data: str
    weight_grams: Optional[float] = 50.0  # Default weight if not provided

class StatsResponse(BaseModel):
    """Statistics response"""
    total_records: int
    total_by_label: Dict[str, int]
    average_confidence: float
    recent_24h: int
    
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    orchestrator_status: Dict
    total_records: int

# ==================== GLOBAL STATE ====================

class ImageBuffer:
    """Buffer untuk 5 ảnh trước submit ke processing"""
    def __init__(self, buffer_size: int = BUFFER_SIZE):
        self.buffer_size = buffer_size
        self.images = []
        self.weights = []
        self.batch_id = 0
        self.lock = asyncio.Lock()
    
    async def add_image(self, image: np.ndarray, weight: float = 50.0):
        """Thêm ảnh vào buffer"""
        async with self.lock:
            self.images.append(image)
            self.weights.append(weight)
            current_count = len(self.images)
            return current_count
    
    async def is_full(self) -> bool:
        """Kiểm tra buffer đã fullchưa"""
        async with self.lock:
            return len(self.images) >= self.buffer_size
    
    async def get_and_clear(self) -> tuple:
        """Lấy buffer và clear"""
        async with self.lock:
            self.batch_id += 1
            batch_id = self.batch_id
            images = self.images.copy()
            weights = self.weights.copy()
            self.images = []
            self.weights = []
            return batch_id, images, weights

image_buffer = ImageBuffer()

# ==================== WEBSOCKET MANAGER ====================

class WebSocketConnectionManager:
    """Quản lý WebSocket connections"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Khi client kết nối"""
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
        print(f"✓ Client connected (total: {len(self.active_connections)})")
    
    async def disconnect(self, websocket: WebSocket):
        """Khi client ngắt kết nối"""
        async with self.lock:
            self.active_connections.remove(websocket)
        print(f"✗ Client disconnected (total: {len(self.active_connections)})")
    
    async def broadcast(self, message: dict):
        """Gửi message tới tất cả clients"""
        async with self.lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"❌ Broadcast error: {e}")

manager = WebSocketConnectionManager()

# ==================== BACKGROUND TASKS ====================

async def process_batches_background():
    """
    Task chạy ở background để poll result_queue từ multiprocessing
    Khi có kết quả từ SECONDARY process, gửi về tất cả connected clients
    """
    orchestrator = get_orchestrator()
    
    while True:
        try:
            # Poll result_queue (non-blocking, timeout 1 giây)
            result = orchestrator.get_result(timeout=1)
            
            if result:
                print(f"\n[📡 BACKGROUND] Nhận kết quả batch #{result['batch_id']}")
                
                # Parse results
                batch_id = result['batch_id']
                results = result['results']
                
                # Prepare response để gửi về ESP32
                # Mã từ 1-5 tùy theo loại rác và trạng thái nước
                response_data = {
                    'batch_id': batch_id,
                    'results': []
                }
                
                # Save to database + prepare response
                try:
                    session = app.session_factory()
                    
                    for idx, res in enumerate(results):
                        label = res['label']
                        confidence = res['confidence']
                        has_liquid = res['has_liquid']
                        liquid_conf = res['liquid_confidence']
                        weight_grams = res['weight_grams']
                        
                        # Xác định mã output (1-5) dựa trên kết quả
                        output_code = determine_output_code(label, has_liquid, weight_grams)
                        
                        # Save to database
                        try:
                            record = TrashRepository.create_record(
                                db_session=session,
                                image_path=f"batch_{batch_id}_image_{idx}.jpg",
                                label=label,
                                confidence=confidence,
                                has_liquid=has_liquid,
                                weight_grams=weight_grams,
                                individual_confidences=json.dumps({
                                    'primary_conf': confidence,
                                    'liquid_conf': liquid_conf
                                }),
                                primary_model_output=label,
                                secondary_model_output=f"liquid={has_liquid}"
                            )
                            print(f"[💾 DB] Saved record #{record.id}: {label} (has_liquid={has_liquid})")
                        except Exception as db_err:
                            print(f"[❌ DB] Error saving record: {db_err}")
                        
                        # Add to response
                        response_data['results'].append({
                            'image_idx': idx,
                            'label': label,
                            'confidence': f"{confidence:.2%}",
                            'has_liquid': has_liquid,
                            'weight_grams': weight_grams,
                            'output_code': output_code  # 1-5 code cho ESP32
                        })
                    
                    session.close()
                
                except Exception as e:
                    print(f"[❌ ERROR] Error processing results: {e}")
                
                # Broadcast to all connected clients
                await manager.broadcast({
                    'type': 'classification_result',
                    'data': response_data
                })
                
                print(f"[📡 BROADCAST] Gửi kết quả tới {len(manager.active_connections)} clients")
        
        except Exception as e:
            print(f"[❌ BACKGROUND] Error in process_batches: {e}")
        
        # Giữ task chạy continuous
        await asyncio.sleep(0.1)

# ==================== HELPER FUNCTIONS ====================

def determine_output_code(label: str, has_liquid: str, weight_grams: Optional[float]) -> int:
    """
    Xác định mã output (1-5) dựa trên kết quả phân loại
    
    Mã:
      1: Có nước (liquid)
      2: Không có nước (no liquid)
      3: Không rõ (unknown/error)
      4: Loại rác khác (other)
      5: Không phát hiện (no detection)
    
    Args:
        label: Label từ YOLO1
        has_liquid: 'yes', 'no', hoặc 'unknown'
        weight_grams: Trọng lượng
    
    Returns:
        Mã output (1-5)
    """
    
    if label == 'no_detection':
        return 5  # No detection
    
    if label == 'error':
        return 3  # Error
    
    # Nếu có nước
    if has_liquid == 'yes':
        return 1  # Has liquid
    
    # Nếu không nước
    if has_liquid == 'no':
        return 2  # No liquid
    
    # Nếu unknown hoặc loại rác khác
    if 'plastic' in label.lower() or 'bottle' in label.lower():
        return 2  # Assume no liquid for non-liquid containers
    
    return 4  # Other

def decode_image_from_base64(base64_str: str) -> Optional[np.ndarray]:
    """Decode base64 string to OpenCV image"""
    try:
        image_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"❌ Image decode error: {e}")
        return None

# ==================== HTTP ROUTES ====================

@app.get("/")
async def dashboard():
    """Dashboard - Serve index.html"""
    try:
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return JSONResponse(
            {"error": str(e), "type": type(e).__name__},
            status_code=500
        )

@app.get("/history")
async def history_page():
    """History Page - Serve history.html"""
    try:
        history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "history.html")
        with open(history_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    except Exception as e:
        print(f"❌ History page error: {e}")
        return JSONResponse(
            {"error": str(e), "type": type(e).__name__},
            status_code=500
        )

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics"""
    try:
        session = app.session_factory()
        
        total = session.query(TrashRecord).count()
        
        # Count by label
        from sqlalchemy import func
        label_counts = session.query(
            TrashRecord.label,
            func.count(TrashRecord.id).label('count')
        ).group_by(TrashRecord.label).all()
        
        total_by_label = {label: count for label, count in label_counts}
        
        # Average confidence
        avg_conf_result = session.query(func.avg(TrashRecord.confidence)).scalar()
        avg_conf = float(avg_conf_result) if avg_conf_result else 0.0
        
        # Recent 24h
        from datetime import timedelta
        time_24h = datetime.utcnow() - timedelta(hours=24)
        recent_24h = session.query(TrashRecord).filter(
            TrashRecord.timestamp >= time_24h
        ).count()
        
        session.close()
        
        return StatsResponse(
            total_records=total,
            total_by_label=total_by_label,
            average_confidence=avg_conf,
            recent_24h=recent_24h
        )
    
    except Exception as e:
        print(f"❌ API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    try:
        orchestrator = get_orchestrator()
        stats = orchestrator.get_queue_stats()
        
        session = app.session_factory()
        total = session.query(TrashRecord).count()
        session.close()
        
        return HealthResponse(
            status='healthy',
            timestamp=datetime.utcnow().isoformat(),
            orchestrator_status=stats,
            total_records=total
        )
    
    except Exception as e:
        return HealthResponse(
            status='error',
            timestamp=datetime.utcnow().isoformat(),
            orchestrator_status={},
            total_records=0
        )

@app.get("/api/records")
async def get_records(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    """Get records with pagination"""
    try:
        session = app.session_factory()
        
        skip = (page - 1) * limit
        records = session.query(TrashRecord).order_by(
            TrashRecord.timestamp.desc()
        ).offset(skip).limit(limit).all()
        
        total = session.query(TrashRecord).count()
        
        session.close()
        
        return {
            'records': [r.to_dict() for r in records],
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/image")
async def upload_image(image_data: ImageData):
    """Upload image (HTTP endpoint)"""
    try:
        # Decode image
        image = decode_image_from_base64(image_data.data)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        # Add to buffer
        count = await image_buffer.add_image(image, image_data.weight_grams)
        
        # Check if buffer is full
        if await image_buffer.is_full():
            # Submit batch to processing
            batch_id, images, weights = await image_buffer.get_and_clear()
            
            orchestrator = get_orchestrator()
            result = orchestrator.submit_batch(batch_id, images, weights)
            
            if result != -1:
                return {
                    'status': 'batch_submitted',
                    'batch_id': batch_id,
                    'image_count': len(images)
                }
        
        return {
            'status': 'buffering',
            'buffer_count': count,
            'buffer_size': BUFFER_SIZE
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== WEBSOCKET ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint cho ESP32-CAM
    
    Receive: {
      "type": "image",
      "data": "base64_encoded_image",
      "weight_grams": 50.0
    }
    
    Send: {
      "type": "classification_result",
      "data": {
        "batch_id": 1,
        "results": [
          {
            "output_code": 1,  # 1-5 (1=has liquid, 2=no liquid, etc.)
            "label": "plastic_bottle",
            "has_liquid": "yes"
          }
        ]
      }
    }
    """
    
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message từ client
            message = await websocket.receive_text()
            
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'image':
                    # Receive ảnh
                    base64_image = data.get('data', '')
                    weight_grams = data.get('weight_grams', 50.0)
                    
                    # Decode image
                    image = decode_image_from_base64(base64_image)
                    if image is None:
                        await websocket.send_json({
                            'type': 'error',
                            'message': 'Invalid image'
                        })
                        continue
                    
                    # Add to buffer
                    count = await image_buffer.add_image(image, weight_grams)
                    
                    await websocket.send_json({
                        'type': 'buffer_status',
                        'buffer_count': count,
                        'buffer_size': BUFFER_SIZE
                    })
                    
                    # Check if buffer full
                    if await image_buffer.is_full():
                        batch_id, images, weights = await image_buffer.get_and_clear()
                        
                        orchestrator = get_orchestrator()
                        result = orchestrator.submit_batch(batch_id, images, weights)
                        
                        if result != -1:
                            await websocket.send_json({
                                'type': 'batch_submitted',
                                'batch_id': batch_id,
                                'message': f'Processing {BUFFER_SIZE} images...'
                            })
                
                elif msg_type == 'ping':
                    # Ping-pong để keep connection alive
                    await websocket.send_json({
                        'type': 'pong',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Invalid JSON'
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await manager.disconnect(websocket)

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*80)
    print("🚀 Starting FastAPI Application")
    print("="*80 + "\n")
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level=LOG_LEVEL,
        workers=1  # 1 worker vì Uvicorn sẽ handle async internally
    )
