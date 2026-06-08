#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

print("="*60)
print("FastAPI Application - Registered Routes")
print("="*60)

for route in app.routes:
    print(f"Path: {route.path:40} Methods: {list(route.methods)}")

print("\n" + "="*60)
