"""Pydantic schemas and entity models for the Procurement Knowledge Graph.

Defines strongly-typed nodes, relationships, provenance metadata, and risk feature
contracts without any dependencies on external LLMs or APIs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class RecordTypeEnum(str, Enum):
    """Types of Government Records."""
    PAN = "PAN"
    GST = "GST"
    UDYAM = "UDYAM"
    FINANCIAL = "FINANCIAL"
    DEBARMENT = "DEBARMENT"
    OEM_AUTHORIZATION = "OEM_AUTHORIZATION"


class ProvenanceMetadata(BaseModel):
    """Audit provenance tracking for government procurement compliance."""
    model_config = ConfigDict(extra="ignore")

    source_file: str = Field(description="Name or path of the originating dataset/file")
    source_record_id: str = Field(description="ID of the record in the source file")
    source_type: str = Field(default="synthetic_dataset", description="Source classification")
    extraction_method: str = Field(default="direct_ingestion", description="Method used to extract fact")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of record creation",
    )


# ---------------------------------------------------------------------------
# Core Node Models
# ---------------------------------------------------------------------------

class CompanyNode(BaseModel):
    """Company / Bidder entity node in Knowledge Graph."""
    model_config = ConfigDict(extra="ignore")

    company_id: str = Field(description="Unique stable company identifier, e.g. CMP-00001")
    legal_name: Optional[str] = Field(default=None, description="Official legal registered company name")
    trade_name: Optional[str] = Field(default=None, description="Trade name or operating name")
    status: Optional[str] = Field(default="ACTIVE", description="Operating status (ACTIVE, DEREGISTERED, etc.)")
    category: Optional[str] = Field(default=None, description="Company category (LLP, Private Limited, etc.)")
    state_jurisdiction: Optional[str] = Field(default=None, description="State of registration")
    enterprise_type: Optional[str] = Field(default=None, description="MSME category: Micro, Small, Medium")
    major_activity: Optional[str] = Field(default=None, description="Primary industry / activity")
    provenance: ProvenanceMetadata


class TenderNode(BaseModel):
    """Public tender entity node in Knowledge Graph."""
    model_config = ConfigDict(extra="ignore")

    reference_number: str = Field(description="Unique GeM / government tender reference number, e.g. GEM/2026/B/1000001")
    tender_id: Optional[str] = Field(default=None, description="Internal UUID or tender ID")
    title: str = Field(description="Title of the tender procurement")
    description: Optional[str] = Field(default=None, description="Summary or description of scope")
    status: str = Field(default="PUBLISHED", description="Tender status: PUBLISHED, CLOSED, AWARDED")
    estimated_value: Optional[float] = Field(default=None, description="Estimated total contract value in INR")
    minimum_turnover: Optional[float] = Field(default=None, description="Mandated minimum turnover in INR")
    minimum_local_content: Optional[float] = Field(default=None, description="Mandated Make in India local content %")
    provenance: ProvenanceMetadata


class RequirementNode(BaseModel):
    """Tender eligibility requirement entity node in Knowledge Graph."""
    model_config = ConfigDict(extra="ignore")

    requirement_id: str = Field(description="Globally unique composite ID, e.g. {reference_number}_{requirement_key}")
    tender_reference: str = Field(description="Reference number of parent tender")
    requirement_key: str = Field(description="Key identifier of requirement, e.g. pan_mandatory")
    field: Optional[str] = Field(default=None, description="Target field to verify (pan, turnover, etc.)")
    type: Optional[str] = Field(default=None, description="Evaluation type: presence, numeric_threshold, equality")
    operator: Optional[str] = Field(default=None, description="Comparison operator: >=, ==, =, etc.")
    value: Optional[Any] = Field(default=None, description="Threshold or required target value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement if applicable")
    currency: Optional[str] = Field(default="INR", description="Currency code for monetary requirements")
    mandatory: bool = Field(default=True, description="Whether passing this clause is strictly mandatory")
    active_required: Optional[bool] = Field(default=None, description="Whether active status is explicitly required")
    description: Optional[str] = Field(default=None, description="Clause text or explanatory note")
    provenance: ProvenanceMetadata


class GovernmentRecordNode(BaseModel):
    """Generic Government Record node."""
    model_config = ConfigDict(extra="ignore")

    record_id: str = Field(description="Unique record identifier")
    record_type: str = Field(description="Record classification (PAN, GST, UDYAM, etc.)")
    company_id: str = Field(description="Owner company identifier")
    status: Optional[str] = Field(default=None, description="Validation status")
    source: Optional[str] = Field(default="government_portal", description="Source registry")
    provenance: ProvenanceMetadata


class PANRecordNode(GovernmentRecordNode):
    """Specific PAN registration record."""
    pan: str
    legal_name: Optional[str] = None
    category: Optional[str] = None
    date_of_issue: Optional[str] = None


class GSTRecordNode(GovernmentRecordNode):
    """Specific GST registration record."""
    gstin: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    registration_date: Optional[str] = None
    state_jurisdiction: Optional[str] = None


class UdyamRecordNode(GovernmentRecordNode):
    """Specific MSME / Udyam registration certificate."""
    udyam_number: str
    enterprise_name: Optional[str] = None
    enterprise_type: Optional[str] = None
    major_activity: Optional[str] = None
    date_of_commencement: Optional[str] = None


class FinancialRecordNode(GovernmentRecordNode):
    """Audited financial year performance record."""
    pan: Optional[str] = None
    financial_year: str
    turnover: float
    net_profit: Optional[float] = None
    filing_date: Optional[str] = None


class DebarmentRecordNode(GovernmentRecordNode):
    """Blacklist / Debarment record from government agencies."""
    pan: Optional[str] = None
    legal_name: Optional[str] = None
    is_debarred: bool = False
    debarment_agency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class OEMRecordNode(GovernmentRecordNode):
    """OEM Authorization certificate record."""
    oem_name: str
    authorized_partner_pan: Optional[str] = None
    authorized_partner_name: Optional[str] = None
    authorization_code: str
    validity_end_date: Optional[str] = None


class OrganizationNode(BaseModel):
    """External organization / OEM entity."""
    model_config = ConfigDict(extra="ignore")

    org_id: str = Field(description="Unique identifier or slug for organization")
    name: str = Field(description="Organization name")
    org_type: str = Field(default="OEM", description="OEM, Government Agency, Procuring Entity")
    provenance: ProvenanceMetadata


class ProductNode(BaseModel):
    """Product or procurement category."""
    model_config = ConfigDict(extra="ignore")

    product_id: str = Field(description="Unique product or category slug")
    name: str = Field(description="Product or category title")
    category: Optional[str] = Field(default=None, description="Broad category group")
    provenance: ProvenanceMetadata


class ContractNode(BaseModel):
    """Contract node (schema-ready for historical procurement contracts)."""
    model_config = ConfigDict(extra="ignore")

    contract_id: str = Field(description="Unique contract number")
    title: Optional[str] = None
    company_id: Optional[str] = None
    tender_reference: Optional[str] = None
    value: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = "COMPLETED"
    provenance: Optional[ProvenanceMetadata] = None


class PerformanceNode(BaseModel):
    """Performance evaluation node (schema-ready for contract execution history)."""
    model_config = ConfigDict(extra="ignore")

    performance_id: str = Field(description="Unique performance record ID")
    contract_id: Optional[str] = None
    delay_days: Optional[int] = None
    penalty: Optional[float] = None
    terminated: Optional[bool] = None
    completed: Optional[bool] = None
    dispute: Optional[bool] = None
    completion_date: Optional[str] = None
    provenance: Optional[ProvenanceMetadata] = None


class DocumentNode(BaseModel):
    """Submitted or verified document node."""
    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(description="Unique document hash or ID")
    filename: str
    document_type: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    provenance: Optional[ProvenanceMetadata] = None


# ---------------------------------------------------------------------------
# Feature Extraction Contract (For Future Risk Engine)
# ---------------------------------------------------------------------------

class BidderRiskFeatures(BaseModel):
    """Structured graph feature payload for future Risk Prediction Engine.

    NOTE: Fields for which actual data is not present in the current dataset
    are strictly None (null) rather than fabricated 0s.
    """
    model_config = ConfigDict(extra="ignore")

    company_id: str
    legal_name: Optional[str] = None

    # Government record verification indicators
    has_valid_pan: Optional[bool] = None
    has_active_gst: Optional[bool] = None
    has_udyam: Optional[bool] = None
    debarment_status: Optional[bool] = None
    oem_authorized: Optional[bool] = None

    # Audited financial features from 3-year records
    financial_years_count: int = 0
    latest_turnover: Optional[float] = None
    average_turnover_3yr: Optional[float] = None
    latest_net_profit: Optional[float] = None

    # Historical contract execution features
    # NOTE: Set to None when historical contracts dataset is not yet loaded
    historical_contract_count: Optional[int] = None
    successful_contract_count: Optional[int] = None
    delayed_contract_count: Optional[int] = None
    penalty_count: Optional[int] = None
    termination_count: Optional[int] = None
    dispute_count: Optional[int] = None
    tender_history_count: Optional[int] = None
    similar_product_contract_count: Optional[int] = None

    # Compliance score: Owned by Member 2 Deterministic Compliance Engine, NOT KG
    compliance_score: Optional[float] = Field(
        default=None,
        description="Provided strictly by the Member 2 compliance engine during bid evaluation",
    )

    provenance: dict[str, Any] = Field(default_factory=dict)

