"""Canonical Requirement Seed and Family Generator.

Generates structured, strongly-typed requirement families across 11 procurement categories,
providing a deterministic base for linguistic synthesis and anti-leakage dataset splitting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class RequirementFamily:
    """Represents a canonical semantic requirement family.

    Crucial for Zero Leakage: dataset splits are performed at the family level,
    ensuring linguistic variations of the same requirement do not cross train/test splits.
    """
    family_id: str
    category: str
    field: Optional[str]
    operator: Optional[str]
    value: Any
    unit: Optional[str] = None
    period: Optional[str] = None
    mandatory: bool = True
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_canonical_dict(self, requirement_id: str) -> dict[str, Any]:
        """Convert to the canonical target schema object."""
        return {
            "requirement_id": requirement_id,
            "category": self.category,
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "unit": self.unit,
            "period": self.period,
            "mandatory": self.mandatory,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_reason": self.ambiguity_reason,
        }


def build_seed_requirement_families() -> list[RequirementFamily]:
    """Construct the comprehensive catalog of canonical requirement families."""
    families: list[RequirementFamily] = []

    # -----------------------------------------------------------------------
    # 1. FINANCIAL CATEGORY
    # -----------------------------------------------------------------------
    turnover_values = [
        (2500000, "25L"),
        (5000000, "50L"),
        (10000000, "1Cr"),
        (20000000, "2Cr"),
        (50000000, "5Cr"),
        (100000000, "10Cr"),
        (250000000, "25Cr"),
        (500000000, "50Cr"),
    ]
    for val, tag in turnover_values:
        # Annual turnover (>=)
        families.append(
            RequirementFamily(
                family_id=f"FAM_FIN_ANNUAL_TURNOVER_{tag}",
                category="financial",
                field="annual_turnover",
                operator=">=",
                value=val,
                unit="INR",
                period=None,
                mandatory=True,
                tags=("financial", "turnover", "annual"),
            )
        )
        # Average turnover with period (>=)
        families.append(
            RequirementFamily(
                family_id=f"FAM_FIN_AVG_TURNOVER_3YR_{tag}",
                category="financial",
                field="average_turnover",
                operator=">=",
                value=val,
                unit="INR",
                period="preceding 3 financial years",
                mandatory=True,
                tags=("financial", "turnover", "average", "temporal"),
            )
        )

    # Net worth & Solvency
    net_worth_values = [(1000000, "10L"), (5000000, "50L"), (10000000, "1Cr"), (25000000, "2.5Cr")]
    for val, tag in net_worth_values:
        families.append(
            RequirementFamily(
                family_id=f"FAM_FIN_NET_WORTH_{tag}",
                category="financial",
                field="net_worth",
                operator=">=",
                value=val,
                unit="INR",
                period=None,
                mandatory=True,
                tags=("financial", "net_worth"),
            )
        )

    solvency_values = [(2000000, "20L"), (5000000, "50L"), (10000000, "1Cr")]
    for val, tag in solvency_values:
        families.append(
            RequirementFamily(
                family_id=f"FAM_FIN_SOLVENCY_{tag}",
                category="financial",
                field="solvency",
                operator=">=",
                value=val,
                unit="INR",
                period=None,
                mandatory=True,
                tags=("financial", "solvency"),
            )
        )

    families.append(
        RequirementFamily(
            family_id="FAM_FIN_PROFITABILITY",
            category="financial",
            field="profitability",
            operator="==",
            value=True,
            unit=None,
            period="last 3 financial years",
            mandatory=True,
            tags=("financial", "profitability", "temporal"),
        )
    )

    # -----------------------------------------------------------------------
    # 2. TAX & STATUTORY
    # -----------------------------------------------------------------------
    families.append(
        RequirementFamily(
            family_id="FAM_TAX_PAN_MANDATORY",
            category="tax_statutory",
            field="pan",
            operator="exists",
            value=True,
            unit=None,
            mandatory=True,
            tags=("tax", "pan"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_TAX_GSTIN_MANDATORY",
            category="tax_statutory",
            field="gstin",
            operator="exists",
            value=True,
            unit=None,
            mandatory=True,
            tags=("tax", "gstin"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_TAX_GST_ACTIVE_STATUS",
            category="tax_statutory",
            field="gst_status",
            operator="==",
            value="ACTIVE",
            unit=None,
            mandatory=True,
            tags=("tax", "gst_status"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_TAX_ITR_3YR",
            category="tax_statutory",
            field="itr_filing",
            operator=">=",
            value=3,
            unit="years",
            period="last 3 assessment years",
            mandatory=True,
            tags=("tax", "itr", "temporal"),
        )
    )

    # -----------------------------------------------------------------------
    # 3. MSME / UDYAM
    # -----------------------------------------------------------------------
    families.append(
        RequirementFamily(
            family_id="FAM_MSME_UDYAM_CERT",
            category="msme",
            field="udyam",
            operator="exists",
            value=True,
            unit=None,
            mandatory=False,
            tags=("msme", "udyam"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_MSME_CLASSIFICATION_MICRO_SMALL",
            category="msme",
            field="msme_classification",
            operator="contains",
            value="Micro or Small",
            unit=None,
            mandatory=False,
            tags=("msme", "classification"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_MSME_NSIC_REGISTRATION",
            category="msme",
            field="nsic_registration",
            operator="exists",
            value=True,
            unit=None,
            mandatory=False,
            tags=("msme", "nsic"),
        )
    )

    # -----------------------------------------------------------------------
    # 4. EXPERIENCE
    # -----------------------------------------------------------------------
    for exp_yr in [2, 3, 5, 7, 10]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_EXP_YEARS_{exp_yr}YR",
                category="experience",
                field="years_of_experience",
                operator=">=",
                value=exp_yr,
                unit="years",
                period=None,
                mandatory=True,
                tags=("experience", "years"),
            )
        )

    for proj_cnt in [1, 2, 3, 5]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_EXP_PROJECTS_{proj_cnt}",
                category="experience",
                field="completed_projects",
                operator=">=",
                value=proj_cnt,
                unit="projects",
                period="during the last 5 years",
                mandatory=True,
                tags=("experience", "projects", "temporal"),
            )
        )

    families.append(
        RequirementFamily(
            family_id="FAM_EXP_GOV_PROJECTS_2",
            category="experience",
            field="government_project_experience",
            operator=">=",
            value=2,
            unit="projects",
            period="past 3 years",
            mandatory=True,
            tags=("experience", "government", "temporal"),
        )
    )

    # -----------------------------------------------------------------------
    # 5. TECHNICAL SPECIFICATIONS
    # -----------------------------------------------------------------------
    for cores in [16, 32, 64, 128]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_TECH_CPU_{cores}C",
                category="technical",
                field="cpu_cores",
                operator=">=",
                value=cores,
                unit="cores",
                mandatory=True,
                tags=("technical", "cpu"),
            )
        )

    for vram in [48, 80, 96, 144, 192]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_TECH_GPU_VRAM_{vram}GB",
                category="technical",
                field="gpu_memory",
                operator=">=",
                value=vram,
                unit="GB",
                mandatory=True,
                tags=("technical", "gpu", "memory"),
            )
        )

    for ram in [64, 128, 192, 256, 512, 1024, 2048]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_TECH_RAM_{ram}GB",
                category="technical",
                field="ram_capacity",
                operator=">=",
                value=ram,
                unit="GB",
                mandatory=True,
                tags=("technical", "ram", "memory"),
            )
        )

    for tb in [1, 2, 4, 8, 16, 32]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_TECH_STORAGE_{tb}TB",
                category="technical",
                field="storage_capacity",
                operator=">=",
                value=tb,
                unit="TB",
                mandatory=True,
                tags=("technical", "storage"),
            )
        )

    for bw in [10, 25, 40, 100, 200]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_TECH_BANDWIDTH_{bw}G",
                category="technical",
                field="network_bandwidth",
                operator=">=",
                value=bw,
                unit="Gbps",
                mandatory=True,
                tags=("technical", "network"),
            )
        )

    families.append(
        RequirementFamily(
            family_id="FAM_TECH_OP_TEMP_45C",
            category="technical",
            field="operating_temperature",
            operator="<=",
            value=45,
            unit="Celsius",
            mandatory=True,
            tags=("technical", "temperature"),
        )
    )

    # -----------------------------------------------------------------------
    # 6. CERTIFICATION
    # -----------------------------------------------------------------------
    for iso in ["ISO 9001", "ISO 27001", "ISO 14001", "ISO 20000"]:
        clean_tag = iso.replace(" ", "_")
        families.append(
            RequirementFamily(
                family_id=f"FAM_CERT_{clean_tag}",
                category="certification",
                field="iso_certification",
                operator="contains",
                value=iso,
                unit=None,
                mandatory=True,
                tags=("certification", "iso"),
            )
        )

    # Compound certification (includes_all)
    families.append(
        RequirementFamily(
            family_id="FAM_CERT_COMPOUND_9001_27001",
            category="certification",
            field="iso_certification",
            operator="includes_all",
            value=["ISO 9001", "ISO 27001"],
            unit=None,
            mandatory=True,
            tags=("certification", "compound", "iso"),
        )
    )

    families.append(
        RequirementFamily(
            family_id="FAM_CERT_BIS_MANDATORY",
            category="certification",
            field="bis_certification",
            operator="exists",
            value=True,
            unit=None,
            mandatory=True,
            tags=("certification", "bis"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_CERT_STQC_MANDATORY",
            category="certification",
            field="stqc_certificate",
            operator="exists",
            value=True,
            unit=None,
            mandatory=True,
            tags=("certification", "stqc"),
        )
    )

    # -----------------------------------------------------------------------
    # 7. OEM & MANUFACTURER AUTHORIZATION
    # -----------------------------------------------------------------------
    families.append(
        RequirementFamily(
            family_id="FAM_OEM_MAF_MANDATORY",
            category="oem",
            field="oem_authorization",
            operator="==",
            value=True,
            unit=None,
            mandatory=True,
            tags=("oem", "maf"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_OEM_AUTHORIZED_DISTRIBUTOR",
            category="oem",
            field="authorized_distributor",
            operator="==",
            value=True,
            unit=None,
            mandatory=True,
            tags=("oem", "distributor"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_OEM_AUTH_VALIDITY_24M",
            category="oem",
            field="authorization_validity_period",
            operator=">=",
            value=24,
            unit="months",
            mandatory=True,
            tags=("oem", "validity"),
        )
    )

    # -----------------------------------------------------------------------
    # 8. LOCAL CONTENT (MAKE IN INDIA)
    # -----------------------------------------------------------------------
    for lcp in [20, 50, 60, 80]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_MII_LOCAL_CONTENT_{lcp}PCT",
                category="local_content",
                field="local_content_percentage",
                operator=">=",
                value=lcp,
                unit="%",
                mandatory=True,
                tags=("local_content", "mii"),
            )
        )

    families.append(
        RequirementFamily(
            family_id="FAM_MII_CLASS_I_SUPPLIER",
            category="local_content",
            field="make_in_india_class",
            operator="==",
            value="Class-I Local Supplier",
            unit=None,
            mandatory=True,
            tags=("local_content", "class_i"),
        )
    )

    # -----------------------------------------------------------------------
    # 9. LEGAL & DEBARMENT
    # -----------------------------------------------------------------------
    families.append(
        RequirementFamily(
            family_id="FAM_LEGAL_NON_DEBARRED",
            category="legal",
            field="is_debarred",
            operator="==",
            value=False,
            unit=None,
            mandatory=True,
            tags=("legal", "debarment"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_LEGAL_NON_BLACKLISTING_AFFIDAVIT",
            category="legal",
            field="non_blacklisting_declaration",
            operator="exists",
            value=True,
            unit=None,
            mandatory=True,
            tags=("legal", "affidavit"),
        )
    )

    # -----------------------------------------------------------------------
    # 10. COMMERCIAL & BID SECURITY
    # -----------------------------------------------------------------------
    emd_values = [(50000, "50k"), (100000, "1L"), (250000, "2.5L"), (500000, "5L"), (1000000, "10L")]
    for val, tag in emd_values:
        families.append(
            RequirementFamily(
                family_id=f"FAM_COMM_EMD_{tag}",
                category="commercial",
                field="emd_amount",
                operator="==",
                value=val,
                unit="INR",
                mandatory=True,
                tags=("commercial", "emd"),
            )
        )

    families.append(
        RequirementFamily(
            family_id="FAM_COMM_BID_SECURITY_DECLARATION",
            category="commercial",
            field="bid_security_declaration",
            operator="exists",
            value=True,
            unit=None,
            mandatory=False,
            tags=("commercial", "bsd"),
        )
    )
    families.append(
        RequirementFamily(
            family_id="FAM_COMM_PBG_5PCT",
            category="commercial",
            field="performance_bank_guarantee_percentage",
            operator="<=",
            value=5,
            unit="%",
            mandatory=True,
            tags=("commercial", "pbg"),
        )
    )

    # -----------------------------------------------------------------------
    # 11. DELIVERY, INSTALLATION & WARRANTY
    # -----------------------------------------------------------------------
    for d_days in [15, 30, 45, 60, 90]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_DELIV_PERIOD_{d_days}D",
                category="delivery",
                field="delivery_period",
                operator="<=",
                value=d_days,
                unit="days",
                mandatory=True,
                tags=("delivery", "lead_time"),
            )
        )

    for w_yrs in [1, 2, 3, 5]:
        families.append(
            RequirementFamily(
                family_id=f"FAM_DELIV_WARRANTY_{w_yrs}YR",
                category="delivery",
                field="warranty_period",
                operator=">=",
                value=w_yrs,
                unit="years",
                mandatory=True,
                tags=("delivery", "warranty"),
            )
        )

    # -----------------------------------------------------------------------
    # 12. AMBIGUOUS REQUIREMENT FAMILIES (REVIEW Routing)
    # -----------------------------------------------------------------------
    ambiguous_specs = [
        (
            "FAM_AMB_RAM_DISJUNCTIVE",
            "technical",
            "RAM",
            "Conditional disjunctive configuration (8 x 192 GB OR 16 x 96 GB) without firm commitment",
        ),
        (
            "FAM_AMB_STORAGE_UP_TO",
            "technical",
            "storage_capacity",
            "Non-committal wording ('Up to 2 TB storage may be provided depending on availability')",
        ),
        (
            "FAM_AMB_CERT_EQUIVALENT",
            "certification",
            "iso_certification",
            "Subjective discretionary clause ('Equivalent certification may be accepted subject to buyer approval')",
        ),
        (
            "FAM_AMB_TURNOVER_APPROX",
            "financial",
            "annual_turnover",
            "Vague financial threshold ('Turnover roughly in the range of 50 lakhs or higher preferred')",
        ),
        (
            "FAM_AMB_EXPERIENCE_RELEVANT",
            "experience",
            "years_of_experience",
            "Ambiguous qualifying adjective ('Adequate and relevant experience as deemed satisfactory by committee')",
        ),
        (
            "FAM_AMB_OEM_FLEXIBLE",
            "oem",
            "oem_authorization",
            "Optional or non-firm authorization ('OEM authorization letter or equivalent undertaking acceptable if applicable')",
        ),
    ]
    for fid, cat, fld, reason in ambiguous_specs:
        families.append(
            RequirementFamily(
                family_id=fid,
                category="ambiguous",
                field=fld,
                operator=None,
                value=None,
                unit=None,
                mandatory=True,
                is_ambiguous=True,
                ambiguity_reason=reason,
                tags=("ambiguous", cat),
            )
        )

    return families


class RequirementGenerator:
    """Manages creation, filtering, and indexing of requirement families."""

    def __init__(self, families: Optional[list[RequirementFamily]] = None) -> None:
        self.families = families or build_seed_requirement_families()
        self._family_map = {f.family_id: f for f in self.families}

    def get_family(self, family_id: str) -> Optional[RequirementFamily]:
        return self._family_map.get(family_id)

    def list_categories(self) -> list[str]:
        return sorted(set(f.category for f in self.families))

    def filter_by_category(self, category: str) -> list[RequirementFamily]:
        return [f for f in self.families if f.category == category]

    def count(self) -> int:
        return len(self.families)
