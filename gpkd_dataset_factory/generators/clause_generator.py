"""Natural Language Tender Clause Synthesizer.

Generates syntactically diverse, realistic procurement clauses across
Easy, Medium, Hard difficulty tiers, table-like formats, negations,
and ambiguous non-committal clauses.
"""

from __future__ import annotations

import random
from typing import Any, Optional
from gpkd_dataset_factory.generators.requirement_generator import RequirementFamily


def format_inr_amount(amount: int | float, format_style: str = "lakh_crore") -> str:
    """Format an INR amount into varied natural linguistic expressions."""
    if amount >= 10000000:
        cr = amount / 10000000
        cr_str = f"{cr:g}"
        if format_style == "symbol_crore":
            return f"₹{cr_str} Crore"
        elif format_style == "inr_crore":
            return f"INR {cr_str} Cr"
        elif format_style == "word_crore":
            return f"Rs. {cr_str} Crores"
        elif format_style == "full_numeric":
            return f"INR {amount:,}"
        return f"₹{cr_str} Cr"
    elif amount >= 100000:
        lakh = amount / 100000
        lakh_str = f"{lakh:g}"
        if format_style == "symbol_lakh":
            return f"₹{lakh_str} Lakhs"
        elif format_style == "inr_lakh":
            return f"INR {lakh_str} Lakhs"
        elif format_style == "word_lakh":
            return f"Rs. {lakh_str} Lacs"
        elif format_style == "full_numeric":
            return f"INR {amount:,}"
        return f"₹{lakh_str} Lakhs"
    else:
        return f"₹{amount:,}"


class ClauseGenerator:
    """Synthesizes natural language clauses from canonical requirement families."""

    def __init__(self, seed: Optional[int] = 42) -> None:
        self.rng = random.Random(seed)

    def generate_clauses_for_family(
        self,
        family: RequirementFamily,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate a specified number of diverse clauses for a requirement family.

        Returns:
            List of dicts: {"text": str, "difficulty": str, "method": str, "is_table": bool}
        """
        results: list[dict[str, Any]] = []

        if family.is_ambiguous:
            return self._generate_ambiguous_clauses(family, count)

        # Distribute count across easy, medium, hard
        num_easy = max(1, int(count * 0.35))
        num_hard = max(1, int(count * 0.20))
        num_med = max(1, count - num_easy - num_hard)

        for _ in range(num_easy):
            results.append(self._generate_easy(family))
        for _ in range(num_med):
            results.append(self._generate_medium(family))
        for _ in range(num_hard):
            results.append(self._generate_hard(family))

        # Ensure exact count
        self.rng.shuffle(results)
        return results[:count]

    def _generate_easy(self, family: RequirementFamily) -> dict[str, Any]:
        """Easy: Short, direct, declarative or imperative syntax."""
        field_name = family.field or "Specification"
        op = family.operator
        val = family.value
        unit = family.unit

        # Check for table-like presentation (10% of easy)
        if self.rng.random() < 0.25:
            text = self._make_table_format(family)
            return {"text": text, "difficulty": "easy", "method": "tabular", "is_table": True}

        # 1. Financial
        if family.category == "financial":
            if field_name == "profitability":
                text = "Bidder must have reported a positive net profit over the last 3 financial years."
            elif "net_worth" in field_name:
                amt_str = format_inr_amount(val, "symbol_lakh")
                text = f"Bidder must have a minimum net worth of {amt_str}."
            elif "solvency" in field_name:
                amt_str = format_inr_amount(val, "symbol_lakh")
                text = f"Bank solvency certificate of at least {amt_str} is required."
            elif "average" in field_name:
                amt_str = format_inr_amount(val, "symbol_crore")
                text = f"Average annual turnover of at least {amt_str} over the preceding 3 financial years is required."
            else:
                amt_str = format_inr_amount(val, self.rng.choice(["symbol_crore", "inr_crore", "symbol_lakh"]))
                templates = [
                    f"Bidder must have annual turnover of at least {amt_str}.",
                    f"Minimum turnover requirement is {amt_str}.",
                    f"The vendor's annual turnover shall be >= {amt_str}.",
                    f"Annual turnover must not be less than {amt_str}.",
                ]
                text = self.rng.choice(templates)

        # 2. Tax & Statutory
        elif family.category == "tax_statutory":
            if field_name == "pan":
                text = self.rng.choice([
                    "Valid PAN card submission is mandatory.",
                    "The bidder must possess a valid PAN.",
                    "Copy of PAN card is required.",
                ])
            elif field_name == "gstin":
                text = self.rng.choice([
                    "Active GSTIN registration is compulsory.",
                    "The vendor must furnish valid GST certificate.",
                    "Submission of GSTIN registration is mandatory.",
                ])
            elif field_name == "gst_status":
                text = "GST registration status of the bidder must strictly be ACTIVE."
            else:
                text = f"Submission of ITR for last {val} years is mandatory."

        # 3. MSME
        elif family.category == "msme":
            if field_name == "udyam":
                text = self.rng.choice([
                    "Valid Udyam Registration Certificate is required for MSME exemption.",
                    "Bidders seeking MSME benefit must submit Udyam certificate.",
                ])
            elif field_name == "msme_classification":
                text = f"Bidder must belong to {val} enterprise category under MSME."
            else:
                text = "Bidder must possess valid NSIC registration certificate."

        # 4. Experience
        elif family.category == "experience":
            if "years" in field_name:
                text = self.rng.choice([
                    f"Bidder must have at least {val} years of experience.",
                    f"Minimum {val} years experience in the relevant field is required.",
                ])
            elif "government" in field_name:
                text = f"Bidder must have completed at least {val} government projects."
            else:
                text = f"The vendor must have completed at least {val} similar projects."

        # 5. Technical
        elif family.category == "technical":
            templates = [
                f"{field_name.replace('_', ' ').title()} must be at least {val} {unit or ''}.",
                f"Required {field_name.replace('_', ' ').title()}: minimum {val} {unit or ''}.",
                f"Minimum {field_name.replace('_', ' ')} shall be >= {val} {unit or ''}.",
            ]
            text = self.rng.choice(templates).strip()

        # 6. Certification
        elif family.category == "certification":
            if field_name == "bis_certification":
                text = "Bureau of Indian Standards (BIS) certification is mandatory."
            elif field_name == "stqc_certificate":
                text = "STQC test certificate is mandatory for the offered equipment."
            elif op == "includes_all":
                text = f"Bidder must possess both {val[0]} and {val[1]} certifications."
            else:
                text = f"The bidder must hold valid {val} certification."

        # 7. OEM
        elif family.category == "oem":
            if field_name == "authorized_distributor":
                text = self.rng.choice([
                    "Bidder must be an authorized distributor of the OEM.",
                    "The vendor shall be an official tier-1 distributor for the manufacturer.",
                ])
            elif field_name == "authorization_validity_period":
                text = f"OEM authorization letter must be valid for at least {val} months."
            else:
                text = self.rng.choice([
                    "Manufacturer Authorization Form (MAF) is mandatory.",
                    "Bidder must submit tender-specific OEM authorization.",
                ])

        # 8. Local Content
        elif family.category == "local_content":
            if field_name == "make_in_india_class":
                text = f"The bidder must qualify as a {val}."
            else:
                text = f"Minimum local content requirement under Make in India is {val}%."

        # 9. Legal
        elif family.category == "legal":
            if field_name == "is_debarred":
                text = self.rng.choice([
                    "The participating bidder must not be debarred by any government authority.",
                    "Bidder shall not be under active debarment or suspension.",
                ])
            elif field_name == "non_blacklisting_declaration":
                text = self.rng.choice([
                    "Submission of a notarized non-blacklisting affidavit is mandatory.",
                    "Vendor must submit a sworn non-blacklisting declaration.",
                ])
            else:
                text = "Declaration of clean litigation history must be submitted."

        # 10. Commercial
        elif family.category == "commercial":
            if field_name == "bid_security_declaration":
                text = "MSME bidders must submit a valid Bid Security Declaration in lieu of EMD."
            elif field_name == "performance_bank_guarantee_percentage":
                text = f"Performance Bank Guarantee (PBG) of {val}% of contract value is required."
            else:
                amt_str = format_inr_amount(val)
                text = f"EMD amount of {amt_str} must be submitted with the bid."

        # 11. Delivery
        elif family.category == "delivery":
            if field_name == "installation_period":
                text = f"On-site installation must be completed within {val} days."
            elif field_name == "delivery_period":
                text = f"Consignment delivery must be completed within {val} days."
            else:
                text = f"Comprehensive on-site warranty of at least {val} years is mandatory."

        else:
            text = f"{field_name.replace('_', ' ').title()} requirement: {op} {val} {unit or ''}."

        return {"text": text, "difficulty": "easy", "method": "direct_declarative", "is_table": False}

    def _generate_medium(self, family: RequirementFamily) -> dict[str, Any]:
        """Medium: Formal procurement clauses, modal verbs, temporal scopes, and conditions."""
        field_name = family.field or "Specification"
        val = family.value
        unit = family.unit
        period_str = f" over the {family.period}" if family.period else ""

        # 1. Financial
        if family.category == "financial":
            if field_name == "profitability":
                text = "The vendor shall have reported operating profit in each of the last 3 financial years as evidenced by audited statements."
            elif "net_worth" in field_name:
                amt_str = format_inr_amount(val, "word_crore")
                templates = [
                    f"The net worth of the bidder as on the last day of previous financial year shall be not less than {amt_str}.",
                    f"Bidders are required to demonstrate audited positive net worth exceeding {amt_str}.",
                ]
                text = self.rng.choice(templates)
            elif "solvency" in field_name:
                amt_str = format_inr_amount(val, "word_crore")
                text = f"The vendor shall furnish a bank solvency certificate for an amount not less than {amt_str} issued by a scheduled commercial bank."
            elif "average" in field_name:
                amt_str = format_inr_amount(val, "word_crore")
                text = f"The participating vendor shall demonstrate an average annual turnover of not less than {amt_str} over the preceding 3 financial years."
            else:
                amt_str = format_inr_amount(val, self.rng.choice(["word_crore", "inr_lakh", "symbol_crore"]))
                templates = [
                    f"The participating vendor shall demonstrate an annual turnover of not less than {amt_str}.",
                    f"Bidders are required to show audited annual turnover not below {amt_str} certified by a Chartered Accountant.",
                    f"The firm should have reported an annual turnover exceeding or equal to {amt_str} in their audited balance sheets.",
                    f"Turnover criteria: The bidder shall have achieved a financial turnover of at least {amt_str}.",
                ]
                text = self.rng.choice(templates)

        # 2. Tax & Statutory
        elif family.category == "tax_statutory":
            if field_name == "pan":
                text = "The bidder must be in possession of a valid Permanent Account Number (PAN) issued by the Income Tax Department."
            elif field_name == "gstin":
                text = "The vendor is obligated to furnish verifiable proof of active Goods and Services Tax (GSTIN) registration."
            elif field_name == "gst_status":
                text = "The Goods and Services Tax registration of the participating vendor shall strictly remain in ACTIVE status."
            else:
                text = f"The tenderer must furnish audited Income Tax Returns along with computation for the immediately preceding {val} assessment years."

        # 3. MSME
        elif family.category == "msme":
            if field_name == "udyam":
                text = "Micro and Small Enterprises claiming fee or EMD exemption shall upload a valid Udyam Registration Certificate."
            elif field_name == "msme_classification":
                text = f"To avail MSME procurement benefits, the bidder shall be officially classified as {val} in Udyam portal."
            else:
                text = "The vendor shall produce a valid Single Point Registration Scheme certificate issued by NSIC."

        # 4. Experience
        elif family.category == "experience":
            period_scope = f" {family.period}" if family.period else ""
            if "years" in field_name:
                templates = [
                    f"Vendor must demonstrate a proven track record spanning at least {val} years in the relevant procurement domain.",
                    f"The firm shall have been in active commercial operations for a minimum duration of {val} years.",
                ]
                text = self.rng.choice(templates)
            elif "government" in field_name:
                text = f"The bidder shall have successfully executed not less than {val} contracts for Central or State Government entities{period_scope}."
            else:
                text = f"The bidder shall have successfully executed not less than {val} contracts of similar nature{period_scope}."

        # 5. Technical
        elif family.category == "technical":
            templates = [
                f"The proposed computing infrastructure shall support {field_name.replace('_', ' ')} of no less than {val} {unit or ''}.",
                f"Bidders must ensure the offered hardware provides {field_name.replace('_', ' ')} of at least {val} {unit or ''}.",
                f"System specification mandates that {field_name.replace('_', ' ')} shall not be less than {val} {unit or ''}.",
            ]
            text = self.rng.choice(templates)

        # 6. Certification
        elif family.category == "certification":
            if field_name == "bis_certification":
                text = "The supplied equipment must carry mandatory Bureau of Indian Standards (BIS) registration or ISI mark certification."
            elif field_name == "stqc_certificate":
                text = "The vendor shall furnish a valid STQC evaluation certificate for compliance with national standards."
            elif family.operator == "includes_all":
                text = f"Participating entities shall be certified under both {val[0]} and {val[1]} quality frameworks at the time of bid submission."
            else:
                text = f"The bidder must be actively certified under {val} and submit valid accreditation certificates issued by an accredited registrar."

        # 7. OEM
        elif family.category == "oem":
            if field_name == "authorized_distributor":
                text = "The participating entity shall furnish verifiable documentary proof of being an authorized distributor appointed by the original manufacturer."
            elif field_name == "authorization_validity_period":
                text = f"The manufacturer authorization submitted by the vendor shall possess a remaining validity of not less than {val} months from bid closing."
            else:
                text = "In case the bidder is not the OEM, they must submit a valid tender-specific Manufacturer Authorization Form (MAF) signed by the authorized OEM signatory."

        # 8. Local Content
        elif family.category == "local_content":
            if field_name == "make_in_india_class":
                text = f"Bidders claiming preference under Make in India must submit certificate demonstrating classification as {val}."
            else:
                text = f"Under the Public Procurement (Preference to Make in India) Order, the minimum local content offered by the bidder shall be at least {val}%."

        # 9. Legal
        elif family.category == "legal":
            if field_name == "is_debarred":
                text = "The vendor shall affirm that they have not been placed on any debarment list by GeM, NIC, or any Central/State procurement agency."
            elif field_name == "non_blacklisting_declaration":
                text = "The vendor shall furnish a notarized declaration on non-judicial stamp paper affirming non-blacklisting by any public authority."
            else:
                text = "A sworn affidavit declaring that the firm is free from material ongoing litigation shall accompany the pre-qualification dossier."

        # 10. Commercial
        elif family.category == "commercial":
            if field_name == "bid_security_declaration":
                text = "Bidders claiming exemption from Earnest Money Deposit must submit a signed Bid Security Declaration as per GeM GTC."
            elif field_name == "performance_bank_guarantee_percentage":
                text = f"The successful bidder shall furnish a Performance Bank Guarantee (PBG) equivalent to {val}% of the total awarded contract value."
            else:
                amt_str = format_inr_amount(val)
                text = f"Bid security / EMD of {amt_str} must be remitted via BG or electronic transfer prior to bid opening."

        # 11. Delivery
        elif family.category == "delivery":
            if field_name == "installation_period":
                text = f"Site installation, deployment, and operational acceptance testing must be completed within {val} days from physical delivery."
            elif field_name == "delivery_period":
                text = f"Entire supply and delivery of equipment shall be accomplished within a period not exceeding {val} days from the contract date."
            else:
                text = f"The offered equipment shall carry a comprehensive on-site OEM warranty for a minimum duration of {val} years with 24x7 support."

        else:
            text = f"The bidder shall fulfill the condition that {field_name.replace('_', ' ')} satisfies the threshold of {val} {unit or ''}{period_str}."

        return {"text": text, "difficulty": "medium", "method": "procurement_formal", "is_table": False}

    def _generate_hard(self, family: RequirementFamily) -> dict[str, Any]:
        """Hard: Bureaucratic legalistic syntax, complex syntactic inversions, double negations."""
        field_name = family.field or "Specification"
        val = family.value
        unit = family.unit
        period_str = f" across the immediately {family.period}" if family.period else ""

        # 1. Financial
        if family.category == "financial":
            if field_name == "profitability":
                text = "Bidders having incurred operational losses in any of the preceding three financial years shall be summarily disqualified from technical evaluation."
            elif "net_worth" in field_name:
                amt_str = format_inr_amount(val, "inr_crore")
                templates = [
                    f"The net worth of the participating bidder as on the close of the previous audited financial year must strictly not be less than {amt_str}, certified with valid UDIN.",
                    f"Bidders failing to demonstrate a positive tangible net worth exceeding or equal to {amt_str} based on statutory audited balance sheets shall be deemed non-responsive.",
                ]
                text = self.rng.choice(templates)
            elif "solvency" in field_name:
                amt_str = format_inr_amount(val, "inr_crore")
                text = f"The bidder must procure and submit a Bank Solvency Certificate for an aggregate sum of not less than {amt_str} from a Scheduled Commercial Bank, dated within six months prior to tender closing."
            elif "average" in field_name:
                amt_str = format_inr_amount(val, self.rng.choice(["full_numeric", "word_crore", "inr_crore"]))
                text = f"Tenderers whose average annual audited turnover falls below {amt_str} across the immediately preceding 3 financial years shall not satisfy the financial pre-qualification threshold."
            else:
                amt_str = format_inr_amount(val, self.rng.choice(["full_numeric", "word_crore", "inr_crore"]))
                templates = [
                    f"Firms participating in the bidding process must have maintained an audited turnover of not below {amt_str}, failing which their technical proposal shall be summarily rejected without further clarification.",
                    f"Notwithstanding any relaxation under general procurement guidelines, tenderers whose annual turnover falls below {amt_str} shall not satisfy the pre-qualification criteria.",
                    f"It is an indispensable condition of eligibility that the reported financial turnover of the applicant firm shall be equal to or exceed {amt_str}, duly supported by statutory auditor certificates with valid UDIN.",
                ]
                text = self.rng.choice(templates)

        # 2. Tax & Statutory
        elif family.category == "tax_statutory":
            if field_name == "pan":
                text = "Submission of a self-attested, legible copy of the Permanent Account Number (PAN) card registered in the exact corporate name of the bidder is an absolute pre-condition for technical evaluation."
            elif field_name == "gstin":
                text = "The bidder must hold an active GSTIN registration and submit the latest GST filing verification report (GSTR-3B/GSTR-1), failing which the bid shall be summarily rejected."
            elif field_name == "gst_status":
                text = "Under no circumstances shall bids be entertained from entities whose GST registration status reflects cancelled, suspended, or inactive on the GST common portal."
            else:
                text = f"Tenderers must furnish certified acknowledgments of Income Tax Returns for not less than the immediately preceding {val} assessment years, accompanied by corresponding computation statements."

        # 3. MSME
        elif family.category == "msme":
            if field_name == "udyam":
                text = "In the event the bidder seeks exemption from payment of tender document fees or EMD under the Public Procurement Policy, submission of an active Udyam Registration Certificate is mandatory."
            elif field_name == "msme_classification":
                text = f"Enterprises tendering under MSME reservations must prove classification strictly as {val} via valid statutory Udyam portal registration records."
            else:
                text = "Bidders availing NSIC concessions must furnish valid and unexpired Single Point Registration Scheme documentation issued by NSIC authorities."

        # 4. Experience
        elif family.category == "experience":
            if "years" in field_name:
                text = f"Bidders lacking a proven, continuous corporate track record of at least {val} years in executing projects of comparable scale shall be disqualified at the technical stage."
            elif "government" in field_name:
                text = f"It is mandatory that the applicant has satisfactorily completed not less than {val} contracts directly for Central or State Government departments or PSUs{period_str}."
            else:
                text = f"Documentary evidence establishing that the vendor has successfully delivered at least {val} projects of similar scope and magnitude{period_str} must be uploaded."

        # 5. Technical
        elif family.category == "technical":
            templates = [
                f"Offered solutions possessing {field_name.replace('_', ' ')} below {val} {unit or ''} shall be deemed technically non-compliant, and no deviation shall be permitted under any circumstances.",
                f"The technical evaluation committee shall strictly verify that {field_name.replace('_', ' ')} provided by the OEM is configured to no less than {val} {unit or ''} in standard production specifications.",
            ]
            text = self.rng.choice(templates)

        # 6. Certification
        elif family.category == "certification":
            if field_name == "bis_certification":
                text = "Tenderers offering goods without compulsory Bureau of Indian Standards (BIS) conformity certification and valid license shall face immediate disqualification."
            elif field_name == "stqc_certificate":
                text = "A test certificate issued by an accredited STQC laboratory certifying compliance with specifications must be enclosed with the technical bid."
            elif family.operator == "includes_all":
                text = f"Failure to submit verifiable and currently active certificate copies for each of the stipulated standards ({val[0]} and {val[1]}) shall result in outright disqualification at the preliminary evaluation stage."
            else:
                text = f"Possession of a currently valid {val} certificate duly registered with the National Accreditation Board is a non-negotiable prerequisite for pre-qualification."

        # 7. OEM
        elif family.category == "oem":
            if field_name == "authorized_distributor":
                text = "Where the tenderer is not the original equipment manufacturer, they must furnish documentary proof demonstrating designated status as an authorized distributor or premier partner."
            elif field_name == "authorization_validity_period":
                text = f"The tender-specific OEM authorization must unambiguously certify that the partner authorization remains unexpired and valid for a continuous period of at least {val} months beyond bid validity."
            else:
                text = "Tenders submitted without a verifiable Manufacturer Authorization Form (MAF) executed by an authorized signatory of the OEM shall be rejected at the technical opening."

        # 8. Local Content
        elif family.category == "local_content":
            if field_name == "make_in_india_class":
                text = f"In compliance with DPIIT public procurement directives, the bidder must tender a statutory auditor certification affirming eligibility as a {val}."
            else:
                text = f"Under the Public Procurement (Preference to Make in India) Order, the local value addition percentage offered by the bidder shall strictly not fall below {val}%."

        # 9. Legal
        elif family.category == "legal":
            if field_name == "is_debarred":
                text = "The bidder must declare under penalty of perjury that neither the bidding company nor any of its promoters are currently debarred or suspended by any government authority."
            elif field_name == "non_blacklisting_declaration":
                text = "A notarized non-blacklisting affidavit executed on non-judicial stamp paper within 30 days of bid submission must accompany the technical bid."
            else:
                text = "An undertaking on non-judicial stamp paper affirming that the bidder has no disqualifying ongoing litigation or arbitration proceedings must accompany the bid."

        # 10. Commercial
        elif family.category == "commercial":
            if field_name == "bid_security_declaration":
                text = "Bidders exempt from EMD must tender a legally binding Bid Security Declaration accepting debarment for a period up to 2 years in the event of bid withdrawal during validity."
            elif field_name == "performance_bank_guarantee_percentage":
                text = f"The successful contractor shall furnish an irrevocable Performance Bank Guarantee equivalent to strictly {val}% of the total accepted contract value within 15 days of LoA."
            else:
                amt_str = format_inr_amount(val, "full_numeric")
                if family.operator == "==":
                    text = f"Earnest Money Deposit (EMD) in the exact stipulated sum of {amt_str} must be remitted via Bank Guarantee from any Scheduled Commercial Bank."
                else:
                    text = f"Earnest Money Deposit (EMD) of an amount not less than {amt_str} must be furnished in the form of Bank Guarantee from any Scheduled Commercial Bank."

        # 11. Delivery
        elif family.category == "delivery":
            if field_name == "installation_period":
                text = f"Site installation, deployment, and operational acceptance testing must strictly be concluded within a maximum window of {val} days from physical delivery."
            elif field_name == "delivery_period":
                text = f"Time being the essence of this procurement, the entire consignment delivery shall strictly be completed within a period not exceeding {val} days from notification of award."
            else:
                text = f"The supplied equipment shall be covered by an unconditional comprehensive on-site OEM warranty for a minimum duration of {val} years with 24x7 support."

        else:
            text = f"The bidder's qualification is strictly contingent upon demonstrating that {field_name.replace('_', ' ')} does not fall short of {val} {unit or ''}{period_str}."

        return {"text": text, "difficulty": "hard", "method": "legalistic_inversion", "is_table": False}

    def _make_table_format(self, family: RequirementFamily) -> str:
        """Format as tabular tender specification snippet."""
        field_str = (family.field or "Metric").replace("_", " ").title()
        val_str = f"{family.value}"
        if family.unit == "INR":
            val_str = format_inr_amount(family.value, "symbol_lakh")
        elif family.unit:
            val_str = f"{family.value} {family.unit}"

        styles = [
            f"Parameter: {field_str} | Minimum Requirement: {val_str}",
            f"Specification: {field_str}\nThreshold: >= {val_str}\nMandatory: Yes",
            f"Item: {field_str} -- Specified Target: {family.operator or '>='} {val_str}",
            f"Schedule of Requirements -> {field_str}: {val_str} (Mandatory)",
        ]
        return self.rng.choice(styles)

    def _generate_ambiguous_clauses(
        self,
        family: RequirementFamily,
        count: int,
    ) -> list[dict[str, Any]]:
        """Generate genuinely non-committal or disjunctive clauses that trigger REVIEW."""
        field_name = family.field or "Parameter"
        fid = family.family_id

        variants: list[str] = []
        if "RAM_DISJUNCTIVE" in fid:
            variants = [
                "Depending on configuration, the compute nodes may provide 8 × 192 GB OR 16 × 96 GB memory.",
                "Memory configuration can be either 96 GB or 192 GB per GPU as per system availability.",
                "Memory option: 8x192GB or alternatively 16x96GB modules based on chassis selection.",
            ]
        elif "STORAGE_UP_TO" in fid:
            variants = [
                "Up to 2 TB high-speed storage may optionally be provided.",
                "Storage capacity may be up to 2 TB depending on vendor design.",
                "System supports storage of up to 2 TB or as specified in technical annexure.",
            ]
        elif "CERT_EQUIVALENT" in fid:
            variants = [
                "Equivalent national or international certification may be accepted subject to committee approval.",
                "ISO 9001 or any comparable quality standard acceptable to the competent authority.",
                "Bidders may provide equivalent compliance documentation subject to scrutiny.",
            ]
        elif "TURNOVER_APPROX" in fid:
            variants = [
                "Annual turnover roughly in the range of 50 lakhs or higher preferred.",
                "Bidder should preferably demonstrate adequate turnover in the ballpark of ₹50 Lakhs.",
                "Turnover of approximately ₹50 Lakhs or commensurate financial standing expected.",
            ]
        else:
            variants = [
                f"Adequate and relevant {field_name.replace('_', ' ')} as deemed satisfactory by the evaluation committee.",
                f"Optional {field_name.replace('_', ' ')} documentation may be requested if applicable.",
                f"Subject to discretion of procuring officer, {field_name.replace('_', ' ')} may be relaxed.",
            ]

        results = []
        for v in variants[:count]:
            results.append({
                "text": v,
                "difficulty": "medium",
                "method": "ambiguous_disjunction",
                "is_table": False,
            })
        while len(results) < count:
            results.append({
                "text": self.rng.choice(variants),
                "difficulty": "hard",
                "method": "ambiguous_disjunction",
                "is_table": False,
            })
        return results
