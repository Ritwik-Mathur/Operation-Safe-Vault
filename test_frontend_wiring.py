"""
test_frontend_wiring.py
───────────────────────
Validates every fixed frontend button by calling the corresponding backend
endpoint with the exact same payload the frontend now sends.

Run with both servers up:
    python test_frontend_wiring.py
"""
import urllib.request, urllib.parse, json, sys, time

BASE = "http://localhost:8000"

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
SKIP = "\033[93m[SKIP]\033[0m"

def post_form(path, fields):
    """Send multipart/form-data exactly like a browser fetch() with FormData."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = b""
    for k, v in fields.items():
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
            f"{v}\r\n"
        ).encode()
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


results = []

print("=" * 60)
print("Frontend Wiring Verification — Testing all fixed buttons")
print("=" * 60)
print()

# ── Test 1: Navbar + ThreatSandbox → POST /analyze/text ─────────────────────
print("1. Navbar 'Analyze Threat' / Sandbox 'INITIATE SCAN' → POST /analyze/text")
print("   Payload: FormData { message, sender='unknown', channel='sms' }")
status, data = post_form("/analyze/text", {
    "message": "URGENT! Your account has been suspended. Click here to verify: bit.ly/secure-login-now",
    "sender": "unknown",
    "channel": "sms",
})
if status == 200 and "combined" in data:
    combined = data["combined"]
    score = combined.get("score", 0)
    verdict = combined.get("verdict", "?")
    reasons = combined.get("reasons", [])
    print(f"   {PASS} HTTP {status} — score={score:.1f}, verdict='{verdict}'")
    print(f"         {len(reasons)} reasons — first: {reasons[0][:70] if reasons else 'none'}")
    results.append(True)
else:
    print(f"   {FAIL} HTTP {status} — response: {str(data)[:120]}")
    results.append(False)
print()

# ── Test 2: Sandbox URL-mode → POST /analyze/url ────────────────────────────
print("2. Sandbox 'INITIATE SCAN' (URL mode) → POST /analyze/url")
print("   Payload: FormData { url }")
status, data = post_form("/analyze/url", {
    "url": "https://bit.ly/suspicious-login-portal",
})
if status == 200 and "score" in data:
    print(f"   {PASS} HTTP {status} — score={data['score']:.1f}, verdict='{data.get('verdict','?')}'")
    results.append(True)
else:
    print(f"   {FAIL} HTTP {status} — response: {str(data)[:120]}")
    results.append(False)
print()

# ── Test 3: Sandbox 'BLOCK SOURCE' → POST /feedback ─────────────────────────
print("3. Sandbox 'BLOCK SOURCE' → POST /feedback")
print("   Payload: FormData { analysis_id, user_verdict='scam', ... }")
status, data = post_form("/feedback", {
    "analysis_id": "test-id",
    "user_verdict": "scam",
    "original_score": "82",
    "original_verdict": "HIGH RISK",
    "source": "text",
    "original_input": "URGENT! Click bit.ly/secure-login-now",
    "comment": "Blocked from Threat Sandbox",
})
if status == 200 and data.get("status") == "feedback recorded":
    print(f"   {PASS} HTTP {status} — feedback recorded successfully")
    results.append(True)
else:
    print(f"   {FAIL} HTTP {status} — response: {str(data)[:120]}")
    results.append(False)
print()

# ── Test 4: Hero 'View Documentation' → GET /docs ────────────────────────────
print("4. Hero 'View Documentation' → opens /docs in new tab")
try:
    req = urllib.request.Request(BASE + "/docs", method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode(errors="replace")
        if "swagger" in html.lower() or "openapi" in html.lower() or "FastAPI" in html:
            print(f"   {PASS} HTTP {r.status} — FastAPI /docs page returned (Swagger UI detected)")
            results.append(True)
        else:
            print(f"   {PASS} HTTP {r.status} — /docs is reachable (HTML: {len(html)} chars)")
            results.append(True)
except Exception as e:
    print(f"   {FAIL} Cannot reach /docs: {e}")
    results.append(False)
print()

# ── Test 5: GET /detection-stats (used in voice lab WebSocket page) ──────────
print("5. GET /detection-stats (WebSocket Live Call stats)")
try:
    req = urllib.request.Request(BASE + "/detection-stats", method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print(f"   {PASS} HTTP {r.status} — {data}")
        results.append(True)
except Exception as e:
    print(f"   {FAIL} {e}")
    results.append(False)
print()

# ── Summary ──────────────────────────────────────────────────────────────────
passed = sum(results)
total  = len(results)
print("=" * 60)
print(f"Results: {passed}/{total} passed")
print("=" * 60)

sys.exit(0 if passed == total else 1)
