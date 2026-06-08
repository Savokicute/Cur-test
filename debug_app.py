#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("DEBUG: Loading app.main")
print("="*60)

from app.main import app

print("\nApp loaded successfully!")
print("\nRegistered routes:")
for route in app.routes:
    print(f"  {route.path:40} {list(route.methods)}")

print("\n" + "="*60)
print("Starting server on http://localhost:8001")
print("="*60)

import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8001)
