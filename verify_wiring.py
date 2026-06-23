"""
verify_wiring.py  --  Tests all fixed button->endpoint connections
Run: python verify_wiring.py
"""
import sys
import urllib.request
import json

BASE = "http://localhost:8000"

def post_form(path, fields):
    boundary = "TestBoundary7MA4YW"
    parts = []
    for k, v in fields.items():
        part = (
            "--" + boundary + "\r\n"
            + 'Content-Disposition: form-data; name="' + k + '"\r\n\r\n'
            + str(v) + "\r\n"
        )
        parts.append(part)
    body = "".join(parts) + "--" + boundary + "--\r\n"
    body_bytes = body.encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=body_bytes,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


results = []

# ---- Test 1 ---------------------------------------------------------------
print("TEST 1: POST /analyze/text  [Navbar 'Analyze Threat' + Sandbox text mode]")
s, d = post_form("/analyze/text", {
    "message": "URGENT! Your account suspended. Click bit.ly/secure-login-now to restore access.",
    "sender": "unknown",
    "channel": "sms",
})
combined = d.get("combined", d)
score   = combined.get("score", 0)
verdict = combined.get("verdict", "?")
reasons = combined.get("reasons", [])
ok = s == 200 and "score" in combined
results.append(ok)
print("  HTTP", s, " score=", round(score,1), " verdict=", verdict, " reasons=", len(reasons))
print("  First reason:", reasons[0][:80] if reasons else "none")
print("  PASS:", ok)
print()

# ---- Test 2 ---------------------------------------------------------------
print("TEST 2: POST /analyze/url  [Sandbox URL mode]")
s, d = post_form("/analyze/url", {"url": "https://bit.ly/suspicious-login-portal"})
ok = s == 200 and "score" in d
results.append(ok)
print("  HTTP", s, " score=", d.get("score"), " verdict=", d.get("verdict"))
print("  PASS:", ok)
print()

# ---- Test 3 ---------------------------------------------------------------
print("TEST 3: POST /feedback  [Sandbox 'BLOCK SOURCE' button]")
s, d = post_form("/feedback", {
    "analysis_id":      "sandbox-test-01",
    "user_verdict":     "scam",
    "original_score":   "82",
    "original_verdict": "HIGH RISK",
    "source":           "text",
    "original_input":   "URGENT! bit.ly/secure-login-now",
    "comment":          "Blocked from Threat Sandbox",
})
ok = s == 200 and d.get("status") == "feedback recorded"
results.append(ok)
print("  HTTP", s, " status=", d.get("status"))
print("  PASS:", ok)
print()

# ---- Test 4 ---------------------------------------------------------------
print("TEST 4: GET /docs  [Hero 'View Documentation' button]")
try:
    with urllib.request.urlopen(BASE + "/docs", timeout=10) as r:
        html = r.read().decode(errors="replace")
        ok = r.status == 200 and len(html) > 100
        results.append(ok)
        print("  HTTP", r.status, " HTML chars=", len(html),
              " Swagger=", ("swagger" in html.lower() or "openapi" in html.lower()))
        print("  PASS:", ok)
except Exception as e:
    results.append(False)
    print("  FAIL:", e)
print()

# ---- Test 5 ---------------------------------------------------------------
print("TEST 5: GET /detection-stats  [Live call WebSocket stats]")
try:
    with urllib.request.urlopen(BASE + "/detection-stats", timeout=10) as r:
        data = json.loads(r.read())
        ok = r.status == 200
        results.append(ok)
        print("  HTTP", r.status, " data=", data)
        print("  PASS:", ok)
except Exception as e:
    results.append(False)
    print("  FAIL:", e)
print()

# ---- Summary ---------------------------------------------------------------
passed = sum(results)
total  = len(results)
sep = "=" * 50
print(sep)
print("RESULTS:", passed, "/", total, "PASSED")
print(sep)
sys.exit(0 if passed == total else 1)
