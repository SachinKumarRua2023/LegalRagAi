"""
Legal AI Agent — interprets natural language queries and dispatches to the right tool.
Supports: semantic search, file/folder scoped search, indexing, status checks.
"""
from __future__ import annotations
import re
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.agents.tools import TOOLS, TOOL_DESCRIPTIONS
from src.rag.pipeline import query, query_file, query_folder, format_response
from src.vector_db.indexer import get_index_status

console = Console()


class LegalAgent:
    """
    Conversational AI agent for US legal case research.

    Capabilities:
    - Semantic search across all indexed documents
    - File-scoped and folder-scoped queries
    - File type filtering (search in PDFs, DOCX, etc.)
    - Document indexing
    - Source citation for every answer
    """

    def __init__(self):
        self._history: list[dict] = []
        console.print(Panel(
            "[bold cyan]Legal RAG AI Agent[/bold cyan]\n"
            "US Legal Case Research System\n"
            "Type [bold]/help[/bold] for commands | [bold]/quit[/bold] to exit",
            border_style="cyan",
        ))

    # ── Intent detection ───────────────────────────────────────────────────────

    def _detect_intent(self, text: str) -> tuple[str, dict]:
        """Detect user intent from natural language."""
        text_lower = text.lower().strip()

        # Commands
        if text_lower in ("/help", "help", "?"):
            return "help", {}
        if text_lower in ("/quit", "quit", "exit", "bye"):
            return "quit", {}
        if text_lower in ("/status", "status", "index status", "show status"):
            return "status", {}
        if text_lower in ("/files", "list files", "show files", "what files"):
            return "list_files", {}
        if text_lower.startswith("/index "):
            path = text[7:].strip()
            return "index", {"path": path}
        if text_lower.startswith("/upload "):
            path = text[8:].strip()
            return "index", {"path": path}

        # File-scoped query: "in file X.pdf, what is..."
        m = re.search(r'(?:in file|from file|search file)\s+["\']?([^\s"\']+\.[a-z]+)["\']?\s*[:,]?\s*(.+)', text, re.I)
        if m:
            return "search_file", {"file": m.group(1), "question": m.group(2)}

        # Folder-scoped query: "in folder /data/raw, what is..."
        m = re.search(r'(?:in folder|from folder|search folder)\s+["\']?([^\s"\']+)["\']?\s*[:,]?\s*(.+)', text, re.I)
        if m:
            return "search_folder", {"folder": m.group(1), "question": m.group(2)}

        # File type filter: "search in PDFs about..."
        m = re.search(r'(?:search in|look in|only in)\s+(pdf|docx|doc|pptx|xlsx|csv|txt)s?\s+(?:about|for|regarding)?\s*(.+)', text, re.I)
        if m:
            return "search_type", {"file_type": m.group(1).lower(), "question": m.group(2)}

        # File reference: "tell me about the file X"
        m = re.search(r'(?:about the file|file named?|document named?)\s+["\']?([^\s"\']+\.[a-z]+)["\']?', text, re.I)
        if m:
            return "search_file", {"file": m.group(1), "question": text}

        # Default: general search
        return "search", {"question": text}

    # ── Response rendering ─────────────────────────────────────────────────────

    def _render_result(self, result: dict[str, Any]):
        """Render a RAG pipeline result to the console."""
        console.print()
        console.print(Markdown(result["answer"]))

        if result.get("sources"):
            table = Table(title="Sources", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=3)
            table.add_column("File", style="cyan")
            table.add_column("Location", style="green")
            table.add_column("Score", style="yellow", width=7)

            for i, src in enumerate(result["sources"], 1):
                folder = src.get("source_folder", "")
                # Shorten folder path for display
                if len(folder) > 50:
                    folder = "..." + folder[-47:]
                table.add_row(
                    str(i),
                    src.get("source_file", "—"),
                    folder,
                    str(src.get("relevance_score", "—")),
                )
            console.print(table)

    def _render_status(self):
        status = get_index_status()
        table = Table(title="Vector DB Index Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Collection", status.get("collection", ""))
        table.add_row("Total Chunks", str(status.get("total_chunks", 0)))
        table.add_row("Unique Files", str(status.get("unique_files", 0)))
        table.add_row("DB Path", status.get("db_path", ""))
        console.print(table)

        if status.get("files"):
            ftable = Table(title="Indexed Files")
            ftable.add_column("File", style="cyan")
            ftable.add_column("Type", style="yellow")
            ftable.add_column("Folder", style="green")
            for f in status["files"][:20]:
                ftable.add_row(
                    f.get("source_file", ""),
                    f.get("file_type", ""),
                    f.get("source_folder", "")[-60:] if f.get("source_folder") else "",
                )
            console.print(ftable)

    def _render_help(self):
        console.print(Panel(
            "[bold]Commands:[/bold]\n"
            "  /help              — Show this help\n"
            "  /status            — Show index statistics\n"
            "  /files             — List all indexed files\n"
            "  /index <path>      — Index a file or folder\n"
            "  /quit              — Exit\n\n"
            "[bold]Search Examples:[/bold]\n"
            "  What are the key facts in contract dispute cases?\n"
            "  In file doe_v_roe.pdf, what was the court's ruling?\n"
            "  In folder /data/raw, search for fourth amendment cases\n"
            "  Search in PDFs about criminal sentencing\n"
            "  What cases involve civil rights violations?",
            title="Help",
            border_style="green",
        ))

    # ── Main process loop ──────────────────────────────────────────────────────

    def process(self, user_input: str) -> str | None:
        """Process a single user input. Returns 'quit' to signal exit."""
        intent, params = self._detect_intent(user_input.strip())

        if intent == "quit":
            console.print("[yellow]Goodbye![/yellow]")
            return "quit"

        elif intent == "help":
            self._render_help()

        elif intent == "status":
            self._render_status()

        elif intent == "list_files":
            files = TOOLS["list_files"]()
            if not files:
                console.print("[yellow]No files indexed yet.[/yellow]")
            else:
                t = Table(title=f"Indexed Files ({len(files)})")
                t.add_column("File", style="cyan")
                t.add_column("Type", style="yellow")
                t.add_column("Path", style="green")
                for f in files:
                    t.add_row(f.get("source_file", ""), f.get("file_type", ""), f.get("source_path", ""))
                console.print(t)

        elif intent == "index":
            from pathlib import Path
            path = Path(params["path"])
            console.print(f"[cyan]Indexing: {path}[/cyan]")
            if path.is_file():
                result = TOOLS["index_file"](str(path))
            else:
                result = TOOLS["index_folder"](str(path))
            console.print(f"[green]Done: {result}[/green]")

        elif intent == "search":
            console.print(f"[dim]Searching: {params['question'][:80]}...[/dim]")
            result = query(params["question"])
            self._render_result(result)

        elif intent == "search_file":
            console.print(f"[dim]Searching in file '{params['file']}'...[/dim]")
            result = query_file(params["file"], params["question"])
            self._render_result(result)

        elif intent == "search_folder":
            console.print(f"[dim]Searching in folder '{params['folder']}'...[/dim]")
            result = query_folder(params["folder"], params["question"])
            self._render_result(result)

        elif intent == "search_type":
            console.print(f"[dim]Searching in {params['file_type'].upper()} files...[/dim]")
            result = query(params["question"], filter_file_type=params["file_type"])
            self._render_result(result)

        self._history.append({"input": user_input, "intent": intent})
        return None

    def run_interactive(self):
        """Run interactive REPL loop."""
        while True:
            try:
                user_input = console.input("\n[bold green]You:[/bold green] ").strip()
                if not user_input:
                    continue
                signal = self.process(user_input)
                if signal == "quit":
                    break
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")
            except EOFError:
                break
