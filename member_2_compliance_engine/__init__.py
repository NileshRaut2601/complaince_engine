"""Member 2 Compliance Engine package.

Responsible for:
1. Extracting structured requirements from tender documents.
2. Parsing and normalizing requirements and bidder evidence.
3. Evaluating evidence deterministically using Python rules.
4. Routing ambiguous / semantic cases to LLM reasoning.
5. Providing auditable compliance verdicts (COMPLIANT, NON_COMPLIANT, MISSING, REVIEW).
6. Performance evaluation metrics.
"""

__version__ = "1.0.0"

