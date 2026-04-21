"""
Processor - Multiprocessing Architecture (PRIMARY & SECONDARY)
================================================================================
Tiến trình 1 (PRIMARY): Chạy YOLO1 để phân loại 38 loại rác
Tiến trình 2 (SECONDARY): Chạy YOLO2 để xác nhận có nước/không nước

Giao thức giao tiếp:
  PRIMARY -> Queue (intermediate) -> SECONDARY
  
Cơ chế kết hợp (2 tiến trình hoạt động song song):
  1. Có chất lỏng + trọng lượng > ngưỡng => Có nước
  2. Không chất lỏng + trọng lượng <= ngưỡng => Không nước
  3. Model báo không nước nhưng trọng lượng > ngưỡng => Có nước (do nước đầy chai)
  4. Model báo có chất lỏng nhưng trọng lượng < ngưỡng => Có nước (ngưỡng quá cao)
================================================================================
"""

import os
import sys
import json
import multiprocessing as mp
import queue
import time
import numpy as np
import cv2
from typing import Dict, Tuple, Optional
from datetime import datetime

# Thêm project directory vào path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MODEL_PATH, MODEL_SECONDARY_PATH, QUEUE_TIMEOUT, MAX_QUEUE_SIZE,
    WEIGHT_THRESHOLD, YOLO1_CONF, YOLO1_IMGSZ, YOLO1_DEVICE,
    YOLO2_CONF, YOLO2_IMGSZ, YOLO2_DEVICE, UPLOAD_FOLDER, BUFFER_SIZE
)


class PrimaryProcessor(mp.Process):
    """
    Tiến trình 1 (PRIMARY CLASSIFICATION)
    ========================================
    Chuyên trách: Phân loại 38 loại rác thải
    
    Input: Nhận ảnh từ main process qua queue
    Output: Gửi kết quả (label, bounding_box) qua intermediate_queue
    
    Hoạt động:
    - Load YOLO1 model (best.pt)
    - Loop: Lấy ảnh từ input_queue -> Inference -> Gửi vào intermediate_queue
    - Nếu label là "Chai nhựa"/"Lon"/v.v. -> Gửi crop image vào secondary_queue
    """
    
    def __init__(self, input_queue: mp.Queue, intermediate_queue: mp.Queue, 
                 shutdown_event: mp.Event, worker_id: int = 0):
        super().__init__()
        self.daemon = False
        self.input_queue = input_queue
        self.intermediate_queue = intermediate_queue
        self.shutdown_event = shutdown_event
        self.worker_id = worker_id
        self.yolo_model = None
        self.labels_map = self._init_labels_map()
    
    def _init_labels_map(self) -> Dict[int, str]:
        """38 loại rác thải (dùng để map class_id -> label)"""
        return {
            0: 'plastic_bottle', 1: 'plastic_bag', 2: 'plastic_cup',
            3: 'plastic_container', 4: 'paper_box', 5: 'paper_sheet',
            6: 'cardboard', 7: 'newspaper', 8: 'aluminum_can',
            9: 'steel_can', 10: 'glass_bottle', 11: 'glass_jar',
            12: 'metal_can', 13: 'metal_wire', 14: 'textile_cloth',
            15: 'textile_bag', 16: 'wood_piece', 17: 'wood_board',
            18: 'ceramic_cup', 19: 'ceramic_plate', 20: 'leather_shoe',
            21: 'leather_bag', 22: 'rubber_tire', 23: 'rubber_ball',
            24: 'food_waste', 25: 'food_bottle', 26: 'organic_material',
            27: 'electronic_device', 28: 'battery', 29: 'lightbulb',
            30: 'metal_scrap', 31: 'plastic_film', 32: 'foam_material',
            33: 'composite_material', 34: 'mixed_waste', 35: 'hazardous',
            36: 'unknown', 37: 'misc'
        }
    
    def load_model(self):
        """Load YOLO1 model"""
        try:
            if os.path.exists(MODEL_PATH):
                from ultralytics import YOLO
                self.yolo_model = YOLO(MODEL_PATH)
                print(f"[PRIMARY-{self.worker_id}] ✓ YOLO1 model loaded: {MODEL_PATH}")
                return True
            else:
                print(f"[PRIMARY-{self.worker_id}] ⚠ best.pt not found. Using dummy mode.")
                return False
        except Exception as e:
            print(f"[PRIMARY-{self.worker_id}] ✗ Error loading YOLO1: {e}")
            return False
    
    def perform_inference(self, image: np.ndarray) -> Tuple[str, float, Optional[np.ndarray]]:
        """
        Thực hiện YOLO1 inference
        
        Args:
            image: OpenCV image (numpy array)
            
        Returns:
            Tuple: (label, confidence, crop_image_for_secondary)
        """
        try:
            if self.yolo_model is None:
                # Dummy mode
                dummy_labels = list(self.labels_map.values())[:5]
                return (
                    np.random.choice(dummy_labels),
                    float(np.random.uniform(0.7, 0.99)),
                    image  # Gửi toàn bộ ảnh vào secondary
                )
            
            # Real YOLO1 inference
            results = self.yolo_model(
                image, 
                conf=YOLO1_CONF, 
                imgsz=YOLO1_IMGSZ, 
                verbose=False,
                device=YOLO1_DEVICE
            )
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None and len(result.boxes) > 0:
                    # Lấy detection với confidence cao nhất
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    boxes = result.boxes.xyxy.cpu().numpy().astype(int)
                    
                    max_idx = np.argmax(confidences)
                    confidence = float(confidences[max_idx])
                    class_id = int(class_ids[max_idx])
                    box = boxes[max_idx]
                    
                    # Map class_id to label
                    label = self.labels_map.get(class_id, f'unknown_{class_id}')
                    
                    # Crop ảnh vùng detected để gửi cho SECONDARY
                    x1, y1, x2, y2 = box
                    crop_image = image[max(0, y1):min(image.shape[0], y2), 
                                      max(0, x1):min(image.shape[1], x2)]
                    
                    return label, confidence, crop_image
            
            return 'no_detection', 0.0, image
        
        except Exception as e:
            print(f"[PRIMARY-{self.worker_id}] ✗ Inference error: {e}")
            return 'error', 0.0, image
    
    def run(self):
        """Main loop của PRIMARY process"""
        print(f"\n[PRIMARY-{self.worker_id}] Khởi động tiến trình Primary Classification")
        
        # Load model
        if not self.load_model():
            print(f"[PRIMARY-{self.worker_id}] ✗ Không thể load model. Dừng tiến trình.")
            return
        
        print(f"[PRIMARY-{self.worker_id}] ✓ Sẵn sàng xử lý ảnh")
        
        while not self.shutdown_event.is_set():
            try:
                # Lấy ảnh từ input queue (timeout để check shutdown)
                try:
                    item = self.input_queue.get(timeout=1)
                    
                    if item is None:  # Shutdown signal
                        break
                    
                    batch_id, images, weights = item
                    
                    print(f"[PRIMARY-{self.worker_id}] 📸 Nhận batch #{batch_id} ({len(images)} ảnh)")
                    
                    # Xử lý từng ảnh
                    results = []
                    for idx, (image, weight) in enumerate(zip(images, weights)):
                        label, confidence, crop_image = self.perform_inference(image)
                        
                        result = {
                            'batch_id': batch_id,
                            'image_idx': idx,
                            'label': label,
                            'confidence': confidence,
                            'crop_image': crop_image,
                            'weight_grams': weight,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        results.append(result)
                        
                        print(f"[PRIMARY-{self.worker_id}]   [{idx+1}/{len(images)}] {label} (conf={confidence:.2%})")
                    
                    # Gửi kết quả vào intermediate queue
                    self.intermediate_queue.put(('primary_result', batch_id, results))
                    print(f"[PRIMARY-{self.worker_id}] ✓ Batch #{batch_id} hoàn thành -> Intermediate Queue")
                
                except queue.Empty:
                    # Timeout, tiếp tục chờ
                    continue
                except Exception as e:
                    print(f"[PRIMARY-{self.worker_id}] ✗ Error processing batch: {e}")
                    continue
            
            except KeyboardInterrupt:
                print(f"[PRIMARY-{self.worker_id}] ⛔ Received interrupt signal")
                break
        
        print(f"[PRIMARY-{self.worker_id}] 🛑 Tiến trình PRIMARY dừng")


class SecondaryProcessor(mp.Process):
    """
    Tiến trình 2 (SECONDARY VERIFICATION)
    ========================================
    Chuyên trách: Xác nhận có nước / không nước bên trong chai/bình
    
    Input: Nhận crop image từ intermediate_queue (kết quả từ PRIMARY)
    Output: Gửi kết quả final (label, confidence, has_liquid) qua result_queue
    
    Hoạt động:
    - Load YOLO2 model (lightweight - best_secondary.pt)
    - Loop: Lấy crop từ intermediate_queue -> Inference nước -> Gửi vào result_queue
    - Kết hợp với weight_grams để xác định: CÓ NƯỚC hay KHÔNG NƯỚC
    
    Logic kết hợp 4 trường hợp:
      1. Model báo CÓ + weight > ngưỡng => CÓ NƯỚC ✓
      2. Model báo KHÔNG + weight <= ngưỡng => KHÔNG NƯỚC ✓
      3. Model báo KHÔNG + weight > ngưỡng => CÓ NƯỚC (nước đầy chai, che nhãn)
      4. Model báo CÓ + weight < ngưỡng => CÓ NƯỚC (ngưỡng quá cao)
    """
    
    def __init__(self, intermediate_queue: mp.Queue, result_queue: mp.Queue,
                 shutdown_event: mp.Event, worker_id: int = 0):
        super().__init__()
        self.daemon = False
        self.intermediate_queue = intermediate_queue
        self.result_queue = result_queue
        self.shutdown_event = shutdown_event
        self.worker_id = worker_id
        self.yolo_model = None
    
    def load_model(self):
        """Load YOLO2 model"""
        try:
            if os.path.exists(MODEL_SECONDARY_PATH):
                from ultralytics import YOLO
                self.yolo_model = YOLO(MODEL_SECONDARY_PATH)
                print(f"[SECONDARY-{self.worker_id}] ✓ YOLO2 model loaded: {MODEL_SECONDARY_PATH}")
                return True
            else:
                print(f"[SECONDARY-{self.worker_id}] ⚠ best_secondary.pt not found. Using dummy mode.")
                return False
        except Exception as e:
            print(f"[SECONDARY-{self.worker_id}] ✗ Error loading YOLO2: {e}")
            return False
    
    def detect_liquid(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Phát hiện có chất lỏng trong ảnh crop
        
        Args:
            image: Crop image từ PRIMARY
            
        Returns:
            Tuple: (has_liquid: bool, confidence: float)
        """
        try:
            if self.yolo_model is None:
                # Dummy mode
                has_liquid = bool(np.random.rand() > 0.5)
                return has_liquid, float(np.random.uniform(0.6, 0.95))
            
            # Real YOLO2 inference
            results = self.yolo_model(
                image,
                conf=YOLO2_CONF,
                imgsz=YOLO2_IMGSZ,
                verbose=False,
                device=YOLO2_DEVICE
            )
            
            if results and len(results) > 0:
                result = results[0]
                
                # Nếu detect được liquid class
                if result.boxes is not None and len(result.boxes) > 0:
                    has_liquid = True
                    confidence = float(result.boxes.conf.cpu().numpy().max())
                    return has_liquid, confidence
            
            return False, 0.0
        
        except Exception as e:
            print(f"[SECONDARY-{self.worker_id}] ✗ Liquid detection error: {e}")
            return False, 0.0
    
    def determine_has_liquid(self, model_detected: bool, model_conf: float, 
                           label: str, weight_grams: Optional[float]) -> Tuple[str, float]:
        """
        Kết hợp model output + weight để xác định FINAL: CÓ NƯỚC / KHÔNG NƯỚC
        
        Args:
            model_detected: Model phát hiện chất lỏng
            model_conf: Độ tin cậy của model
            label: Label từ PRIMARY (e.g., 'plastic_bottle')
            weight_grams: Trọng lượng (grams)
            
        Returns:
            Tuple: ('yes'/'no', final_confidence)
        """
        
        # Lấy ngưỡng trọng lượng cho loại này
        weight_threshold = WEIGHT_THRESHOLD.get(
            'bottle' if 'bottle' in label.lower() else 'default'
        )
        
        # Nếu không có weight data, dùng model result
        if weight_grams is None:
            return ('yes' if model_detected else 'no', model_conf)
        
        # Logic kết hợp 4 trường hợp
        if model_detected and weight_grams > weight_threshold:
            # Case 1: Model báo CÓ + weight > ngưỡng => CÓ NƯỚC
            return ('yes', model_conf * 0.95)
        
        elif not model_detected and weight_grams <= weight_threshold:
            # Case 2: Model báo KHÔNG + weight <= ngưỡng => KHÔNG NƯỚC
            return ('no', model_conf * 0.95)
        
        elif not model_detected and weight_grams > weight_threshold:
            # Case 3: Model báo KHÔNG nhưng weight > ngưỡng => CÓ NƯỚC (nước đầy)
            return ('yes', (1 - model_conf) * 0.85)
        
        else:  # model_detected and weight_grams <= weight_threshold
            # Case 4: Model báo CÓ nhưng weight < ngưỡng => CÓ NƯỚC (ngưỡng quá cao)
            return ('yes', model_conf * 0.80)
    
    def run(self):
        """Main loop của SECONDARY process"""
        print(f"\n[SECONDARY-{self.worker_id}] Khởi động tiến trình Secondary Verification")
        
        # Load model
        if not self.load_model():
            print(f"[SECONDARY-{self.worker_id}] ⚠ Không thể load YOLO2. Sử dụng weight-only logic.")
        
        print(f"[SECONDARY-{self.worker_id}] ✓ Sẵn sàng xác nhận nước")
        
        while not self.shutdown_event.is_set():
            try:
                try:
                    # Lấy kết quả từ PRIMARY
                    msg_type, batch_id, primary_results = self.intermediate_queue.get(timeout=1)
                    
                    if msg_type is None:  # Shutdown signal
                        break
                    
                    print(f"[SECONDARY-{self.worker_id}] 📊 Nhận batch #{batch_id} từ PRIMARY")
                    
                    # Xử lý từng result từ PRIMARY
                    final_results = []
                    for primary_result in primary_results:
                        crop_image = primary_result['crop_image']
                        label = primary_result['label']
                        weight_grams = primary_result['weight_grams']
                        
                        # Xác định có nước
                        model_detected, model_conf = self.detect_liquid(crop_image)
                        has_liquid, liquid_conf = self.determine_has_liquid(
                            model_detected, model_conf, label, weight_grams
                        )
                        
                        final_result = {
                            'batch_id': batch_id,
                            'image_idx': primary_result['image_idx'],
                            'label': label,
                            'confidence': primary_result['confidence'],
                            'has_liquid': has_liquid,
                            'liquid_confidence': liquid_conf,
                            'weight_grams': weight_grams,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        final_results.append(final_result)
                        
                        print(f"[SECONDARY-{self.worker_id}]   → {label}: {has_liquid} (liquid_conf={liquid_conf:.2%})")
                    
                    # Gửi kết quả FINAL vào result_queue
                    self.result_queue.put(('final_result', batch_id, final_results))
                    print(f"[SECONDARY-{self.worker_id}] ✓ Batch #{batch_id} hoàn thành -> Result Queue")
                
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[SECONDARY-{self.worker_id}] ✗ Error processing batch: {e}")
                    continue
            
            except KeyboardInterrupt:
                print(f"[SECONDARY-{self.worker_id}] ⛔ Received interrupt signal")
                break
        
        print(f"[SECONDARY-{self.worker_id}] 🛑 Tiến trình SECONDARY dừng")


class ProcessorOrchestrator:
    """
    Orchestrator: Quản lý cả PRIMARY và SECONDARY processes
    =========================================================
    Chuyên trách: Khởi tạo, quản lý các tiến trình và giao tiếp với main app
    
    Giao thức:
      Main App -> input_queue -> [PRIMARY] -> intermediate_queue -> [SECONDARY] -> result_queue -> Main App
    """
    
    def __init__(self):
        self.input_queue = mp.Queue(maxsize=MAX_QUEUE_SIZE)
        self.intermediate_queue = mp.Queue(maxsize=MAX_QUEUE_SIZE)
        self.result_queue = mp.Queue(maxsize=MAX_QUEUE_SIZE)
        self.shutdown_event = mp.Event()
        
        self.primary_processes = []
        self.secondary_processes = []
        self.is_running = False
    
    def start(self):
        """Khởi động tất cả processes"""
        print("\n" + "="*80)
        print("🚀 MULTIPROCESSING ORCHESTRATOR - KHỞI ĐỘNG")
        print("="*80)
        
        # Khởi động PRIMARY processes
        print("\n[ORCHESTRATOR] Khởi động PRIMARY processes...")
        from config import PRIMARY_PROCESS_WORKERS
        for i in range(PRIMARY_PROCESS_WORKERS):
            p = PrimaryProcessor(
                self.input_queue, 
                self.intermediate_queue, 
                self.shutdown_event,
                worker_id=i
            )
            p.start()
            self.primary_processes.append(p)
            print(f"[ORCHESTRATOR] ✓ PRIMARY Worker-{i} started (PID: {p.pid})")
        
        # Khởi động SECONDARY processes
        print("\n[ORCHESTRATOR] Khởi động SECONDARY processes...")
        from config import SECONDARY_PROCESS_WORKERS
        for i in range(SECONDARY_PROCESS_WORKERS):
            p = SecondaryProcessor(
                self.intermediate_queue,
                self.result_queue,
                self.shutdown_event,
                worker_id=i
            )
            p.start()
            self.secondary_processes.append(p)
            print(f"[ORCHESTRATOR] ✓ SECONDARY Worker-{i} started (PID: {p.pid})")
        
        self.is_running = True
        print("\n" + "="*80)
        print("✅ Tất cả processes đã khởi động thành công!")
        print("="*80 + "\n")
    
    def stop(self):
        """Dừng tất cả processes"""
        print("\n" + "="*80)
        print("🛑 MULTIPROCESSING ORCHESTRATOR - DỪNG")
        print("="*80)
        
        self.shutdown_event.set()
        
        # Gửi shutdown signals
        self.input_queue.put(None)
        self.intermediate_queue.put((None, None, None))
        
        # Đợi processes kết thúc
        for p in self.primary_processes + self.secondary_processes:
            p.join(timeout=5)
            if p.is_alive():
                p.terminate()
                p.join()
        
        self.is_running = False
        print("✅ Tất cả processes đã dừng\n")
    
    def submit_batch(self, batch_id: int, images: list, weights: list = None) -> int:
        """
        Gửi batch ảnh vào xử lý
        
        Args:
            batch_id: ID của batch (dùng để track)
            images: List of OpenCV images
            weights: List of weights (grams) - nếu None, dùng default
            
        Returns:
            batch_id nếu thành công, -1 nếu lỗi
        """
        try:
            if not self.is_running:
                print("❌ Processor không đang chạy!")
                return -1
            
            if len(images) != BUFFER_SIZE:
                print(f"❌ Cần {BUFFER_SIZE} ảnh, nhận {len(images)}")
                return -1
            
            if weights is None:
                weights = [50.0] * BUFFER_SIZE  # Default weight
            
            # Đặt vào input queue
            self.input_queue.put((batch_id, images, weights))
            print(f"[ORCHESTRATOR] 📥 Batch #{batch_id} đã submit vào input_queue")
            return batch_id
        
        except Exception as e:
            print(f"[ORCHESTRATOR] ✗ Error submitting batch: {e}")
            return -1
    
    def get_result(self, timeout: float = None) -> Optional[Dict]:
        """
        Lấy kết quả từ result_queue
        
        Args:
            timeout: Timeout tính bằng giây
            
        Returns:
            Dict chứa final result hoặc None nếu timeout
        """
        try:
            msg_type, batch_id, results = self.result_queue.get(timeout=timeout)
            
            if msg_type == 'final_result':
                return {
                    'batch_id': batch_id,
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        except queue.Empty:
            return None
        except Exception as e:
            print(f"[ORCHESTRATOR] ✗ Error getting result: {e}")
            return None
    
    def get_queue_stats(self) -> Dict:
        """Lấy thống kê về các queues"""
        return {
            'input_queue_size': self.input_queue.qsize(),
            'intermediate_queue_size': self.intermediate_queue.qsize(),
            'result_queue_size': self.result_queue.qsize(),
            'is_running': self.is_running,
            'primary_processes': len([p for p in self.primary_processes if p.is_alive()]),
            'secondary_processes': len([p for p in self.secondary_processes if p.is_alive()])
        }


# Global instance
orchestrator = None

def init_orchestrator() -> ProcessorOrchestrator:
    """Khởi tạo global orchestrator"""
    global orchestrator
    if orchestrator is None:
        orchestrator = ProcessorOrchestrator()
    return orchestrator

def start_orchestrator():
    """Khởi động orchestrator"""
    global orchestrator
    orchestrator = init_orchestrator()
    orchestrator.start()

def stop_orchestrator():
    """Dừng orchestrator"""
    global orchestrator
    if orchestrator is not None:
        orchestrator.stop()

def get_orchestrator() -> ProcessorOrchestrator:
    """Lấy global orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        raise RuntimeError("Orchestrator not initialized!")
    return orchestrator
