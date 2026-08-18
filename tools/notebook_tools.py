"""Helper utilities extracted from Day3/Day4 notebooks.

Provides functions to rebuild the index, grounding prompt text, simple
response-schema validation and unsupported-claim detection used by the
project's notebook workflows.
"""
import re
import json
from typing import List, Dict

GROUNDING_SYSTEM_PROMPT = """You are a citation-bound clinical evidence assistant.

RULES — follow every one exactly:
1. Answer ONLY using the context passages provided below. Never use outside medical knowledge.
2. Every claim in your "recommendation" must be directly supported by the "evidence" you cite.
3. You MUST return your answer as a mapping with keys: recommendation, evidence, citations, confidence
4. If the context does not contain enough information to answer confidently, set
   confidence to "insufficient", leave evidence and citations empty, and write a plain
   refusal in "recommendation" instead of guessing.
5. Never invent a citation. Never soften a refusal into a partial guess.
"""


def extract_claims(text: str) -> List[str]:
    """Very small claim splitter: break on sentence boundaries and ignore short fragments."""
    sentences = re.split(r'(?<=[.!?])\s+', (text or '').strip())
    return [s for s in sentences if len(s.split()) > 3]


def is_claim_supported(claim: str, evidence_text: str, min_overlap: float = 0.35) -> bool:
    """Checks word overlap between a claim and the evidence text as a proxy for support."""
    claim_words = set(w.lower().strip(".,;:") for w in claim.split() if len(w) > 3)
    evidence_words = set(w.lower().strip(".,;:") for w in (evidence_text or '').split() if len(w) > 3)
    if not claim_words:
        return True
    overlap = len(claim_words & evidence_words) / len(claim_words)
    return overlap >= min_overlap


def check_unsupported_claims(answer_dict: Dict) -> List[str]:
    """Return a list of flagged claims that are not supported by the provided evidence."""
    if not isinstance(answer_dict, dict):
        return []
    if answer_dict.get("confidence") == "insufficient":
        return []
    claims = extract_claims(answer_dict.get("recommendation", ""))
    evidence = answer_dict.get("evidence", "")
    flagged = [c for c in claims if not is_claim_supported(c, evidence)]
    return flagged


def simple_schema_validate(answer_dict: Dict) -> bool:
    """Lightweight validation matching the Day3 response schema.

    Expects keys: recommendation (str), evidence (str), citations (list), confidence (one of allowed).
    This is intentionally small to avoid an extra dependency on `jsonschema`.
    """
    if not isinstance(answer_dict, dict):
        return False
    if 'recommendation' not in answer_dict or 'confidence' not in answer_dict:
        return False
    if not isinstance(answer_dict.get('recommendation'), str):
        return False
    if not isinstance(answer_dict.get('evidence', ''), str):
        return False
    citations = answer_dict.get('citations', [])
    if not isinstance(citations, list):
        return False
    for c in citations:
        if not isinstance(c, dict):
            return False
        if not any(k in c for k in ('document', 'page', 'section')):
            return False
    if answer_dict.get('confidence') not in ('high', 'medium', 'low', 'insufficient'):
        return False
    return True


def parse_expected_source(expected_str: str):
    """Parse expected source like 'GINA 2026, Page 205' into (doc,page).
    Returns (document_name_lower, page_int_or_None).
    """
    if not expected_str:
        return None, None
    m = re.search(r'(?P<doc>[^,]+)(?:,\s*Page\s*(?P<page>\d+))?', expected_str)
    if not m:
        return expected_str.strip().lower(), None
    doc = m.group('doc').strip().lower()
    page = int(m.group('page')) if m.group('page') else None
    return doc, page
