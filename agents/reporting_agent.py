"""SentinelIQ Reporting Agent.

Final agent in the LangGraph pipeline. Generates an 8-section PDF
investigation report using fpdf2, uploads it to AWS S3, and sends
Gmail SMTP alerts for CRITICAL transactions.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 20.2, 20.3
"""

from __future__ import annotations

import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fpdf import FPDF

from models import (
    RoutedTransaction,
    SummaryStats,
    WorkflowState,
)


class _ReportPDF(FPDF):
    """Custom FPDF subclass with SentinelIQ header and footer."""

    HEADER_TEXT = "SENTINELIQ FRAUD INVESTIGATION REPORT"
    FOOTER_TEXT = (
        "SentinelIQ | AI Fraud Transaction Investigation Assistant "
        "| Developed by Team 9 \u00b7 Group 9 \u00b7 IIT Roorkee"
    )

    def header(self) -> None:
        """Render the report header on every page."""
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(245, 158, 11)  # --primary amber
        self.cell(0, 10, self.HEADER_TEXT, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        # Separator line
        self.set_draw_color(31, 41, 55)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        """Render the footer on every page."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(156, 163, 175)  # --muted
        self.cell(0, 10, self.FOOTER_TEXT, align="C")


class ReportingAgent:
    """Fourth agent in the LangGraph pipeline.

    Compiles an 8-section PDF fraud investigation report, uploads it
    to AWS S3, and sends Gmail alerts when CRITICAL transactions exist.
    """

    def __init__(self, config: dict | None = None) -> None:
        """Initialise the ReportingAgent.

        Args:
            config: Runtime configuration dictionary (from config.json).
        """
        self.config = config or {}

    def compile_report(self, state: WorkflowState) -> WorkflowState:
        """Orchestrate PDF build, S3 upload, Gmail alert.

        Args:
            state: The shared WorkflowState after action routing.

        Returns:
            Updated WorkflowState with report_url populated.
        """
        errors: list[str] = list(state.get("errors", []))
        routed = state.get("routed_transactions", [])
        summary = state.get("summary_stats")
        session_id = summary.session_id if summary else str(uuid.uuid4())

        # Build PDF
        try:
            pdf_bytes = self.build_pdf(routed, summary)
        except Exception as e:
            errors.append(f"ReportingAgent: PDF generation failed: {e}")
            state["errors"] = errors
            state["report_url"] = ""
            return state

        # Upload to S3
        report_url = ""
        try:
            report_url = self.upload_to_s3(pdf_bytes, session_id)
        except Exception as e:
            errors.append(f"ReportingAgent: S3 upload failed: {e}")

        # Send Gmail alert if CRITICAL transactions exist
        critical_count = summary.critical_count if summary else 0
        if critical_count > 0:
            try:
                self.send_gmail_alert(routed, summary, report_url)
            except Exception as e:
                errors.append(f"ReportingAgent: Gmail alert failed: {e}")

        state["report_url"] = report_url
        state["errors"] = errors
        return state

    def build_pdf(
        self,
        routed_transactions: list[RoutedTransaction],
        summary: SummaryStats | None,
    ) -> bytes:
        """Render an 8-section PDF investigation report.

        Sections:
        1. Executive Summary
        2. Transaction Overview
        3. CRITICAL Alerts
        4. HIGH-Risk Transactions
        5. MED-Batch Items
        6. Auto-Cleared Transactions
        7. Pattern Memory Insights
        8. Methodology Notes

        Args:
            routed_transactions: All routed transactions from the workflow.
            summary: Aggregate statistics for the run.

        Returns:
            PDF file content as bytes.
        """
        pdf = _ReportPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Partition transactions by tier
        critical_txns = [t for t in routed_transactions if t.tier == "CRITICAL"]
        high_txns = [t for t in routed_transactions if t.tier == "HIGH_QUEUE"]
        med_txns = [t for t in routed_transactions if t.tier == "MED_BATCH"]
        auto_txns = [t for t in routed_transactions if t.tier == "AUTO_CLEAR"]

        # Section 1: Executive Summary
        self._section_heading(pdf, "1. Executive Summary")
        if summary:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, (
                f"Session ID: {summary.session_id}\n"
                f"Total Transactions Processed: {summary.total}\n"
                f"Processing Time: {summary.processing_time_sec:.2f} seconds\n"
                f"Autonomy Rate: {summary.autonomy_rate:.1%}\n\n"
                f"Risk Distribution:\n"
                f"  CRITICAL: {summary.critical_count}\n"
                f"  HIGH: {summary.high_count}\n"
                f"  MED: {summary.med_count}\n"
                f"  AUTO-CLEARED: {summary.auto_cleared_count}\n\n"
                f"Confidence Split:\n"
                f"  HIGH confidence: {summary.high_confidence_count}\n"
                f"  LOW confidence: {summary.low_confidence_count}"
            ))
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, "No summary statistics available.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Section 2: Transaction Overview
        self._section_heading(pdf, "2. Transaction Overview")
        pdf.set_font("Helvetica", "", 10)
        total = len(routed_transactions)
        pdf.multi_cell(0, 5, (
            f"Total routed transactions: {total}\n"
            f"CRITICAL: {len(critical_txns)} | HIGH_QUEUE: {len(high_txns)} | "
            f"MED_BATCH: {len(med_txns)} | AUTO_CLEAR: {len(auto_txns)}"
        ))
        pdf.ln(4)

        # Section 3: CRITICAL Alerts
        self._section_heading(pdf, "3. CRITICAL Alerts")
        self._render_transaction_table(pdf, critical_txns, max_rows=20)

        # Section 4: HIGH-Risk Transactions
        self._section_heading(pdf, "4. HIGH-Risk Transactions")
        self._render_transaction_table(pdf, high_txns, max_rows=30)

        # Section 5: MED-Batch Items
        self._section_heading(pdf, "5. MED-Batch Items")
        self._render_transaction_table(pdf, med_txns, max_rows=30)

        # Section 6: Auto-Cleared Transactions
        self._section_heading(pdf, "6. Auto-Cleared Transactions")
        self._render_transaction_table(pdf, auto_txns, max_rows=30)

        # Section 7: Pattern Memory Insights
        self._section_heading(pdf, "7. Pattern Memory Insights")
        pdf.set_font("Helvetica", "", 10)
        # Summarise pattern adjustments across transactions
        adjustments = [
            t.scored.pattern_adjustment
            for t in routed_transactions
            if t.scored.pattern_adjustment != 0
        ]
        if adjustments:
            positive = [a for a in adjustments if a > 0]
            negative = [a for a in adjustments if a < 0]
            pdf.multi_cell(0, 5, (
                f"Transactions with pattern adjustments: {len(adjustments)}\n"
                f"  Positive adjustments (approved patterns): {len(positive)}\n"
                f"  Negative adjustments (rejected patterns): {len(negative)}\n"
                f"  Average adjustment: {sum(adjustments) / len(adjustments):+.1f}"
            ))
        else:
            pdf.cell(
                0, 5,
                "No pattern memory adjustments applied in this session.",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(4)

        # Section 8: Methodology Notes
        self._section_heading(pdf, "8. Methodology Notes")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, (
            "SentinelIQ employs a multi-agent LangGraph pipeline:\n"
            "1. Transaction Agent: Parses CSV, computes 5 binary fraud feature flags, "
            "builds network graph.\n"
            "2. Fraud Detection Agent: Retrieves policy context via FAISS RAG, "
            "scores 0-100 using Gemini 1.5 Flash, applies pattern memory adjustment.\n"
            "3. Action Agent: Routes transactions into CRITICAL/HIGH/MED/AUTO tiers "
            "based on score and confidence.\n"
            "4. Reporting Agent: Compiles this report, uploads to S3, "
            "sends Gmail alerts for CRITICAL cases.\n\n"
            "Scoring is augmented by a self-learning pattern memory that records "
            "analyst APPROVE/REJECT decisions and applies decay-adjusted "
            "score modifications (+10/-15) to recurring patterns.\n\n"
            "Rule-based fallback scoring (active_count x 20 with night multiplier) "
            "ensures continuity when the LLM API is unavailable."
        ))

        # Output PDF bytes
        return bytes(pdf.output())

    def upload_to_s3(self, pdf_bytes: bytes, session_id: str) -> str:
        """Upload the PDF report to S3 and return a presigned URL.

        Target path:
            s3://fraud-investigation-group9/reports/{date}/{session_id}/FraudReport.pdf

        Args:
            pdf_bytes: The PDF file content.
            session_id: UUID4 identifying this workflow session.

        Returns:
            Presigned URL string for the uploaded PDF (valid for 7 days).

        Raises:
            ClientError: If the S3 upload or presigning fails.
        """
        bucket = "fraud-investigation-group9"
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"reports/{date_str}/{session_id}/FraudReport.pdf"

        s3_client = boto3.client("s3")

        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )

        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=7 * 24 * 3600,  # 7 days
        )

        return presigned_url

    def send_gmail_alert(
        self,
        routed_transactions: list[RoutedTransaction],
        summary: SummaryStats | None,
        report_url: str,
    ) -> None:
        """Send a Gmail SMTP alert for CRITICAL transactions.

        Only triggered when critical_count > 0.

        Args:
            routed_transactions: All routed transactions.
            summary: Aggregate statistics.
            report_url: Presigned S3 URL for the PDF report.

        Raises:
            Exception: If SMTP connection or sending fails.
        """
        gmail_address = os.environ.get("GMAIL_ADDRESS", "")
        gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")

        if not gmail_address or not gmail_password:
            raise ValueError(
                "GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables required"
            )

        critical_txns = [t for t in routed_transactions if t.tier == "CRITICAL"]
        critical_count = len(critical_txns)

        if critical_count == 0:
            return

        # Build email
        subject = (
            f"SentinelIQ CRITICAL Alert: {critical_count} "
            f"high-risk transaction(s) detected"
        )

        # Build body
        body_lines = [
            "SentinelIQ Fraud Investigation Alert",
            "=" * 40,
            "",
            f"CRITICAL Transactions Detected: {critical_count}",
            "",
            "Transaction Details:",
            "-" * 40,
        ]

        for txn in critical_txns[:10]:  # Limit to first 10 in email
            row = txn.scored.enriched.row
            body_lines.append(
                f"  ID: {row.transaction_id} | Account: {row.account_id} | "
                f"Amount: {row.amount:.2f} | Score: {txn.scored.final_score}"
            )

        if critical_count > 10:
            body_lines.append(f"  ... and {critical_count - 10} more")

        body_lines.extend([
            "",
            "-" * 40,
            "",
            "Full Investigation Report:",
            report_url if report_url else "(Report URL not available)",
            "",
            "This is an automated alert from SentinelIQ.",
            "AI Fraud Transaction Investigation Assistant",
            "Developed by Team 9 · Group 9 · IIT Roorkee",
        ])

        body = "\n".join(body_lines)

        # Send via SMTP
        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = gmail_address  # Send to self (configurable)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_address, gmail_password)
            server.send_message(msg)

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _section_heading(self, pdf: _ReportPDF, title: str) -> None:
        """Render a section heading in the PDF."""
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(249, 250, 251)  # --fg
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)  # Reset to black for body text
        pdf.ln(1)

    def _render_transaction_table(
        self,
        pdf: _ReportPDF,
        transactions: list[RoutedTransaction],
        max_rows: int = 30,
    ) -> None:
        """Render a transaction summary table in the PDF.

        Args:
            pdf: The PDF instance.
            transactions: List of routed transactions to display.
            max_rows: Maximum rows to render (prevents oversized PDFs).
        """
        if not transactions:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, "None in this category.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
            return

        # Table header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(31, 41, 55)  # --border dark
        pdf.set_text_color(249, 250, 251)
        col_widths = [25, 25, 20, 15, 15, 90]
        headers = ["Txn ID", "Account", "Amount", "Score", "Conf", "Reason"]
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, border=1, fill=True)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(0, 0, 0)
        for txn in transactions[:max_rows]:
            row = txn.scored.enriched.row
            reason = txn.scored.llm_score.reason[:50] + (
                "..." if len(txn.scored.llm_score.reason) > 50 else ""
            )
            cells = [
                str(row.transaction_id)[:12],
                str(row.account_id)[:12],
                f"{row.amount:.0f}",
                str(txn.scored.final_score),
                txn.scored.llm_score.confidence[:4],
                reason,
            ]
            for i, cell_text in enumerate(cells):
                pdf.cell(col_widths[i], 5, cell_text, border=1)
            pdf.ln()

        if len(transactions) > max_rows:
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(
                0, 5,
                f"... {len(transactions) - max_rows} additional transactions not shown.",
                new_x="LMARGIN", new_y="NEXT",
            )

        pdf.ln(3)
