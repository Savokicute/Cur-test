"""
全面配置同步端到端测试
测试所有5个前端配置页面的修改能否正确同步到 config.yaml
"""
import urllib.request, json, urllib.parse, sys, os

BASE = "http://localhost:8000/api"
CONFIG_PATH = r"d:\chao-TrendRadar\Cur-test - v3\trendRadar\config\config.yaml"

passed = 0
failed = 0
errors = []

def read_yaml_raw():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def api(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "code": e.code, "body": e.read().decode()[:200]}

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        errors.append((name, detail))
        print(f"  FAIL: {name} — {detail}")

# ============================================================
print("=" * 60)
print("配置同步端到端测试")
print("=" * 60)

# ---- 备份原始 config.yaml ----
original_yaml = read_yaml_raw()
print(f"\n[备份] 原始 config.yaml 已保存 ({len(original_yaml)} bytes)")

# ============================================================
# 测试 1: Settings (系统设置) → app / schedule / advanced 模块
# ============================================================
print("\n--- 测试 1: 系统设置 (Settings) ---")

# 1a. app 模块
test_val_app = {"timezone": "Asia/Tokyo", "show_version_update": False}
r = api("PUT", "/config/module?module=app", test_val_app)
test("app模块保存", r.get("success") == True, f"resp={r}")

r2 = api("GET", "/config/module?module=app")
val = r2.get("data", {}).get("value", {})
test("app模块读取-timezone", val.get("timezone") == "Asia/Tokyo", f"got={val.get('timezone')}")
test("app模块读取-show_version", val.get("show_version_update") == False, f"got={val.get('show_version_update')}")

# 1b. schedule 模块
test_val_sched = {"enabled": False, "preset": "custom"}
r = api("PUT", "/config/module?module=schedule", test_val_sched)
test("schedule模块保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=schedule")
val = r2.get("data", {}).get("value", {})
test("schedule读取-enabled", val.get("enabled") == False)
test("schedule读取-preset", val.get("preset") == "custom")

# 1c. advanced 模块
test_val_adv = {"debug": True}
r = api("PUT", "/config/module?module=advanced", test_val_adv)
test("advanced模块保存", r.get("success") == True)

# 恢复 app/schedule/advanced
api("PUT", "/config/module?module=app", {"timezone": "Asia/Shanghai", "show_version_update": True})
api("PUT", "/config/module?module=schedule", {"enabled": True, "preset": "morning_evening"})
api("PUT", "/config/module?module=advanced", {"debug": False})

# ============================================================
# 测试 2: AIConfig (AI智能) → ai / ai_filter / ai_analysis / ai_translation
# ============================================================
print("\n--- 测试 2: AI智能 (AIConfig) ---")

# 2a. ai 模块
test_val_ai = {"model": "gpt-4o-test", "timeout": 60, "temperature": 0.5}
r = api("PUT", "/config/module?module=ai", test_val_ai)
test("ai模块保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=ai")
val = r2.get("data", {}).get("value", {})
test("ai读取-model", val.get("model") == "gpt-4o-test")
test("ai读取-timeout", val.get("timeout") == 60)
test("ai读取-temperature", val.get("temperature") == 0.5)

# 2b. ai_filter 模块
test_val_aif = {"min_score": 0.85, "batch_size": 100}
r = api("PUT", "/config/module?module=ai_filter", test_val_aif)
test("ai_filter保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=ai_filter")
val = r2.get("data", {}).get("value", {})
test("ai_filter读取-min_score", val.get("min_score") == 0.85)

# 2c. ai_analysis 模块
test_val_aia = {"enabled": False, "language": "English"}
r = api("PUT", "/config/module?module=ai_analysis", test_val_aia)
test("ai_analysis保存", r.get("success") == True)

# 2d. ai_translation 模块
test_val_ait = {"enabled": False, "language": "English"}
r = api("PUT", "/config/module?module=ai_translation", test_val_ait)
test("ai_translation保存", r.get("success") == True)

# 恢复 AI 配置
api("PUT", "/config/module?module=ai", {
    "model": "openai/doubao-seed-2-0-mini-260215",
    "api_key": "sk-jMrOy2GMy17cCmkXrricFEOx3AXtLy5uYhpddYhQi2sFEcVm",
    "api_base": "https://www.dmxapi.cn/v1",
    "timeout": 120, "temperature": 1.0, "max_tokens": 5000, "num_retries": 1,
    "fallback_models": []
})
api("PUT", "/config/module?module=ai_filter", {"batch_size": 200, "batch_interval": 2, "min_score": 0.7, "reclassify_threshold": 0.6})
api("PUT", "/config/module?module=ai_analysis", {"enabled": True, "language": "Chinese"})
api("PUT", "/config/module?module=ai_translation", {"enabled": True, "language": "中文"})

# ============================================================
# 测试 3: ContentPolicy (内容策略) → report / filter / display
# ============================================================
print("\n--- 测试 3: 内容策略 (ContentPolicy) ---")

# 3a. report 模块
test_val_rpt = {"mode": "daily", "display_mode": "full"}
r = api("PUT", "/config/module?module=report", test_val_rpt)
test("report保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=report")
val = r2.get("data", {}).get("value", {})
test("report读取-mode", val.get("mode") == "daily")

# 3b. filter 模块
test_val_flt = {"method": "keyword", "priority_sort_enabled": False}
r = api("PUT", "/config/module?module=filter", test_val_flt)
test("filter保存", r.get("success") == True)

# 3c. display 模块
test_val_disp = {"region_order": ["hotlist", "new_items"], "max_items": 50}
r = api("PUT", "/config/module?module=display", test_val_disp)
test("display保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=display")
val = r2.get("data", {}).get("value", {})
test("display读取-max_items", val.get("max_items") == 50)

# 恢复
api("PUT", "/config/module?module=report", {"mode": "current", "display_mode": "keyword", "sort_by_position_first": False, "rank_threshold": 5, "max_news_per_keyword": 0})
api("PUT", "/config/module?module=filter", {"method": "ai", "priority_sort_enabled": True})
api("PUT", "/config/module?module=display", {
    "region_order": ["new_items", "hotlist", "rss", "standalone", "ai_analysis"],
    "regions": {"hotlist": True, "new_items": False, "rss": True, "standalone": False, "ai_analysis": True},
    "standalone": {"platforms": ["zhihu", "wallstreetcn-hot"], "rss_feeds": [], "max_items": 20}
})

# ============================================================
# 测试 4: NotifyStorage (通知存储) → notification / storage
# ============================================================
print("\n--- 测试 4: 通知存储 (NotifyStorage) ---")

# 4a. notification 模块
test_val_notif = {"enabled": False, "channels": {"feishu": {"webhook_url": "https://test.example.com"}}}
r = api("PUT", "/config/module?module=notification", test_val_notif)
test("notification保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=notification")
val = r2.get("data", {}).get("value", {})
test("notification读取-enabled", val.get("enabled") == False, f"got={val.get('enabled')}, type={type(val.get('enabled'))}")
test("notification无嵌套value", "value" not in val, f"keys={list(val.keys())[:5]}")

# 4b. storage 模块
test_val_stor = {"backend": "local", "formats": {"sqlite": True, "txt": True}}
r = api("PUT", "/config/module?module=storage", test_val_stor)
test("storage保存", r.get("success") == True)

r2 = api("GET", "/config/module?module=storage")
val = r2.get("data", {}).get("value", {})
test("storage读取-backend", val.get("backend") == "local")

# 恢复
api("PUT", "/config/module?module=notification", {"enabled": True, "channels": {"feishu": {"webhook_url": ""}}})
api("PUT", "/config/module?module=storage", {"backend": "auto", "formats": {"sqlite": True, "txt": False, "html": True}})

# ============================================================
# 测试 5: Sources (采集源配置) → platforms (via sources API)
# ============================================================
print("\n--- 测试 5: 采集源配置 (Sources) ---")

# 5a. 热榜平台总开关
test_val_src = {"hotSourcesEnabled": False, "enabledPlatforms": [
    {"id": "wallstreetcn-hot", "name": "华尔街见闻", "enabled": True},
    {"id": "thepaper", "name": "澎湃新闻", "enabled": True},
    {"id": "cls-hot", "name": "财联社热门", "enabled": True},
    {"id": "ifeng", "name": "凤凰网", "enabled": True},
]}
r = api("PUT", "/sources/hot-sources", test_val_src)
test("热榜平台总开关禁用", r.get("success") == True, f"resp={r}")

r2 = api("GET", "/sources/hot-sources")
val2 = r2.get("data", {})
test("热榜平台读取-disabled", val2.get("hotSourcesEnabled") == False)

# 5b. 恢复启用
restore_src = {"hotSourcesEnabled": True, "enabledPlatforms": [
    {"id": "wallstreetcn-hot", "name": "华尔街见闻", "enabled": True},
    {"id": "thepaper", "name": "澎湃新闻", "enabled": True},
    {"id": "cls-hot", "name": "财联社热门", "enabled": True},
    {"id": "ifeng", "name": "凤凰网", "enabled": True},
]}
r = api("PUT", "/sources/hot-sources", restore_src)
test("热榜平台恢复启用", r.get("success") == True)

# ============================================================
# 测试 6: config.yaml 文件级验证
# ============================================================
print("\n--- 测试 6: config.yaml 文件级验证 ---")

yaml_after = read_yaml_raw()
test("YAML文件非空", len(yaml_after) > 100)
test("YAML包含notification段", "notification:" in yaml_after)
test("YAML包含platforms段", "platforms:" in yaml_after)
test("YAML包含ai段", "\nai:" in yaml_after or "  ai:" in yaml_after)
test("YAML无嵌套value", "  value:\n" not in yaml_after and "\n  value:" not in yaml_after[:500])

# 验证关键字段值正确
lines = yaml_after.split("\n")
notif_found = False
for i, line in enumerate(lines):
    if "notification:" in line and i + 1 < len(lines):
        next_line = lines[i + 1]
        if "enabled:" in next_line:
            notif_found = True
            test("YAML中notification.enabled直接存在", "  value:" not in next_line)
            break

# ============================================================
# 结果汇总
# ============================================================
print("\n" + "=" * 60)
print(f"结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")
if errors:
    print("\n失败详情:")
    for name, detail in errors:
        print(f"  ✗ {name}: {detail}")
else:
    print("\n全部通过! 所有配置页面修改均可正确同步到 config.yaml ✅")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
