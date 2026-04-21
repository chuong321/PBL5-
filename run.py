#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run Script - Entry Point (FastAPI + Uvicorn)
Khởi động FastAPI server với Multiprocessing support
"""

import os
import sys
import io

# Fix encoding cho Windows terminal
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Thêm project directory vào Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    import uvicorn
    
    print("\n" + "="*80)
    print("🗑️  Trash Classification System - FastAPI + Multiprocessing")
    print("="*80 + "\n")
    
    # Run FastAPI app using Uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        workers=1  # 1 worker vì Uvicorn sẽ handle async internally
    )

