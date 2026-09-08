"""Deterministic rules for document presence and existence checks."""

from typing import List, Tuple
from member_2_compliance_engine.schemas.evidence import EvidenceItem


def evaluate_existence_rule(
    required_document_name: str,
    evidence_items: List[EvidenceItem],
) -> Tuple[bool, str]:
    """Evaluate whether a mandatory tender document or certification exists in evidence.

    Args:
        required_document_name: Name/type of document required (e.g., 'Manufacturer Authorization Form')
        evidence_items: List of retrieved evidence snippets

    Returns:
        Tuple[bool, str]: (is_compliant, reason)
    """
    if not evidence_items:
        return False, f"No evidence found for required document '{required_document_name}'."

    # Look for positive confirmation or presence
    req_tokens = [t.lower() for t in required_document_name.split() if len(t) > 2]

    found_matches = []
    for item in evidence_items:
        txt = item.text.lower()
        # Check negative assertions first: e.g. "not provided", "not submitted", "missing"
        if any(neg in txt for neg in ["not submitted", "not provided", "not attached", "is missing"]):
            return False, f"Document '{required_document_name}' explicitly recorded as missing in {item.source_file} (page {item.page})."

        # Check token matches
        matches = [t for t in req_tokens if t in txt]
        if len(matches) >= max(1, len(req_tokens) // 2):
            found_matches.append(item)

    if found_matches:
        ref = found_matches[0]
        return True, (
            f"Required document '{required_document_name}' confirmed present in "
            f"{ref.source_file} (page {ref.page})."
        )

    return False, f"Submitted documents do not contain evidence of '{required_document_name}'."

