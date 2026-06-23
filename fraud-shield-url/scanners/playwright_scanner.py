"""Playwright-based browser automation for URL detonation"""
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from models import PlaywrightFinding
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class PlaywrightScanner:
    """Local headless browser for detecting phishing patterns and suspicious behavior"""

    # Patterns indicative of phishing/credential harvesting
    PHISHING_KEYWORDS = [
        "password", "login", "signin", "sign in", "authenticate",
        "confirm identity", "verify account", "update payment",
        "verify card", "billing address", "social security",
        "ssn", "OTP", "2FA", "verify phone"
    ]

    SUSPICIOUS_SCRIPT_KEYWORDS = [
        "eval", "document.write", "window.location", "ajax",
        "XMLHttpRequest", "fetch", "keylogger", "steal"
    ]

    def __init__(self):
        self.playwright = None
        self.browser = None

    async def scan(self, url: str, timeout: int = 15) -> Optional[PlaywrightFinding]:
        """
        Visit URL with headless browser and detect phishing indicators.

        Looks for:
        - Login/password forms
        - Redirects and navigation chains
        - Suspicious external requests
        - Malicious scripts

        Returns:
            PlaywrightFinding or None if scan fails
        """
        playwright = None
        browser = None
        context = None
        page = None

        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Intercept requests for analysis
            requests_made = []
            def handle_request(request):
                requests_made.append({
                    "url": request.url,
                    "resource_type": request.resource_type,
                    "method": request.method
                })
            page.on("request", handle_request)

            # Navigate with timeout
            response = await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            # Collect findings
            finding = PlaywrightFinding(
                final_url=page.url,
                response_time_ms=int(response.timing["responseEnd"]) if response else 0
            )

            # Check for forms
            forms = await page.query_selector_all("form")
            login_form_count = 0
            password_field_count = 0

            for form in forms:
                form_html = await form.evaluate("el => el.outerHTML")
                form_lower = form_html.lower()
                if any(keyword in form_lower for keyword in self.PHISHING_KEYWORDS):
                    login_form_count += 1

                password_fields = await form.query_selector_all("input[type='password']")
                password_field_count += len(password_fields)

            finding.login_forms_detected = login_form_count > 0
            finding.password_fields = password_field_count

            # Check all input fields
            all_inputs = await page.query_selector_all("input")
            for input_elem in all_inputs:
                input_type = await input_elem.get_attribute("type")
                if input_type and "password" in input_type.lower():
                    finding.password_fields += 1

            # Analyze scripts
            scripts = await page.query_selector_all("script")
            suspicious_script_count = 0

            for script in scripts:
                script_content = await script.evaluate("el => el.textContent")
                if script_content:
                    script_lower = script_content.lower()
                    if any(keyword in script_lower for keyword in self.SUSPICIOUS_SCRIPT_KEYWORDS):
                        suspicious_script_count += 1

            if suspicious_script_count > 0:
                finding.suspicious_scripts = [f"Suspicious script #{i}" for i in range(1, suspicious_script_count + 1)]

            # External requests (potential C2 or data exfiltration)
            external_domains = set()
            from urllib.parse import urlparse

            page_domain = urlparse(url).netloc
            for req in requests_made:
                req_domain = urlparse(req["url"]).netloc
                if req_domain and req_domain != page_domain and req["resource_type"] in ["xhr", "fetch"]:
                    external_domains.add(req_domain)

            finding.external_requests = [{"domain": domain, "type": "external"} for domain in list(external_domains)[:5]]

            # Get page text preview
            page_text = await page.evaluate("() => document.body.innerText")
            finding.page_text_preview = (page_text[:200] if page_text else "")

            logger.info(f"Playwright scan complete for {url}")
            return finding

        except PlaywrightTimeoutError:
            logger.warning(f"Playwright timeout for {url}")
            return PlaywrightFinding(
                final_url=url,
                errors=["Browser timeout - possibly intentional evasion"]
            )
        except Exception as e:
            logger.error(f"Playwright scan error: {str(e)}")
            return PlaywrightFinding(
                final_url=url,
                errors=[str(e)]
            )
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
