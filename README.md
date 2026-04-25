# 🗑️ Trash Classification System

FastAPI + Multiprocessing + YOLO v8 — Phân loại rác thải real-time qua ESP32-CAM.

## Workflow

```
ESP32-CAM → WebSocket → FastAPI buffer 5 ảnh
  → PRIMARY process: YOLO1 phân loại 38 loại rác
    → SECONDARY process: YOLO2 kiểm tra có nước
      → Output code 1-5 → ESP32
```

## Quick Start

```bash
# 1. Clone & setup
git clone <repo-url>
cd PBL5-
git config core.hooksPath .githooks
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. Đặt model files (nếu có)
#    model_trash/best.pt   — YOLO1 phân loại 38 loại rác
#    model_liquid/best.pt  — YOLO2 kiểm tra nước

# 3. Chạy server
python run.py
```

Truy cập: http://localhost:8000

## Project Structure

```
PBL5-/
├── config.py                 # Cấu hình (server, model, YOLO params)
├── main.py                   # FastAPI app + WebSocket + background tasks
├── models.py                 # SQLAlchemy models
├── run.py                    # Entry point
├── Dockerfile                # Docker image (chứa model files)
│
├── model_trash/best.pt       # YOLO1 - 38 loại rác (git ignored)
├── model_liquid/best.pt      # YOLO2 - kiểm tra nước (git ignored)
│
├── services/
│   └── processor.py          # Multiprocessing: PRIMARY + SECONDARY
├── repositories/
│   └── trash_repository.py   # Database CRUD
├── templates/                # HTML pages
├── static/                   # CSS, JS
│
├── .githooks/pre-push        # Auto build Docker khi có model files
├── build_and_push.sh         # Manual build & push Docker to ECR
├── build_and_push.bat        # Manual build & push (Windows)
│
├── infra/                    # Terraform + Terragrunt (AWS infrastructure)
│   └── aws/
│       ├── 4_deployments/    # CI/CD: ECR, KMS, CodePipeline
│       └── 5_workloads/      # App: VPC, ECS Cluster, ECS Service
│
└── ESP32_CLIENT_EXAMPLE/     # Arduino code cho ESP32-CAM
```

## Model Files

Model files (`*.pt`) **không nằm trên Git** vì quá lớn (~50MB). Chúng được đóng gói trong Docker image.

- `model_trash/best.pt` — YOLO1 phân loại 38 loại rác
- `model_liquid/best.pt` — YOLO2 kiểm tra nước

## Git Hook — Auto Build Docker

Khi `git push`, hook `pre-push` sẽ tự kiểm tra:

| Trường hợp | Hành vi |
|---|---|
| **Không có** model files | Push code bình thường, không build Docker |
| **Có** model_trash/best.pt + model_liquid/best.pt | Tự động build Docker → push lên ECR → rồi push code |

**Setup (chạy 1 lần sau khi clone):**
```bash
git config core.hooksPath .githooks
```

**Build Docker thủ công (nếu cần):**
```bash
# Windows
build_and_push.bat

# Linux/Mac
bash build_and_push.sh
```

## AWS Infrastructure

Region: `ap-southeast-1` (Singapore)

```
GitHub push → CodePipeline → CodeBuild (pytest) → Done
                                                    ↑ chỉ test code

Git hook (local) → Docker build (có model) → Push ECR
                                                    ↑ chỉ khi có model files
```

### Deploy hạ tầng

```bash
# Cần: terraform, terragrunt, AWS CLI configured

# 1. VPC
cd infra/aws/5_workloads/ap-southeast-1/prod/vpc
terragrunt apply

# 2. ECS Cluster + ALB
cd ../ecs/cluster
terragrunt apply

# 3. ECR Repository
cd ../../../../4_deployments/main/ap-southeast-1/ecr
terragrunt apply

# 4. ECS Service
cd ../../../../5_workloads/ap-southeast-1/prod/ecs/service
terragrunt apply

# 5. CI/CD Pipeline
cd ../../../../../4_deployments/main/ap-southeast-1/kms && terragrunt apply
cd ../artifacts && terragrunt apply
cd ../pipeline && terragrunt apply
```

## API

| Endpoint | Method | Mô tả |
|---|---|---|
| `/` | GET | Dashboard |
| `/history` | GET | Lịch sử phân loại |
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Thống kê |
| `/api/records?page=1&limit=20` | GET | Records (pagination) |
| `/ws` | WebSocket | ESP32-CAM stream |

## Output Codes (ESP32)

| Code | Ý nghĩa |
|---|---|
| 1 | Có nước |
| 2 | Không nước |
| 3 | Lỗi / Unknown |
| 4 | Loại khác |
| 5 | Không phát hiện |

## Configuration

File `config.py`:

```python
# YOLO1 - Phân loại rác
YOLO1_CONF = 0.4        # Confidence threshold
YOLO1_IMGSZ = 416       # Input size
YOLO1_DEVICE = 'cpu'    # 'cpu' hoặc 'cuda'

# YOLO2 - Kiểm tra nước
YOLO2_CONF = 0.5
YOLO2_IMGSZ = 320

# Multiprocessing
PRIMARY_PROCESS_WORKERS = 2
SECONDARY_PROCESS_WORKERS = 1
BUFFER_SIZE = 5
```

## ESP32-CAM

Xem `ESP32_CLIENT_EXAMPLE/` — chỉnh WiFi SSID, password, và server IP.
