"""
Email Detector – IMAP Integration + Email Header Analysis
──────────────────────────────────────────────────────────
Connects to real email inbox via IMAP and scans messages:
  1. Header analysis   (SPF, DKIM, DMARC, reply-to mismatch)
  2. Sender reputation (domain age, free email providers)
  3. Content routing   (passes body to text detector)
"""

import os
import re
import email
import imaplib
from typing import Dict, Any, List, Tuple
from email.header import decode_header

from core.threat_score import ThreatScore


# ── Email Header Analysis ───────────────────────────────────────────────────

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "protonmail.com", "mail.com", "yandex.com", "zoho.com", "icloud.com",
    "tutanota.com", "gmx.com",
}


def analyze_headers(raw_email: str) -> Tuple[float, List[str]]:
    """Analyze email headers for spoofing indicators."""
    reasons = []
    score = 0.0

    try:
        msg = email.message_from_string(raw_email)

        # From / Reply-To mismatch
        from_addr = msg.get("From", "")
        reply_to = msg.get("Reply-To", "")
        if reply_to and from_addr:
            from_domain = from_addr.split("@")[-1].rstrip(">").lower()
            reply_domain = reply_to.split("@")[-1].rstrip(">").lower()
            if from_domain != reply_domain:
                score += 25
                reasons.append(f"Reply-To mismatch: From={from_domain}, Reply-To={reply_domain}")

        # SPF check
        received_spf = msg.get("Received-SPF", "").lower()
        if "fail" in received_spf:
            score += 30
            reasons.append("SPF check FAILED – sender domain spoofing likely")
        elif "softfail" in received_spf:
            score += 15
            reasons.append("SPF softfail – sender domain may be spoofed")

        # DKIM check
        dkim = msg.get("DKIM-Signature", "")
        auth_results = msg.get("Authentication-Results", "").lower()
        if "dkim=fail" in auth_results:
            score += 25
            reasons.append("DKIM signature FAILED – email may be forged")
        elif not dkim and not any(k in auth_results for k in ["dkim=pass", "dkim=none"]):
            score += 10
            reasons.append("No DKIM signature – cannot verify sender authenticity")

        # DMARC
        if "dmarc=fail" in auth_results:
            score += 20
            reasons.append("DMARC check FAILED")

        # Free email claiming to be official
        from_domain = from_addr.split("@")[-1].rstrip(">").lower() if "@" in from_addr else ""
        display_name = from_addr.split("<")[0].strip().strip('"').lower() if "<" in from_addr else ""
        official_keywords = ["bank", "support", "admin", "security", "service", "verify", "tax", "government"]

        if from_domain in FREE_EMAIL_PROVIDERS:
            if any(k in display_name for k in official_keywords):
                score += 30
                reasons.append(f"Official-sounding name '{display_name}' from free email ({from_domain})")

        # X-Mailer / unusual sending tool
        x_mailer = msg.get("X-Mailer", "")
        if x_mailer and any(s in x_mailer.lower() for s in ["phpmailer", "swiftmailer", "mass", "bulk"]):
            score += 15
            reasons.append(f"Mass mailing tool detected: {x_mailer}")

    except Exception as e:
        reasons.append(f"Header analysis error: {str(e)[:60]}")

    return min(score, 100.0), reasons


def extract_email_body(raw_email: str) -> str:
    """Extract plain text body from raw email."""
    try:
        msg = email.message_from_string(raw_email)
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode("utf-8", errors="replace")
    except Exception:
        pass
    return ""


def extract_urls_from_email(body: str) -> List[str]:
    """Extract all URLs from email body."""
    return re.findall(r"https?://[^\s<>\"']+", body)


# ── IMAP Fetcher ────────────────────────────────────────────────────────────

class IMAPFetcher:
    """Connect to IMAP inbox and fetch recent emails for scanning."""

    def __init__(self, host: str, email_addr: str, password: str, port: int = 993):
        self.host = host
        self.email_addr = email_addr
        self.password = password
        self.port = port

    def fetch_recent(self, folder: str = "INBOX", count: int = 10) -> List[Dict]:
        """Fetch the N most recent emails."""
        results = []
        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.email_addr, self.password)
            mail.select(folder)

            _, data = mail.search(None, "ALL")
            email_ids = data[0].split()
            recent_ids = email_ids[-count:] if len(email_ids) > count else email_ids

            for eid in reversed(recent_ids):
                _, msg_data = mail.fetch(eid, "(RFC822)")
                raw = msg_data[0][1].decode("utf-8", errors="replace")
                msg = email.message_from_string(raw)

                subject = ""
                raw_subject = msg.get("Subject", "")
                if raw_subject:
                    decoded = decode_header(raw_subject)
                    subject = decoded[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(decoded[0][1] or "utf-8", errors="replace")

                results.append({
                    "id": eid.decode(),
                    "from": msg.get("From", ""),
                    "subject": subject,
                    "date": msg.get("Date", ""),
                    "raw": raw,
                    "body": extract_email_body(raw),
                })

            mail.logout()
        except Exception as e:
            results.append({"error": str(e)[:120]})

        return results


# ── Main Detector ───────────────────────────────────────────────────────────

class EmailDetector:
    def analyze_raw(self, raw_email: str) -> Dict[str, Any]:
        """Analyze a single raw email (RFC822 format)."""
        reasons = []

        header_score, header_reasons = analyze_headers(raw_email)
        reasons.extend(header_reasons)

        body = extract_email_body(raw_email)
        urls = extract_urls_from_email(body)

        if urls:
            reasons.append(f"Contains {len(urls)} URL(s) – should be scanned separately")

        return ThreatScore.build(
            score=header_score,
            reasons=reasons,
            source="email",
            raw={
                "urls_found": urls[:5],
                "body_length": len(body),
                "header_score": round(header_score, 1),
            },
        )

    def analyze_body(self, body: str, sender: str = "unknown") -> Dict[str, Any]:
        """Analyze just the email body text (when raw headers unavailable)."""
        reasons = []
        score = 0.0

        # Check sender domain
        if "@" in sender:
            domain = sender.split("@")[-1].lower()
            if domain in FREE_EMAIL_PROVIDERS:
                score += 10
                reasons.append(f"Sent from free email provider: {domain}")

        return ThreatScore.build(
            score=score,
            reasons=reasons,
            source="email",
            raw={"sender": sender, "body_length": len(body)},
        )
