"""SentinelIQ LangGraph Multi-Agent Workflow Orchestration.

Orchestrates the four agents as nodes in a LangGraph StateGraph:
  router → transaction_agent → fraud_detection_agent → action_agent → reporting_agent

Manages shared WorkflowState across the pipeline and exposes a single
invoke() entry point called by the Streamlit UI.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 5.8
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import networkx as nx
import pandas as pd
from langgraph.graph import StateGraph, END

from models import (
    EnrichedTransaction,
    RoutedTransaction,
    ScoredTransaction,
    SummaryStats,
    WorkflowState,
    derive_label,
)
from agents.transaction_agent import TransactionAgent
from agents.fraud_detection_agent import FraudDetectionAgent
from agents.action_agent import ActionAgent
from agents.reporting_agent import ReportingAgent
from pattern_store import PatternStore
from rag.rag_pipeline import RAGPipeline


class SentinelIQWorkflow:
    """Orchestrates the SentinelIQ four-agent pipeline via LangGraph.

    The workflow defines a StateGraph with nodes:
      router → transaction_agent → fraud_detection_agent → action_agent → reporting_agent

    Each node wraps the corresponding agent's process method with error
    handling that captures exceptions into WorkflowState.errors and allows
    the pipeline to continue to the next node.

    Attributes:
        config: Runtime configuration dictionary loaded from config.json.
        transaction_agent: TransactionAgent instance.
        fraud_detection_agent: FraudDetectionAgent instance.
        action_agent: ActionAgent instance.
        reporting_agent: ReportingAgent instance.
        pattern_store: PatternStore instance for score adjustments.
        rag_pipeline: RAGPipeline instance for policy retrieval.
        graph: Compiled LangGraph StateGraph.
    """

    def __init__(self, config: dict) -> None:
        """Initialise the workflow with all agents and dependencies.

        Args:
            config: Runtime configuration dictionary (from config.json).
        """
        self.config = config

        # Instantiate shared dependencies
        self.pattern_store = PatternStore()

        # Instantiate RAG pipeline (may raise if index not built)
        try:
            self.rag_pipeline = RAGPipeline(
                index_path="rag/faiss_index",
                embedding_model="models/embedding-001",
            )
        except FileNotFoundError:
            # If FAISS index is not built, RAG will be unavailable
            # The FraudDetectionAgent will fall back to rule-based scoring
            self.rag_pipeline = None  # type: ignore[assignment]

        # Instantiate LLM (Gemini 1.5 Flash via LangChain)
        self._llm = self._create_llm()

        # Instantiate agents
        self.transaction_agent = TransactionAgent()
        self.fraud_detection_agent = FraudDetectionAgent(
            rag_pipeline=self.rag_pipeline,
            llm=self._llm,
            pattern_store=self.pattern_store,
            config=self.config,
        )
        self.action_agent = ActionAgent()
        self.reporting_agent = ReportingAgent(config=self.config)

        # Build and compile the LangGraph StateGraph
        self.graph = self._build_graph()

    def invoke(self, transactions_df: pd.DataFrame) -> WorkflowState:
        """Run the full pipeline on a DataFrame and return the final state.

        Initialises WorkflowState, runs the compiled graph, computes
        SummaryStats (total, critical_count, high_count, med_count,
        auto_cleared_count, autonomy_rate, processing_time_sec, session_id),
        and returns the completed state.

        Args:
            transactions_df: DataFrame of transaction rows to process.

        Returns:
            Fully populated WorkflowState after all agents have completed.
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())

        # Initialise the shared state
        initial_state: WorkflowState = {
            "transactions_df": transactions_df,
            "config": self.config,
            "enriched_transactions": [],
            "scored_transactions": [],
            "routed_transactions": [],
            "network_graph": nx.DiGraph(),
            "report_url": "",
            "summary_stats": None,  # type: ignore[typeddict-item]
            "errors": [],
        }

        # Run the compiled graph
        final_state = self.graph.invoke(initial_state)

        # Compute SummaryStats from the final state
        processing_time_sec = time.time() - start_time
        summary_stats = self._compute_summary_stats(
            final_state, session_id, processing_time_sec
        )
        final_state["summary_stats"] = summary_stats

        return final_state

    def _build_graph(self):
        """Define and compile the LangGraph StateGraph.

        Nodes:
          - router: Entry point, validates state and passes through
          - transaction_agent: Computes feature flags and network graph
          - fraud_detection_agent: Scores all enriched transactions
          - action_agent: Routes scored transactions into tiers
          - reporting_agent: Generates PDF report, uploads to S3, alerts

        Returns:
            Compiled LangGraph graph ready for invocation.
        """
        # Define the state graph with WorkflowState as the state type
        graph = StateGraph(dict)

        # Add nodes with error-handling wrappers
        graph.add_node("router", self._router_node)
        graph.add_node("transaction_agent", self._transaction_agent_node)
        graph.add_node("fraud_detection_agent", self._fraud_detection_agent_node)
        graph.add_node("action_agent", self._action_agent_node)
        graph.add_node("reporting_agent", self._reporting_agent_node)

        # Define edges: linear pipeline
        graph.set_entry_point("router")
        graph.add_edge("router", "transaction_agent")
        graph.add_edge("transaction_agent", "fraud_detection_agent")
        graph.add_edge("fraud_detection_agent", "action_agent")
        graph.add_edge("action_agent", "reporting_agent")
        graph.add_edge("reporting_agent", END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Node implementations with error handling
    # ------------------------------------------------------------------

    def _router_node(self, state: dict) -> dict:
        """Entry node: validates state and passes through.

        Ensures the state has all required keys initialised.

        Args:
            state: The current WorkflowState dictionary.

        Returns:
            The state (potentially with errors appended if invalid).
        """
        errors = list(state.get("errors") or [])

        # Validate that transactions_df is present and non-empty
        df = state.get("transactions_df")
        if df is None or (hasattr(df, "empty") and df.empty):
            errors.append("Router: No transactions provided or DataFrame is empty.")

        state["errors"] = errors
        return state

    def _transaction_agent_node(self, state: dict) -> dict:
        """Execute the Transaction Agent with error handling.

        Args:
            state: The current WorkflowState dictionary.

        Returns:
            Updated state with enriched_transactions and network_graph.
        """
        try:
            state = self.transaction_agent.process(state)
        except Exception as e:
            errors = list(state.get("errors") or [])
            errors.append(
                f"TransactionAgent: Unhandled exception — {type(e).__name__}: {e}"
            )
            state["errors"] = errors
            # Ensure downstream keys exist even on failure
            if "enriched_transactions" not in state:
                state["enriched_transactions"] = []
            if "network_graph" not in state:
                state["network_graph"] = nx.DiGraph()
        return state

    def _fraud_detection_agent_node(self, state: dict) -> dict:
        """Execute the Fraud Detection Agent with error handling.

        Scores each enriched transaction individually, catching per-transaction
        errors so that one failure doesn't block the rest. If both the RAG
        pipeline and LLM are unavailable, uses rule-based fallback directly.

        Args:
            state: The current WorkflowState dictionary.

        Returns:
            Updated state with scored_transactions.
        """
        errors = list(state.get("errors") or [])
        scored: list[ScoredTransaction] = []

        enriched_transactions = state.get("enriched_transactions", [])

        # Check if infrastructure is available
        use_fallback_directly = (
            self.rag_pipeline is None or self._llm is None
        )
        if use_fallback_directly and enriched_transactions:
            errors.append(
                "FraudDetectionAgent: RAG pipeline or LLM unavailable, "
                "using rule-based fallback for all transactions."
            )

        for txn in enriched_transactions:
            try:
                if use_fallback_directly:
                    # Skip RAG/LLM path entirely, use rule-based fallback
                    scored_txn = self._score_with_fallback(txn)
                else:
                    scored_txn = self.fraud_detection_agent.score_transaction(txn)
                scored.append(scored_txn)
            except Exception as e:
                errors.append(
                    f"FraudDetectionAgent: Failed to score "
                    f"{txn.row.transaction_id} — {type(e).__name__}: {e}"
                )

        state["scored_transactions"] = scored
        state["errors"] = errors
        return state

    def _score_with_fallback(self, txn) -> ScoredTransaction:
        """Score a transaction using rule-based fallback directly.

        Used when RAG pipeline or LLM is unavailable. Computes pattern
        hash and applies adjustment even in fallback mode.

        Args:
            txn: An EnrichedTransaction instance.

        Returns:
            ScoredTransaction using rule-based scoring.
        """
        llm_score = self.fraud_detection_agent.score_rule_fallback(txn)

        # Compute pattern hash and lookup adjustment
        pattern_hash = self.pattern_store.compute_hash(
            txn.flags, txn.row.bank_name, txn.hour_bucket
        )
        adjustment = self.pattern_store.lookup(
            pattern_hash,
            as_of=datetime.now(timezone.utc),
        )

        # Apply adjustment and clamp
        final_score = max(0, min(100, llm_score.score + adjustment))
        final_label = derive_label(final_score)

        return ScoredTransaction(
            enriched=txn,
            llm_score=llm_score,
            pattern_adjustment=adjustment,
            final_score=final_score,
            final_label=final_label,
            pattern_hash=pattern_hash,
        )

    def _action_agent_node(self, state: dict) -> dict:
        """Execute the Action Agent with error handling.

        Args:
            state: The current WorkflowState dictionary.

        Returns:
            Updated state with routed_transactions.
        """
        try:
            state = self.action_agent.route(state)
        except Exception as e:
            errors = list(state.get("errors") or [])
            errors.append(
                f"ActionAgent: Unhandled exception — {type(e).__name__}: {e}"
            )
            state["errors"] = errors
            if "routed_transactions" not in state:
                state["routed_transactions"] = []
        return state

    def _reporting_agent_node(self, state: dict) -> dict:
        """Execute the Reporting Agent with error handling.

        Args:
            state: The current WorkflowState dictionary.

        Returns:
            Updated state with report_url.
        """
        try:
            state = self.reporting_agent.compile_report(state)
        except Exception as e:
            errors = list(state.get("errors") or [])
            errors.append(
                f"ReportingAgent: Unhandled exception — {type(e).__name__}: {e}"
            )
            state["errors"] = errors
            if "report_url" not in state:
                state["report_url"] = ""
        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_llm(self):
        """Create the LangChain Gemini 1.5 Flash LLM instance.

        Returns:
            ChatGoogleGenerativeAI instance, or None if API key is missing.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.1,
                convert_system_message_to_human=True,
            )
        except Exception:
            return None

    def _compute_summary_stats(
        self,
        state: dict,
        session_id: str,
        processing_time_sec: float,
    ) -> SummaryStats:
        """Compute aggregate statistics from the final workflow state.

        Args:
            state: The completed WorkflowState dictionary.
            session_id: UUID4 string for this session.
            processing_time_sec: Total elapsed time for the workflow.

        Returns:
            SummaryStats dataclass with all aggregate counts and rates.
        """
        routed = state.get("routed_transactions", [])
        scored = state.get("scored_transactions", [])

        total = len(routed)
        critical_count = sum(1 for t in routed if t.tier == "CRITICAL")
        high_count = sum(1 for t in routed if t.tier == "HIGH_QUEUE")
        med_count = sum(1 for t in routed if t.tier == "MED_BATCH")
        auto_cleared_count = sum(1 for t in routed if t.tier == "AUTO_CLEAR")

        # Autonomy rate: (auto_cleared + med_batch) / total
        if total > 0:
            autonomy_rate = (auto_cleared_count + med_count) / total
        else:
            autonomy_rate = 0.0

        # Confidence counts from scored transactions
        high_confidence_count = sum(
            1 for t in scored if t.llm_score.confidence == "HIGH"
        )
        low_confidence_count = sum(
            1 for t in scored if t.llm_score.confidence == "LOW"
        )

        return SummaryStats(
            total=total,
            critical_count=critical_count,
            high_count=high_count,
            med_count=med_count,
            auto_cleared_count=auto_cleared_count,
            autonomy_rate=autonomy_rate,
            high_confidence_count=high_confidence_count,
            low_confidence_count=low_confidence_count,
            processing_time_sec=processing_time_sec,
            session_id=session_id,
        )
