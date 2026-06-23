"""URL Sandbox - FastAPI main application"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime
from typing import Optional

from models import ScanRequest, ScanResponse, ScanFindings
from config import settings
from scanners.virustotal import VirusTotalScanner
from scanners.urlscan import URLScanScanner
from scanners.playwright_scanner import PlaywrightScanner
from scoring import RiskScorer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fraud Shield AI - URL Sandbox",
    description="Real-time behavioral URL analysis and threat scoring",
    version="0.1.0"
)

# Initialize scanners and scorer
vt_scanner = VirusTotalScanner(api_key=settings.virustotal_api_key)
urlscan_scanner = URLScanScanner(api_key=settings.urlscan_api_key)
playwright_scanner = PlaywrightScanner()
risk_scorer = RiskScorer(
    vt_weight=settings.vt_weight,
    urlscan_weight=settings.urlscan_weight,
    playwright_weight=settings.playwright_weight
)

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("URL Sandbox starting up...")
    # TODO: Initialize browser pool for Playwright if needed

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("URL Sandbox shutting down...")
    # TODO: Close browser instances

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "url-sandbox",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/scan-url", response_model=ScanResponse)
async def scan_url(request: ScanRequest) -> ScanResponse:
    """
    Scan a URL for phishing and malicious behavior.
    
    Runs three parallel checks:
    1. VirusTotal - Known-bad database
    2. URLScan.io - Cloud sandbox behavioral report
    3. Playwright - Local headless browser analysis
    
    Returns combined threat score (0-100) with reasoning.
    """
    scan_id = str(uuid.uuid4())
    url_str = str(request.url)
    
    logger.info(f"Starting scan {scan_id} for URL: {url_str}")
    
    try:
        import asyncio
        
        vt_result = await vt_scanner.scan(url_str)
        urlscan_result = await urlscan_scanner.scan(url_str)
        playwright_result = await playwright_scanner.scan(url_str, timeout=request.timeout_override or settings.playwright_timeout)
        
        # Combine findings
        findings = ScanFindings(
            virustotal=vt_result,
            urlscan=urlscan_result,
            playwright=playwright_result
        )
        
        # Calculate risk score
        threat_score, reason = risk_scorer.calculate_score(findings)
        
        # Prepare response
        response = ScanResponse(
            scan_id=scan_id,
            url=url_str,
            threat_score=threat_score,
            reason=reason,
            findings=findings,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Scan {scan_id} complete - Score: {threat_score}/100")
        return response
        
    except Exception as e:
        logger.error(f"Error scanning {url_str}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Fraud Shield AI - URL Sandbox",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "scan": "/scan-url (POST)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port
    )
