"""Deterministic numeric comparison rules for tender requirements.

Supports operators: ==, >=, <=, <, >
Does not use an LLM for arithmetic comparisons.
"""

from typing import Tuple


def evaluate_numeric_comparison(
    operator: str,
    required_value: float,
    observed_value: float,
    parameter: str = "value",
    unit_label: str = "",
) -> Tuple[bool, str]:
    """Deterministically compare observed vs required numeric values.

    Args:
        operator: Comparison operator ('==', '>=', '<=', '<', '>')
        required_value: The threshold defined in buyer's tender requirement
        observed_value: The normalized value extracted from bidder's evidence
        parameter: Name of the parameter being evaluated (for auditable reason)
        unit_label: Unit string for display (e.g. '₹', 'Lakhs', 'GB')

    Returns:
        Tuple[bool, str]: (is_compliant, auditable_reason)

    Raises:
        ValueError: If operator is unsupported.
    """
    op = operator.strip().lower()
    tol = 1e-6

    unit_str = f" {unit_label}".rstrip() if unit_label else ""

    if op in ["==", "=", "eq"]:
        passed = abs(observed_value - required_value) < tol
        if passed:
            reason = f"Observed {parameter}{unit_str} ({observed_value}) equals required ({required_value})."
        else:
            reason = f"Observed {parameter}{unit_str} ({observed_value}) does not equal required ({required_value})."

    elif op in [">=", "gte"]:
        passed = (observed_value - required_value) >= -tol
        if passed:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) satisfies minimum requirement "
                f"(>= {required_value}{unit_str})."
            )
        else:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) is below the minimum required "
                f"({required_value}{unit_str})."
            )

    elif op in ["<=", "lte"]:
        passed = (observed_value - required_value) <= tol
        if passed:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) satisfies maximum limit "
                f"(<= {required_value}{unit_str})."
            )
        else:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) exceeds the maximum allowed limit "
                f"({required_value}{unit_str})."
            )

    elif op in [">", "gt"]:
        passed = (observed_value - required_value) > tol
        if passed:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) is strictly greater than required "
                f"(> {required_value}{unit_str})."
            )
        else:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) is not strictly greater than "
                f"required ({required_value}{unit_str})."
            )

    elif op in ["<", "lt"]:
        passed = (observed_value - required_value) < -tol
        if passed:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) is strictly less than required "
                f"(< {required_value}{unit_str})."
            )
        else:
            reason = (
                f"Observed {parameter} ({observed_value}{unit_str}) is not strictly less than "
                f"required ({required_value}{unit_str})."
            )

    else:
        raise ValueError(f"Unsupported numeric operator: '{operator}'.")

    return passed, reason

