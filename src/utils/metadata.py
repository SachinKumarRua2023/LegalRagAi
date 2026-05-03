"""Metadata extraction utilities for legal documents."""
from __future__ import annotations
import re
from typing import Any

# Patterns to extract legal metadata from text
_CASE_NUMBER_PAT = re.compile(r"\b(?:No\.|Case\s+No\.?|Docket\s+No\.?)\s*([\w\-:]+)", re.I)
_COURT_PAT = re.compile(
    r"(?:United States|U\.S\.)\s+(District|Circuit|Court of Appeals|Bankruptcy|Supreme)\s+Court"
    r"|(?:Supreme Court of the United States|SCOTUS)",
    re.I,
)
_DATE_PAT = re.compile(
    r"(?:Decided|Filed|Argued|Submitted)[\s:]+([A-Z][a-z]+ \d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})",
    re.I,
)
_PARTIES_PAT = re.compile(r"^([A-Z][A-Z\s,\.]+)\s+v(?:s?)\.\s+([A-Z][A-Z\s,\.]+)", re.M)
_JUDGE_PAT = re.compile(r"(?:Judge|Justice|Chief Justice)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.I)


def extract_legal_metadata(text: str) -> dict[str, Any]:
    """Extract common legal metadata from case text."""
    meta: dict[str, Any] = {}

    m = _CASE_NUMBER_PAT.search(text)
    if m:
        meta["case_number"] = m.group(1).strip()

    m = _COURT_PAT.search(text)
    if m:
        meta["court"] = m.group(0).strip()

    m = _DATE_PAT.search(text)
    if m:
        meta["decision_date"] = m.group(1).strip()

    m = _PARTIES_PAT.search(text[:500])
    if m:
        meta["plaintiff"] = m.group(1).strip()
        meta["defendant"] = m.group(2).strip()

    judges = _JUDGE_PAT.findall(text[:2000])
    if judges:
        meta["judges"] = ", ".join(set(judges[:5]))

    return meta


def enrich_metadata(chunks: list[dict]) -> list[dict]:
    """Add legal metadata extraction to chunks that look like case text."""
    for chunk in chunks:
        text = chunk.get("text", "")
        if len(text) > 200:
            legal_meta = extract_legal_metadata(text)
            if legal_meta:
                chunk["metadata"].update(legal_meta)
    return chunks
