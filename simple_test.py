#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("Step 1: Importing app.main")
print("="*60)
import app.main

print("\nStep 2: Inspecting app.main contents")
print("="*60)
print("app exists: hasattr(app.main, 'app')? " + str(hasattr(app.main, 'app')))
if hasattr(app.main, 'app'):
    app_inst = app.main.app
    print("\nApp instance found!")
    print("\nRegistered routes:")
    for route in app_inst.routes:
        print(f"  {route.path:40} {list(route.methods)}")
    print("\n" + "="*60)
    print("Checking sources router import...")
    import app.api.sources
    print("\napp.api.sources imported!")
    print("  sources.router: " + str(app.api.sources.router))

print("\n" + "="*60)
print("Done!")
