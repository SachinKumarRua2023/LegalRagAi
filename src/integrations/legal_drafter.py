"""
Claude-powered professional legal email drafter.
Combines RAG case knowledge + Tavily internet research + attachment content
into a formal, citation-rich legal letter rendered as clean HTML.
"""
from __future__ import annotations
from datetime import date
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

LEGAL_DRAFTER_SYSTEM = """You are a senior US legal counsel with 20+ years of experience in civil litigation, contract law, and insurance disputes.

Your task: Draft a professional legal response email AND generate a professional email subject line.

OUTPUT FORMAT — Return ONLY valid JSON with exactly two keys:
{
  "subject": "Professional Email Subject Line Here",
  "body": "Full HTML email body here"
}

SUBJECT LINE RULES:
- Professional and specific (e.g., "Legal Response: Mechanic's Lien Dispute — ARS v. Pramukh Inc.")
- Under 80 characters
- No markdown, no quotes inside the subject

BODY HTML RULES — Use this exact HTML structure:
<div style="font-family: Georgia, serif; max-width: 700px; color: #1a1a1a; line-height: 1.8;">

  <p style="color: #555; margin-bottom: 20px;">[Date]</p>

  <p style="margin-bottom: 6px;"><strong>Re:</strong> [Matter/Subject]</p>

  <p style="margin-bottom: 24px;">Dear [Recipient Name],</p>

  <p style="margin-bottom: 16px;">[Opening paragraph — state purpose clearly]</p>

  <h3 style="color: #0a1628; border-bottom: 1px solid #c9a84c; padding-bottom: 6px; margin-top: 28px;">I. FACTUAL BACKGROUND</h3>
  <p style="margin-bottom: 16px;">[Facts from case documents]</p>

  <h3 style="color: #0a1628; border-bottom: 1px solid #c9a84c; padding-bottom: 6px; margin-top: 28px;">II. LEGAL ARGUMENT</h3>
  <p style="margin-bottom: 16px;">[Legal arguments with proper citations]</p>

  <h3 style="color: #0a1628; border-bottom: 1px solid #c9a84c; padding-bottom: 6px; margin-top: 28px;">III. CONCLUSION</h3>
  <p style="margin-bottom: 24px;">[Conclusion and demand/request]</p>

  <p style="margin-bottom: 4px;">Respectfully submitted,</p>
  <p style="margin-bottom: 4px;"><strong>Legal AI Research Assistant</strong></p>
  <p style="margin-bottom: 24px; color: #555;">On behalf of the Client</p>

  <hr style="border: none; border-top: 1px solid #ddd; margin: 24px 0;">
  <h4 style="color: #0a1628;">LEGAL AUTHORITIES CITED</h4>
  <ul style="padding-left: 20px; color: #333;">
    <li style="margin-bottom: 8px;">[Case citation 1]</li>
    <li style="margin-bottom: 8px;">[Case citation 2]</li>
  </ul>

</div>

STRICT RULES:
1. Build the STRONGEST possible legal argument for the client using ALL provided evidence.
2. Cite every legal case with proper US format: Case Name, Volume Reporter Page (Court Year).
3. NEVER fabricate cases or facts — only use what is provided in context.
4. Return ONLY the JSON — no explanation, no markdown fences, no extra text.
"""


def draft_legal_email(
    question: str,
    rag_answer: str,
    rag_sources: list[dict],
    web_results: list[dict],
    attachment_text: str = "",
    from_name: str = "Client",
) -> dict:
    """
    Draft a professional legal response using Claude.
    Returns dict with 'subject' and 'body' (HTML).
    Falls back to plain text RAG answer if Claude unavailable.
    """
    if not ANTHROPIC_API_KEY:
        print("[LegalDrafter] ANTHROPIC_API_KEY not set — returning RAG answer.")
        return {
            "subject": f"Legal Response: {question[:60]}",
            "body": f"<p>{rag_answer}</p>",
        }

    try:
        import anthropic
        import json as _json

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # ── Build context sections ──────────────────────────────────────────

        sources_block = "\n".join(
            f"  [{i+1}] {s.get('source_file', 'Unknown')} "
            f"(relevance: {s.get('relevance_score', 0):.2f})\n"
            f"      \"{s.get('content_preview', '')[:250]}\""
            for i, s in enumerate(rag_sources[:6])
        )

        web_block = "\n".join(
            f"  [{r['type'].upper()}] {r['title']}\n"
            f"  URL: {r['url']}\n"
            f"  Excerpt: {r['content'][:400]}"
            for r in web_results[:8]
        ) if web_results else "  No additional internet research available."

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
TASK: Draft a formal professional legal response letter.
Build the strongest argument for our client using ALL evidence.
Return ONLY the JSON with "subject" and "body" keys as instructed.
════════════════════════════════════════════════════════
"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            system=LEGAL_DRAFTER_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = msg.content[0].text.strip()

        # Strip markdown fences if Claude added them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = _json.loads(raw)
        subject = result.get("subject", f"Legal Response: {question[:60]}")
        body = result.get("body", f"<p>{rag_answer}</p>")

        print(f"[LegalDrafter] Drafted: subject='{subject[:60]}' body={len(body)} chars")
        return {"subject": subject, "body": body}

    except Exception as e:
        print(f"[LegalDrafter] Claude drafting failed (non-fatal): {e}")
        return {
            "subject": f"Legal Response: {question[:60]}",
            "body": f"<p>{rag_answer}</p>",
        }
