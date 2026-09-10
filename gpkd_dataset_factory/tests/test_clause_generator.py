"""Unit tests for ClauseGenerator and linguistic synthesis."""

import pytest
from gpkd_dataset_factory.generators.clause_generator import ClauseGenerator, format_inr_amount
from gpkd_dataset_factory.generators.requirement_generator import RequirementGenerator


class TestClauseGenerator:
    """Test natural language clause synthesis across difficulty levels."""

    @pytest.fixture
    def req_gen(self):
        return RequirementGenerator()

    @pytest.fixture
    def clause_gen(self):
        return ClauseGenerator(seed=123)

    def test_format_inr_amount(self):
        assert "50 Lakhs" in format_inr_amount(5000000, "symbol_lakh")
        assert "5 Crore" in format_inr_amount(50000000, "symbol_crore")
        assert "INR 50,000,000" in format_inr_amount(50000000, "full_numeric")

    def test_generate_clauses_difficulty_distribution(self, req_gen, clause_gen):
        fam = req_gen.get_family("FAM_FIN_ANNUAL_TURNOVER_5Cr")
        clauses = clause_gen.generate_clauses_for_family(fam, count=10)
        assert len(clauses) == 10

        diffs = [c["difficulty"] for c in clauses]
        assert "easy" in diffs
        assert "medium" in diffs
        assert "hard" in diffs

        for c in clauses:
            assert len(c["text"]) > 15
            assert "turnover" in c["text"].lower() or "crore" in c["text"].lower()

    def test_generate_table_format_clauses(self, req_gen, clause_gen):
        fam = req_gen.get_family("FAM_TECH_RAM_192GB")
        # Direct call to table maker
        tbl_text = clause_gen._make_table_format(fam)
        assert "Ram" in tbl_text or "Parameter" in tbl_text or "Specification" in tbl_text
        assert "192 GB" in tbl_text

    def test_generate_ambiguous_clauses(self, req_gen, clause_gen):
        fam = req_gen.get_family("FAM_AMB_RAM_DISJUNCTIVE")
        clauses = clause_gen.generate_clauses_for_family(fam, count=5)
        assert len(clauses) == 5
        for c in clauses:
            assert c["method"] == "ambiguous_disjunction"
            assert "or" in c["text"].lower() or "may" in c["text"].lower()

