"""SentinelIQ Transaction Agent.

First agent in the LangGraph pipeline. Parses each transaction row,
computes 5 binary fraud feature flags, validates CSV data, and builds
a NetworkX directed graph for network analysis visualization.

Requirements: 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.1–2.9, 11.2, 11.3, 11.4
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import networkx as nx
import pandas as pd
from dateutil import parser as dateutil_parser

from models import (
    EnrichedTransaction,
    FeatureFlags,
    TransactionRow,
    WorkflowState,
)

# --------------------------------------------------------------------------
# City coordinate lookup for haversine distance computation.
# Maps city name (case-insensitive key) to (latitude, longitude).
# --------------------------------------------------------------------------
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "ahmedabad": (23.0225, 72.5714),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "pune": (18.5204, 73.8567),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    "kochi": (9.9312, 76.2673),
    "chandigarh": (30.7333, 76.7794),
    "patna": (25.6093, 85.1376),
    "bhopal": (23.2599, 77.4126),
    "guwahati": (26.1445, 91.7362),
}

# Valid bank names (warn on others, do not skip)
VALID_BANKS = {"HDFC", "SBI", "ICICI", "Axis"}

# Earth radius in kilometres (for haversine)
_EARTH_RADIUS_KM = 6371.0


def haversine(loc1: str, loc2: str) -> float:
    """Compute haversine distance in km between two city names.

    Resolves city names to coordinates via the CITY_COORDINATES lookup dict.
    Returns -1.0 if either location cannot be resolved.

    Args:
        loc1: First location (city name string).
        loc2: Second location (city name string).

    Returns:
        Distance in km, or -1.0 on resolution failure.
    """
    coords1 = CITY_COORDINATES.get(loc1.strip().lower())
    coords2 = CITY_COORDINATES.get(loc2.strip().lower())

    if coords1 is None or coords2 is None:
        return -1.0

    lat1, lon1 = math.radians(coords1[0]), math.radians(coords1[1])
    lat2, lon2 = math.radians(coords2[0]), math.radians(coords2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + (
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return _EARTH_RADIUS_KM * c


class TransactionAgent:
    """First agent in the SentinelIQ pipeline.

    Responsibilities:
      - Validate and parse CSV rows into TransactionRow instances
      - Compute 5 binary fraud feature flags per transaction
      - Build a NetworkX DiGraph for network visualization
    """

    def process(self, state: WorkflowState) -> WorkflowState:
        """Enrich all transactions with feature flags and graph data.

        Args:
            state: The shared WorkflowState dict containing transactions_df.

        Returns:
            Updated WorkflowState with enriched_transactions, network_graph,
            and error messages appended.
        """
        df: pd.DataFrame = state["transactions_df"]
        errors: list[str] = list(state.get("errors") or [])

        # Parse and validate rows
        rows, skip_count, row_errors = self._parse_dataframe(df)
        errors.extend(row_errors)

        processed_count = len(rows)
        errors.append(
            f"TransactionAgent: processed {processed_count} rows, "
            f"skipped {skip_count} rows."
        )

        # Group rows by account for flag computation
        account_rows: dict[str, list[TransactionRow]] = defaultdict(list)
        for row in rows:
            account_rows[row.account_id].append(row)

        # Sort each account's transactions by timestamp
        for acct_rows in account_rows.values():
            acct_rows.sort(key=lambda r: r.timestamp)

        # Build merchant history: set of (account_id, merchant_id) for
        # the last 30 days relative to the latest transaction in the dataset
        merchant_history = self._build_merchant_history(rows)

        # Compute feature flags for each row
        enriched: list[EnrichedTransaction] = []
        for row in rows:
            flags = self.compute_feature_flags(
                row, account_rows[row.account_id], merchant_history
            )
            hour_bucket = row.timestamp.hour // 6
            flags_text = self._build_flags_text(flags)
            enriched.append(
                EnrichedTransaction(
                    row=row,
                    flags=flags,
                    flags_text=flags_text,
                    hour_bucket=hour_bucket,
                )
            )

        # Build network graph
        network_graph = self.build_network_graph(rows)

        state["enriched_transactions"] = enriched
        state["network_graph"] = network_graph
        state["errors"] = errors
        return state

    def compute_feature_flags(
        self,
        row: TransactionRow,
        account_rows: list[TransactionRow],
        merchant_history: set[tuple[str, str]],
    ) -> FeatureFlags:
        """Compute 5 binary fraud feature flags for a single transaction.

        Args:
            row: The transaction to compute flags for.
            account_rows: All rows for the same account, sorted by timestamp.
            merchant_history: Set of (account_id, merchant_id) pairs seen
                in the preceding 30 days.

        Returns:
            FeatureFlags dataclass with all 5 flags and active_count.
        """
        # --- Velocity flag ---
        # True if ≥3 transactions from same account within any 60-min window
        # containing the current transaction.
        window_start = row.timestamp - timedelta(minutes=60)
        count_in_window = sum(
            1
            for r in account_rows
            if window_start <= r.timestamp <= row.timestamp
        )
        velocity_flag = count_in_window >= 3

        # --- Geographic anomaly flag ---
        # True if haversine > 200 km from preceding txn in < 60 min.
        geo_anomaly_flag = False
        prev_row = None
        for r in account_rows:
            if r.timestamp < row.timestamp:
                prev_row = r
            else:
                break
        if prev_row is not None:
            dist_km = haversine(prev_row.location, row.location)
            if dist_km < 0:
                # Resolution failure → flag stays False
                geo_anomaly_flag = False
            else:
                time_diff_min = (
                    row.timestamp - prev_row.timestamp
                ).total_seconds() / 60
                geo_anomaly_flag = dist_km > 200 and time_diff_min < 60

        # --- Round amount flag ---
        # True if amount is multiple of 500 AND >= 10,000
        round_amount_flag = (
            row.amount >= 10000 and row.amount % 500 == 0
        )

        # --- Unusual hour flag ---
        # True if transaction hour is in {0, 1, 2, 3, 4}
        unusual_hour_flag = row.timestamp.hour in {0, 1, 2, 3, 4}

        # --- New merchant flag ---
        # True if (account_id, merchant_id) pair not in merchant history
        new_merchant_flag = (
            row.account_id,
            row.merchant_id,
        ) not in merchant_history

        # Compute active count
        flags_list = [
            velocity_flag,
            geo_anomaly_flag,
            round_amount_flag,
            unusual_hour_flag,
            new_merchant_flag,
        ]
        active_count = sum(int(f) for f in flags_list)

        return FeatureFlags(
            velocity_flag=velocity_flag,
            geo_anomaly_flag=geo_anomaly_flag,
            round_amount_flag=round_amount_flag,
            unusual_hour_flag=unusual_hour_flag,
            new_merchant_flag=new_merchant_flag,
            active_count=active_count,
        )

    def build_network_graph(self, rows: list[TransactionRow]) -> nx.DiGraph:
        """Build directed graph from transaction rows for network analysis.

        Nodes are accounts (with bank attribute) and merchants. Edges are
        directed from account to merchant for each transaction. Relay nodes
        (in-degree + out-degree > 5) are tagged. Nodes in simple cycles
        are tagged with in_cycle=True.

        Args:
            rows: List of validated TransactionRow instances.

        Returns:
            A NetworkX DiGraph with tagged nodes and edges.
        """
        G = nx.DiGraph()

        for row in rows:
            # Add account node
            if not G.has_node(row.account_id):
                G.add_node(
                    row.account_id,
                    type="account",
                    bank=row.bank_name,
                    node_type="normal",
                    in_cycle=False,
                )

            # Add merchant node
            if not G.has_node(row.merchant_id):
                G.add_node(
                    row.merchant_id,
                    type="merchant",
                    node_type="normal",
                    in_cycle=False,
                )

            # Add directed edge (account → merchant)
            G.add_edge(
                row.account_id,
                row.merchant_id,
                amount=row.amount,
                transaction_id=row.transaction_id,
                timestamp=str(row.timestamp),
            )

        # Tag relay nodes: combined in-degree + out-degree > 5
        for node in G.nodes():
            degree = G.in_degree(node) + G.out_degree(node)
            if degree > 5:
                G.nodes[node]["node_type"] = "relay"

        # Detect simple cycles and tag participating nodes
        try:
            cycles = list(nx.simple_cycles(G))
            for cycle in cycles:
                for node in cycle:
                    G.nodes[node]["in_cycle"] = True
        except Exception:
            # If cycle detection fails (e.g. on very large graphs), skip
            pass

        return G

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_dataframe(
        self, df: pd.DataFrame
    ) -> tuple[list[TransactionRow], int, list[str]]:
        """Parse and validate a DataFrame into TransactionRow instances.

        Validation rules:
          - Skip rows with missing transaction_id or account_id
          - Skip rows with invalid/unparseable amount (must be > 0)
          - Skip rows with unparseable timestamp
          - Warn on unknown bank_name but do NOT skip

        Args:
            df: Raw transactions DataFrame.

        Returns:
            Tuple of (valid_rows, skip_count, error_messages).
        """
        rows: list[TransactionRow] = []
        skip_count = 0
        errors: list[str] = []

        for idx, record in df.iterrows():
            # Check required key columns
            txn_id = record.get("transaction_id")
            acct_id = record.get("account_id")

            if pd.isna(txn_id) or str(txn_id).strip() == "":
                skip_count += 1
                errors.append(
                    f"Row {idx}: skipped — missing transaction_id."
                )
                continue

            if pd.isna(acct_id) or str(acct_id).strip() == "":
                skip_count += 1
                errors.append(
                    f"Row {idx}: skipped — missing account_id."
                )
                continue

            txn_id = str(txn_id).strip()
            acct_id = str(acct_id).strip()

            # Validate amount
            try:
                amount = float(record.get("amount", 0))
            except (ValueError, TypeError):
                skip_count += 1
                errors.append(
                    f"Row {idx} ({txn_id}): skipped — invalid amount."
                )
                continue

            if amount <= 0:
                skip_count += 1
                errors.append(
                    f"Row {idx} ({txn_id}): skipped — amount not > 0."
                )
                continue

            # Validate timestamp
            ts_raw = record.get("timestamp")
            try:
                if isinstance(ts_raw, pd.Timestamp):
                    timestamp = ts_raw.to_pydatetime()
                elif isinstance(ts_raw, datetime):
                    timestamp = ts_raw
                else:
                    timestamp = dateutil_parser.parse(str(ts_raw))
            except (ValueError, TypeError, OverflowError):
                skip_count += 1
                errors.append(
                    f"Row {idx} ({txn_id}): skipped — unparseable timestamp."
                )
                continue

            # Warn on unknown bank_name (do NOT skip)
            bank_name = str(record.get("bank_name", "")).strip()
            if bank_name not in VALID_BANKS:
                errors.append(
                    f"Row {idx} ({txn_id}): warning — unknown bank_name "
                    f"'{bank_name}'."
                )

            # Extract remaining fields (best effort)
            merchant_id = str(record.get("merchant_id", "")).strip()
            location = str(record.get("location", "")).strip()
            transaction_type = str(
                record.get("transaction_type", "")
            ).strip()

            try:
                is_fraud_label = int(record.get("is_fraud_label", 0))
            except (ValueError, TypeError):
                is_fraud_label = 0

            rows.append(
                TransactionRow(
                    transaction_id=txn_id,
                    account_id=acct_id,
                    bank_name=bank_name,
                    amount=amount,
                    timestamp=timestamp,
                    merchant_id=merchant_id,
                    location=location,
                    transaction_type=transaction_type,
                    is_fraud_label=is_fraud_label,
                    customer_email=str(record.get("customer_email", "")) if "customer_email" in record.index else "",
                )
            )

        return rows, skip_count, errors

    def _build_merchant_history(
        self, rows: list[TransactionRow]
    ) -> set[tuple[str, str]]:
        """Build set of (account_id, merchant_id) pairs seen in last 30 days.

        The 30-day window is computed relative to the latest transaction
        timestamp in the dataset.

        Args:
            rows: All validated transaction rows.

        Returns:
            Set of (account_id, merchant_id) tuples representing known
            merchant relationships.
        """
        if not rows:
            return set()

        latest = max(r.timestamp for r in rows)
        cutoff = latest - timedelta(days=30)

        history: set[tuple[str, str]] = set()
        for row in rows:
            if row.timestamp >= cutoff:
                history.add((row.account_id, row.merchant_id))

        return history

    @staticmethod
    def _build_flags_text(flags: FeatureFlags) -> str:
        """Build a human-readable flags summary string for LLM prompts.

        Args:
            flags: The computed FeatureFlags.

        Returns:
            Comma-separated description of active flags, or "None" if
            no flags are active.
        """
        parts: list[str] = []
        if flags.velocity_flag:
            parts.append("velocity_burst")
        if flags.geo_anomaly_flag:
            parts.append("geographic_anomaly")
        if flags.round_amount_flag:
            parts.append("round_amount")
        if flags.unusual_hour_flag:
            parts.append("unusual_hour")
        if flags.new_merchant_flag:
            parts.append("new_merchant")

        if not parts:
            return "No active fraud flags"
        return f"Active flags ({len(parts)}/5): {', '.join(parts)}"
