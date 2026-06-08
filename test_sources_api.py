#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import yaml

from app.api.sources import (
    load_trendradar_config,
    TRENDRADAR_CONFIG_PATH
)

def test_config_load():
    print(f"Testing config load from: {TRENDRADAR_CONFIG_PATH}")
    try:
        config = load_trendradar_config()
        print(f"Successfully loaded config!")
        print(f"Config keys: {list(config.keys())}")
        
        platforms = config.get("platforms", {})
        print(f"\nPlatforms config:")
        print(f"  enabled: {platforms.get('enabled')}")
        print(f"  sources: {platforms.get('sources')}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_available_platforms():
    from app.api.sources import AVAILABLE_PLATFORMS
    print(f"\n\nAvailable platforms count: {len(AVAILABLE_PLATFORMS)}")
    for p in AVAILABLE_PLATFORMS:
        print(f"  - {p['name']} ({p['id']})")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing TrendRadar Configuration Loading")
    print("=" * 60)
    test_config_load()
    test_available_platforms()
    print("=" * 60)
