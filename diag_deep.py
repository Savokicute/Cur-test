import urllib.request, json, urllib.parse, traceback

base = "http://localhost:8000/api"

print("=== Deep Issue 1: Article crash debug ===")
# Get 28th item URL
req = urllib.request.Request(f"{base}/hotspots?date=2026-05-28")
resp = urllib.request.urlopen(req)
data28 = json.loads(resp.read().decode())
items28 = []
for platform, plist in (data28.get("data",{}).get("groups") or {}).items():
    items28.extend(plist)

if items28:
    url28 = items28[0].get("url")
    print(f"28th item url: {url28[:80]}...")
    encoded = urllib.parse.quote(url28, safe="")
    try:
        req = urllib.request.Request(f"{base}/articles/{encoded}")
        resp = urllib.request.urlopen(req, timeout=5)
        art28 = json.loads(resp.read().decode())
        print(f"Result: {json.dumps(art28, ensure_ascii=False)[:200]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP Error {e.code}: {body[:300]}")
    except Exception as e:
        print(f"Error: {e}")

print("\n=== Deep Issue 2: Sources save - exact payload test ===")
# Test with exact same format frontend would send
payload = {
    "hotSourcesEnabled": True,
    "enabledPlatforms": [
        {"id": "wallstreetcn-hot", "name": "华尔街见闻", "enabled": True},
        {"id": "thepaper", "name": "澎湃新闻", "enabled": True},
        {"id": "cls-hot", "name": "财联社热门", "enabled": True},
        {"id": "ifeng", "name": "凤凰网", "enabled": True},
    ]
}
body = json.dumps(payload).encode()
req = urllib.request.Request(f"{base}/sources/hot-sources", data=body, method="PUT", headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=5)
result = json.loads(resp.read().decode())
print(f"Sources PUT: success={result.get('success')}, msg={result.get('message','')}")

# Read back to verify
req2 = urllib.request.Request(f"{base}/sources/hot-sources")
resp2 = urllib.request.urlopen(req2)
data2 = json.loads(resp2.read().decode())
print(f"Sources GET enabled={data2.get('data',{}).get('hotSourcesEnabled')}")
platforms = data2.get('data',{}).get('availablePlatforms',[])
for p in platforms[:4]:
    print(f"  {p.get('id')}: enabled={p.get('enabled')}")

print("\n=== Deep Issue 3: Notif save - test with 'value' wrapper ===")
# Test what frontend actually sends (with value wrapper)
payload3 = {
    "value": {
        "enabled": False,
        "channels": {"feishu": {"webhook_url": ""}}
    }
}
body3 = json.dumps(payload3).encode()
req3 = urllib.request.Request(f"{base}/config/module?module=notification", data=body3, method="PUT", headers={"Content-Type": "application/json"})
resp3 = urllib.request.urlopen(req3, timeout=5)
result3 = json.loads(resp3.read().decode())
print(f"Notif PUT (with value wrapper): success={result3.get('success')}")

req4 = urllib.request.Request(f"{base}/config/module?module=notification")
resp4 = urllib.request.urlopen(req4)
data4 = json.loads(resp4.read().decode())
val4 = data4.get("data",{}).get("value",{})
print(f"Notif read back: enabled={val4.get('enabled')}, has_value_key={'value' in val4}")
