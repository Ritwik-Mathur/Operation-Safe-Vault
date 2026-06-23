"""
Central Classification Engine
──────────────────────────────
Routes incoming data to the appropriate detectors and combines results.
This is the brain of Fraud Shield — it decides which detectors to run
based on the type of input and aggregates the output.
"""

from typing import Dict, Any, Optional
from core.threat_score import ThreatScore
from core.vector_db import VectorDB


class CentralClassifier:

    def __init__(self, vector_db: VectorDB):
        self.db = vector_db

    async def classify(
        self,
        message: str = "",
        sender: str = "unknown",
        channel: str = "sms",
        url: str = "",
        audio_bytes: Optional[bytes] = None,
        audio_filename: str = "",
        file_bytes: Optional[bytes] = None,
        file_filename: str = "",
    ) -> Dict[str, Any]:
        """
        Run all applicable detectors and return a combined threat assessment.
        Only runs detectors for which input data is provided.
        """
        results = {}

        if message:
            from detectors.text_detector import TextDetector
            from detectors.credential_detector import CredentialDetector

            text_det = TextDetector(self.db)
            results["text"] = text_det.analyze(message, sender, channel)

            cred_det = CredentialDetector()
            results["credential"] = cred_det.analyze(message)

        if url:
            from detectors.url_detector import URLDetector
            url_det = URLDetector()
            results["url"] = await url_det.analyze(url)

        if audio_bytes:
            from detectors.voice_detector import VoiceDetector
            voice_det = VoiceDetector(vector_db=self.vector_db if hasattr(self, 'vector_db') else None)
            results["voice"] = voice_det.analyze(audio_bytes, audio_filename)

        if file_bytes:
            from detectors.file_detector import FileDetector
            file_det = FileDetector()
            results["file"] = file_det.analyze(file_bytes, file_filename)

        combined = ThreatScore.combine(results)
        return {"components": results, "combined": combined}
