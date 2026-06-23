"""VirusTotal API integration for URL scanning"""
import logging
import httpx
from models import VirusTotalFinding
from typing import Optional

logger = logging.getLogger(__name__)

class VirusTotalScanner:
    """Queries VirusTotal database for known malicious URLs"""
    
    BASE_URL = "https://www.virustotal.com/api/v3"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-apikey": api_key}
    
    async def scan(self, url: str, timeout: int = 10) -> Optional[VirusTotalFinding]:
        """
        Scan a URL against VirusTotal database.
        
        Returns:
            VirusTotalFinding or None if scan fails
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                url_id = self._encode_url(url)
                
                response = await client.get(
                    f"{self.BASE_URL}/urls/{url_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_response(data)
        
        except httpx.HTTPError as e:
            logger.warning(f"VirusTotal API error for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"VirusTotal scan error: {str(e)}")
            return None
    
    def _encode_url(self, url: str) -> str:
        """Convert URL to VirusTotal format (base64 urlsafe encoding)"""
        import base64
        if "://" in url:
            url = url.split("://", 1)[1]
        encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        return encoded
    
    def _parse_response(self, data: dict) -> VirusTotalFinding:
        """Parse VirusTotal API response"""
        try:
            attributes = data.get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            
            return VirusTotalFinding(
                detection_count=stats.get("malicious", 0),
                undetected_count=stats.get("undetected", 0),
                suspicious_count=stats.get("suspicious", 0),
                latest_scan_date=attributes.get("last_analysis_date"),
                categories=attributes.get("last_analysis_results", {}),
                scan_id=data.get("data", {}).get("id")
            )
        except Exception as e:
            logger.error(f"Error parsing VirusTotal response: {str(e)}")
            return VirusTotalFinding(detection_count=0, undetected_count=0, suspicious_count=0)
