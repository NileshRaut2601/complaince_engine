"""Unit tests for normalization layer."""

from datetime import date
import pytest

from member_2_compliance_engine.normalization.normalizer import (
    NormalizationError,
    extract_evidence_numeric_value,
    normalize_currency,
    normalize_date,
    normalize_duration,
    normalize_number,
    normalize_unit,
)


class TestNumberNormalization:
    def test_clean_numbers(self):
        assert normalize_number(50) == 50.0
        assert normalize_number("50.5") == 50.5
        assert normalize_number("5,000,000") == 5000000.0
        assert normalize_number("50,00,000") == 5000000.0
        assert normalize_number("99.9%") == 99.9

    def test_invalid_number_raises_error(self):
        with pytest.raises(NormalizationError):
            normalize_number("not_a_number")

        with pytest.raises(NormalizationError):
            normalize_number(None)


class TestCurrencyNormalization:
    def test_inr_formats(self):
        # ₹50 Lakhs = 5,000,000
        val, curr = normalize_currency("₹50 Lakhs")
        assert val == 5_000_000.0
        assert curr == "INR"

        # 50 lakh
        val, curr = normalize_currency("50 lakh", currency="INR")
        assert val == 5_000_000.0
        assert curr == "INR"

        # 50 lakhs
        val, curr = normalize_currency("50 lakhs", currency="INR")
        assert val == 5_000_000.0
        assert curr == "INR"

        # ₹50,00,000
        val, curr = normalize_currency("₹50,00,000")
        assert val == 5_000_000.0
        assert curr == "INR"

        # INR 50,00,000
        val, curr = normalize_currency("INR 50,00,000")
        assert val == 5_000_000.0
        assert curr == "INR"

        # 5 Crores = 50,000,000
        val, curr = normalize_currency("5 Crores")
        assert val == 50_000_000.0
        assert curr == "INR"

    def test_usd_formats(self):
        val, curr = normalize_currency("USD 10 Million")
        assert val == 10_000_000.0
        assert curr == "USD"

        val, curr = normalize_currency("$10 Million")
        assert val == 10_000_000.0
        assert curr == "USD"

        val, curr = normalize_currency("$10,000,000")
        assert val == 10_000_000.0
        assert curr == "USD"

    def test_unsafe_currency_conversion(self):
        # Ambiguous numbers without currency context should fail if default is disallowed
        with pytest.raises(NormalizationError):
            normalize_currency(50, allow_default_currency=False)

        with pytest.raises(NormalizationError):
            normalize_currency("no monetary value here")


class TestStorageNormalization:
    def test_binary_storage_conventions(self):
        # 1 TB = 1024 GB
        val, unit = normalize_unit(1, "TB", target_unit="GB")
        assert val == 1024.0
        assert unit == "GB"

        # 2 TB = 2048 GB
        val, unit = normalize_unit(2, "TB", target_unit="GB")
        assert val == 2048.0
        assert unit == "GB"

        # 2048 GB == 2048 GB
        val, unit = normalize_unit(2048, "GB", target_unit="GB")
        assert val == 2048.0
        assert unit == "GB"

        # String parsing
        val, unit = normalize_unit("2 TB", target_unit="GB")
        assert val == 2048.0

        val, unit = normalize_unit("512 MB", target_unit="GB")
        assert val == 0.5

    def test_invalid_storage_unit(self):
        with pytest.raises(NormalizationError):
            normalize_unit(10, "FLOP")


class TestDurationNormalization:
    def test_duration_to_years(self):
        val, u = normalize_duration("5 years")
        assert val == 5.0
        assert u == "years"

        val, u = normalize_duration("60 months")
        assert val == 5.0
        assert u == "years"

        val, u = normalize_duration("365 days")
        assert round(val, 1) == 1.0


class TestDateNormalization:
    def test_standard_formats(self):
        # DD/MM/YYYY
        d1 = normalize_date("15/08/2024")
        assert d1 == date(2024, 8, 15)

        # DD-MM-YYYY
        d2 = normalize_date("26-01-2023")
        assert d2 == date(2023, 1, 26)

        # YYYY-MM-DD
        d3 = normalize_date("2024-12-31")
        assert d3 == date(2024, 12, 31)

    def test_invalid_date(self):
        with pytest.raises(NormalizationError):
            normalize_date("invalid-date-string")


class TestEvidenceExtraction:
    def test_extract_turnover(self):
        text = "The company's reported annual turnover is ₹65 Lakhs for the financial year."
        amt, curr = extract_evidence_numeric_value(text, parameter="turnover", unit="lakhs", currency="INR")
        assert amt == 6_500_000.0
        assert curr == "INR"

    def test_extract_storage(self):
        text = "AI Workload Node RAM is certified at 2 TB with ECC support."
        val, unit = extract_evidence_numeric_value(text, parameter="RAM", unit="GB")
        assert val == 2048.0
        assert unit == "GB"

