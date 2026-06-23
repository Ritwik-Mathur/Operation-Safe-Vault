"""
Voice Module — FastAPI Server (Fixed)
Fixes:
  1. Correct temp file path (next to this file, not CWD)
  2. Fixed import path (works from Fraud_Detection_shield/ directory)
  3. Returns full structured result
"""
import os
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

try:
    from voice_module.detector import analyze_voice
except ImportError:
    from detector import analyze_voice

app = FastAPI(
    title="Fraud Shield AI — Voice Guard",
    description="Real-time voice fraud + deepfake detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store temp files next to this script, not wherever uvicorn is run from
TEMP_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
async def root():
    return {
        "service": "Fraud Shield AI — Voice Guard",
        "status": "running",
        "endpoints": {
            "analyze": "POST /analyze_voice  (upload a .wav file)",
            "health":  "GET  /health"
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice_guard"}


@app.post("/analyze_voice")
async def analyze(file: UploadFile = File(...)):
    """
    Upload a .wav audio file and get a fraud threat score.
    Returns: score (0-100), risk level, verdict, reasons, transcript.
    """
    # Save uploaded file with unique name to avoid conflicts
    filename = f"temp_{uuid.uuid4().hex[:8]}.wav"
    file_path = os.path.join(TEMP_DIR, filename)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = analyze_voice(file_path)
        result["filename"] = file.filename
        return result

    except Exception as e:
        return {
            "score": 0,
            "risk": "ERROR",
            "verdict": "Analysis failed",
            "reasons": [str(e)],
            "transcript": "",
            "filename": file.filename
        }
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)