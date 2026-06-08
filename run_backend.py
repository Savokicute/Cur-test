#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app
import uvicorn

print("="*60)
print("Starting FastAPI Backend on http://localhost:8000")
print("="*60)
print("Registered routes:")
for route in app.routes:
    print(f"  {route.path:40} {list(route.methods)}")
print("\n" + "="*60)

uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
