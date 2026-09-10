"""Unit tests for RequirementGenerator and seed families."""

import pytest
from gpkd_dataset_factory.generators.requirement_generator import (
    RequirementFamily,
    RequirementGenerator,
    build_seed_requirement_families,
)


class TestRequirementGenerator:
    """Test seed requirement family construction and catalog completeness."""

    @pytest.fixture
    def generator(self):
        return RequirementGenerator()

    def test_seed_families_count_and_categories(self, generator):
        assert generator.count() >= 50
        cats = generator.list_categories()
        expected = [
            "ambiguous",
            "certification",
            "commercial",
            "delivery",
            "experience",
            "financial",
            "legal",
            "local_content",
            "msme",
            "oem",
            "tax_statutory",
            "technical",
        ]
        for exp in expected:
            assert exp in cats, f"Missing category in catalog: {exp}"

    def test_canonical_dict_conversion(self, generator):
        fam = generator.get_family("FAM_FIN_ANNUAL_TURNOVER_50L")
        assert fam is not None
        d = fam.to_canonical_dict("REQ_000001")
        assert d["requirement_id"] == "REQ_000001"
        assert d["category"] == "financial"
        assert d["field"] == "annual_turnover"
        assert d["operator"] == ">="
        assert d["value"] == 5000000
        assert d["unit"] == "INR"
        assert d["mandatory"] is True
        assert d["is_ambiguous"] is False

    def test_ambiguous_family_target(self, generator):
        amb_fams = generator.filter_by_category("ambiguous")
        assert len(amb_fams) >= 5
        sample = amb_fams[0]
        d = sample.to_canonical_dict("REQ_000099")
        assert d["is_ambiguous"] is True
        assert d["operator"] is None
        assert d["value"] is None
        assert d["ambiguity_reason"] is not None

    def test_filter_by_category(self, generator):
        tech_fams = generator.filter_by_category("technical")
        assert len(tech_fams) >= 15
        for f in tech_fams:
            assert f.category == "technical"
            assert f.field in ("cpu_cores", "gpu_memory", "ram_capacity", "storage_capacity", "network_bandwidth", "operating_temperature")

