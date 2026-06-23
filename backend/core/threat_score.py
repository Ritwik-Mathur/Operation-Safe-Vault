"""
Unified Threat Scoring Engine
─────────────────────────────
Converts raw detector outputs into a threat score (0-100) with:
  - Verdict (SCAM / SUSPECTED / UNCERTAIN / SAFE)
  - Confidence level
  - Fidelity ranking (how trustworthy is this score, based on how many detectors fired)
  - Human-readable reasoning chain
"""

from typing import Dict, Any, List


WEIGHTS = {
    "text": 0.25,
    "credential": 0.20,
    "url": 0.20,
    "voice": 0.15,
    "file": 0.10,
    "email": 0.10,
}

VERDICT_MAP = [
    (80, "SCAM",      "CRITICAL", "HIGH"),
    (55, "SUSPECTED",  "HIGH",     "MEDIUM"),
    (30, "UNCERTAIN",  "MEDIUM",   "LOW"),
    (0,  "SAFE",       "LOW",      "NONE"),
]


def _verdict(score: float):
    for threshold, verdict, severity, confidence in VERDICT_MAP:
        if score >= threshold:
            return verdict, severity, confidence
    return "SAFE", "LOW", "NONE"


def _fidelity(component_results: Dict[str, Dict]) -> str:
    """
    Fidelity ranking: how reliable is this combined score?
    Based on how many detectors actually contributed data.
    """
    active = sum(1 for r in component_results.values() if r.get("score", 0) > 0 or r.get("reasons"))
    total = len(component_results)
    if total == 0:
        return "NONE"
    ratio = active / total
    if ratio >= 0.8:
        return "HIGH"
    elif ratio >= 0.5:
        return "MEDIUM"
    elif ratio > 0:
        return "LOW"
    return "NONE"


class ThreatScore:

    @staticmethod
    def build(
        score: float,
        reasons: List[str],
        source: str,
        raw: Dict[str, Any] = None,
    ) -> Dict:
        score = max(0.0, min(100.0, score))
        verdict, severity, confidence = _verdict(score)
        return {
            "source": source,
            "score": round(score, 1),
            "verdict": verdict,
            "severity": severity,
            "confidence": confidence,
            "reasons": reasons,
            "raw": raw or {},
        }

    @staticmethod
    def combine(component_results: Dict[str, Dict]) -> Dict:
        """Weighted average of all available component scores with fidelity ranking."""
        if not component_results:
            return ThreatScore.build(0, ["No data provided"], "combined")

        total_weight = 0.0
        weighted_sum = 0.0
        all_reasons = []

        for source, result in component_results.items():
            w = WEIGHTS.get(source, 0.15)
            s = result.get("score", 0)
            weighted_sum += s * w
            total_weight += w
            for r in result.get("reasons", []):
                all_reasons.append(f"[{source.upper()}] {r}")

        final_score = weighted_sum / total_weight if total_weight > 0 else 0

        result = ThreatScore.build(final_score, all_reasons, "combined")
        result["fidelity"] = _fidelity(component_results)
        result["detectors_used"] = list(component_results.keys())
        return result
