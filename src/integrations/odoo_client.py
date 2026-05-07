"""Odoo CRM integration — logs every query as a CRM lead + message thread."""
from __future__ import annotations
import xmlrpc.client
from functools import lru_cache
from typing import Any

from config.settings import ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS


class OdooClient:
    def __init__(self):
        if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS]):
            raise ValueError("Odoo credentials not configured.")
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
        self._uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
        if not self._uid:
            raise ValueError("Odoo authentication failed — check credentials.")
        self._models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
        print(f"[Odoo] Connected as uid={self._uid}")

    def _exec(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        return self._models.execute_kw(
            ODOO_DB, self._uid, ODOO_PASS, model, method, args, kwargs or {}
        )

    # ── Find or create a contact (res.partner) for a username ─────────────────

    def _get_or_create_partner(self, username: str) -> int:
        partners = self._exec("res.partner", "search_read",
                              [[["name", "=", username]]], {"fields": ["id"], "limit": 1})
        if partners:
            return partners[0]["id"]
        return self._exec("res.partner", "create", [{"name": username, "comment": "Legal AI user"}])

    # ── Log a query/answer conversation as a CRM lead ─────────────────────────

    def log_conversation(
        self,
        username: str,
        question: str,
        answer: str,
        sources: list[dict],
        chunks_retrieved: int,
        channel: str = "web",  # "web" | "email" | "voice"
    ) -> int:
        partner_id = self._get_or_create_partner(username)
        source_list = "\n".join(
            f"  • {s.get('source_file', '')} (score: {s.get('relevance_score', 0):.2f})"
            for s in sources[:5]
        )
        lead_id = self._exec("crm.lead", "create", [{
            "name": f"[{channel.upper()}] {question[:80]}",
            "partner_id": partner_id,
            "description": (
                f"<b>User:</b> {username}<br>"
                f"<b>Channel:</b> {channel}<br>"
                f"<b>Chunks retrieved:</b> {chunks_retrieved}<br><br>"
                f"<b>Question:</b><br>{question}<br><br>"
                f"<b>Answer:</b><br>{answer[:2000]}<br><br>"
                f"<b>Sources:</b><br>{source_list}"
            ),
            "tag_ids": [],
        }])
        return lead_id

    # ── Log a support ticket / bug report ─────────────────────────────────────

    def create_support_ticket(
        self,
        name: str,
        email: str,
        subject: str,
        description: str,
    ) -> int:
        partner_id = self._get_or_create_partner(name)
        # Try helpdesk first, fall back to CRM lead
        try:
            ticket_id = self._exec("helpdesk.ticket", "create", [{
                "name": subject,
                "partner_id": partner_id,
                "partner_email": email,
                "description": description,
            }])
            return ticket_id
        except Exception:
            return self._exec("crm.lead", "create", [{
                "name": f"[SUPPORT] {subject}",
                "partner_id": partner_id,
                "description": f"From: {email}\n\n{description}",
            }])


@lru_cache(maxsize=1)
def get_odoo_client() -> OdooClient | None:
    try:
        return OdooClient()
    except Exception as e:
        print(f"[Odoo] Not available: {e}")
        return None


def log_to_odoo(
    username: str,
    question: str,
    answer: str,
    sources: list[dict],
    chunks_retrieved: int,
    channel: str = "web",
) -> None:
    """Fire-and-forget Odoo logging — never crashes the main request."""
    try:
        client = get_odoo_client()
        if client:
            client.log_conversation(username, question, answer, sources, chunks_retrieved, channel)
    except Exception as e:
        print(f"[Odoo] Log failed (non-fatal): {e}")
