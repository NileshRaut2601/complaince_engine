"""Safe normalization layer for tender requirements and evidence metrics.

Handles:
- Indian & International currencies (Lakhs, Crores, INR, USD, Million, Billion)
- Digital storage units (KB, MB, GB, TB, PB) using binary 1024 convention
- Temporal durations (years, months, days)
- Standard date formats (DD/MM/YYYY, YYYY-MM-DD)
- Numeric cleaning (stripping Indian 50,00,000 and Western 5,000,000 separators)

Safety principle:
Never silently guess ambiguous units or currencies. If conversion cannot be
safely determined, raise NormalizationError so the compliance engine can
classify the requirement as REVIEW.
"""

import re
from datetime import date, datetime
from typing import Any, Optional, Tuple, Union
from dateutil import parser as date_parser


class NormalizationError(ValueError):
    """Raised when a value cannot be safely or unambiguously normalized."""
    pass


# Multipliers for Indian & International numbering systems
CURRENCY_MULTIPLIERS = {
    "k": 1_000.0,
    "thousand": 1_000.0,
    "thousands": 1_000.0,
    "lakh": 100_000.0,
    "lakhs": 100_000.0,
    "lac": 100_000.0,
    "lacs": 100_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "mn": 1_000_000.0,
    "crore": 10_000_000.0,
    "crores": 10_000_000.0,
    "cr": 10_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
}

CURRENCY_SYMBOLS = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}

# Binary storage multipliers relative to GB
STORAGE_TO_GB = {
    "b": 1.0 / (1024.0 ** 3),
    "byte": 1.0 / (1024.0 ** 3),
    "bytes": 1.0 / (1024.0 ** 3),
    "kb": 1.0 / (1024.0 ** 2),
    "kilobyte": 1.0 / (1024.0 ** 2),
    "mb": 1.0 / 1024.0,
    "megabyte": 1.0 / 1024.0,
    "gb": 1.0,
    "gigabyte": 1.0,
    "tb": 1024.0,
    "terabyte": 1024.0,
    "pb": 1024.0 * 1024.0,
    "petabyte": 1024.0 * 1024.0,
}

# Duration multipliers relative to Years
DURATION_TO_YEARS = {
    "day": 1.0 / 365.0,
    "days": 1.0 / 365.0,
    "month": 1.0 / 12.0,
    "months": 1.0 / 12.0,
    "yr": 1.0,
    "yrs": 1.0,
    "year": 1.0,
    "years": 1.0,
}


def normalize_number(val: Any, unit: Optional[str] = None) -> float:
    """Normalize raw numeric inputs, handling formatted strings and commas.

    Supports:
    - Standard floats/ints (e.g. 50, 65.5)
    - Comma-separated strings (both Western "5,000,000" and Indian "50,00,000")
    - Unit multipliers if specified (e.g. val=50, unit="lakhs" -> 5,000,000.0)

    Raises:
        NormalizationError: If value cannot be parsed as a valid number.
    """
    if val is None:
        raise NormalizationError("Cannot normalize None to a number.")

    if isinstance(val, (int, float)):
        num = float(val)
    elif isinstance(val, str):
        cleaned = val.strip().replace(",", "")
        # Remove trailing percentage sign if present
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1].strip()
        try:
            num = float(cleaned)
        except ValueError as exc:
            raise NormalizationError(f"Cannot parse '{val}' as a numeric value.") from exc
    else:
        raise NormalizationError(f"Unsupported type {type(val)} for numeric normalization.")

    if unit:
        u = unit.strip().lower()
        if u in CURRENCY_MULTIPLIERS:
            num *= CURRENCY_MULTIPLIERS[u]

    return num


def normalize_currency(
    val: Any,
    unit: Optional[str] = None,
    currency: Optional[str] = None,
    allow_default_currency: bool = True,
) -> Tuple[float, str]:
    """Normalize monetary expressions into standard base float and currency code.

    Examples:
    - "₹50 Lakhs" -> (5000000.0, "INR")
    - "50 lakh" with currency="INR" -> (5000000.0, "INR")
    - "₹50,00,000" -> (5000000.0, "INR")
    - "INR 50,00,000" -> (5000000.0, "INR")
    - "5 Crores" with default currency -> (50000000.0, "INR")
    - "USD 10 Million" -> (10000000.0, "USD")
    - "$10 Million" -> (10000000.0, "USD")

    Safety:
    - Pure numbers like "50" without currency or unit context will NOT be
      assumed as Lakhs. If currency cannot be determined, raises NormalizationError.

    Returns:
        Tuple[float, str]: (normalized_amount, currency_iso_code)
    """
    detected_currency = currency.upper() if currency else None
    multiplier = 1.0

    if isinstance(val, (int, float)):
        if unit:
            u_clean = unit.strip().lower()
            if u_clean in CURRENCY_MULTIPLIERS:
                multiplier = CURRENCY_MULTIPLIERS[u_clean]
        amount = float(val) * multiplier
        curr = detected_currency or ("INR" if allow_default_currency else None)
        if not curr:
            raise NormalizationError(f"Cannot determine currency for numeric value '{val}'.")
        return amount, curr

    if not isinstance(val, str):
        raise NormalizationError(f"Unsupported type {type(val)} for currency normalization.")

    s = val.strip()

    # Detect currency symbols
    for sym, code in CURRENCY_SYMBOLS.items():
        pattern = re.compile(rf"^{re.escape(sym)}\s*|\s*{re.escape(sym)}$|^{re.escape(sym)}", re.IGNORECASE)
        if re.search(pattern, s):
            detected_currency = code
            s = re.sub(pattern, "", s).strip()
            break

    # Look for currency codes prefix/suffix (INR, USD, EUR, GBP, Rs) and unit words
    words = s.split()
    cleaned_words = []
    found_multiplier_in_string = False
    for w in words:
        w_lower = w.lower().strip(".:;,")
        if w_lower in CURRENCY_SYMBOLS:
            detected_currency = CURRENCY_SYMBOLS[w_lower]
        elif w_lower in CURRENCY_MULTIPLIERS:
            multiplier *= CURRENCY_MULTIPLIERS[w_lower]
            found_multiplier_in_string = True
        else:
            cleaned_words.append(w)

    # Apply explicit unit multiplier only if none was extracted from the string
    if not found_multiplier_in_string and unit:
        u_clean = unit.strip().lower()
        if u_clean in CURRENCY_MULTIPLIERS:
            multiplier *= CURRENCY_MULTIPLIERS[u_clean]

    s_remaining = " ".join(cleaned_words).strip()

    # Remove commas and clean
    s_clean = s_remaining.replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", s_clean)
    if not match:
        raise NormalizationError(f"No numeric amount found in monetary expression '{val}'.")

    try:
        base_num = float(match.group(0))
    except ValueError as exc:
        raise NormalizationError(f"Invalid monetary number in '{val}'.") from exc

    final_amount = base_num * multiplier
    final_currency = detected_currency or (currency.upper() if currency else None)

    if not final_currency:
        if allow_default_currency:
            final_currency = "INR"
        else:
            raise NormalizationError(f"No currency detected for '{val}' and default not permitted.")

    return final_amount, final_currency


def normalize_unit(
    val: Any,
    unit: Optional[str] = None,
    target_unit: str = "GB",
) -> Tuple[float, str]:
    """Normalize digital storage capacity into standard units (default: GB).

    Binary convention (1024-based):
    1 TB = 1024 GB
    1 PB = 1024 TB = 1,048,576 GB
    1 MB = 1/1024 GB

    Examples:
    - (2, "TB") -> (2048.0, "GB")
    - "2048 GB" -> (2048.0, "GB")
    - "1 TB" -> (1024.0, "GB")
    - "192 GB" -> (192.0, "GB")

    Returns:
        Tuple[float, str]: (normalized_value, target_unit)
    """
    target = target_unit.lower()
    if target not in STORAGE_TO_GB:
        raise NormalizationError(f"Unsupported target storage unit: '{target_unit}'.")

    val_num: Optional[float] = None
    detected_unit = unit.lower().strip() if unit else None

    if isinstance(val, (int, float)):
        val_num = float(val)
    elif isinstance(val, str):
        s = val.strip()
        # Find number and unit pattern (e.g., "2 TB", "2048GB")
        m = re.search(r"([-+]?\d*\.?\d+)\s*([a-zA-Z]+)?", s)
        if not m:
            raise NormalizationError(f"Cannot parse storage value from '{val}'.")
        val_num = float(m.group(1))
        if m.group(2) and not detected_unit:
            detected_unit = m.group(2).lower().strip()
    else:
        raise NormalizationError(f"Unsupported type {type(val)} for storage normalization.")

    if not detected_unit:
        raise NormalizationError(f"Storage unit missing for value '{val}'.")

    if detected_unit not in STORAGE_TO_GB:
        raise NormalizationError(f"Unrecognized storage unit '{detected_unit}' in '{val}'.")

    # Convert to base GB
    val_in_gb = val_num * STORAGE_TO_GB[detected_unit]
    # Convert from base GB to target
    final_val = val_in_gb / STORAGE_TO_GB[target]

    return final_val, target_unit.upper()


def normalize_duration(val: Any, target_unit: str = "years") -> Tuple[float, str]:
    """Normalize time duration into standard units (default: years).

    Examples:
    - "5 years" -> (5.0, "years")
    - "60 months" -> (5.0, "years")
    - 5 (with target_unit="years") -> (5.0, "years")

    Returns:
        Tuple[float, str]: (normalized_duration, target_unit)
    """
    target = target_unit.lower().strip()
    if target not in DURATION_TO_YEARS:
        raise NormalizationError(f"Unsupported target duration unit: '{target_unit}'.")

    duration_num: Optional[float] = None
    detected_unit: Optional[str] = None

    if isinstance(val, (int, float)):
        duration_num = float(val)
        detected_unit = target
    elif isinstance(val, str):
        s = val.strip()
        m = re.search(r"([-+]?\d*\.?\d+)\s*([a-zA-Z]+)?", s)
        if not m:
            raise NormalizationError(f"Cannot parse duration from '{val}'.")
        duration_num = float(m.group(1))
        if m.group(2):
            detected_unit = m.group(2).lower().strip()
        else:
            detected_unit = target
    else:
        raise NormalizationError(f"Unsupported type {type(val)} for duration normalization.")

    if detected_unit not in DURATION_TO_YEARS:
        raise NormalizationError(f"Unrecognized duration unit '{detected_unit}' in '{val}'.")

    duration_in_years = duration_num * DURATION_TO_YEARS[detected_unit]
    final_duration = duration_in_years / DURATION_TO_YEARS[target]

    return round(final_duration, 4), target


def normalize_date(val: Any) -> date:
    """Safely normalize date representations into datetime.date.

    Supports:
    - DD/MM/YYYY
    - DD-MM-YYYY
    - YYYY-MM-DD
    - Standard textual dates (e.g. '31 March 2024')

    Safety:
    - Standard government tender convention uses day-first (DD/MM/YYYY).
    - If date format is ambiguous or invalid, raises NormalizationError.
    """
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()

    if not isinstance(val, str) or not val.strip():
        raise NormalizationError(f"Invalid date input: '{val}'.")

    s = val.strip()

    # Try explicit ISO format first (YYYY-MM-DD)
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError as exc:
            raise NormalizationError(f"Invalid calendar date in '{s}'.") from exc

    # Try DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if dmy_match:
        day = int(dmy_match.group(1))
        month = int(dmy_match.group(2))
        year = int(dmy_match.group(3))
        try:
            return date(year, month, day)
        except ValueError as exc:
            raise NormalizationError(f"Invalid calendar date in '{s}'.") from exc

    # Fallback to dateutil parser with dayfirst=True
    try:
        dt = date_parser.parse(s, dayfirst=True)
        return dt.date()
    except (ValueError, OverflowError) as exc:
        raise NormalizationError(f"Cannot safely parse date from '{val}'.") from exc


def extract_evidence_numeric_value(
    evidence_text: str,
    parameter: Optional[str] = None,
    unit: Optional[str] = None,
    currency: Optional[str] = None,
) -> Tuple[float, Optional[str]]:
    """Extract and normalize a relevant numeric or monetary metric from evidence text.

    Finds expressions matching currency (e.g., '₹65 Lakhs', '42 Lakhs') or
    units (e.g., '2 TB', '64 GB', '5 years').
    """
    text = evidence_text.strip()

    # 1. Currency extraction
    is_currency = (
        (currency is not None)
        or (unit and unit.lower() in CURRENCY_MULTIPLIERS)
        or any(sym in text for sym in ["₹", "Rs", "rs", "INR", "USD", "$", "lakh", "crore"])
    )
    if is_currency:
        # First priority: expressions with explicit currency symbol or multiplier word
        pattern_explicit = re.compile(
            r"(?:₹|rs\.?|inr|\$|usd)\s*(\d+(?:[.,]\d+)?)\s*(lakhs?|crores?|lacs?|million|billion|thousand|k)?|"
            r"(\d+(?:[.,]\d+)?)\s*(lakhs?|crores?|lacs?|million|billion|thousand|k)\b",
            re.IGNORECASE,
        )
        for m in pattern_explicit.finditer(text):
            start_idx = m.start()
            preceding = text[max(0, start_idx - 4):start_idx].lower()
            if "fy" in preceding:
                continue
            full_match = m.group(0).strip()
            try:
                norm_amt, curr = normalize_currency(
                    full_match,
                    unit=unit,
                    currency=currency or "INR",
                )
                return norm_amt, curr
            except NormalizationError:
                continue

        # Second priority: bare numbers, ignoring 4-digit years (1990-2099) and FY prefixes
        pattern_general = re.compile(r"(\d+(?:[.,]\d+)?)")
        for m in pattern_general.finditer(text):
            start_idx = m.start()
            preceding = text[max(0, start_idx - 4):start_idx].lower()
            if "fy" in preceding or "year" in preceding:
                continue
            num_str = m.group(1).replace(",", "")
            # Skip likely 4-digit year numbers
            if len(num_str) == 4 and num_str.isdigit() and 1990 <= int(num_str) <= 2099:
                continue
            try:
                norm_amt, curr = normalize_currency(
                    num_str,
                    unit=unit,
                    currency=currency or "INR",
                )
                return norm_amt, curr
            except NormalizationError:
                continue

    # 2. Storage extraction
    is_storage = (
        (unit and unit.lower() in STORAGE_TO_GB)
        or any(u in text.lower() for u in ["tb", "gb", "mb", "kb", "pb"])
    )
    if is_storage:
        pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(tb|gb|mb|kb|pb|terabyte|gigabyte|megabyte)s?",
            re.IGNORECASE,
        )
        matches = list(pattern.finditer(text))
        if matches:
            # If multiple storage values in text, return the first or handle in conflict
            m = matches[0]
            val = float(m.group(1))
            u = m.group(2)
            # Normalize to standardized comparison baseline GB
            norm_val, target_u = normalize_unit(val, unit=u, target_unit="GB")
            return norm_val, target_u

    # 3. Duration extraction
    is_duration = (
        (unit and unit.lower() in DURATION_TO_YEARS)
        or any(u in text.lower() for u in ["year", "years", "month", "months", "day", "days"])
    )
    if is_duration:
        pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(years?|months?|days?|yrs?)",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            val = float(m.group(1))
            u = m.group(2)
            norm_val, target_u = normalize_duration(f"{val} {u}", target_unit=unit or "years")
            return norm_val, target_u

    # 4. Plain number fallback
    pattern = re.compile(r"[-+]?\d+(?:,\d+)*(?:\.\d+)?")
    m = pattern.search(text)
    if m:
        val = normalize_number(m.group(0), unit=unit)
        return val, unit

    raise NormalizationError(f"No quantifiable metric found matching parameter '{parameter}' in: '{evidence_text}'.")
