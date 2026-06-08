#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from app.api.sources import (
    load_trendradar_config,
    TRENDRADAR_CONFIG_PATH
)

def test_config_abs_path():
    print(f"Testing absolute path config load from: {TRENDRADAR_CONFIG_PATH}")
    try:
        print(f"Config path absolute? {TRENDRADAR_CONFIG_PATH.is_absolute()}")
        print(f"Config path exists? {TRENDRADAR_CONFIG_PATH.exists()}")
        
        config = load_trendradar_config()
        print(f"Successfully loaded config from absolute path!")
        
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

if __name__ == "__main__":
    print("=" * 60)
    print("Testing TrendRadar Configuration - Absolute Path")
    print("=" * 60)
    test_config_abs_path()
    print("=" * 60)
