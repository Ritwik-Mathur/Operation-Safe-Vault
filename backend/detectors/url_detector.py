"""
URL Detector – Enhanced Multi-Layer URL Phishing Analysis
──────────────────────────────────────────────────────────
Five-layer pipeline:
  1. Heuristic checks        (typosquatting, suspicious TLDs, shorteners)
  2. SSL certificate check   (validity, issuer, expiry)
  3. WHOIS lookup            (domain age, registrar)
  4. Playwright sandbox      (behavioral analysis – redirects, credential forms)
  5. VirusTotal API          (community threat intelligence)
"""

import os
import re
import ssl
import socket
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse
from datetime import datetime

from core.threat_score import ThreatScore


# ── Layer 1: Heuristic Checks ───────────────────────────────────────────────

SUSPICIOUS_TLDS = {".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click",
                   ".download", ".zip", ".mov", ".loan", ".work", ".buzz"}
URL_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "tiny.cc",
                  "rb.gy", "cutt.ly", "is.gd", "v.gd", "shorturl.at"}
BRAND_KEYWORDS = [
    "paypal", "amazon", "google", "microsoft", "apple", "netflix",
    "facebook", "instagram", "whatsapp", "bank", "sbi", "hdfc", "icici",
    "paytm", "phonepe", "upi", "aadhaar", "incometax", "irctc",
    "flipkart", "gmail", "outlook", "linkedin",
]
LEGIT_DOMAINS = {
    "paypal": "paypal.com", "amazon": "amazon.com", "google": "google.com",
    "microsoft": "microsoft.com", "apple": "apple.com", "netflix": "netflix.com",
    "facebook": "facebook.com", "instagram": "instagram.com", "sbi": "onlinesbi.sbi",
    "paytm": "paytm.com", "flipkart": "flipkart.com",
}


def heuristic_checks(url: str) -> Tuple[float, List[str]]:
    reasons = []
    score = 0.0
    try:
        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        tld = "." + domain.split(".")[-1] if "." in domain else ""

        if tld in SUSPICIOUS_TLDS:
            score += 25
            reasons.append(f"Suspicious TLD: {tld}")

        if any(s in domain for s in URL_SHORTENERS):
            score += 20
            reasons.append("URL shortener – destination hidden")

        for brand in BRAND_KEYWORDS:
            if brand in domain:
                legit = LEGIT_DOMAINS.get(brand)
                if legit and legit != domain and not domain.endswith(f".{legit}"):
                    score += 35
                    reasons.append(f"Brand impersonation: '{brand}' in '{domain}' (real: {legit})")

        if re.match(r"\d{1,3}(\.\d{1,3}){3}", domain):
            score += 30
            reasons.append("IP address used instead of domain name")

        parts = domain.split(".")
        if len(parts) > 4:
            score += 15
            reasons.append(f"Excessive subdomains ({len(parts) - 2})")

        # Homograph / typosquatting
        if re.search(r"[0oO][1lI]|[1lI][0oO]|rn(?=\w)|vv", domain):
            score += 20
            reasons.append("Possible homograph/typosquat attack in domain")

        cred_words = ["login", "signin", "verify", "update", "secure", "account", "password", "otp", "confirm"]
        path_hits = [w for w in cred_words if w in path]
        if path_hits:
            score += min(20, len(path_hits) * 7)
            reasons.append(f"Credential harvesting path: {', '.join(path_hits)}")

        if parsed.scheme == "http":
            score += 10
            reasons.append("No HTTPS – unencrypted")

        # Excessively long URL
        if len(url) > 200:
            score += 10
            reasons.append(f"Unusually long URL ({len(url)} chars) – possible obfuscation")

    except Exception as e:
        reasons.append(f"URL parse error: {e}")

    return min(score, 100.0), reasons


# ── Layer 2: SSL Certificate Check ──────────────────────────────────────────

def ssl_check(url: str) -> Tuple[float, List[str]]:
    reasons = []
    score = 0.0
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        hostname = parsed.netloc.split(":")[0]
        if not hostname:
            return 0.0, []

        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                # Check expiry
                not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                days_left = (not_after - datetime.utcnow()).days
                if days_left < 0:
                    score += 30
                    reasons.append("SSL certificate has EXPIRED")
                elif days_left < 7:
                    score += 15
                    reasons.append(f"SSL certificate expires in {days_left} days")

                # Check issuer – free/quick certs are suspicious for brand sites
                issuer = dict(x[0] for x in cert.get("issuer", []))
                org = issuer.get("organizationName", "").lower()
                if "let's encrypt" in org:
                    score += 5
                    reasons.append("Free SSL certificate (Let's Encrypt) – common in phishing")

                # Check if cert matches domain
                san = cert.get("subjectAltName", [])
                cert_domains = [v for t, v in san if t == "DNS"]
                if hostname not in cert_domains and f"*.{'.'.join(hostname.split('.')[1:])}" not in cert_domains:
                    score += 25
                    reasons.append("SSL certificate does NOT match domain name")

    except ssl.SSLCertVerificationError as e:
        score += 30
        reasons.append(f"SSL verification failed: {str(e)[:80]}")
    except (socket.timeout, ConnectionRefusedError, OSError):
        score += 10
        reasons.append("Could not establish SSL connection")
    except Exception:
        pass

    return min(score, 60.0), reasons


# ── Layer 3: WHOIS Lookup ───────────────────────────────────────────────────

def whois_check(url: str) -> Tuple[float, List[str]]:
    try:
        import whois
    except ImportError:
        return 0.0, ["python-whois not installed – WHOIS check skipped"]

    reasons = []
    score = 0.0
    try:
        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
        domain = parsed.netloc.split(":")[0]
        w = whois.whois(domain)

        # Domain age
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        if creation:
            age_days = (datetime.now() - creation).days
            if age_days < 30:
                score += 35
                reasons.append(f"Domain registered {age_days} days ago – very new (high risk)")
            elif age_days < 180:
                score += 20
                reasons.append(f"Domain registered {age_days} days ago – relatively new")
            elif age_days < 365:
                score += 10
                reasons.append(f"Domain age: {age_days} days")

        # Privacy protection (common in scam domains)
        registrant = str(w.get("org", "") or w.get("registrant", "") or "")
        if "privacy" in registrant.lower() or "proxy" in registrant.lower():
            score += 10
            reasons.append("WHOIS privacy/proxy service – identity hidden")

    except Exception:
        reasons.append("WHOIS lookup failed – domain may not exist")
        score += 15

    return min(score, 60.0), reasons


# ── Layer 4: Playwright Sandbox ─────────────────────────────────────────────

async def sandbox_analysis(url: str) -> Tuple[float, List[str]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return 0.0, ["Playwright not installed – sandbox skipped"]

    score = 0.0
    reasons = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            redirects = []
            page.on("response", lambda r: redirects.append(r.url) if r.status in (301, 302, 303, 307, 308) else None)

            downloads = []
            page.on("download", lambda d: downloads.append(d.suggested_filename))

            try:
                await page.goto(url, timeout=12000, wait_until="domcontentloaded")
            except Exception as e:
                reasons.append(f"Page load failed: {str(e)[:60]}")
                await browser.close()
                return 15.0, reasons

            final_url = page.url

            if len(redirects) > 2:
                score += 20
                reasons.append(f"Redirect chain ({len(redirects)} hops) – possible cloaking")

            if urlparse(final_url).netloc != urlparse(url).netloc:
                score += 25
                reasons.append(f"Redirected to different domain: {urlparse(final_url).netloc}")

            if downloads:
                score += 40
                reasons.append(f"Auto-download triggered: {', '.join(downloads[:3])}")

            pw_fields = await page.locator("input[type='password']").count()
            if pw_fields > 0:
                score += 30
                reasons.append(f"Password field detected ({pw_fields} inputs)")

            otp_fields = await page.locator("input[maxlength='1'], input[maxlength='4'], input[maxlength='6']").count()
            if otp_fields >= 4:
                score += 25
                reasons.append(f"OTP input fields detected ({otp_fields} boxes)")

            title = (await page.title()).lower()
            urgency = ["urgent", "verify", "suspended", "locked", "alert", "warning", "confirm"]
            hits = [w for w in urgency if w in title]
            if hits:
                score += 15
                reasons.append(f"Urgency in page title: {', '.join(hits)}")

            # Check for iframes (often used in phishing)
            iframes = await page.locator("iframe").count()
            if iframes > 2:
                score += 10
                reasons.append(f"Multiple iframes ({iframes}) – possible clickjacking")

            await browser.close()
    except Exception as e:
        reasons.append(f"Sandbox error: {str(e)[:80]}")

    return min(score, 100.0), reasons


# ── Layer 5: VirusTotal ─────────────────────────────────────────────────────

async def virustotal_check(url: str) -> Tuple[float, List[str]]:
    vt_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not vt_key:
        return 0.0, []
    try:
        import httpx, base64
        url_id = base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers={"x-apikey": vt_key}, timeout=8,
            )
            if r.status_code == 200:
                stats = r.json()["data"]["attributes"]["last_analysis_stats"]
                mal = stats.get("malicious", 0)
                sus = stats.get("suspicious", 0)
                total = sum(stats.values()) or 1
                score = min((mal + sus) / total * 200, 100.0)
                reasons = []
                if mal:
                    reasons.append(f"VirusTotal: {mal}/{total} engines flagged as malicious")
                if sus:
                    reasons.append(f"VirusTotal: {sus}/{total} engines flagged as suspicious")
                return score, reasons
    except Exception:
        pass
    return 0.0, []


# ── Main Detector ───────────────────────────────────────────────────────────

class URLDetector:
    async def analyze(self, url: str) -> Dict[str, Any]:
        reasons = []

        h_score, h_reasons = heuristic_checks(url)
        reasons.extend(h_reasons)

        ssl_score, ssl_reasons = ssl_check(url)
        reasons.extend(ssl_reasons)

        whois_score, whois_reasons = whois_check(url)
        reasons.extend(whois_reasons)

        s_score, s_reasons = await sandbox_analysis(url)
        reasons.extend(s_reasons)

        vt_score, vt_reasons = await virustotal_check(url)
        reasons.extend(vt_reasons)

        final = (h_score * 0.20) + (ssl_score * 0.15) + (whois_score * 0.15) + (s_score * 0.30) + (vt_score * 0.20)

        return ThreatScore.build(
            score=final,
            reasons=reasons,
            source="url",
            raw={
                "url": url,
                "heuristic_score": round(h_score, 1),
                "ssl_score": round(ssl_score, 1),
                "whois_score": round(whois_score, 1),
                "sandbox_score": round(s_score, 1),
                "virustotal_score": round(vt_score, 1),
            },
        )
