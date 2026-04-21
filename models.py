"""
Models - Database Entity Definitions (SQLAlchemy 2.0)
Định nghĩa các bảng và cấu trúc dữ liệu
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class TrashRecord(Base):
    """
    Model: Bản ghi phân loại rác
    Lưu trữ kết quả nhận diện từ AI
    """
    __tablename__ = 'trash_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_path = Column(String(255), nullable=False)  # Đường dẫn file ảnh
    label = Column(String(50), nullable=False)  # Nhãn rác (38 loại)
    confidence = Column(Float, nullable=False)  # Độ tin cậy (0-1)
    has_liquid = Column(String(10), nullable=True)  # 'yes', 'no', 'unknown' - Kết quả từ tiến trình 2
    weight_grams = Column(Float, nullable=True)  # Trọng lượng (grams) từ cảm biến
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Metadata
    individual_confidences = Column(String(255), nullable=True)  # JSON string của 5 confidence riêng lẻ
    primary_model_output = Column(String(255), nullable=True)  # Output từ YOLO1
    secondary_model_output = Column(String(255), nullable=True)  # Output từ YOLO2
    
    def __repr__(self):
        return f'<TrashRecord {self.id}: {self.label} ({self.confidence:.2%}) liquid={self.has_liquid}>'
    
    def to_dict(self):
        """Chuyển đổi sang dictionary cho JSON response"""
        return {
            'id': self.id,
            'image_path': self.image_path,
            'label': self.label,
            'confidence': f"{self.confidence:.2%}",
            'has_liquid': self.has_liquid or 'unknown',
            'weight_grams': self.weight_grams,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else 'N/A'
        }


def init_db(database_url: str):
    """Khởi tạo database - Tạo tables nếu chưa tồn tại"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    print("✓ Database initialized successfully!")
    return engine


def get_session_factory(database_url: str):
    """Tạo session factory"""
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal
