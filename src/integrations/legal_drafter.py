"""
Claude-powered professional legal email drafter.
Combines RAG case knowledge + Tavily internet research + attachment content
into a formal, citation-rich legal letter.
"""
from __future__ import annotations
from datetime import date
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

LEGAL_DRAFTER_SYSTEM = """You are a senior US legal counsel with 20+ years of experience in civil litigation, contract law, and insurance disputes.

Your task is to draft a comprehensive, professional legal response email based on the provided context.

STRICT RULES:
1. Format as a formal legal letter — proper date, salutation, structured body, professional closing.
2. Cite every legal case or statute using proper US legal citation format (e.g., Brown v. Board of Education, 347 U.S. 483 (1954)).
3. Build the STRONGEST possible legal argument in favor of the client using ALL provided evidence.
4. Reference specific case documents where they support the argument.
5. NEVER fabricate cases, facts, or citations — only use what is explicitly provided.
6. End with a "Legal Authorities Cited" section listing all cases and statutes referenced.
7. Use precise legal language — this is going directly to opposing counsel or the court.
8. Maximum 600 words in the body. Be comprehensive but focused.

LETTER STRUCTURE:
[Date]

Re: [Subject/Matter]

Dear [Recipient],

[Opening — state the purpose clearly]

[Section 1 — Facts established from case documents]

[Section 2 — Legal argument supported by case law and statutes]

[Section 3 — Conclusion and demand/request]

Respectfully,
[Legal AI Research Assistant]
On behalf of the Client

---
LEGAL AUTHORITIES CITED:
[List all cases and statutes referenced]
"""


def draft_legal_email(
    question: str,
    rag_answer: str,
    rag_sources: list[dict],
    web_results: list[dict],
    attachment_text: str = "",
    from_name: str = "Client",
) -> str:
    """
    Draft a professional legal response using Claude.
    Falls back to formatted RAG answer if Claude unavailable.
    """
    if not ANTHROPIC_API_KEY:
        print("[LegalDrafter] ANTHROPIC_API_KEY not set — returning RAG answer.")
        return rag_answer

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # ── Build context sections ──────────────────────────────────────────

        # Case document findings
        sources_block = "\n".join(
            f"  [{i+1}] {s.get('source_file', 'Unknown')} "
            f"(relevance: {s.get('relevance_score', 0):.2f})\n"
            f"      \"{s.get('content_preview', '')[:250]}\""
            for i, s in enumerate(rag_sources[:6])
        )

        # Internet legal research
        if web_results:
            web_block = "\n".join(
                f"  [{r['type'].upper()}] {r['title']}\n"
                f"  URL: {r['url']}\n"
                f"  Excerpt: {r['content'][:400]}"
                for r in web_results[:8]
            )
        else:
            web_block = "  No additional internet research available."

        # Attachment content
        attachment_block = (
            f"\nCONTENT FROM EMAIL ATTACHMENT:\n{attachment_text[:2000]}\n"
            if attachment_text.strip() else ""
        )

        today = date.today().strftime("%B %d, %Y")

        user_prompt = f"""
DATE: {today}
CLIENT/SENDER: {from_name}
INQUIRY/SUBJECT: {question}

════════════════════════════════════════════════════════
SECTION A — RAG ANALYSIS (from our case document database):
════════════════════════════════════════════════════════
{rag_answer[:2000]}

════════════════════════════════════════════════════════
SECTION B — SUPPORTING CASE DOCUMENTS (Pinecone database):
════════════════════════════════════════════════════════
{sources_block}
{attachment_block}
════════════════════════════════════════════════════════
SECTION C — INTERNET LEGAL RESEARCH (cases, statutes, precedents):
════════════════════════════════════════════════════════
{web_block}

════════════════════════════════════════════════════════
TASK: Draft a formal professional legal response letter to the above inquiry.
Build the strongest possible argument for our client using ALL evidence above.
Cite specific cases from Section C using proper US legal citation format.
Reference specific documents from Section B where they support the argument.
════════════════════════════════════════════════════════
"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2500,
            system=LEGAL_DRAFTER_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )

        drafted = msg.content[0].text
        print(f"[LegalDrafter] Claude drafted {len(drafted)} char legal letter.")
        return drafted

    except Exception as e:
        print(f"[LegalDrafter] Claude drafting failed (non-fatal): {e}")
        return rag_answer
