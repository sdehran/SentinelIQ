"""SentinelIQ Fraud Detection Agent.

Core scoring engine that retrieves relevant policy context from the FAISS
RAG pipeline, calls Gemini 1.5 Flash with a structured prompt, parses the
JSON response, and applies pattern memory adjustment.

Requirements: 3.1–3.10, 4.1–4.8
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

from models import (
    EnrichedTransaction,
    LLMScore,
    ScoredTransaction,
    derive_label,
)
from pattern_store import PatternStore
from rag.rag_pipeline import RAGPipeline


class FraudDetectionAgent:
    """Scores transactions using RAG-augmented LLM with pattern memory.

    The agent retrieves policy context from a FAISS index, constructs a
    structured prompt for Gemini 1.5 Flash, parses the JSON response,
    applies pattern memory adjustments, and falls back to rule-based
    scoring when the LLM is unavailable.
    """

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        llm,
        pattern_store: PatternStore,
        config: dict,
    ) -> None:
        """Initialise the Fraud Detection Agent.

        Args:
            rag_pipeline: RAGPipeline instance for policy chunk retrieval.
            llm: LangChain-compatible LLM (ChatGoogleGenerativeAI).
            pattern_store: PatternStore instance for score adjustments.
            config: Runtime configuration dictionary from config.json.
        """
        self.rag_pipeline = rag_pipeline
        self.llm = llm
        self.pattern_store = pattern_store
        self.config = config

    def score_transaction(self, txn: EnrichedTransaction) -> ScoredTransaction:
        """Score a single enriched transaction using RAG + LLM + pattern memory.

        Builds a RAG query from the transaction's flags, retrieves top-k
        policy chunks, constructs a prompt, calls the LLM with retry/backoff,
        parses the response, applies pattern adjustment, clamps the score,
        and re-derives the label.

        Args:
            txn: An EnrichedTransaction with computed feature flags.

        Returns:
            A ScoredTransaction with final score and label.

        Raises:
            Exception: If all retries fail and fallback_mode is False.
        """
        # Build RAG query from active flags and bank name
        query = self._build_rag_query(txn)
        rag_top_k = self.config.get("rag_top_k", 3)
        policy_chunks = self.rag_pipeline.retrieve(query, k=rag_top_k)

        # Build prompt
        prompt = self.build_llm_prompt(txn.row, txn.flags, policy_chunks)

        # Attempt LLM call with retry/backoff
        retry_attempts = self.config.get("retry_attempts", 3)
        fallback_mode = self.config.get("fallback_mode", True)
        llm_score: LLMScore | None = None
        last_exception: Exception | None = None

        for attempt in range(retry_attempts):
            try:
                raw_response = self.llm.invoke(prompt)
                # Handle LangChain message objects
                if hasattr(raw_response, "content"):
                    raw_text = raw_response.content
                else:
                    raw_text = str(raw_response)
                llm_score = self.parse_llm_response(raw_text)
                break
            except Exception as e:
                last_exception = e
                if attempt < retry_attempts - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    time.sleep(2**attempt)

        # If all retries exhausted
        if llm_score is None:
            if fallback_mode:
                llm_score = self.score_rule_fallback(txn)
            else:
                raise last_exception  # type: ignore[misc]

        # Compute pattern hash and lookup adjustment
        pattern_hash = self.pattern_store.compute_hash(
            txn.flags, txn.row.bank_name, txn.hour_bucket
        )
        adjustment = self.pattern_store.lookup(
            pattern_hash, as_of=datetime.now(timezone.utc)
        )

        # Apply adjustment and clamp
        final_score = self._clamp(llm_score.score + adjustment, 0, 100)
        final_label = derive_label(final_score)

        return ScoredTransaction(
            enriched=txn,
            llm_score=llm_score,
            pattern_adjustment=adjustment,
            final_score=final_score,
            final_label=final_label,
            pattern_hash=pattern_hash,
        )

    def score_rule_fallback(self, txn: EnrichedTransaction) -> LLMScore:
        """Compute a rule-based fallback score when the LLM is unavailable.

        Formula: base_score = active_count × 20
        If unusual_hour_flag is True: score = round(base_score × 1.3)
        Score is clamped to [0, 100]. Confidence is always LOW.

        Args:
            txn: An EnrichedTransaction with computed feature flags.

        Returns:
            LLMScore with source="rule_fallback" and confidence="LOW".
        """
        score = txn.flags.active_count * 20

        if txn.flags.unusual_hour_flag and score > 0:
            score = round(score * 1.3)

        score = min(score, 100)
        label = derive_label(score)

        # Build reason from active flags
        active_flags_text = self._active_flags_text(txn.flags)
        reason = f"Rule-based: {active_flags_text}"

        return LLMScore(
            score=score,
            label=label,
            reason=reason,
            confidence="LOW",
            source="rule_fallback",
        )

    def build_llm_prompt(
        self,
        row,
        flags,
        policy_chunks: list[str],
    ) -> str:
        """Construct a structured 5-section prompt for Gemini.

        Sections:
        1. Transaction details
        2. Feature flags summary
        3. Policy context (RAG chunks)
        4. Output format instruction
        5. Reason word-limit instruction

        Args:
            row: TransactionRow with transaction data.
            flags: FeatureFlags computed for the transaction.
            policy_chunks: List of relevant policy text chunks from FAISS.

        Returns:
            A formatted prompt string for the LLM.
        """
        # Section 1: Transaction details
        section_1 = (
            "## Transaction Details\n"
            f"- Transaction ID: {row.transaction_id}\n"
            f"- Account ID: {row.account_id}\n"
            f"- Bank: {row.bank_name}\n"
            f"- Amount: ₹{row.amount:,.2f}\n"
            f"- Timestamp: {row.timestamp}\n"
            f"- Merchant ID: {row.merchant_id}\n"
            f"- Location: {row.location}\n"
            f"- Transaction Type: {row.transaction_type}\n"
        )

        # Section 2: Feature flags summary
        section_2 = (
            "## Feature Flags\n"
            f"- Velocity Flag (>=3 txns in 60 min): {flags.velocity_flag}\n"
            f"- Geographic Anomaly Flag (>200km in <60 min): {flags.geo_anomaly_flag}\n"
            f"- Round Amount Flag (multiple of 500, >=10000): {flags.round_amount_flag}\n"
            f"- Unusual Hour Flag (hour 0-4): {flags.unusual_hour_flag}\n"
            f"- New Merchant Flag (not seen in 30 days): {flags.new_merchant_flag}\n"
            f"- Active Flag Count: {flags.active_count}/5\n"
        )

        # Section 3: Policy context
        if policy_chunks:
            chunks_text = "\n---\n".join(policy_chunks)
            section_3 = (
                "## Relevant Fraud Policy Context\n"
                f"{chunks_text}\n"
            )
        else:
            section_3 = "## Relevant Fraud Policy Context\nNo policy context available.\n"

        # Section 4: Output format instruction
        section_4 = (
            "## Output Format\n"
            "You are a fraud detection AI. Analyse the transaction above and respond "
            "with ONLY a valid JSON object in the following format:\n"
            "```json\n"
            '{"score": <integer 0-100>, "label": "<CRITICAL|HIGH|MED|LOW>", '
            '"reason": "<explanation>", "confidence": "<HIGH|LOW>"}\n'
            "```\n"
            "- score: Fraud risk score from 0 (no risk) to 100 (certain fraud)\n"
            "- label: CRITICAL (>=85), HIGH (70-84), MED (40-69), LOW (<40)\n"
            "- confidence: HIGH if you are confident in the assessment, LOW otherwise\n"
        )

        # Section 5: Reason word-limit instruction
        section_5 = (
            "## Important Constraints\n"
            "- Your reason MUST be 80 words or fewer.\n"
            "- Respond with ONLY the JSON object, no additional text.\n"
        )

        return f"{section_1}\n{section_2}\n{section_3}\n{section_4}\n{section_5}"

    def parse_llm_response(self, raw: str) -> LLMScore:
        """Parse the LLM JSON response into an LLMScore.

        Extracts JSON from the raw response, coerces score to int,
        clamps to [0, 100], and normalises label/confidence to uppercase.

        Args:
            raw: Raw string response from the LLM.

        Returns:
            LLMScore with source="llm".

        Raises:
            ValueError: If JSON parsing fails or required fields are missing.
        """
        # Try to extract JSON from the response
        json_obj = self._extract_json(raw)

        if json_obj is None:
            raise ValueError(f"Failed to parse JSON from LLM response: {raw[:200]}")

        # Extract and validate required fields
        try:
            score = int(json_obj["score"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid or missing 'score' field: {e}") from e

        # Clamp score to [0, 100]
        score = self._clamp(score, 0, 100)

        try:
            label = str(json_obj["label"]).upper()
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid or missing 'label' field: {e}") from e

        # Validate label
        if label not in ("CRITICAL", "HIGH", "MED", "LOW"):
            # Re-derive from score if label is invalid
            label = derive_label(score)

        try:
            reason = str(json_obj.get("reason", "No reason provided"))
        except (TypeError,):
            reason = "No reason provided"

        try:
            confidence = str(json_obj["confidence"]).upper()
        except (KeyError, TypeError):
            confidence = "LOW"  # Default to LOW if missing

        # Validate confidence
        if confidence not in ("HIGH", "LOW"):
            confidence = "LOW"

        return LLMScore(
            score=score,
            label=label,
            reason=reason,
            confidence=confidence,
            source="llm",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_rag_query(self, txn: EnrichedTransaction) -> str:
        """Build a text query for RAG retrieval from active flags.

        Args:
            txn: The enriched transaction.

        Returns:
            A query string summarising the fraud signals for policy lookup.
        """
        parts: list[str] = []

        if txn.flags.velocity_flag:
            parts.append("velocity burst rapid transactions")
        if txn.flags.geo_anomaly_flag:
            parts.append("geographic anomaly impossible travel")
        if txn.flags.round_amount_flag:
            parts.append("round amount suspicious pattern")
        if txn.flags.unusual_hour_flag:
            parts.append("unusual hour late night transaction")
        if txn.flags.new_merchant_flag:
            parts.append("new merchant first-time vendor")

        if not parts:
            parts.append("normal transaction low risk")

        parts.append(f"bank:{txn.row.bank_name}")

        return " ".join(parts)

    def _active_flags_text(self, flags) -> str:
        """Build a human-readable summary of active flags.

        Args:
            flags: FeatureFlags instance.

        Returns:
            Comma-separated string of active flag names.
        """
        active: list[str] = []
        if flags.velocity_flag:
            active.append("velocity")
        if flags.geo_anomaly_flag:
            active.append("geo_anomaly")
        if flags.round_amount_flag:
            active.append("round_amount")
        if flags.unusual_hour_flag:
            active.append("unusual_hour")
        if flags.new_merchant_flag:
            active.append("new_merchant")

        if not active:
            return "no active flags"
        return ", ".join(active)

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Extract a JSON object from LLM text output.

        Tries multiple strategies:
        1. Direct JSON parse of the entire text
        2. Extract from markdown code block
        3. Find first { ... } occurrence

        Args:
            text: Raw LLM response text.

        Returns:
            Parsed dictionary or None if extraction fails.
        """
        # Strategy 1: Try direct parse
        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: Extract from markdown code block
        code_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL
        )
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: Find first { ... } pattern
        brace_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    @staticmethod
    def _clamp(value: int, min_val: int, max_val: int) -> int:
        """Clamp an integer value to [min_val, max_val].

        Args:
            value: The value to clamp.
            min_val: Minimum bound.
            max_val: Maximum bound.

        Returns:
            Clamped integer.
        """
        return max(min_val, min(max_val, value))
