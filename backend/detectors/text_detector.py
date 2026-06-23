"""
Text Detector – SMS / Email scam analysis (Enhanced)
─────────────────────────────────────────────────────
Four-layer pipeline:
  1. NLP intent classification      (Groq Llama 3.3 70B)
  2. Stylometry analysis            (rule-based heuristics)
  3. Vector similarity              (ChromaDB semantic search)
  4. AI-generated text detection    (Groq Llama 3.3 70B)
"""

import os
import re
import json
from typing import Dict, Any, List, Tuple

from groq import Groq

from core.vector_db import VectorDB
from core.threat_score import ThreatScore
from middleware.shadow_guard import scrub_pii
from middleware.dlp_guard import CANARY_INSTRUCTION


# ── Layer 1: Stylometry ─────────────────────────────────────────────────────

URGENCY_WORDS = [
    # English
    "urgent", "immediately", "now", "expire", "suspend", "blocked",
    "verify", "confirm", "act now", "limited time", "within 24 hours",
    "deactivate", "arrest", "penalty", "overdue", "last chance",
    "time is running out", "respond immediately",
    # Hindi / Hinglish
    "turant", "abhi", "jaldi", "band ho jayega", "band kar denge",
    "suspend ho jayega", "verify karo", "confirm karo", "sirf 24 ghante",
    "kal tak", "aaj hi", "abhi karo", "phone mat katna", "line pe raho",
    "warna action liya jayega", "warna case hoga", "ek ghante mein",
    "der mat karo", "abhi nahi toh",
    # Devanagari
    "अभी करो", "तुरंत करो", "जल्दी करो", "आज ही", "देर मत करो",
    "फोन मत काटना", "लाइन पे रहो", "वरना केस होगा", "बंद हो जाएगा",
    "ब्लॉक हो जाएगा", "अभी नहीं तो",
]
REWARD_WORDS = [
    # English
    "won", "winner", "prize", "lottery", "congratulations", "selected",
    "lucky", "claim", "free", "gift", "offer", "reward", "bonus",
    # Hindi / Hinglish
    "jeeta hai", "lucky draw", "inaam", "inam", "jeet liya",
    "free milega", "gift milega", "chunaa gaya", "selected ho gaye",
    "car jeeti", "ek crore", "lucky draw jeeta", "claim karo",
    # Devanagari
    "लकी ड्रा", "इनाम", "पुरस्कार", "जीत गए", "क्लेम करो",
    "मुफ्त", "लॉटरी", "करोड़ रुपये", "इनाम मिला",
]
THREAT_WORDS = [
    # English
    "arrest", "legal action", "fir", "police", "court", "sue", "penalty",
    "blocked", "suspended", "terminated", "prosecution", "warrant",
    "digital arrest", "non-bailable warrant", "cyber crime",
    # Hindi / Hinglish
    "giraftaar", "arrest ho jayenge", "police aa jayegi", "fir darj",
    "jail jayenge", "kanuni karyavahi", "case darj", "warrant aayega",
    "pakad lenge", "action lenge", "digital arrest", "cbi officer",
    "ed officer", "income tax notice", "cyber crime department",
    # Devanagari
    "गिरफ्तारी", "अरेस्ट", "डिजिटल अरेस्ट", "पुलिस आएगी",
    "केस दर्ज", "एफआईआर", "वारंट", "साइबर क्राइम", "सीबीआई",
    "प्रवर्तन निदेशालय", "आयकर नोटिस",
]
SENSITIVE_ASK = [
    # English
    "otp", "password", "pin", "cvv", "card number", "aadhaar", "pan",
    "bank account", "upi", "share your", "send your", "credit card",
    "debit card", "social security", "routing number", "net banking",
    "remote access", "teamviewer", "anydesk", "screen share",
    # Hindi / Hinglish
    "otp batao", "otp bhejo", "otp share karo", "number batao",
    "account number do", "password batao", "pin batao", "card details do",
    "bank details do", "upi pin", "aadhaar number do", "details share karo",
    "paisa transfer karo", "paise bhejo", "safe account mein transfer",
    "kyc update karo", "kyc verify karo", "kisi ko mat batana",
    # Devanagari
    "ओटीपी", "ओटीपी बताओ", "पासवर्ड बताओ", "पिन बताओ",
    "आधार नंबर", "पैन कार्ड", "बैंक डिटेल्स", "खाता नंबर",
    "यूपीआई पिन", "केवाईसी", "पैसे ट्रांसफर", "किसी को मत बताना",
]


def stylometry_score(text: str) -> Tuple[float, List[str]]:
    lower = text.lower()
    reasons = []
    score = 0.0

    urgency_hits = [w for w in URGENCY_WORDS if w in lower]
    if urgency_hits:
        score += min(30, len(urgency_hits) * 7)
        reasons.append(f"Urgency language: {', '.join(urgency_hits[:4])}")

    reward_hits = [w for w in REWARD_WORDS if w in lower]
    if reward_hits:
        score += min(25, len(reward_hits) * 7)
        reasons.append(f"Reward/prize language: {', '.join(reward_hits[:4])}")

    threat_hits = [w for w in THREAT_WORDS if w in lower]
    if threat_hits:
        score += min(30, len(threat_hits) * 9)
        reasons.append(f"Threat language: {', '.join(threat_hits[:4])}")

    sensitive_hits = [w for w in SENSITIVE_ASK if w in lower]
    if sensitive_hits:
        score += min(35, len(sensitive_hits) * 11)
        reasons.append(f"Requesting sensitive info: {', '.join(sensitive_hits[:4])}")

    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.3:
        score += 10
        reasons.append("Excessive capitalization (urgency signal)")

    if re.search(r"(bit\.ly|tinyurl|t\.co|goo\.gl|tiny\.cc|ow\.ly|rb\.gy|cutt\.ly)", lower):
        score += 15
        reasons.append("URL shortener found in message")

    # Grammar issues (common in scam texts)
    if re.search(r"dear (customer|user|sir|madam|valued)", lower):
        score += 8
        reasons.append("Generic greeting pattern (common in scam templates)")

    return min(score, 100.0), reasons


# ── Layer 2: NLP Intent via Claude ──────────────────────────────────────────

NLP_SYSTEM = """You are a scam detection engine specializing in Indian fraud patterns. You understand English, Hindi, Hinglish (mixed Hindi-English), and Devanagari script equally well. Always analyze the full message regardless of language.
Analyze the message and return ONLY valid JSON:
{
  "is_scam": true/false,
  "confidence": 0-100,
  "intent": "phishing|banking_fraud|government_impersonation|tech_support|kyc_scam|prize_scam|job_scam|family_emergency|legitimate|unknown",
  "reasoning": "one sentence in English"
}
Detect these Indian scam patterns in ANY language:
- Banking fraud: OTP/CVV/PIN requests, fake bank calls, account block/suspend threats
- Government impersonation: fake CBI/ED/Income Tax/TRAI/RBI/police officers, digital arrest threats
- KYC scams: fake KYC update requests from banks or UPI apps
- Delivery scams: fake Amazon/customs/courier fee demands
- Prize/lottery scams: lucky draw, inaam, car/cash prize claims
- Job scams: work from home, earn per day, registration fee
- Family emergency: distressed relative from new number asking for money
- Urgency + isolation: "kisi ko mat batana", "don't tell anyone", "stay on the line"
- Remote access: AnyDesk, TeamViewer, screen share requests
High confidence indicators: requests for OTP/password/Aadhaar/PAN, threats of arrest, money transfer to "safe account", isolation tactics.""" + CANARY_INSTRUCTION


def nlp_analyze(text: str) -> Tuple[float, str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return 0.0, "unknown", "GROQ_API_KEY not set – NLP skipped"
    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[
                {"role": "system", "content": NLP_SYSTEM},
                {"role": "user", "content": f"Analyze this message:\n\n{scrub_pii(text)}"},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw)
        score = float(data.get("confidence", 0)) if data.get("is_scam") else 0.0
        return score, data.get("intent", "unknown"), data.get("reasoning", "")
    except Exception as e:
        return 0.0, "unknown", f"NLP error: {str(e)[:80]}"


# ── Layer 3: AI-Generated Text Detection ────────────────────────────────────

AI_DETECT_SYSTEM = """You detect AI-generated text. Analyze the writing style and return ONLY valid JSON:
{
  "is_ai_generated": true/false,
  "confidence": 0-100,
  "indicators": ["list of specific indicators"]
}
Look for: uniform sentence structure, lack of typos in phishing context, overly polished grammar, generic phrasing, unusual formality.""" + CANARY_INSTRUCTION


def detect_ai_generated(text: str) -> Tuple[float, List[str]]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return 0.0, []
    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[
                {"role": "system", "content": AI_DETECT_SYSTEM},
                {"role": "user", "content": scrub_pii(text)},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw)
        if data.get("is_ai_generated"):
            conf = float(data.get("confidence", 0))
            indicators = data.get("indicators", [])
            return conf * 0.3, [f"AI-generated text detected ({conf}% conf): {', '.join(indicators[:3])}"]
        return 0.0, []
    except Exception:
        return 0.0, []


# ── Main Detector ───────────────────────────────────────────────────────────

class TextDetector:
    def __init__(self, vector_db: VectorDB):
        self.db = vector_db

    def analyze(self, message: str, sender: str = "unknown", channel: str = "sms") -> Dict[str, Any]:
        reasons = []

        # Layer 1 – Stylometry
        stylo_score, stylo_reasons = stylometry_score(message)
        reasons.extend(stylo_reasons)

        # Layer 2 – NLP Intent
        nlp_s, intent, nlp_reason = nlp_analyze(message)
        if nlp_reason:
            reasons.append(f"NLP: {nlp_reason}")

        # Layer 3 – Vector similarity
        similar = self.db.query_similarity(message)
        vector_score = 0.0
        if similar:
            top = similar[0]
            vector_score = top["similarity_pct"]
            if vector_score > 55:
                reasons.append(
                    f"Similar to known scam ({top['similarity_pct']}%): \"{top['template'][:50]}...\""
                )

        # Layer 4 – AI-generated detection
        ai_score, ai_reasons = detect_ai_generated(message)
        reasons.extend(ai_reasons)

        # Weighted combination
        final = (stylo_score * 0.25) + (nlp_s * 0.35) + (vector_score * 0.25) + (ai_score * 0.15)

        return ThreatScore.build(
            score=final,
            reasons=reasons,
            source="text",
            raw={
                "channel": channel,
                "sender": sender,
                "stylometry_score": round(stylo_score, 1),
                "nlp_score": round(nlp_s, 1),
                "nlp_intent": intent,
                "vector_score": round(vector_score, 1),
                "ai_gen_score": round(ai_score, 1),
                "similar_templates": similar[:2],
            },
        )
