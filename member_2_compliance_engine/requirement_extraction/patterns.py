"""Controlled dictionaries and regex patterns for deterministic tender requirement parsing.

Enables pure offline, rule-based extraction without any LLM dependencies.
"""

import re
from typing import Dict, List, Tuple

# Controlled operator keyword mappings
OPERATOR_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:at least|minimum of|minimum|not less than|>=)\b", re.IGNORECASE), ">="),
    (re.compile(r"\b(?:at most|maximum of|maximum|not exceeding|not more than|<=)\b", re.IGNORECASE), "<="),
    (re.compile(r"\b(?:strictly greater than|more than|>)\b", re.IGNORECASE), ">"),
    (re.compile(r"\b(?:strictly less than|fewer than|<)\b", re.IGNORECASE), "<"),
    (re.compile(r"\b(?:exactly|must be|shall be|equal to|equals|==)\b", re.IGNORECASE), "=="),
    (re.compile(r"\b(?:is mandatory|must be submitted|shall be submitted|must be provided|mandatory|required|exists)\b", re.IGNORECASE), "exists"),
    (re.compile(r"\b(?:must contain|must hold|certified under|certified with|with|holds|having|contains)\b", re.IGNORECASE), "contains"),
    (re.compile(r"\b(?:must include all|includes all|both|all of)\b", re.IGNORECASE), "includes_all"),
]

# Controlled category and parameter dictionaries
FINANCIAL_KEYWORDS = [
    "turnover", "annual turnover", "revenue", "net worth", "paid up capital",
    "financial capacity", "working capital", "profit", "solvency"
]

TECHNICAL_KEYWORDS = [
    "ram", "memory", "storage", "disk", "ssd", "hdd", "gpu", "cpu", "processor",
    "cores", "bandwidth", "throughput", "clock speed", "capacity", "interface"
]

COMPLIANCE_DOCUMENTS = [
    "manufacturer authorization form", "maf", "oem authorization",
    "iso 9001", "iso 27001", "iso 14001", "cmmi", "gst registration",
    "gst certificate", "pan card", "power of attorney", "bid security",
    "earnest money deposit", "emd", "affidavit", "solvency certificate",
    "incorporation certificate", "certificate of incorporation"
]

EXPERIENCE_KEYWORDS = [
    "experience", "years of experience", "past experience", "track record",
    "completed projects", "similar works", "prior experience"
]

# Unit patterns
CURRENCY_UNITS = ["lakh", "lakhs", "crore", "crores", "lac", "lacs", "million", "billion", "thousand"]
STORAGE_UNITS = ["pb", "tb", "gb", "mb", "kb", "petabyte", "terabyte", "gigabyte", "megabyte", "kilobyte"]
DURATION_UNITS = ["year", "years", "month", "months", "day", "days"]

# Ambiguous and conditional keywords that should trigger REVIEW
AMBIGUITY_KEYWORDS = [
    re.compile(r"\b(?:or|either\b.*?\bor)\b", re.IGNORECASE),
    re.compile(r"\b(?:alternatively|may be|might be)\b", re.IGNORECASE),
    re.compile(r"\b(?:up to\b.*?\bor)\b", re.IGNORECASE),
    re.compile(r"\b(?:depending on configuration|subject to|as applicable|optional)\b", re.IGNORECASE),
]

