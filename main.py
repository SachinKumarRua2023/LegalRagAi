"""
main.py — Interactive Legal AI Agent entry point.

Usage:
    python main.py                      # Interactive REPL
    python main.py --query "What is..."  # Single query
    python main.py --query "..." --file case.pdf   # Query in specific file
    python main.py --query "..." --folder ./data/raw/criminal
    python main.py --status             # Index status
"""
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="CompleteRagAI — Legal AI Research Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--query", "-q", type=str, help="Run a single query and exit")
    parser.add_argument("--file", "-f", type=str, help="Restrict search to this file name")
    parser.add_argument("--folder", type=str, help="Restrict search to this folder path")
    parser.add_argument("--type", type=str, help="Filter by file type (pdf, docx, etc.)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    parser.add_argument("--status", action="store_true", help="Show index status and exit")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    args = parser.parse_args()

    if args.no_color:
        import os
        os.environ["NO_COLOR"] = "1"

    if args.status:
        from src.vector_db.indexer import get_index_status
        status = get_index_status()
        console.print_json(data=status)
        return

    if args.query:
        # Single-shot query mode
        from src.rag.pipeline import query, format_response
        result = query(
            question=args.query,
            n_results=args.top_k,
            filter_file=args.file,
            filter_folder=args.folder,
            filter_file_type=getattr(args, "type", None),
            verbose=True,
        )
        console.print(format_response(result))
        return

    # Interactive REPL mode
    from src.agents.legal_agent import LegalAgent
    agent = LegalAgent()
    agent.run_interactive()


if __name__ == "__main__":
    main()
