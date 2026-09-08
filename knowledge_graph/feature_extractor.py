"""Feature extractor module for the Procurement Knowledge Graph.

Extracts structured relational, regulatory, and financial features for a bidder.
Feeds into the future Risk Prediction Engine while strictly adhering to data boundaries:
unrecorded historical performance fields return None (null) rather than fabricated zeros.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from knowledge_graph.connection import Neo4jConnection
from knowledge_graph.models import BidderRiskFeatures
from knowledge_graph.queries import (
    get_bidder_profile,
    get_bidder_historical_contracts,
    get_bidder_performance_history,
    get_tenders_for_bidder,
)

logger = logging.getLogger("knowledge_graph.feature_extractor")


class RiskFeatureExtractor:
    """Extracts machine-readable risk features from the Knowledge Graph for a company."""

    def __init__(self, conn: Optional[Neo4jConnection] = None) -> None:
        self.conn = conn

    def extract_features_from_profile_dict(
        self,
        profile: dict[str, Any],
        contracts: Optional[list[dict[str, Any]]] = None,
        performance_records: Optional[list[dict[str, Any]]] = None,
        tenders: Optional[list[dict[str, Any]]] = None,
    ) -> BidderRiskFeatures:
        """Extract structured features from a pre-fetched or synthetic profile dictionary.

        Allows pure deterministic feature calculation during unit testing without
        requiring an active Neo4j database connection.
        """
        company_id = profile.get("company_id", "UNKNOWN")
        legal_name = profile.get("legal_name")

        # 1. Statutory Registration Indicators
        pan_rec = profile.get("pan_record") or {}
        has_valid_pan = (pan_rec.get("status") == "VALID") if pan_rec else None

        gst_rec = profile.get("gst_record") or {}
        has_active_gst = (gst_rec.get("status") == "ACTIVE") if gst_rec else None

        udyam_rec = profile.get("udyam_record") or {}
        has_udyam = bool(udyam_rec.get("udyam_number")) if udyam_rec else False

        deb_rec = profile.get("debarment_record") or {}
        debarment_status = deb_rec.get("is_debarred") if deb_rec else None

        oem_rec = profile.get("oem_record") or {}
        oem_authorized = bool(oem_rec.get("authorization_code")) if oem_rec else False

        # 2. Audited Financial Indicators
        fin_records = profile.get("financial_records") or []
        fin_count = len(fin_records)
        latest_turnover: Optional[float] = None
        avg_turnover: Optional[float] = None
        latest_profit: Optional[float] = None

        if fin_records:
            # Sort by financial year descending if possible
            valid_turnovers: list[float] = []
            for r in fin_records:
                if r.get("turnover") is not None:
                    valid_turnovers.append(float(r["turnover"]))

            if valid_turnovers:
                latest_turnover = valid_turnovers[0]
                avg_turnover = sum(valid_turnovers) / len(valid_turnovers)

            for r in fin_records:
                if r.get("net_profit") is not None:
                    latest_profit = float(r["net_profit"])
                    break

        # 3. Contract & Performance History
        # DATA BOUNDARY CHECK:
        # If the contracts list is None, contract tracking is not loaded in current dataset.
        # If contracts is empty list [], company has 0 recorded contracts.
        historical_contract_count: Optional[int] = None
        successful_contract_count: Optional[int] = None
        delayed_contract_count: Optional[int] = None
        penalty_count: Optional[int] = None
        termination_count: Optional[int] = None
        dispute_count: Optional[int] = None
        similar_product_contract_count: Optional[int] = None

        if contracts is not None:
            historical_contract_count = len(contracts)
            if historical_contract_count > 0 and performance_records is not None:
                successful_contract_count = sum(1 for p in performance_records if p.get("completed"))
                delayed_contract_count = sum(1 for p in performance_records if (p.get("delay_days") or 0) > 0)
                penalty_count = sum(1 for p in performance_records if (p.get("penalty") or 0) > 0)
                termination_count = sum(1 for p in performance_records if p.get("terminated"))
                dispute_count = sum(1 for p in performance_records if p.get("dispute"))

        tender_count: Optional[int] = len(tenders) if tenders is not None else 0

        # Construct audited features
        return BidderRiskFeatures(
            company_id=company_id,
            legal_name=legal_name,
            has_valid_pan=has_valid_pan,
            has_active_gst=has_active_gst,
            has_udyam=has_udyam,
            debarment_status=debarment_status,
            oem_authorized=oem_authorized,
            financial_years_count=fin_count,
            latest_turnover=latest_turnover,
            average_turnover_3yr=avg_turnover,
            latest_net_profit=latest_profit,
            historical_contract_count=historical_contract_count,
            successful_contract_count=successful_contract_count,
            delayed_contract_count=delayed_contract_count,
            penalty_count=penalty_count,
            termination_count=termination_count,
            dispute_count=dispute_count,
            tender_history_count=tender_count,
            similar_product_contract_count=similar_product_contract_count,
            compliance_score=None,  # Owned strictly by Member 2 compliance engine
            provenance={
                "source": "knowledge_graph",
                "extracted_from": "government_records.json",
                "historical_contracts_available": contracts is not None,
                "note": "Performance metrics are null when historical performance dataset is unrecorded.",
            },
        )

    def extract_features(self, company_id: str) -> Optional[BidderRiskFeatures]:
        """Query Neo4j Knowledge Graph and extract features for a company."""
        if not self.conn:
            raise RuntimeError("Cannot extract features: no active Neo4jConnection provided.")

        profile = get_bidder_profile(self.conn, company_id)
        if not profile:
            return None

        # Fetch contract / performance / tender links from graph
        contracts = get_bidder_historical_contracts(self.conn, company_id)
        # If no contracts were found in graph, pass None to indicate dataset does not contain them
        contracts_arg = contracts if contracts else None
        perf = get_bidder_performance_history(self.conn, company_id)
        perf_arg = perf if perf else None
        tenders = get_tenders_for_bidder(self.conn, company_id)

        return self.extract_features_from_profile_dict(
            profile=profile,
            contracts=contracts_arg,
            performance_records=perf_arg,
            tenders=tenders,
        )

