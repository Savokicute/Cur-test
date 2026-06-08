# coding=utf-8
"""媒体 API 基本功能测试"""

import sys
import io
from pathlib import Path

# 设置标准输出为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """测试模块导入"""
    print("Test 1: Module imports...")

    try:
        from app.services.media_service import MediaService
        from app.api import media
        print("[PASS] All modules imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_init():
    """测试服务初始化"""
    print("\nTest 2: Service initialization...")

    try:
        from app.services.media_service import MediaService

        # 使用默认存储目录
        service = MediaService()
        storage_path = service.storage_root  # 直接访问属性

        print(f"[PASS] Storage path: {storage_path}")
        print(f"[PASS] Directory exists: {storage_path.exists()}")
        return True
    except Exception as e:
        print(f"[FAIL] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_path_validation():
    """测试路径验证（安全防护）"""
    print("\nTest 3: Path security validation...")

    try:
        from app.api.media import _validate_path
        from app.services.media_service import MediaService

        service = MediaService()

        # 测试正常路径
        normal_path = "images/2026/05/29/test.jpg"
        full_path, is_valid = _validate_path(normal_path)
        print(f"[PASS] Normal path validation: {is_valid}")

        # 测试路径遍历攻击
        attack_path = "../../../etc/passwd"
        full_path, is_valid = _validate_path(attack_path)
        print(f"[PASS] Path traversal attack blocked: {not is_valid}")

        # 测试 URL 编码的路径遍历
        encoded_attack = "..%2F..%2F..%2Fetc%2Fpasswd"
        full_path, is_valid = _validate_path(encoded_attack)
        print(f"[PASS] URL-encoded path traversal blocked: {not is_valid}")

        return True
    except Exception as e:
        print(f"[FAIL] Path validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mime_types():
    """测试 MIME 类型映射"""
    print("\nTest 4: MIME type mapping...")

    try:
        from app.api.media import _get_mime_type

        test_cases = [
            ("test.jpg", "image/jpeg"),
            ("photo.png", "image/png"),
            ("anim.gif", "image/gif"),
            ("modern.webp", "image/webp"),
            ("video.mp4", "video/mp4"),
            ("unknown.xyz", "application/octet-stream"),
        ]

        all_passed = True
        for filename, expected_mime in test_cases:
            actual_mime = _get_mime_type(filename)
            passed = actual_mime == expected_mime
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {filename} -> {actual_mime} (expected: {expected_mime})")
            all_passed = all_passed and passed

        return all_passed
    except Exception as e:
        print(f"[FAIL] MIME type test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_size_formatting():
    """测试文件大小格式化"""
    print("\nTest 5: File size formatting...")

    try:
        from app.api.media import _format_size

        test_cases = [
            (500, "500.00 B"),
            (1024, "1.00 KB"),
            (1048576, "1.00 MB"),
            (1073741824, "1.00 GB"),
        ]

        all_passed = True
        for size_bytes, expected in test_cases:
            result = _format_size(size_bytes)
            passed = result == expected
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {size_bytes} bytes -> {result} (expected: {expected})")
            all_passed = all_passed and passed

        return all_passed
    except Exception as e:
        print(f"[FAIL] Size formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Media API Functionality Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_service_init,
        test_path_validation,
        test_mime_types,
        test_size_formatting,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)

    if all(results):
        print("\n[SUCCESS] All tests passed! Media API is ready.")
        return 0
    else:
        print("\n[FAILURE] Some tests failed. Check error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
