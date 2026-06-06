"""SentinelIQ Action Agent.

Routes each scored transaction into one of four autonomy tiers based on
the final score and confidence level:

- CRITICAL (score >= 85): Immediate hold + Gmail alert
- HIGH_QUEUE (score 70-84 any confidence, OR score 40-69 with LOW confidence):
  Analyst approval queue
- MED_BATCH (score 40-69 with HIGH confidence, OR score <40 with LOW confidence):
  Daily batch queue
- AUTO_CLEAR (score <40 with HIGH confidence): No action required

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from __future__ import annotations

from models import RoutedTransaction, ScoredTransaction, WorkflowState


class ActionAgent:
    """Third agent in the LangGraph pipeline.

    Classifies all scored transactions into routing tiers and populates
    human-readable action notes for each routed transaction.
    """

    def route(self, state: WorkflowState) -> WorkflowState:
        """Iterate all scored transactions, apply routing, return updated state.

        Args:
            state: The shared WorkflowState containing scored_transactions.

        Returns:
            Updated WorkflowState with routed_transactions populated.
        """
        routed: list[RoutedTransaction] = []

        for txn in state["scored_transactions"]:
            routed_txn = self.route_single(txn)
            routed.append(routed_txn)

        state["routed_transactions"] = routed
        return state

    def route_single(self, txn: ScoredTransaction) -> RoutedTransaction:
        """Apply 3-tier autonomy routing logic for a single transaction.

        Routing rules:
        - score >= 85 → CRITICAL
        - score 70-84 (any confidence) → HIGH_QUEUE
        - score 40-69, HIGH confidence → MED_BATCH
        - score 40-69, LOW confidence → HIGH_QUEUE (escalation)
        - score < 40, HIGH confidence → AUTO_CLEAR
        - score < 40, LOW confidence → MED_BATCH (cautious)

        Args:
            txn: A ScoredTransaction with final_score and confidence.

        Returns:
            A RoutedTransaction with tier and action_notes assigned.
        """
        score = txn.final_score
        confidence = txn.llm_score.confidence.upper()
        txn_id = txn.enriched.row.transaction_id
        account_id = txn.enriched.row.account_id

        if score >= 85:
            tier = "CRITICAL"
            action_notes = (
                f"CRITICAL: Transaction {txn_id} on account {account_id} "
                f"scored {score}. Immediate account hold applied. "
                f"Gmail alert triggered."
            )

        elif score >= 70:
            tier = "HIGH_QUEUE"
            action_notes = (
                f"HIGH RISK: Transaction {txn_id} on account {account_id} "
                f"scored {score} (confidence: {confidence}). "
                f"Added to analyst approval queue."
            )

        elif score >= 40:
            if confidence == "LOW":
                # Low confidence in MED range → escalate to HIGH_QUEUE
                tier = "HIGH_QUEUE"
                action_notes = (
                    f"ESCALATED: Transaction {txn_id} on account {account_id} "
                    f"scored {score} with LOW confidence. "
                    f"Escalated to analyst approval queue for review."
                )
            else:
                # HIGH confidence in MED range → daily batch
                tier = "MED_BATCH"
                action_notes = (
                    f"BATCH: Transaction {txn_id} on account {account_id} "
                    f"scored {score} (confidence: HIGH). "
                    f"Added to daily 6PM batch digest."
                )

        else:
            # score < 40
            if confidence == "LOW":
                # Low confidence in LOW range → cautious batch
                tier = "MED_BATCH"
                action_notes = (
                    f"CAUTIOUS BATCH: Transaction {txn_id} on account "
                    f"{account_id} scored {score} with LOW confidence. "
                    f"Added to daily batch queue for safety."
                )
            else:
                # HIGH confidence in LOW range → auto-clear
                tier = "AUTO_CLEAR"
                action_notes = (
                    f"AUTO-CLEARED: Transaction {txn_id} on account "
                    f"{account_id} scored {score} (confidence: HIGH). "
                    f"No action required. Pattern hash stored."
                )

        return RoutedTransaction(scored=txn, tier=tier, action_notes=action_notes)
