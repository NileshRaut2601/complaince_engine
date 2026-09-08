"""Deterministic date and duration comparison rules."""

from datetime import date
from typing import Tuple, Union

from member_2_compliance_engine.normalization.normalizer import (
    NormalizationError,
    normalize_date,
    normalize_duration,
)


def evaluate_date_rule(
    operator: str,
    required_date_val: Union[date, str],
    observed_date_val: Union[date, str],
) -> Tuple[bool, str]:
    """Deterministically evaluate calendar date comparison.

    E.g. Incorporation date <= 01/01/2020.
    """
    op = operator.strip().lower()

    try:
        req_d = normalize_date(required_date_val)
        obs_d = normalize_date(observed_date_val)
    except NormalizationError as exc:
        raise ValueError(f"Date normalization failed: {exc}") from exc

    if op in ["==", "=", "eq"]:
        passed = (obs_d == req_d)
        reason = f"Observed date ({obs_d}) {'matches' if passed else 'does not match'} required date ({req_d})."
    elif op in ["<=", "lte", "on_or_before"]:
        passed = (obs_d <= req_d)
        reason = (
            f"Observed date ({obs_d}) is {'on or before' if passed else 'after'} "
            f"required date ({req_d})."
        )
    elif op in [">=", "gte", "on_or_after"]:
        passed = (obs_d >= req_d)
        reason = (
            f"Observed date ({obs_d}) is {'on or after' if passed else 'before'} "
            f"required date ({req_d})."
        )
    elif op in ["<", "lt", "before"]:
        passed = (obs_d < req_d)
        reason = (
            f"Observed date ({obs_d}) is {'strictly before' if passed else 'not before'} "
            f"required date ({req_d})."
        )
    elif op in [">", "gt", "after"]:
        passed = (obs_d > req_d)
        reason = (
            f"Observed date ({obs_d}) is {'strictly after' if passed else 'not after'} "
            f"required date ({req_d})."
        )
    else:
        raise ValueError(f"Unsupported date operator: '{operator}'.")

    return passed, reason


def evaluate_duration_rule(
    operator: str,
    required_duration_val: Union[float, str],
    observed_duration_val: Union[float, str],
    unit: str = "years",
) -> Tuple[bool, str]:
    """Deterministically evaluate duration/experience comparison.

    E.g. Relevant experience >= 5 years.
    """
    op = operator.strip().lower()

    try:
        req_val, req_u = normalize_duration(required_duration_val, target_unit=unit)
        obs_val, obs_u = normalize_duration(observed_duration_val, target_unit=unit)
    except NormalizationError as exc:
        raise ValueError(f"Duration normalization failed: {exc}") from exc

    tol = 1e-4

    if op in [">=", "gte"]:
        passed = (obs_val - req_val) >= -tol
        reason = (
            f"Observed duration ({obs_val} {obs_u}) satisfies minimum requirement "
            f"(>= {req_val} {req_u})."
        )
    elif op in ["<=", "lte"]:
        passed = (obs_val - req_val) <= tol
        reason = (
            f"Observed duration ({obs_val} {obs_u}) satisfies maximum requirement "
            f"(<= {req_val} {req_u})."
        )
    elif op in ["==", "=", "eq"]:
        passed = abs(obs_val - req_val) < tol
        reason = (
            f"Observed duration ({obs_val} {obs_u}) {'matches' if passed else 'does not match'} "
            f"required ({req_val} {req_u})."
        )
    elif op in [">", "gt"]:
        passed = (obs_val - req_val) > tol
        reason = (
            f"Observed duration ({obs_val} {obs_u}) is greater than required ({req_val} {req_u})."
        )
    elif op in ["<", "lt"]:
        passed = (obs_val - req_val) < -tol
        reason = (
            f"Observed duration ({obs_val} {obs_u}) is less than required ({req_val} {req_u})."
        )
    else:
        raise ValueError(f"Unsupported duration operator: '{operator}'.")

    return passed, reason

