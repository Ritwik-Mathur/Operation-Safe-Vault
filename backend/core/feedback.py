"""
Human-in-the-Loop Feedback System
──────────────────────────────────
Stores user verdicts (confirm/deny) on analysis results.
Used for:
  1. Improving future accuracy (feedback loop)
  2. Demo value – shows judges you handle false positives properly
  3. Feeding confirmed scams back into vector DB
"""

import json
import os
import time
from typing import Dict, Any, List, Optional

FEEDBACK_FILE = "./feedback_store.json"


class FeedbackStore:

    def __init__(self, path: str = FEEDBACK_FILE):
        self.path = path
        self._store: List[Dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    self._store = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._store = []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._store, f, indent=2, default=str)

    def add_feedback(
        self,
        analysis_id: str,
        user_verdict: str,        # "scam" | "safe" | "unsure"
        original_score: float,
        original_verdict: str,
        source: str,
        original_input: str = "",
        comment: str = "",
    ) -> Dict:
        entry = {
            "id": analysis_id,
            "timestamp": time.time(),
            "user_verdict": user_verdict,
            "original_score": original_score,
            "original_verdict": original_verdict,
            "source": source,
            "original_input": original_input[:500],
            "comment": comment,
            "was_correct": (
                (user_verdict == "scam" and original_verdict in ("SCAM", "SUSPECTED"))
                or (user_verdict == "safe" and original_verdict == "SAFE")
            ),
        }
        self._store.append(entry)
        self._save()
        return entry

    def get_accuracy_stats(self) -> Dict:
        """Calculate how accurate our system has been based on user feedback."""
        if not self._store:
            return {"total_feedback": 0, "accuracy_pct": None, "false_positives": 0, "false_negatives": 0}

        total = len(self._store)
        correct = sum(1 for e in self._store if e.get("was_correct"))
        false_pos = sum(1 for e in self._store
                        if e.get("user_verdict") == "safe"
                        and e.get("original_verdict") in ("SCAM", "SUSPECTED"))
        false_neg = sum(1 for e in self._store
                        if e.get("user_verdict") == "scam"
                        and e.get("original_verdict") == "SAFE")

        return {
            "total_feedback": total,
            "accuracy_pct": round(correct / total * 100, 1) if total > 0 else None,
            "false_positives": false_pos,
            "false_negatives": false_neg,
            "correct": correct,
        }

    def get_recent(self, limit: int = 20) -> List[Dict]:
        return sorted(self._store, key=lambda e: e.get("timestamp", 0), reverse=True)[:limit]
