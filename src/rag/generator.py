"""
LLM response generator.
Priority order (auto mode): Groq → Gemini → Claude → Echo
All three have free tiers.
"""
from __future__ import annotations
from functools import lru_cache

from config.settings import (
    LLM_PROVIDER,
    GEMINI_MODEL, GOOGLE_API_KEY,
    CLAUDE_MODEL, ANTHROPIC_API_KEY,
    GROQ_MODEL, GROQ_API_KEY,
)

SYSTEM_PROMPT = """You are an expert AI legal research assistant specializing in USA legal cases.

Your job:
1. Answer questions using ONLY the provided document context.
2. ALWAYS cite your sources by referencing the [Source N: ...] markers.
3. **IMPORTANT: Quote actual content from the sources** — show relevant sentences/paragraphs, not just file names.
4. At the end of EVERY answer include a "Sources Used" section listing all sources cited.
5. If the context doesn't contain enough information, say so clearly — never make up facts.
6. Format responses clearly with headings and bullet points where appropriate.

Source citation format:
- Always mention: File name, folder path, page/slide/section when available.
- **Quote the actual text** that supports your answer from the context.
- Example: "According to [Source 1: File: doe_v_roe.pdf | Folder: /data/raw | Page 3], the court held that 'the defendant's rights were violated when...'"

When sources don't contain the answer:
- Clearly state what information IS available in the sources (list case names, topics, etc.)
- Explain that the specific query topic wasn't found in the indexed documents.
- Suggest alternative queries that might yield results from the available content.
"""


# ── Groq (FREE — 30 RPM, Llama 3.3 70B) ─────────────────────────────────────

class GroqGenerator:
    def __init__(self):
        from groq import Groq
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set.")
        self._client = Groq(api_key=GROQ_API_KEY)
        print(f"[LLM] Groq ready: {GROQ_MODEL}")

    def generate(self, query: str, context: str) -> str:
        prompt = (
            f"Context Documents:\n{context}\n\n"
            f"User Question: {query}\n\n"
            f"Answer (always cite [Source N] tags from above):"
        )
        resp = self._client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        return resp.choices[0].message.content


# ── Gemini (FREE — 15 RPM, 1M tokens/day) ────────────────────────────────────

class GeminiGenerator:
    def __init__(self):
        from google import genai
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set.")
        self._client = genai.Client(api_key=GOOGLE_API_KEY)
        self._model = GEMINI_MODEL
        print(f"[LLM] Gemini ready: {GEMINI_MODEL}")

    def generate(self, query: str, context: str) -> str:
        from google import genai as _genai
        prompt = (
            f"Context Documents:\n{context}\n\n"
            f"User Question: {query}\n\n"
            f"Answer (always cite [Source N] tags from above):"
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=_genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
            ),
        )
        return response.text


# ── Claude (Paid, but good fallback) ─────────────────────────────────────────

class ClaudeGenerator:
    def __init__(self):
        import anthropic
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set.")
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print(f"[LLM] Claude ready: {CLAUDE_MODEL}")

    def generate(self, query: str, context: str) -> str:
        prompt = (
            f"Context Documents:\n{context}\n\n"
            f"User Question: {query}\n\n"
            f"Answer (always cite [Source N] tags from above):"
        )
        msg = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text


# ── Echo (testing, no API key) ────────────────────────────────────────────────

class EchoGenerator:
    def generate(self, query: str, context: str) -> str:
        return (
            f"[ECHO MODE — set GROQ_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY in .env]\n\n"
            f"**Query:** {query}\n\n**Retrieved context preview:**\n{context[:500]}..."
        )


# ── Factory ───────────────────────────────────────────────────────────────────

def _try(cls, name: str):
    try:
        return cls()
    except Exception as e:
        print(f"[LLM] {name} failed: {e}")
        return None


@lru_cache(maxsize=1)
def get_generator():
    """Returns the best available LLM generator (cached singleton)."""
    provider = LLM_PROVIDER.lower()

    if provider == "groq":
        g = _try(GroqGenerator, "Groq")
        if g:
            return g
    elif provider == "gemini":
        g = _try(GeminiGenerator, "Gemini")
        if g:
            return g
    elif provider == "claude":
        g = _try(ClaudeGenerator, "Claude")
        if g:
            return g
    else:
        # "auto" — try in order: Groq (fastest free) → Gemini → Claude
        if GROQ_API_KEY:
            g = _try(GroqGenerator, "Groq")
            if g:
                return g
        if GOOGLE_API_KEY:
            g = _try(GeminiGenerator, "Gemini")
            if g:
                return g
        if ANTHROPIC_API_KEY:
            g = _try(ClaudeGenerator, "Claude")
            if g:
                return g

    print("[LLM] No API keys found — running in echo mode")
    return EchoGenerator()
