"""Deterministic string and pattern evaluation rules for tender requirements.

Supports operators: == (exact_match), contains, includes_all
"""

from typing import List, Tuple, Union


def evaluate_string_rule(
    operator: str,
    required_value: Union[str, List[str]],
    observed_text: str,
    case_sensitive: bool = False,
) -> Tuple[bool, str]:
    """Deterministically evaluate string matching and containment rules.

    Args:
        operator: '==', 'exact_match', 'contains', 'includes_all'
        required_value: Target string or list of required strings
        observed_text: Raw or extracted text from bidder evidence
        case_sensitive: Whether comparison should preserve case

    Returns:
        Tuple[bool, str]: (is_compliant, auditable_reason)
    """
    op = operator.strip().lower()
    text = observed_text if case_sensitive else observed_text.lower()

    if op in ["==", "exact_match", "equals"]:
        if not isinstance(required_value, str):
            req_str = str(required_value)
        else:
            req_str = required_value

        target = req_str if case_sensitive else req_str.lower()
        passed = (text.strip() == target.strip())
        if passed:
            reason = f"Observed text exactly matches required '{req_str}'."
        else:
            reason = f"Observed text does not match required '{req_str}'."

    elif op in ["contains", "contain", "includes"]:
        if not isinstance(required_value, str):
            req_str = str(required_value)
        else:
            req_str = required_value

        target = req_str if case_sensitive else req_str.lower()
        passed = target in text
        if passed:
            reason = f"Evidence contains the required string '{req_str}'."
        else:
            reason = f"Evidence does not contain the required string '{req_str}'."

    elif op in ["includes_all", "include_all", "all"]:
        if isinstance(required_value, str):
            # Split comma-separated tokens if string
            targets = [t.strip() for t in required_value.split(",") if t.strip()]
        elif isinstance(required_value, list):
            targets = [str(t).strip() for t in required_value]
        else:
            targets = [str(required_value).strip()]

        missing = []
        for t in targets:
            sub = t if case_sensitive else t.lower()
            if sub not in text:
                missing.append(t)

        passed = len(missing) == 0
        if passed:
            reason = f"Evidence contains all {len(targets)} required specifications: {targets}."
        else:
            reason = f"Evidence is missing required specifications: {missing}."

    else:
        raise ValueError(f"Unsupported string operator: '{operator}'.")

    return passed, reason

