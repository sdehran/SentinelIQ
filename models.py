"""SentinelIQ Data Models Module.

Defines all dataclasses, TypedDict state, and utility functions
used throughout the SentinelIQ fraud investigation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

import networkx as nx
import pandas as pd


def derive_label(score: int) -> str:
    """Derive a risk label from a numeric fraud score.

    Args:
        score: Integer fraud score in [0, 100].

    Returns:
        One of "CRITICAL", "HIGH", "MED", or "LOW".
    """
    if score >= 85:
        return "CRITICAL"
    elif score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MED"
    else:
        return "LOW"


@dataclass
class TransactionRow:
    """Raw CSV transaction input."""

    transaction_id: str
    account_id: str
    bank_name: str
    amount: float
    timestamp: datetime
    merchant_id: str
    location: str
    transaction_type: str
    is_fraud_label: int
    customer_email: str = ""


@dataclass
class FeatureFlags:
    """Five binary fraud feature flags for a transaction."""

    velocity_flag: bool
    geo_anomaly_flag: bool
    round_amount_flag: bool
    unusual_hour_flag: bool
    new_merchant_flag: bool
    active_count: int  # number of True flags (0-5)


@dataclass
class EnrichedTransaction:
    """Transaction enriched with feature flags and metadata."""

    row: TransactionRow
    flags: FeatureFlags
    flags_text: str
    hour_bucket: int  # floor(hour / 6) → 0-3


@dataclass
class LLMScore:
    """Score result from LLM or rule-based fallback."""

    score: int  # 0-100
    label: str  # "CRITICAL" | "HIGH" | "MED" | "LOW"
    reason: str  # <= 80 words
    confidence: str  # "HIGH" | "LOW"
    source: str  # "llm" | "rule_fallback"


@dataclass
class ScoredTransaction:
    """Transaction with final score after pattern adjustment."""

    enriched: EnrichedTransaction
    llm_score: LLMScore
    pattern_adjustment: int  # +10, -15, or 0
    final_score: int  # clamped 0-100
    final_label: str  # re-derived from final_score
    pattern_hash: str  # MD5 hash


@dataclass
class RoutedTransaction:
    """Scored transaction assigned to an autonomy tier."""

    scored: ScoredTransaction
    tier: str  # "CRITICAL" | "HIGH_QUEUE" | "MED_BATCH" | "AUTO_CLEAR"
    action_notes: str


@dataclass
class SummaryStats:
    """Aggregate statistics for a workflow run."""

    total: int
    critical_count: int
    high_count: int
    med_count: int
    auto_cleared_count: int
    autonomy_rate: float
    high_confidence_count: int
    low_confidence_count: int
    processing_time_sec: float
    session_id: str  # UUID4


@dataclass
class PatternEntry:
    """A single entry in the pattern memory store."""

    hash: str
    feature_combination: str
    decision: str  # "approved" | "rejected"
    times_seen: int
    score_adjustment: int  # +10 or -15
    created_at: str  # ISO 8601
    last_updated: str  # ISO 8601


@dataclass
class ChatMessage:
    """A single message in the chatbot conversation."""

    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime


class WorkflowState(TypedDict):
    """LangGraph shared state passed between all agent nodes."""

    transactions_df: pd.DataFrame
    config: dict
    enriched_transactions: list[EnrichedTransaction]
    scored_transactions: list[ScoredTransaction]
    routed_transactions: list[RoutedTransaction]
    network_graph: nx.DiGraph
    report_url: str
    summary_stats: SummaryStats
    errors: list[str]
