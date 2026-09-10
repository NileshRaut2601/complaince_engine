"""Variation and Controlled OCR Noise Generator.

Produces surface variations, procurement synonym substitutions,
and controlled realistic OCR noise while preserving the integrity of the target JSON.
"""

from __future__ import annotations

import random
from typing import Optional

SYNONYMS = {
    "bidder": ["vendor", "supplier", "contractor", "participating firm", "tenderer", "applicant"],
    "must": ["shall", "is required to", "needs to", "has to", "is mandated to"],
    "at least": ["not less than", "no less than", "a minimum of", "equal to or greater than"],
    "mandatory": ["compulsory", "strictly required", "an essential condition", "obligatory"],
    "annual turnover": ["financial turnover", "reported turnover", "yearly turnover"],
}

# Common optical character recognition (OCR) substitution confusions
OCR_SUBSTITUTIONS = {
    "m": "rn",
    "cl": "d",
    "vv": "w",
    "0": "O",
    "1": "l",
    "5": "S",
}


class VariationGenerator:
    """Applies controlled surface mutations and realistic scanning artifacts."""

    def __init__(self, seed: Optional[int] = 42) -> None:
        self.rng = random.Random(seed)

    def apply_synonym_variation(self, text: str) -> str:
        """Substitute procurement terminology with valid synonyms."""
        words = text.split()
        modified = False
        new_words = []
        for w in words:
            clean_w = w.lower().strip(".,;:()")
            if clean_w in SYNONYMS and not modified and self.rng.random() < 0.4:
                replacement = self.rng.choice(SYNONYMS[clean_w])
                # Preserve capitalization
                if w[0].isupper():
                    replacement = replacement.capitalize()
                new_words.append(replacement)
                modified = True
            else:
                new_words.append(w)
        return " ".join(new_words)

    def inject_ocr_noise(self, text: str) -> tuple[str, str]:
        """Inject mild, realistic OCR scanning corruption without destroying semantics.

        Returns:
            tuple: (corrupted_text, "ocr")
        """
        chars = list(text)
        if len(chars) < 10:
            return text, "ocr"

        # Apply 1 or 2 subtle OCR substitutions at non-critical positions
        num_mutations = self.rng.randint(1, 2)
        applied = 0
        for _ in range(10):
            idx = self.rng.randint(0, len(chars) - 1)
            char = chars[idx]
            if char in OCR_SUBSTITUTIONS:
                chars[idx] = OCR_SUBSTITUTIONS[char]
                applied += 1
                if applied >= num_mutations:
                    break

        corrupted = "".join(chars)
        # Also occasionally substitute currency symbols common in scanned Indian tenders
        if "₹" in corrupted and self.rng.random() < 0.5:
            corrupted = corrupted.replace("₹", "Rs. ")

        return corrupted, "ocr"

    def add_clause_numbering(self, text: str) -> str:
        """Add realistic tender clause numbering (e.g. '3.2(b)')."""
        sec = self.rng.randint(1, 12)
        sub = self.rng.randint(1, 9)
        letter = self.rng.choice(["a", "b", "c", "i", "ii"])
        prefix = self.rng.choice([
            f"Clause {sec}.{sub}: ",
            f"Section {sec}.{sub}({letter}) - ",
            f"Para {sec}.{sub}: ",
            f"Condition {sec}.{sub}.1: ",
            f"[{sec}.{sub}] ",
        ])
        return prefix + text

