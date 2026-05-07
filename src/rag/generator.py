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
        import time
        prompt = (
            f"Context Documents:\n{context}\n\n"
            f"User Question: {query}\n\n"
            f"Answer (always cite [Source N] tags from above):"
        )
        for attempt in range(3):
            try:
                resp = self._client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2048,
                    temperature=0.1,
                    timeout=60,  # 60 second timeout
                )
                # Validate response
                if not resp or not resp.choices:
                    raise RuntimeError("Empty response from Groq API")
                if not resp.choices[0].message or not resp.choices[0].message.content:
                    raise RuntimeError("Empty message content from Groq API")
                return resp.choices[0].message.content

            except Exception as e:
                err = str(e)
                err_lower = err.lower()

                # Rate limit errors — fail immediately so FallbackGenerator can try next provider
                if "429" in err or "rate_limit" in err_lower or "rate limit" in err_lower:
                    raise RuntimeError("Groq rate limit reached.") from e

                # Timeout errors
                elif "timeout" in err_lower or "timed out" in err_lower:
                    if attempt < 2:
                        wait = 10 * (attempt + 1)
                        print(f"[Groq] Timeout — waiting {wait}s (attempt {attempt+1}/3)...")
                        time.sleep(wait)
                    else:
                        raise RuntimeError("Groq API timeout after multiple attempts.") from e

                # 5xx server errors - retry with backoff
                elif any(code in err for code in ["500", "502", "503", "504"]):
                    if attempt < 2:
                        wait = 5 * (attempt + 1)
                        print(f"[Groq] Server error — waiting {wait}s (attempt {attempt+1}/3)...")
                        time.sleep(wait)
                    else:
                        raise RuntimeError("Groq server error. Please try again later.") from e

                # Authentication errors - don't retry
                elif "401" in err or "403" in err or "authentication" in err_lower or "unauthorized" in err_lower:
                    raise RuntimeError(f"Groq authentication failed: {e}") from e

                # Network errors - retry once
                elif any(net_err in err_lower for net_err in ["connection", "network", "dns", "unreachable"]):
                    if attempt < 2:
                        wait = 5
                        print(f"[Groq] Network error — waiting {wait}s (attempt {attempt+1}/3)...")
                        time.sleep(wait)
                    else:
                        raise RuntimeError(f"Groq network error: {e}") from e

                else:
                    raise


# ── Gemini (FREE — 15 RPM, 1M tokens/day) ────────────────────────────────────

class GeminiGenerator:
    def __init__(self):
        from google import genai
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set.")
        self._client = genai.Client(api_key=GOOGLE_API_KEY)
        self._model = GEMINI_MODEL
        print(f"[LLM] Gemini ready: {GEMINI_MODEL}")

    def _parse_retry_delay(self, error_msg: str) -> int:
        """Extract retry delay from error message or default."""
        import re
        # Look for "retry in Xs" or "RetryInfo" with seconds
        match = re.search(r'retry\s*(?:in)?\s*(\d+\.?\d*)\s*s', error_msg.lower())
        if match:
            return int(float(match.group(1))) + 1
        return 60  # Default 60s for rate limits

    def generate(self, query: str, context: str) -> str:
        import time
        from google import genai as _genai
        from google.api_core import exceptions as google_exceptions

        prompt = (
            f"Context Documents:\n{context}\n\n"
            f"User Question: {query}\n\n"
            f"Answer (always cite [Source N] tags from above):"
        )

        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=_genai.types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                    ),
                )
                # Validate response
                if not response or not response.text:
                    raise RuntimeError("Empty response from Gemini API")
                return response.text

            except google_exceptions.ResourceExhausted as e:
                # Fail immediately so FallbackGenerator can try next provider
                raise RuntimeError("Gemini quota exceeded.") from e

            except google_exceptions.InvalidArgument as e:
                raise RuntimeError(f"Gemini API invalid argument: {e}") from e

            except google_exceptions.PermissionDenied as e:
                raise RuntimeError(f"Gemini API permission denied (invalid key?): {e}") from e

            except Exception as e:
                err = str(e)
                if "429" in err or "resource exhausted" in err.lower() or "quota" in err.lower():
                    raise RuntimeError("Gemini quota exceeded.") from e
                elif "timeout" in err.lower() or "deadline exceeded" in err.lower():
                    if attempt < 2:
                        wait = 10 * (attempt + 1)
                        print(f"[Gemini] Timeout — waiting {wait}s (attempt {attempt+1}/3)...")
                        time.sleep(wait)
                    else:
                        raise RuntimeError("Gemini API timeout after multiple attempts.") from e
                else:
                    raise


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


# ── Runtime fallback chain ────────────────────────────────────────────────────

class FallbackGenerator:
    """Tries generators in order at runtime. If Groq rate-limits, switches to Gemini, then Claude."""

    def __init__(self, generators: list):
        self._generators = generators
        names = [type(g).__name__.replace("Generator", "") for g in generators]
        print(f"[LLM] Fallback chain: {' → '.join(names)}")

    def generate(self, query: str, context: str) -> str:
        last_error = None
        for gen in self._generators:
            name = type(gen).__name__.replace("Generator", "")
            try:
                return gen.generate(query, context)
            except Exception as e:
                print(f"[LLM] {name} failed at runtime: {str(e)[:120]} — trying next provider")
                last_error = e
        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        )


# ── Factory ───────────────────────────────────────────────────────────────────

def _try(cls, name: str):
    try:
        return cls()
    except Exception as e:
        print(f"[LLM] {name} init failed: {e}")
        return None


def _build_chain(primary: str) -> list:
    """Build ordered generator list: primary first, then the rest as fallbacks."""
    order = {
        "groq":   [(GROQ_API_KEY, GroqGenerator, "Groq"),
                   (GOOGLE_API_KEY, GeminiGenerator, "Gemini"),
                   (ANTHROPIC_API_KEY, ClaudeGenerator, "Claude")],
        "gemini": [(GOOGLE_API_KEY, GeminiGenerator, "Gemini"),
                   (GROQ_API_KEY, GroqGenerator, "Groq"),
                   (ANTHROPIC_API_KEY, ClaudeGenerator, "Claude")],
        "claude": [(ANTHROPIC_API_KEY, ClaudeGenerator, "Claude"),
                   (GROQ_API_KEY, GroqGenerator, "Groq"),
                   (GOOGLE_API_KEY, GeminiGenerator, "Gemini")],
        "auto":   [(GROQ_API_KEY, GroqGenerator, "Groq"),
                   (GOOGLE_API_KEY, GeminiGenerator, "Gemini"),
                   (ANTHROPIC_API_KEY, ClaudeGenerator, "Claude")],
    }
    candidates = []
    for key, cls, name in order.get(primary, order["auto"]):
        if key:
            g = _try(cls, name)
            if g:
                candidates.append(g)
    return candidates


@lru_cache(maxsize=1)
def get_generator():
    """Returns a FallbackGenerator that tries providers in order at runtime."""
    provider = LLM_PROVIDER.lower()
    print(f"[LLM] Provider={provider!r} | GROQ={bool(GROQ_API_KEY)} | GOOGLE={bool(GOOGLE_API_KEY)} | ANTHROPIC={bool(ANTHROPIC_API_KEY)}")

    candidates = _build_chain(provider)

    if not candidates:
        print("[LLM] No API keys found — running in echo mode")
        return EchoGenerator()

    if len(candidates) == 1:
        return candidates[0]

    return FallbackGenerator(candidates)
