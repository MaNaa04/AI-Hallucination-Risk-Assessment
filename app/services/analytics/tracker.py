"""
Analytics Tracker — stores verification events for the dashboard.

Uses a simple JSON file for persistence (no external DB needed).
Keeps an in-memory buffer and flushes periodically to disk.
"""

import json
import time
import os
import threading
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")
EVENTS_FILE = os.path.join(DATA_DIR, "verification_events.json")


@dataclass
class VerificationEvent:
    """A single verification event record."""
    request_id: str
    timestamp: str
    question_preview: str  # First 80 chars
    answer_preview: str    # First 120 chars
    score: int
    verdict: str
    sources_used: list[str]
    processing_time_ms: int
    claims_count: int
    evidence_chars: int
    provider: str = ""
    # Preprocessing analytics
    query_type: str = ""
    sentences_found: int = 0
    factual_sentences: int = 0
    # Per-stage timing
    preprocessing_time_ms: int = 0
    retrieval_time_ms: int = 0
    judge_time_ms: int = 0


class AnalyticsTracker:
    """
    Singleton tracker for verification analytics.

    Thread-safe. Stores events in memory and flushes to a JSON file.
    """

    _instance: Optional["AnalyticsTracker"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._events: list[dict] = []
        self._flush_lock = threading.Lock()
        self._load_from_disk()
        logger.info(f"Analytics tracker initialized with {len(self._events)} events")

    def _load_from_disk(self):
        """Load existing events from JSON file."""
        try:
            if os.path.exists(EVENTS_FILE):
                with open(EVENTS_FILE, "r") as f:
                    self._events = json.load(f)
                logger.info(f"Loaded {len(self._events)} events from {EVENTS_FILE}")
        except Exception as e:
            logger.warning(f"Could not load events file: {e}")
            self._events = []

    def _flush_to_disk(self):
        """Write events to JSON file."""
        with self._flush_lock:
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(EVENTS_FILE, "w") as f:
                    json.dump(self._events, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to flush events to disk: {e}")

    def record(self, event: VerificationEvent):
        """Record a verification event."""
        self._events.append(asdict(event))
        # Flush every 5 events or always (small scale)
        if len(self._events) % 5 == 0 or len(self._events) <= 50:
            self._flush_to_disk()
        logger.info(f"Recorded event {event.request_id} | score={event.score} verdict={event.verdict}")

    def get_events(self, limit: int = 50) -> list[dict]:
        """Get recent events, newest first."""
        return list(reversed(self._events[-limit:]))

    def get_stats(self) -> dict:
        """Compute aggregate statistics."""
        total = len(self._events)
        if total == 0:
            return {
                "total_verifications": 0,
                "avg_score": 0,
                "avg_processing_time_ms": 0,
                "verdict_distribution": {},
                "score_distribution": {},
                "sources_distribution": {},
                "verifications_over_time": [],
                "recent_trend": [],
            }

        scores = [e["score"] for e in self._events]
        times = [e.get("processing_time_ms", 0) for e in self._events]

        # Verdict distribution
        verdict_counts = defaultdict(int)
        for e in self._events:
            verdict_counts[e["verdict"]] += 1

        # Score buckets: 0-19, 20-39, 40-59, 60-79, 80-100
        score_buckets = {"0-19": 0, "20-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
        for s in scores:
            if s < 20:
                score_buckets["0-19"] += 1
            elif s < 40:
                score_buckets["20-39"] += 1
            elif s < 60:
                score_buckets["40-59"] += 1
            elif s < 80:
                score_buckets["60-79"] += 1
            else:
                score_buckets["80-100"] += 1

        # Sources distribution
        source_counts = defaultdict(int)
        for e in self._events:
            for src in e.get("sources_used", []):
                source_counts[src] += 1

        # Verifications over time (group by hour)
        time_groups = defaultdict(int)
        for e in self._events:
            ts = e.get("timestamp", "")
            if ts:
                # Group by YYYY-MM-DD HH:00
                hour_key = ts[:13] + ":00"
                time_groups[hour_key] += 1

        time_series = [{"time": k, "count": v} for k, v in sorted(time_groups.items())]

        # Recent trend — last 10 events scores
        recent = [{"score": e["score"], "verdict": e["verdict"]} for e in self._events[-10:]]

        return {
            "total_verifications": total,
            "avg_score": round(sum(scores) / total, 1),
            "avg_processing_time_ms": round(sum(times) / total),
            "verdict_distribution": dict(verdict_counts),
            "score_distribution": score_buckets,
            "sources_distribution": dict(source_counts),
            "verifications_over_time": time_series,
            "recent_trend": recent,
        }

    def get_preprocessing_stats(self) -> dict:
        """Compute preprocessing-specific analytics for the dashboard."""
        total = len(self._events)
        if total == 0:
            return {
                "total": 0,
                "query_type_distribution": {},
                "avg_sentences_found": 0,
                "avg_factual_sentences": 0,
                "avg_claims_extracted": 0,
                "sentence_to_claim_ratio": 0,
                "avg_preprocessing_time_ms": 0,
                "preprocessing_timeline": [],
            }

        # Query type distribution
        qt_counts = defaultdict(int)
        for e in self._events:
            qt = e.get("query_type", "unknown") or "unknown"
            qt_counts[qt] += 1

        # Averages
        sentences = [e.get("sentences_found", 0) for e in self._events]
        factual = [e.get("factual_sentences", 0) for e in self._events]
        claims = [e.get("claims_count", 0) for e in self._events]
        preprocess_times = [e.get("preprocessing_time_ms", 0) for e in self._events]

        total_sentences = sum(sentences)
        total_claims = sum(claims)

        # Per-event breakdown for timeline (last 20)
        timeline = []
        for e in self._events[-20:]:
            timeline.append({
                "request_id": e.get("request_id", "")[:8],
                "query_type": e.get("query_type", "unknown"),
                "sentences": e.get("sentences_found", 0),
                "factual": e.get("factual_sentences", 0),
                "claims": e.get("claims_count", 0),
                "time_ms": e.get("preprocessing_time_ms", 0),
            })

        return {
            "total": total,
            "query_type_distribution": dict(qt_counts),
            "avg_sentences_found": round(sum(sentences) / total, 1),
            "avg_factual_sentences": round(sum(factual) / total, 1),
            "avg_claims_extracted": round(sum(claims) / total, 1),
            "sentence_to_claim_ratio": round(total_sentences / max(total_claims, 1), 1),
            "avg_preprocessing_time_ms": round(sum(preprocess_times) / total, 1),
            "preprocessing_timeline": timeline,
        }

    def get_pipeline_stats(self) -> dict:
        """Compute per-stage pipeline performance stats."""
        total = len(self._events)
        if total == 0:
            return {
                "total": 0,
                "stages": {},
                "pipeline_timeline": [],
            }

        preprocess_times = [e.get("preprocessing_time_ms", 0) for e in self._events]
        retrieval_times = [e.get("retrieval_time_ms", 0) for e in self._events]
        judge_times = [e.get("judge_time_ms", 0) for e in self._events]
        total_times = [e.get("processing_time_ms", 0) for e in self._events]

        def stage_stats(times):
            if not times:
                return {"avg": 0, "min": 0, "max": 0, "p50": 0}
            sorted_t = sorted(times)
            return {
                "avg": round(sum(sorted_t) / len(sorted_t), 1),
                "min": sorted_t[0],
                "max": sorted_t[-1],
                "p50": sorted_t[len(sorted_t) // 2],
            }

        # Per-event waterfall for last 15 events
        waterfall = []
        for e in self._events[-15:]:
            total_ms = e.get("processing_time_ms", 0)
            pre_ms = e.get("preprocessing_time_ms", 0)
            ret_ms = e.get("retrieval_time_ms", 0)
            jdg_ms = e.get("judge_time_ms", 0)
            other_ms = max(0, total_ms - pre_ms - ret_ms - jdg_ms)
            waterfall.append({
                "request_id": e.get("request_id", "")[:8],
                "preprocessing": pre_ms,
                "retrieval": ret_ms,
                "judging": jdg_ms,
                "other": other_ms,
                "total": total_ms,
                "verdict": e.get("verdict", ""),
            })

        return {
            "total": total,
            "stages": {
                "preprocessing": stage_stats(preprocess_times),
                "retrieval": stage_stats(retrieval_times),
                "judging": stage_stats(judge_times),
                "total": stage_stats(total_times),
            },
            "pipeline_timeline": waterfall,
        }

    def clear(self):
        """Clear all events (for testing)."""
        self._events = []
        self._flush_to_disk()
