#!/usr/bin/env python3
# coding=utf-8
"""测试 TrendRadarReader"""

from hot_content_bridge.config import BridgeConfig
from app.integrations import TrendRadarReader

def main():
    print("=" * 60)
    print("测试 TrendRadarReader")
    print("=" * 60)
    
    try:
        # 加载配置
        cfg = BridgeConfig.load()
        print(f"配置加载成功，数据目录: {cfg.data_dir}")
        
        # 创建 reader
        reader = TrendRadarReader(cfg)
        
        # 测试获取最新抓取时间
        print("\n[1] 测试获取最新抓取时间...")
        latest_crawl = reader.get_latest_crawl_time()
        print(f"最新抓取时间: {latest_crawl}")
        
        # 测试获取热榜数据
        print("\n[2] 测试获取热榜数据...")
        latest_crawl, hotspots = reader.get_hotspots_with_articles()
        print(f"找到 {len(hotspots)} 条热榜数据")
        
        if hotspots:
            print("\n前 5 条:")
            for i, item in enumerate(hotspots[:5]):
                print(f"  {i+1}. [{item['platform_name']}] #{item['rank']} {item['title'][:40]}...")
        
        # 测试获取平台列表
        print("\n[3] 测试获取平台列表...")
        platforms = reader.get_platforms()
        print(f"找到 {len(platforms)} 个平台:")
        for p in platforms:
            print(f"  - {p['name']} (id: {p['id']})")
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
