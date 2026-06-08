import urllib.request, json, urllib.parse

base = "http://localhost:8000/api"

print("=== Issue 1: Article detail for 28th vs 1st ===")
# Get 28th hotspots
req = urllib.request.Request(f"{base}/hotspots?date=2026-05-28")
resp = urllib.request.urlopen(req)
data28 = json.loads(resp.read().decode())
items28 = []
for platform, plist in (data28.get("data",{}).get("groups") or {}).items():
    items28.extend(plist)
print(f"28th items: {len(items28)}")

# Get 1st hotspots
req = urllib.request.Request(f"{base}/hotspots?date=2026-06-01")
resp = urllib.request.urlopen(req)
data01 = json.loads(resp.read().decode())
items01 = []
for platform, plist in (data01.get("data",{}).get("groups") or {}).items():
    items01.extend(plist)
print(f"1st items: {len(items01)}")

# Try fetching a 28th article
if items28:
    url28 = items28[0].get("url")
    if url28:
        encoded = urllib.parse.quote(url28, safe="")
        try:
            req = urllib.request.Request(f"{base}/articles/{encoded}")
            resp = urllib.request.urlopen(req, timeout=5)
            art28 = json.loads(resp.read().decode())
            print(f"28th article fetch: success={art28.get('success')}, status={art28.get('data',{}).get('article_status')}, md_chars={art28.get('data',{}).get('md_chars',0)}")
        except Exception as e:
            print(f"28th article fetch ERROR: {e}")

# Try fetching a 1st article
if items01:
    url01 = items01[0].get("url")
    if url01:
        encoded = urllib.parse.quote(url01, safe="")
        try:
            req = urllib.request.Request(f"{base}/articles/{encoded}")
            resp = urllib.request.urlopen(req, timeout=5)
            art01 = json.loads(resp.read().decode())
            print(f"1st article fetch: success={art01.get('success')}, status={art01.get('data',{}).get('article_status')}, md_chars={art01.get('data',{}).get('md_chars',0)}")
        except Exception as e:
            print(f"1st article fetch ERROR: {e}")

print("\n=== Issue 2: Sources config save ===")
try:
    body = json.dumps({"hotSourcesEnabled": True, "enabledPlatforms": [{"id": "test", "name": "test", "enabled": True}]}).encode()
    req = urllib.request.Request(f"{base}/sources/hot-sources", data=body, method="PUT", headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=5)
    result = json.loads(resp.read().decode())
    print(f"Sources PUT: success={result.get('success')}, msg={result.get('message','')}")
except Exception as e:
    print(f"Sources PUT ERROR: {e}")

print("\n=== Issue 3: Notification config save ===")
try:
    body = json.dumps({"enabled": True, "channels": {"feishu": {"webhook_url": ""}}}).encode()
    req = urllib.request.Request(f"{base}/config/module?module=notification", data=body, method="PUT", headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=5)
    result = json.loads(resp.read().decode())
    print(f"Notif PUT: success={result.get('success')}, msg={result.get('message','')}")

    # Re-read to verify
    req2 = urllib.request.Request(f"{base}/config/module?module=notification")
    resp2 = urllib.request.urlopen(req2)
    data2 = json.loads(resp2.read().decode())
    enabled_val = data2.get("data",{}).get("value",{}).get("enabled")
    print(f"Notif re-read: enabled={enabled_val} (expected=True)")
except Exception as e:
    print(f"Notif PUT/READ ERROR: {e}")
