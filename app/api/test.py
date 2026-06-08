import json
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/test", tags=["test"])

# Cache for test data
_test_data = None


@router.get("/sina-result")
async def get_sina_test_result():
    """Get Sina news page test result for frontend display"""
    global _test_data
    if _test_data is None:
        data_path = Path(__file__).parent.parent.parent / "sina_display.json"
        if data_path.exists():
            _test_data = json.loads(data_path.read_text(encoding="utf-8"))
        else:
            # Return minimal structure
            _test_data = {
                "title": "Sina News Test",
                "url": "https://k.sina.com.cn/article_5044281310_m12ca99fde020020qcv.html",
                "total_found": 32,
                "downloaded_ok": 0,
                "images": [],
                "all_urls": [],
            }
    return {"success": True, "data": _test_data}


@router.get("/sina-raw")
async def get_sina_raw_items():
    """Get all extracted items with original URLs"""
    import os
    data_path = Path(__file__).parent.parent.parent / "sina_test_result.json"
    if not data_path.exists():
        return {"success": False, "error": "Test data not found"}
    
    report = json.loads(data_path.read_text(encoding="utf-8"))
    items = report.get("all_found_items", [])
    
    # Filter to only real content images (skip icons/logos)
    content_images = []
    skip = ["icon", "logo", "qr", "thumb_default", "push_qrcode", "login"]
    for item in items:
        url = item.get("url", "")
        alt = (item.get("alt", "") or "").lower()
        url_lower = url.lower()
        if any(k in url_lower or k in alt for k in skip):
            continue
        if len(url) < 20:
            continue
        # Fix broken URLs
        if url.startswith("https:") and not url.startswith("https://"):
            url = "https://" + url[6:]
        elif url.startswith("http:") and not url.startswith("http://"):
            url = "http://" + url[5:]
        item["url"] = url
        content_images.append(item)
    
    return {
        "success": True,
        "data": {
            "title": report["page"]["title"],
            "url": report["page"]["url"],
            "total": len(content_images),
            "items": content_images,
        }
    }
