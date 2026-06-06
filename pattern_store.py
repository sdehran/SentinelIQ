"""SentinelIQ Pattern Memory Store.

Provides a feedback-loop mechanism that records analyst APPROVE/REJECT
decisions and returns decay-adjusted score adjustments for recurring
fraud patterns. Patterns are identified by an MD5 hash of the canonical
feature flag combination + bank name + hour bucket.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Literal

from models import FeatureFlags, PatternEntry


class PatternStore:
    """Persistent JSON-backed pattern memory store.

    Attributes:
        filepath: Path to the pattern_store.json file.
        entries: Dictionary mapping pattern hashes to PatternEntry data.
    """

    # Flag names in the canonical order used for hashing
    _FLAG_NAMES = [
        "geo_anomaly_flag",
        "new_merchant_flag",
        "round_amount_flag",
        "unusual_hour_flag",
        "velocity_flag",
    ]

    def __init__(self, filepath: str = "pattern_store.json") -> None:
        """Initialise the PatternStore, creating the file if it doesn't exist.

        Args:
            filepath: Path to the JSON persistence file.
        """
        self.filepath = filepath
        self.entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load entries from disk, creating an empty store if file is missing."""
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.entries = data if isinstance(data, dict) else {}
        else:
            self.entries = {}
            self.save()

    def save(self) -> None:
        """Persist all entries to pattern_store.json."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

    def compute_hash(self, flags: FeatureFlags, bank: str, hour_bucket: int) -> str:
        """Compute a deterministic MD5 hash for a pattern.

        The hash is derived from the alphabetically sorted active flag names
        joined with "+", followed by the bank name and hour bucket.

        Args:
            flags: The FeatureFlags for the transaction.
            bank: The bank name (e.g. "HDFC").
            hour_bucket: Integer 0-3 derived as floor(hour / 6).

        Returns:
            32-character MD5 hexdigest string.
        """
        active_flags: list[str] = []
        flag_values = {
            "geo_anomaly_flag": flags.geo_anomaly_flag,
            "new_merchant_flag": flags.new_merchant_flag,
            "round_amount_flag": flags.round_amount_flag,
            "unusual_hour_flag": flags.unusual_hour_flag,
            "velocity_flag": flags.velocity_flag,
        }
        for name in self._FLAG_NAMES:
            if flag_values[name]:
                active_flags.append(name)

        canonical = "+".join(active_flags) + "+" + bank + "+" + str(hour_bucket)
        return hashlib.md5(canonical.encode("utf-8")).hexdigest()

    def lookup(self, pattern_hash: str, as_of: datetime | None = None) -> int:
        """Look up the decay-adjusted score adjustment for a pattern hash.

        Decay schedule:
          - 0-90 days:   factor 1.0 (full adjustment)
          - 91-180 days: factor 0.50
          - 181+ days:   factor 0.25

        Args:
            pattern_hash: The MD5 hash to look up.
            as_of: The reference datetime for decay calculation.
                   Defaults to datetime.utcnow() if not provided.

        Returns:
            Integer score adjustment (+10, -15, or 0 with decay applied).
            Returns 0 if the hash is not found.
        """
        if pattern_hash not in self.entries:
            return 0

        if as_of is None:
            as_of = datetime.now(timezone.utc)

        entry = self.entries[pattern_hash]
        last_updated = datetime.fromisoformat(entry["last_updated"])

        # Normalise both to naive UTC for consistent subtraction
        if as_of.tzinfo is not None:
            as_of_naive = as_of.replace(tzinfo=None)
        else:
            as_of_naive = as_of

        if last_updated.tzinfo is not None:
            last_updated_naive = last_updated.replace(tzinfo=None)
        else:
            last_updated_naive = last_updated

        age_days = (as_of_naive - last_updated_naive).days

        if age_days > 180:
            decay_factor = 0.25
        elif age_days > 90:
            decay_factor = 0.50
        else:
            decay_factor = 1.0

        base_adjustment = entry["score_adjustment"]
        return round(base_adjustment * decay_factor)

    def record(
        self,
        pattern_hash: str,
        decision: Literal["approved", "rejected"],
        feature_combination: str = "",
        timestamp: datetime | None = None,
    ) -> None:
        """Record an analyst APPROVE or REJECT decision for a pattern.

        APPROVED decisions set score_adjustment to +10.
        REJECTED decisions set score_adjustment to -15.

        Args:
            pattern_hash: The MD5 hash identifying the pattern.
            decision: Either "approved" or "rejected".
            feature_combination: Human-readable flag combination string.
            timestamp: When the decision was made. Defaults to utcnow().
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        score_adjustment = 10 if decision == "approved" else -15
        ts_iso = timestamp.isoformat()

        if pattern_hash in self.entries:
            entry = self.entries[pattern_hash]
            entry["decision"] = decision
            entry["score_adjustment"] = score_adjustment
            entry["times_seen"] = entry.get("times_seen", 0) + 1
            entry["last_updated"] = ts_iso
            if feature_combination:
                entry["feature_combination"] = feature_combination
        else:
            self.entries[pattern_hash] = {
                "hash": pattern_hash,
                "feature_combination": feature_combination,
                "decision": decision,
                "times_seen": 1,
                "score_adjustment": score_adjustment,
                "created_at": ts_iso,
                "last_updated": ts_iso,
            }

        self.save()

    def get_entry(self, pattern_hash: str) -> PatternEntry | None:
        """Retrieve a PatternEntry by hash, or None if not found.

        Args:
            pattern_hash: The MD5 hash to look up.

        Returns:
            A PatternEntry dataclass instance, or None.
        """
        if pattern_hash not in self.entries:
            return None

        data = self.entries[pattern_hash]
        return PatternEntry(
            hash=data["hash"],
            feature_combination=data.get("feature_combination", ""),
            decision=data["decision"],
            times_seen=data["times_seen"],
            score_adjustment=data["score_adjustment"],
            created_at=data["created_at"],
            last_updated=data["last_updated"],
        )

    def clear(self) -> None:
        """Clear all entries and persist the empty store."""
        self.entries = {}
        self.save()

    @property
    def count(self) -> int:
        """Return the total number of stored patterns."""
        return len(self.entries)

    @property
    def approved_count(self) -> int:
        """Return the number of APPROVED patterns."""
        return sum(
            1 for e in self.entries.values() if e.get("decision") == "approved"
        )

    @property
    def rejected_count(self) -> int:
        """Return the number of REJECTED patterns."""
        return sum(
            1 for e in self.entries.values() if e.get("decision") == "rejected"
        )
