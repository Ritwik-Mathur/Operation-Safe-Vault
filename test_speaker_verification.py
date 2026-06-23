#!/usr/bin/env python3
"""
test_speaker_verification.py
─────────────────────────────
End-to-end test for the Voice Enrollment + Speaker Verification feature.

Usage
-----
  # Option A — Direct module test (no server needed)
  python test_speaker_verification.py --mode module \
      --enroll path/to/real_voice.wav \
      --test   path/to/test_call.wav \
      --customer-id cust_001

  # Option B — Live API test (server must be running: uvicorn main:app)
  python test_speaker_verification.py --mode api \
      --enroll path/to/real_voice.wav \
      --test   path/to/test_call.wav \
      --customer-id cust_001 \
      --base-url http://localhost:8000

Requirements (for module mode):
  pip install speechbrain torchaudio numpy

Requirements (for api mode):
  pip install requests
  (server must be running in another terminal)
"""

import argparse
import json
import sys
import os

# ── Helpers ──────────────────────────────────────────────────────────────────

def print_section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def print_result(label: str, value):
    if isinstance(value, float):
        print(f"  {label:<30} {value:.4f}")
    elif isinstance(value, bool):
        icon = "✅" if value else "❌"
        print(f"  {label:<30} {icon}  {value}")
    else:
        print(f"  {label:<30} {value}")


# ── Module-mode test (bypasses FastAPI) ──────────────────────────────────────

def test_module_mode(enroll_path: str, test_path: str, customer_id: str):
    print_section("MODE: Direct Python module test")

    # Add backend/ to path so imports resolve
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    try:
        from core.speaker_verification import enroll_speaker, verify_speaker, is_enrolled
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        print("     Make sure speechbrain + torchaudio are installed:")
        print("     pip install speechbrain torchaudio")
        sys.exit(1)

    # ── Step 1: Enroll ───────────────────────────────────────────────────────
    print_section("Step 1 — Enroll speaker")
    with open(enroll_path, "rb") as f:
        enroll_bytes = f.read()

    filename = os.path.basename(enroll_path)
    try:
        result = enroll_speaker(customer_id, enroll_bytes, filename)
        print_result("customer_id",     result["customer_id"])
        print_result("enrolled",         result["enrolled"])
        print_result("embedding_dim",    result["embedding_dim"])
        print_result("enrollment_path",  result["enrollment_path"])
        print(f"\n  ✅ Enrollment successful!")
    except Exception as e:
        print(f"  ❌ Enrollment failed: {e}")
        sys.exit(1)

    # ── Step 2: Verify with same audio (should match) ────────────────────────
    print_section("Step 2 — Verify with SAME audio (expected: MATCH)")
    sim, matched = verify_speaker(customer_id, enroll_bytes, filename)
    print_result("similarity_score",    sim)
    print_result("is_match",            matched)
    if matched:
        print("  ✅ PASS — Same-speaker verification returned is_match=True")
    else:
        print("  ⚠️  WARN — Same audio didn't match (similarity below 0.75)")

    # ── Step 3: Verify with test audio ──────────────────────────────────────
    print_section("Step 3 — Verify with TEST audio")
    with open(test_path, "rb") as f:
        test_bytes = f.read()

    test_filename = os.path.basename(test_path)
    sim2, matched2 = verify_speaker(customer_id, test_bytes, test_filename)
    print_result("similarity_score",    sim2)
    print_result("is_match",            matched2)

    if matched2:
        print("  ✅ Test voice MATCHES enrolled profile — same speaker confirmed")
    else:
        print("  ❌ Test voice does NOT match — possible impersonation / different speaker")

    # ── Step 4: is_enrolled check ────────────────────────────────────────────
    print_section("Step 4 — is_enrolled() check")
    enrolled = is_enrolled(customer_id)
    print_result("is_enrolled",         enrolled)
    fake_enrolled = is_enrolled("nonexistent_customer_xyz")
    print_result("nonexistent customer", fake_enrolled)

    print_section("All module tests done!")


# ── API-mode test (hits live FastAPI server) ──────────────────────────────────

def test_api_mode(enroll_path: str, test_path: str, customer_id: str, base_url: str):
    print_section(f"MODE: Live API test  →  {base_url}")

    try:
        import requests
    except ImportError:
        print("  ❌ 'requests' not installed. Run: pip install requests")
        sys.exit(1)

    # ── Step 1: Enroll ───────────────────────────────────────────────────────
    print_section("Step 1 — POST /enroll-voice")
    with open(enroll_path, "rb") as f:
        resp = requests.post(
            f"{base_url}/enroll-voice",
            data={"customer_id": customer_id},
            files={"audio": (os.path.basename(enroll_path), f, "audio/wav")},
            timeout=120,  # model download can take a while on first run
        )

    if resp.status_code == 200:
        data = resp.json()
        print_result("customer_id",    data.get("customer_id"))
        print_result("enrolled",        data.get("enrolled"))
        print_result("embedding_dim",   data.get("embedding_dim"))
        print_result("analysis_id",     data.get("analysis_id"))
        print("  ✅ Enrollment successful!")
    else:
        print(f"  ❌ HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    # ── Step 2: Analyze voice WITHOUT customer_id (baseline) ─────────────────
    print_section("Step 2 — POST /analyze/voice  (no customer_id)")
    with open(test_path, "rb") as f:
        resp = requests.post(
            f"{base_url}/analyze/voice",
            files={"audio": (os.path.basename(test_path), f, "audio/wav")},
            timeout=120,
        )

    if resp.status_code == 200:
        data = resp.json()
        print_result("score",           data.get("score"))
        print_result("verdict",         data.get("verdict"))
        print_result("speaker_match_score", data.get("speaker_match_score", "(not set — expected)"))
        print_result("speaker_verified",    data.get("speaker_verified", "(not set — expected)"))
        print("  ✅ Baseline voice analysis done (no speaker check)")
    else:
        print(f"  ❌ HTTP {resp.status_code}: {resp.text[:300]}")

    # ── Step 3: Analyze voice WITH customer_id ───────────────────────────────
    print_section(f"Step 3 — POST /analyze/voice  (customer_id={customer_id!r})")
    with open(test_path, "rb") as f:
        resp = requests.post(
            f"{base_url}/analyze/voice",
            data={"customer_id": customer_id},
            files={"audio": (os.path.basename(test_path), f, "audio/wav")},
            timeout=120,
        )

    if resp.status_code == 200:
        data = resp.json()
        print_result("score",                data.get("score"))
        print_result("verdict",              data.get("verdict"))
        print_result("speaker_match_score",  data.get("speaker_match_score"))
        print_result("speaker_verified",     data.get("speaker_verified"))
        print("\n  Reasons:")
        for r in data.get("reasons", []):
            if "speaker" in r.lower() or "Speaker" in r or "Voice" in r:
                print(f"    → {r}")
        print(f"\n  Full raw: {json.dumps(data.get('raw', {}), indent=4)}")

        if data.get("speaker_verified"):
            print("  ✅ Speaker VERIFIED — test audio matches enrolled profile")
        else:
            score = data.get("speaker_match_score")
            print(f"  ❌ Speaker NOT verified — similarity={score} (threshold=0.75)")
    else:
        print(f"  ❌ HTTP {resp.status_code}: {resp.text[:300]}")

    print_section("All API tests done!")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="End-to-end test for FraudShield AI speaker verification"
    )
    parser.add_argument(
        "--mode",
        choices=["module", "api"],
        default="module",
        help="'module' = direct Python import (no server needed). "
             "'api'    = hit live FastAPI server.",
    )
    parser.add_argument(
        "--enroll",
        required=True,
        metavar="AUDIO_FILE",
        help="Path to the enrollment audio file (the 'real' customer voice).",
    )
    parser.add_argument(
        "--test",
        required=True,
        metavar="AUDIO_FILE",
        help="Path to the test audio file (the live call to verify).",
    )
    parser.add_argument(
        "--customer-id",
        default="test_customer_001",
        help="Customer ID to enroll / verify against (default: test_customer_001).",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running FastAPI server (api mode only).",
    )

    args = parser.parse_args()

    # Validate files exist
    for path, label in [(args.enroll, "--enroll"), (args.test, "--test")]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} file not found: {path}")
            sys.exit(1)

    if args.mode == "module":
        test_module_mode(args.enroll, args.test, args.customer_id)
    else:
        test_api_mode(args.enroll, args.test, args.customer_id, args.base_url)


if __name__ == "__main__":
    main()
