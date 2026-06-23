"""
File / Attachment Detector
──────────────────────────
Three-layer pipeline:
  1. YARA rules       – hidden scripts, exploit patterns, obfuscated payloads
  2. ClamAV / VT      – known malware signature scan
  3. File type + meta  – extension risk, file size anomalies
"""

import os
import io
import hashlib
from typing import Dict, Any, List, Tuple

from core.threat_score import ThreatScore


# ── YARA Rules ──────────────────────────────────────────────────────────────

YARA_RULES_SOURCE = r"""
rule SuspiciousScript {
    strings:
        $ps1  = "powershell" nocase
        $ps2  = "invoke-expression" nocase
        $cmd  = "cmd.exe" nocase
        $wget = "wget " nocase
        $curl = "curl " nocase
        $b64  = "base64" nocase
        $enc  = "frombase64string" nocase
        $exec = "exec(" nocase
        $eval = "eval(" nocase
    condition:
        3 of them
}

rule PhishingDocument {
    strings:
        $m1 = "AutoOpen" nocase
        $m2 = "Document_Open" nocase
        $m3 = "Shell(" nocase
        $m4 = "WScript.Shell" nocase
        $m5 = "CreateObject" nocase
        $m6 = "Workbook_Open" nocase
    condition:
        2 of them
}

rule ObfuscatedPayload {
    strings:
        $xor      = "xor" nocase
        $rot13    = "rot13" nocase
        $charcode = "charCodeAt" nocase
        $escape   = "unescape(" nocase
        $fromchar = "String.fromCharCode" nocase
    condition:
        2 of them
}

rule EmbeddedURL {
    strings:
        $ip_url = /https?:\/\/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/
        $short1 = "bit.ly" nocase
        $short2 = "tinyurl" nocase
    condition:
        any of them
}

rule CredentialHarvesting {
    strings:
        $p1 = "password" nocase
        $p2 = "username" nocase
        $p3 = "login" nocase
        $p4 = "otp" nocase
        $p5 = "bank account" nocase
        $p6 = "credit card" nocase
        $p7 = "aadhaar" nocase
        $p8 = "ssn" nocase
    condition:
        3 of them
}

rule RansomwareIndicator {
    strings:
        $r1 = "encrypt" nocase
        $r2 = "bitcoin" nocase
        $r3 = "ransom" nocase
        $r4 = "pay" nocase
        $r5 = ".onion" nocase
    condition:
        3 of them
}
"""

RULE_SCORES = {
    "SuspiciousScript": 40,
    "PhishingDocument": 50,
    "ObfuscatedPayload": 45,
    "EmbeddedURL": 20,
    "CredentialHarvesting": 35,
    "RansomwareIndicator": 60,
}


def yara_scan(file_bytes: bytes) -> Tuple[float, List[str]]:
    try:
        import yara
    except ImportError:
        return 0.0, ["python-yara not installed – YARA scan skipped"]

    reasons = []
    score = 0.0
    try:
        rules = yara.compile(source=YARA_RULES_SOURCE)
        matches = rules.match(data=file_bytes)
        for match in matches:
            s = RULE_SCORES.get(match.rule, 20)
            score += s
            reasons.append(f"YARA: {match.rule} matched")
    except Exception as e:
        reasons.append(f"YARA error: {str(e)[:80]}")

    return min(score, 100.0), reasons


# ── ClamAV / VirusTotal ─────────────────────────────────────────────────────

def av_scan(file_bytes: bytes) -> Tuple[float, List[str]]:
    # Try ClamAV first
    try:
        import clamd
        cd = clamd.ClamdUnixSocket()
        result = cd.instream(io.BytesIO(file_bytes))
        status = result.get("stream", ("OK", ""))[0]
        if status == "FOUND":
            return 90.0, [f"ClamAV: malware detected – {result['stream'][1]}"]
        return 0.0, ["ClamAV: clean"]
    except Exception:
        pass

    # Fallback: VirusTotal hash lookup
    vt_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not vt_key:
        return 0.0, []

    try:
        import httpx
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        r = httpx.get(
            f"https://www.virustotal.com/api/v3/files/{sha256}",
            headers={"x-apikey": vt_key}, timeout=8,
        )
        if r.status_code == 200:
            stats = r.json()["data"]["attributes"]["last_analysis_stats"]
            mal = stats.get("malicious", 0)
            total = sum(stats.values()) or 1
            score = min(mal / total * 200, 100.0)
            if mal:
                return score, [f"VirusTotal: {mal}/{total} engines flagged as malicious"]
            return 0.0, ["VirusTotal: clean"]
        elif r.status_code == 404:
            return 0.0, ["VirusTotal: file unknown (not in database)"]
    except Exception:
        pass

    return 0.0, []


# ── Extension / Metadata ────────────────────────────────────────────────────

HIGH_RISK = {".exe", ".bat", ".cmd", ".vbs", ".js", ".ps1", ".msi", ".jar",
             ".scr", ".pif", ".com", ".dll", ".hta", ".wsf", ".cpl"}
MEDIUM_RISK = {".doc", ".docm", ".xls", ".xlsm", ".ppt", ".pptm", ".pdf",
               ".rtf", ".iso", ".img"}


def extension_check(filename: str, file_size: int) -> Tuple[float, List[str]]:
    ext = os.path.splitext(filename.lower())[-1]
    reasons = []
    score = 0.0

    if ext in HIGH_RISK:
        score += 40
        reasons.append(f"High-risk executable file type: {ext}")
    elif ext in MEDIUM_RISK:
        score += 15
        reasons.append(f"Medium-risk file type (may contain macros): {ext}")

    # Double extension trick (e.g., invoice.pdf.exe)
    parts = filename.rsplit(".", 2)
    if len(parts) > 2 and f".{parts[-1].lower()}" in HIGH_RISK:
        score += 30
        reasons.append(f"Double extension trick: {filename}")

    # Suspiciously small executables
    if ext in HIGH_RISK and file_size < 5000:
        score += 15
        reasons.append(f"Suspiciously small executable ({file_size} bytes) – possible dropper")

    return min(score, 80.0), reasons


# ── Main Detector ───────────────────────────────────────────────────────────

class FileDetector:
    def analyze(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        reasons = []
        file_size = len(file_bytes)

        ext_score, ext_reasons = extension_check(filename, file_size)
        reasons.extend(ext_reasons)

        y_score, y_reasons = yara_scan(file_bytes)
        reasons.extend(y_reasons)

        av_score_val, av_reasons = av_scan(file_bytes)
        reasons.extend(av_reasons)

        final = (ext_score * 0.20) + (y_score * 0.40) + (av_score_val * 0.40)

        return ThreatScore.build(
            score=final,
            reasons=reasons,
            source="file",
            raw={
                "filename": filename,
                "size_bytes": file_size,
                "sha256": hashlib.sha256(file_bytes).hexdigest(),
                "extension_score": round(ext_score, 1),
                "yara_score": round(y_score, 1),
                "av_score": round(av_score_val, 1),
            },
        )
