"""Unit tests for Validation engine and anti-leakage checks."""

import pytest
from gpkd_dataset_factory.validators.dataset_validator import (
    validate_dataset_records,
    verify_zero_leakage,
)
from gpkd_dataset_factory.validators.duplicate_detector import check_duplicates
from gpkd_dataset_factory.validators.requirement_validator import (
    ValidationError,
    validate_canonical_target,
    validate_training_example,
)


class TestValidators:
    """Test schema validation, duplicate detection, and anti-leakage gates."""

    def test_valid_canonical_target(self):
        valid = {
            "requirement_id": "REQ_000001",
            "category": "financial",
            "field": "annual_turnover",
            "operator": ">=",
            "value": 50000000,
            "unit": "INR",
            "period": None,
            "mandatory": True,
            "is_ambiguous": False,
            "ambiguity_reason": None,
        }
        # Should not raise
        validate_canonical_target(valid)

    def test_invalid_operator_rejected(self):
        invalid = {
            "requirement_id": "REQ_000001",
            "category": "financial",
            "field": "annual_turnover",
            "operator": "INVALID_OP",
            "value": 50000000,
            "unit": "INR",
            "period": None,
            "mandatory": True,
            "is_ambiguous": False,
            "ambiguity_reason": None,
        }
        with pytest.raises(ValidationError, match="Invalid operator"):
            validate_canonical_target(invalid)

    def test_negative_numeric_value_rejected(self):
        invalid = {
            "requirement_id": "REQ_000001",
            "category": "financial",
            "field": "annual_turnover",
            "operator": ">=",
            "value": -5000,
            "unit": "INR",
            "period": None,
            "mandatory": True,
            "is_ambiguous": False,
            "ambiguity_reason": None,
        }
        with pytest.raises(ValidationError, match="Impossible negative value"):
            validate_canonical_target(invalid)

    def test_ambiguous_target_validation(self):
        amb_valid = {
            "requirement_id": "REQ_000042",
            "category": "ambiguous",
            "field": "RAM",
            "operator": None,
            "value": None,
            "unit": None,
            "period": None,
            "mandatory": True,
            "is_ambiguous": True,
            "ambiguity_reason": "Conditional memory configuration",
        }
        validate_canonical_target(amb_valid)

        amb_invalid = dict(amb_valid, operator=">=")
        with pytest.raises(ValidationError, match="operator=null"):
            validate_canonical_target(amb_invalid)

    def test_training_example_validation(self):
        ex = {
            "id": "GPKD_000001",
            "input": "The bidder must have an annual turnover of at least ₹50 Lakhs.",
            "target": {
                "requirement_id": "REQ_000001",
                "category": "financial",
                "field": "annual_turnover",
                "operator": ">=",
                "value": 5000000,
                "unit": "INR",
                "period": None,
                "mandatory": True,
                "is_ambiguous": False,
                "ambiguity_reason": None,
            },
            "metadata": {
                "source": "synthetic",
                "family_id": "FAM_FIN_50L",
                "category": "financial",
                "difficulty": "easy",
                "generation_method": "direct",
                "noise_type": None,
                "generator_version": "1.0",
            },
        }
        validate_training_example(ex)

    def test_duplicate_detector(self):
        examples = [
            {"id": "GPKD_000001", "input": "Text A", "target": {"value": 1, "operator": "=="}},
            {"id": "GPKD_000002", "input": "Text A", "target": {"value": 2, "operator": "=="}},  # Semantic collision!
            {"id": "GPKD_000001", "input": "Text B", "target": {"value": 3, "operator": "=="}},  # ID collision!
        ]
        rep = check_duplicates(examples)
        assert rep.duplicate_id_count == 1
        assert rep.duplicate_input_count == 1
        assert rep.semantic_collision_count == 1

    def test_anti_leakage_detector_catches_leak(self):
        train = [
            {"id": "GPKD_001", "input": "Turnover >= 5 Cr", "metadata": {"family_id": "FAM_LEAK_01"}}
        ]
        val = [
            {"id": "GPKD_002", "input": "Turnover >= 10 Cr", "metadata": {"family_id": "FAM_SAFE_01"}}
        ]
        test = [
            {"id": "GPKD_003", "input": "Turnover >= 5 Cr", "metadata": {"family_id": "FAM_LEAK_01"}}  # Leaked family!
        ]
        with pytest.raises(ValidationError, match="DATA LEAKAGE DETECTED"):
            verify_zero_leakage(train, val, test)

