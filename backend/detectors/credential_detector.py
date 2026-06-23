"""
Credential Detector – Regex + NER + Entropy Analysis
─────────────────────────────────────────────────────
Detects credential harvesting attempts in text:
  1. Regex patterns – known sensitive data formats
  2. NER (Named Entity Recognition) – extract entities that look like credentials
  3. Entropy analysis – detect obfuscated/encoded data (base64, hex)
"""

import re
import math
from typing import Dict, Any, List, Tuple

from core.threat_score import ThreatScore


# ── Layer 1: Regex Credential Patterns ──────────────────────────────────────

CREDENTIAL_PATTERNS = [
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "Credit/Debit Card Number", 40),
    (r"\b\d{4}\s\d{4}\s\d{4}\b", "Aadhaar Number", 35),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "PAN Number", 35),
    (r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b", "SSN Pattern", 35),
    (r"\b\d{9,18}\b", "Bank Account Number", 20),
    (r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "IFSC Code", 15),
    (r"\bIBAN\s?[A-Z]{2}\d{2}\b", "IBAN Number", 25),
    (r"\bcvv\s*[:=]?\s*\d{3,4}\b", "CVV Number", 45),
    (r"\bpin\s*[:=]?\s*\d{4,6}\b", "PIN Number", 40),
    (r"\botp\s*[:=]?\s*\d{4,8}\b", "OTP Code", 40),
    (r"\bpassword\s*[:=]\s*\S+", "Exposed Password", 45),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email Address", 10),
]


def regex_scan(text: str) -> Tuple[float, List[str]]:
    reasons = []
    score = 0.0
    for pattern, label, weight in CREDENTIAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            score += weight
            reasons.append(f"Detected {label} ({len(matches)} instance{'s' if len(matches) > 1 else ''})")
    return min(score, 100.0), reasons


# ── Layer 2: NER-style Entity Extraction ────────────────────────────────────

REQUEST_PATTERNS = [
    (r"(share|send|provide|enter|type|input|give|submit)\s+(your|the|ur)\s+(\w+)", "Credential Request", 25),
    (r"(verify|confirm|validate|update)\s+(your|the)\s+(account|identity|details|information)", "Verification Request", 20),
    (r"(click|tap|open)\s+(this|the|here|below)\s*(link|url|button)?", "Action Request", 15),
    (r"(log\s*in|sign\s*in)\s+(to|at|here)", "Login Request", 20),
    (r"(fill|complete)\s+(this|the)\s+(form|survey|application)", "Form Fill Request", 15),
]


def ner_scan(text: str) -> Tuple[float, List[str]]:
    lower = text.lower()
    reasons = []
    score = 0.0
    for pattern, label, weight in REQUEST_PATTERNS:
        if re.search(pattern, lower):
            score += weight
            reasons.append(f"NER: {label} pattern detected")
    return min(score, 80.0), reasons


# ── Layer 3: Entropy Analysis ───────────────────────────────────────────────

def shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string. High entropy = possible encoded data."""
    if not text:
        return 0.0
    freq = {}
    for c in text:
        freq[c] = freq.get(c, 0) + 1
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def entropy_scan(text: str) -> Tuple[float, List[str]]:
    reasons = []
    score = 0.0

    # Check for base64-encoded chunks
    b64_chunks = re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text)
    for chunk in b64_chunks:
        ent = shannon_entropy(chunk)
        if ent > 5.0:
            score += 25
            reasons.append(f"High-entropy base64 chunk detected (entropy: {ent:.1f})")
            break

    # Check for hex-encoded chunks
    hex_chunks = re.findall(r"(?:0x)?[0-9a-fA-F]{16,}", text)
    if hex_chunks:
        score += 20
        reasons.append(f"Hex-encoded data detected ({len(hex_chunks)} chunk{'s' if len(hex_chunks) > 1 else ''})")

    # Overall text entropy check (obfuscated messages tend to have high entropy)
    overall_ent = shannon_entropy(text)
    if overall_ent > 5.5 and len(text) > 50:
        score += 15
        reasons.append(f"Unusually high overall text entropy ({overall_ent:.1f}) – possible obfuscation")

    return min(score, 60.0), reasons


# ── Main Detector ───────────────────────────────────────────────────────────

class CredentialDetector:
    def analyze(self, text: str) -> Dict[str, Any]:
        reasons = []

        # Layer 1 – Regex
        r_score, r_reasons = regex_scan(text)
        reasons.extend(r_reasons)

        # Layer 2 – NER
        n_score, n_reasons = ner_scan(text)
        reasons.extend(n_reasons)

        # Layer 3 – Entropy
        e_score, e_reasons = entropy_scan(text)
        reasons.extend(e_reasons)

        final = (r_score * 0.45) + (n_score * 0.30) + (e_score * 0.25)

        return ThreatScore.build(
            score=final,
            reasons=reasons,
            source="credential",
            raw={
                "regex_score": round(r_score, 1),
                "ner_score": round(n_score, 1),
                "entropy_score": round(e_score, 1),
            },
        )
