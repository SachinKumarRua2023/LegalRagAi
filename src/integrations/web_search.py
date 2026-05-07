"""Tavily-powered legal internet research — finds cases, precedents, statutes."""
from __future__ import annotations
from config.settings import TAVILY_API_KEY

# Legal authority domains — highest quality sources only
LEGAL_DOMAINS = [
    "law.justia.com",
    "law.cornell.edu",
    "scholar.google.com",
    "courtlistener.org",
    "findlaw.com",
    "casetext.com",
    "oyez.org",
    "supremecourt.gov",
    "leagle.com",
    "law.com",
]


def search_legal_evidence(query: str, max_results: int = 5) -> list[dict]:
    """
    Search internet for legal cases, precedents, statutes, and arguments.
    Returns structured results ready for Claude to cite.
    Falls back silently if Tavily key not set.
    """
    if not TAVILY_API_KEY:
        print("[WebSearch] TAVILY_API_KEY not set — skipping internet research.")
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)

        # Run two targeted searches for maximum legal coverage
        results = []

        # Search 1: Case law and precedents
        case_search = client.search(
            query=f"legal case law precedent court ruling {query}",
            search_depth="advanced",
            include_domains=LEGAL_DOMAINS,
            max_results=max_results,
        )
        for r in case_search.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:600],
                "type": "case_law",
            })

        # Search 2: Supporting arguments and statutes
        arg_search = client.search(
            query=f"legal argument statute regulation {query}",
            search_depth="advanced",
            max_results=max_results,
        )
        for r in arg_search.get("results", []):
            # Avoid duplicates
            if r.get("url") not in {x["url"] for x in results}:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:600],
                    "type": "statute_argument",
                })

        print(f"[WebSearch] Found {len(results)} legal sources for: '{query[:60]}'")
        return results[:max_results * 2]

    except Exception as e:
        print(f"[WebSearch] Search failed (non-fatal): {e}")
        return []
