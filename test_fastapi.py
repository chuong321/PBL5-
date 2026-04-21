#!/usr/bin/env python
"""
Test Script - FastAPI WebSocket & HTTP API
Kiểm tra server hoạt động bình thường
"""

import requests
import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import sys

# Server settings
SERVER_URL = 'http://localhost:8000'
WS_URL = 'ws://localhost:8000/ws'

print("\n" + "="*80)
print("🧪 TEST SCRIPT - Trash Classification System (FastAPI)")
print("="*80 + "\n")

# ==================== HTTP Tests ====================

print("[1] Testing HTTP Endpoints...\n")

# Test 1: Health Check
print("  [1.1] GET /api/health")
try:
    response = requests.get(f'{SERVER_URL}/api/health', timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"        ✓ Status: {data['status']}")
        print(f"        ✓ Total records: {data['total_records']}")
    else:
        print(f"        ✗ Status: {response.status_code}")
except Exception as e:
    print(f"        ✗ Error: {e}")
    print("        → Server không chạy? (http://localhost:8000)")

# Test 2: Statistics
print("\n  [1.2] GET /api/stats")
try:
    response = requests.get(f'{SERVER_URL}/api/stats', timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"        ✓ Total: {data['total_records']}")
        print(f"        ✓ Avg confidence: {data['average_confidence']:.2%}")
        print(f"        ✓ Recent 24h: {data['recent_24h']}")
    else:
        print(f"        ✗ Status: {response.status_code}")
except Exception as e:
    print(f"        ✗ Error: {e}")

# Test 3: Records
print("\n  [1.3] GET /api/records")
try:
    response = requests.get(f'{SERVER_URL}/api/records?page=1&limit=5', timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"        ✓ Total records: {data['total']}")
        print(f"        ✓ Page: {data['page']}/{data['pages']}")
        if data['records']:
            record = data['records'][0]
            print(f"        ✓ Latest: {record['label']} ({record['confidence']})")
    else:
        print(f"        ✗ Status: {response.status_code}")
except Exception as e:
    print(f"        ✗ Error: {e}")

# ==================== WebSocket Test ====================

print("\n\n[2] Testing WebSocket Connection...\n")

async def test_websocket():
    try:
        # Connect
        async with websockets.connect(WS_URL) as websocket:
            print("  ✓ Connected to WebSocket")
            
            # Test 1: Send ping
            print("\n  [2.1] Sending ping...")
            await websocket.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            resp_data = json.loads(response)
            print(f"        ✓ Received: {resp_data['type']}")
            
            # Test 2: Send test image
            print("\n  [2.2] Sending dummy image...")
            # Create dummy 640x480 RGB image
            dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', dummy_image)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "type": "image",
                "data": base64_image,
                "weight_grams": 75.5
            }
            
            await websocket.send(json.dumps(payload))
            print(f"        ✓ Sent {len(base64_image)//1024}KB image")
            
            # Wait for buffer status
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            resp_data = json.loads(response)
            print(f"        ✓ Buffer status: {resp_data['buffer_count']}/{resp_data['buffer_size']}")
            
            # If we had 5 images would trigger processing
            print("\n  ℹ️  Note: Need 5 images to trigger processing")
            print("     (Each test sends 1 image, buffer fills with 4 more real images)")
            
            print("\n  ✓ WebSocket test completed\n")
    
    except asyncio.TimeoutError:
        print("        ✗ Timeout - no response from server")
    except Exception as e:
        print(f"        ✗ Error: {e}")

# Run WebSocket test
try:
    asyncio.run(test_websocket())
except Exception as e:
    print(f"  ✗ WebSocket test failed: {e}")
    print("  → Maybe WebSocket connection failed?")

# ==================== Summary ====================

print("="*80)
print("✅ Test Completed!")
print("="*80)

print("\n📌 Next Steps:")
print("1. Upload best.pt & best_secondary.pt models to project directory")
print("2. Connect ESP32-CAM WebSocket client to ws://localhost:8000/ws")
print("3. Monitor results in http://localhost:8000 dashboard")
print("4. Check API endpoints for statistics")

print("\n📚 Documentation:")
print("- API Docs: http://localhost:8000/docs")
print("- ReDoc: http://localhost:8000/redoc")
print("- WebSocket: ws://localhost:8000/ws")

print("\n" + "="*80 + "\n")
