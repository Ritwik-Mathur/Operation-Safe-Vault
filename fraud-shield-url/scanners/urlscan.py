"""URLScan.io integration for behavioral URL analysis"""
import logging
import httpx
import asyncio
from models import URLScanFinding
from typing import Optional

logger = logging.getLogger(__name__)

class URLScanScanner:
    """Queries URLScan.io for behavioral analysis and screenshots"""

    BASE_URL = "https://urlscan.io/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"API-Key": api_key}

    async def scan(self, url: str, timeout: int = 30) -> Optional[URLScanFinding]:
        """
        Submit URL to URLScan.io and retrieve behavioral analysis.

        This function:
        1. Submits the URL for scanning
        2. Waits for scan completion (polling)
        3. Returns findings with screenshot URL

        Returns:
            URLScanFinding or None if scan fails
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                submit_response = await client.post(
                    f"{self.BASE_URL}/scan/",
                    headers=self.headers,
                    json={"url": url, "visibility": "public"}
                )
                submit_response.raise_for_status()
                scan_data = submit_response.json()
                scan_uuid = scan_data.get("uuid")

                if not scan_uuid:
                    logger.warning("URLScan: No UUID returned")
                    return None

                logger.info(f"URLScan submitted: {scan_uuid}")

                result = await self._poll_results(client, scan_uuid, timeout=25)
                return result

        except httpx.HTTPError as e:
            logger.warning(f"URLScan API error for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"URLScan scan error: {str(e)}")
            return None

    async def _poll_results(self, client: httpx.AsyncClient, scan_uuid: str, timeout: int = 25) -> Optional[URLScanFinding]:
        """Poll URLScan.io for scan results"""
        import time
        start_time = time.time()
        poll_interval = 2

        while time.time() - start_time < timeout:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/result/{scan_uuid}/",
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data)
                elif response.status_code == 404:
                    logger.debug(f"Scan {scan_uuid} not ready yet")
                    await asyncio.sleep(poll_interval)
                    poll_interval = min(5, poll_interval + 1)
                else:
                    logger.warning(f"Unexpected status {response.status_code}")
                    await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"Error polling results: {str(e)}")
                await asyncio.sleep(poll_interval)

        logger.warning(f"URLScan timeout for {scan_uuid}")
        return None

    def _parse_response(self, data: dict) -> URLScanFinding:
        """Parse URLScan.io API response"""
        try:
            page = data.get("page", {})
            stats = data.get("stats", {})
            screenshot = data.get("screenshot")

            redirect_chain = []
            if "requests" in data:
                for req in data["requests"]:
                    if req.get("response", {}).get("status") in [301, 302, 303, 307, 308]:
                        redirect_chain.append(req.get("request", {}).get("url", ""))

            ads = data.get("lists", {}).get("ads", [])

            return URLScanFinding(
                scan_uuid=data.get("_id"),
                screenshot_url=screenshot,
                dom_text_length=stats.get("domainsLength", 0),
                page_title=page.get("title"),
                http_status_code=page.get("status"),
                page_domain=page.get("domain"),
                final_url=page.get("url"),
                redirect_chain=redirect_chain,
                ads=ads if isinstance(ads, list) else [],
                matches=data.get("verdicts", {})
            )
        except Exception as e:
            logger.error(f"Error parsing URLScan response: {str(e)}")
            return URLScanFinding()
