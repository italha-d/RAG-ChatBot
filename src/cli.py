from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

import config
from src.agent import ask
from src.documents import load_chunks_from_root
from src.ingest_service import ingest_paths
from src.store import collection_count, get_collection

console = Console()


def cmd_ingest(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not root.exists():
        console.print(f"[red]Path not found:[/red] {root}")
        return 1

    console.print(f"[cyan]Loading text from[/cyan] {root}")
    if root.is_file():
        paths = [root]
        console.print(f"[cyan]Indexing file[/cyan] {root}")
    else:
        from src.documents import iter_document_paths

        paths = iter_document_paths(root)
        console.print(f"[cyan]Scanning[/cyan] {root} ({len(paths)} file(s))")

    result = ingest_paths(paths, reset=args.reset)
    if not result.ok:
        console.print("[yellow]No readable text could be indexed.[/yellow]")
        if result.skipped:
            console.print("Skipped: " + ", ".join(result.skipped[:20]))
        return 1

    console.print(
        Panel(
            f"Indexed {result.files_indexed} file(s), {result.chunks_added} chunk(s).\n"
            f"Collection total: {result.total_chunks}\n"
            f"Store: {config.CHROMA_PATH}",
            title="Ingest complete",
            border_style="green",
        )
    )
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    result = ask(
        args.query,
        top_k=args.top_k,
        include_sources=not args.no_sources,
        model=args.model,
    )

    if result.get("warnings"):
        for warning in result["warnings"]:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

    console.print()
    console.print(Markdown(result["answer"]))

    if args.show_passages and result.get("passages"):
        table = Table(title="Retrieved passages", show_lines=True)
        table.add_column("Ref", style="cyan", width=4)
        table.add_column("Location")
        table.add_column("Preview", max_width=60)

        for p in result["passages"]:
            preview = p.text.replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:117] + "..."
            dist = f"{p.distance:.4f}" if p.distance is not None else "n/a"
            table.add_row(str(p.ref_id), f"{p.location_label} (d={dist})", preview)

        console.print()
        console.print(table)

    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from src.app import launch

    console.print(
        Panel(
            f"Starting chatbot at http://{args.host or config.APP_HOST}:{args.port or config.APP_PORT}\n"
            "Press Ctrl+C to stop.",
            title="Web UI",
            border_style="cyan",
        )
    )
    launch(host=args.host, port=args.port, share=args.share)
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    try:
        collection = get_collection()
        count = collection_count(collection)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Could not open index:[/red] {exc}")
        return 1

    console.print(
        Panel(
            f"Ollama host: {config.OLLAMA_HOST}\n"
            f"Embed model: {config.OLLAMA_EMBED_MODEL}\n"
            f"Chat model: {config.OLLAMA_CHAT_MODEL}\n"
            f"Index path: {config.CHROMA_PATH}\n"
            f"Chunks indexed: {count}",
            title="RAG Agent status",
        )
    )
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    console.print(
        Panel(
            "Offline RAG chat. Type a question, or 'exit' / 'quit' to leave.",
            title="RAG Agent",
        )
    )
    while True:
        try:
            query = console.input("\n[bold cyan]You>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye.")
            return 0

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            console.print("Bye.")
            return 0

        result = ask(
            query,
            top_k=args.top_k,
            include_sources=not args.no_sources,
            model=args.model,
        )
        for warning in result.get("warnings", []):
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        console.print()
        console.print(Markdown(result["answer"]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline Ollama RAG agent with inline citations and verbatim quotes.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Index text files from a file or directory")
    ingest.add_argument("path", help="File or folder to ingest")
    ingest.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before ingesting",
    )
    ingest.set_defaults(func=cmd_ingest)

    ask_p = sub.add_parser("ask", help="Ask one question against the index")
    ask_p.add_argument("query", help="Your question")
    ask_p.add_argument("--top-k", type=int, default=None, help="Number of chunks to retrieve")
    ask_p.add_argument("--model", default=None, help="Ollama chat model override")
    ask_p.add_argument(
        "--no-sources",
        action="store_true",
        help="Omit verbatim source appendix after the answer",
    )
    ask_p.add_argument(
        "--show-passages",
        action="store_true",
        help="Print retrieved passage table",
    )
    ask_p.set_defaults(func=cmd_ask)

    chat_p = sub.add_parser("chat", help="Interactive Q&A session")
    chat_p.add_argument("--top-k", type=int, default=None)
    chat_p.add_argument("--model", default=None)
    chat_p.add_argument("--no-sources", action="store_true")
    chat_p.set_defaults(func=cmd_chat)

    status_p = sub.add_parser("status", help="Show index and model configuration")
    status_p.set_defaults(func=cmd_status)

    serve_p = sub.add_parser("serve", help="Launch local web chatbot (drag-and-drop UI)")
    serve_p.add_argument("--host", default=None, help="Bind host (default: 127.0.0.1)")
    serve_p.add_argument("--port", type=int, default=None, help="Port (default: 7860)")
    serve_p.add_argument("--share", action="store_true", help="Create a public Gradio link")
    serve_p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
