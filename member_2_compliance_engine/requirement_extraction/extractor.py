"""Deterministic, rule-based tender requirement extractor.

Uses regular expressions, keyword detection, and controlled dictionaries.
Operates 100% offline with ZERO LLM dependencies.
"""

import re
from typing import Optional

from member_2_compliance_engine.schemas.requirement import (
    CategoryEnum,
    OperatorEnum,
    RequirementType,
    StructuredRequirement,
)
from .patterns import (
    AMBIGUITY_KEYWORDS,
    COMPLIANCE_DOCUMENTS,
    CURRENCY_UNITS,
    DURATION_UNITS,
    EXPERIENCE_KEYWORDS,
    FINANCIAL_KEYWORDS,
    OPERATOR_PATTERNS,
    STORAGE_UNITS,
    TECHNICAL_KEYWORDS,
)


class RequirementExtractor:
    """Extracts structured machine-readable rules from tender clauses deterministically."""

    def extract(self, clause_text: str, rule_id: str = "R001") -> StructuredRequirement:
        """Parse natural language tender text into a StructuredRequirement.

        Args:
            clause_text: Buyer's raw tender requirement clause
            rule_id: Unique rule identifier (e.g., 'R001')

        Returns:
            StructuredRequirement validated model
        """
        text = clause_text.strip()
        if not text:
            raise ValueError("Clause text cannot be empty.")

        text_lower = text.lower()

        # 1. Check for ambiguous or disjunctive constructs first
        for amb_pattern in AMBIGUITY_KEYWORDS:
            if amb_pattern.search(text_lower):
                # Check if it has conditional disjunctions like 'OR' between configurations
                if " or " in text_lower or "either" in text_lower or "up to" in text_lower:
                    return StructuredRequirement(
                        rule_id=rule_id,
                        category=CategoryEnum.TECHNICAL.value if any(k in text_lower for k in TECHNICAL_KEYWORDS) else CategoryEnum.GENERAL.value,
                        parameter="specification",
                        operator=OperatorEnum.CONTAINS.value,
                        required_value=text[:60],
                        unit=None,
                        currency=None,
                        requirement_text=text,
                        requirement_type=RequirementType.AMBIGUOUS.value,
                    )

        # 2. Check for Document Existence (Mandatory forms, certifications)
        for doc in COMPLIANCE_DOCUMENTS:
            if doc in text_lower:
                # Check if mandatory/required/exists
                is_mandatory = any(
                    m in text_lower
                    for m in ["mandatory", "must be submitted", "shall be submitted", "required", "is required", "attached"]
                )
                if is_mandatory or "certificate" in doc or "form" in doc:
                    # Title case format of document name
                    doc_title = " ".join(word.capitalize() for word in doc.split())
                    return StructuredRequirement(
                        rule_id=rule_id,
                        category=CategoryEnum.COMPLIANCE.value,
                        parameter=doc_title,
                        operator=OperatorEnum.EXISTS.value,
                        required_value=doc_title,
                        unit=None,
                        currency=None,
                        requirement_text=text,
                        requirement_type=RequirementType.DOCUMENT_EXISTS.value,
                    )

        # Detect operator
        detected_operator = ">="  # Standard procurement default
        for pattern, op in OPERATOR_PATTERNS:
            if pattern.search(text_lower):
                detected_operator = op
                break

        # 3. Financial / Turnover requirements
        if any(k in text_lower for k in FINANCIAL_KEYWORDS) or "₹" in text or "inr" in text_lower or "lakh" in text_lower or "crore" in text_lower:
            m = re.search(
                r"(?:₹|rs\.?|inr)?\s*(\d+(?:[.,]\d+)?)\s*(lakhs?|crores?|lacs?|million|billion)?",
                text,
                re.IGNORECASE,
            )
            val = float(m.group(1).replace(",", "")) if m else 50.0
            unit = m.group(2).lower() if (m and m.group(2)) else "lakhs"
            param = "annual_turnover" if "turnover" in text_lower else "financial_capacity"
            return StructuredRequirement(
                rule_id=rule_id,
                category=CategoryEnum.FINANCIAL.value,
                parameter=param,
                operator=detected_operator,
                required_value=val,
                unit=unit,
                currency="INR",
                requirement_text=text,
                requirement_type=RequirementType.NUMERIC_COMPARISON.value,
            )

        # 4. Technical / Storage / Memory requirements (RAM, GPU, Storage)
        if any(k in text_lower for k in TECHNICAL_KEYWORDS):
            m = re.search(
                r"(\d+(?:\.\d+)?)\s*(pb|tb|gb|mb|kb|petabyte|terabyte|gigabyte|megabyte)s?",
                text,
                re.IGNORECASE,
            )
            val = float(m.group(1)) if m else 2.0
            unit = m.group(2).upper() if m else "TB"
            param = "RAM" if "ram" in text_lower else ("GPU Memory" if "gpu" in text_lower else "Memory")
            return StructuredRequirement(
                rule_id=rule_id,
                category=CategoryEnum.TECHNICAL.value,
                parameter=param,
                operator=detected_operator,
                required_value=val,
                unit=unit,
                currency=None,
                requirement_text=text,
                requirement_type=RequirementType.NUMERIC_COMPARISON.value,
            )

        # 5. Experience / Duration requirements
        if any(k in text_lower for k in EXPERIENCE_KEYWORDS) or "years" in text_lower:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(years?|months?|days?)", text, re.IGNORECASE)
            val = float(m.group(1)) if m else 5.0
            unit = m.group(2).lower() if m else "years"
            return StructuredRequirement(
                rule_id=rule_id,
                category=CategoryEnum.EXPERIENCE.value,
                parameter="experience",
                operator=detected_operator,
                required_value=val,
                unit=unit,
                currency=None,
                requirement_text=text,
                requirement_type=RequirementType.DURATION.value,
            )

        # 6. Date requirements
        date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b", text)
        if date_match:
            return StructuredRequirement(
                rule_id=rule_id,
                category=CategoryEnum.COMPLIANCE.value,
                parameter="validity_date",
                operator=detected_operator if detected_operator in ["<=", ">=", "=="] else "<=",
                required_value=date_match.group(0),
                unit=None,
                currency=None,
                requirement_text=text,
                requirement_type=RequirementType.DATE_COMPARISON.value,
            )

        # 7. Unsafe / unclassified clause -> Safely mark as AMBIGUOUS (REVIEW)
        return StructuredRequirement(
            rule_id=rule_id,
            category=CategoryEnum.GENERAL.value,
            parameter="specification",
            operator=OperatorEnum.CONTAINS.value,
            required_value=text[:60],
            unit=None,
            currency=None,
            requirement_text=text,
            requirement_type=RequirementType.AMBIGUOUS.value,
        )
