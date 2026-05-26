#!/usr/bin/env python3
"""
Generate docs/RAG_Agent_Team_Tutorial.pdf from docs/RAG_Agent_Team_Tutorial.md

Usage (from project root):
    python scripts/generate_tutorial_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from fpdf import FPDF

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MD_PATH = PROJECT_ROOT / "docs" / "RAG_Agent_Team_Tutorial.md"
PDF_PATH = PROJECT_ROOT / "docs" / "RAG_Agent_Team_Tutorial.pdf"

# Layout
MARGIN = 18
LINE_HEIGHT = 5.5
CODE_SIZE = 8
BODY_SIZE = 10
H1_SIZE = 18
H2_SIZE = 14
H3_SIZE = 12


def _sanitize(text: str) -> str:
    """Replace characters Helvetica cannot render."""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2192": "->",
        "\u2190": "<-",
        "\u2022": "-",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class TutorialPDF(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self._in_code = False

    def header(self) -> None:
        if self.page_no() <= 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5, "Local RAG Agent - Team Tutorial")
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_title_page(self) -> None:
        self.add_page()
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(30, 60, 90)
        self.ln(50)
        self.multi_cell(0, 14, "Local RAG Agent", align="C")
        self.ln(6)
        self.set_font("Helvetica", "", 16)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 10, "Team Tutorial Guide", align="C")
        self.ln(20)
        self.set_font("Helvetica", "", 12)
        self.multi_cell(
            0,
            8,
            _sanitize(
                "A beginner-friendly guide to RAG (Retrieval-Augmented Generation)\n"
                "and how to use this offline Ollama chatbot with your documents."
            ),
            align="C",
        )
        self.ln(30)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 6, f"Source: {MD_PATH.name}", align="C")
        self.set_text_color(0, 0, 0)

    def write_body(self, text: str, bold: bool = False) -> None:
        style = "B" if bold else ""
        self.set_font("Helvetica", style, BODY_SIZE)
        self.set_text_color(0, 0, 0)
        self.set_x(self.l_margin)
        self.multi_cell(0, LINE_HEIGHT, _sanitize(text))

    def write_h1(self, text: str) -> None:
        self.ln(4)
        self.set_font("Helvetica", "B", H1_SIZE)
        self.set_text_color(30, 60, 90)
        self.set_x(self.l_margin)
        self.multi_cell(0, 10, _sanitize(text))
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def write_h2(self, text: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", H2_SIZE)
        self.set_text_color(40, 80, 120)
        self.set_x(self.l_margin)
        self.multi_cell(0, 8, _sanitize(text))
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def write_h3(self, text: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", H3_SIZE)
        self.set_x(self.l_margin)
        self.multi_cell(0, 7, _sanitize(text))
        self.ln(1)

    def write_code_block(self, lines: list[str]) -> None:
        self.set_fill_color(245, 245, 245)
        self.set_font("Courier", "", CODE_SIZE)
        self.ln(2)
        usable = self.w - self.l_margin - self.r_margin - 4
        for line in lines:
            text = _sanitize(line)
            while text:
                chunk = text[:95]
                text = text[95:]
                self.set_x(self.l_margin + 2)
                self.multi_cell(usable, 4.5, "  " + chunk, fill=True)
        self.ln(2)
        self.set_font("Helvetica", "", BODY_SIZE)

    def write_bullet(self, text: str, level: int = 0) -> None:
        indent = "  " * level
        self.set_font("Helvetica", "", BODY_SIZE)
        self.set_x(self.l_margin)
        self.multi_cell(0, LINE_HEIGHT, _sanitize(f"{indent}- {text}"))

    def write_table_block(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        self.ln(2)
        self.set_font("Helvetica", "", 9)
        for row in rows:
            line = " | ".join(_sanitize(c) for c in row)
            self.set_x(self.l_margin)
            self.multi_cell(0, 5, line)
        self.ln(2)
        self.set_font("Helvetica", "", BODY_SIZE)


def parse_markdown(md_text: str) -> list[tuple[str, str | list[str]]]:
    """Parse markdown into (type, content) blocks."""
    blocks: list[tuple[str, str | list[str]]] = []
    lines = md_text.splitlines()
    i = 0
    code_buf: list[str] = []

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if code_buf:
                blocks.append(("code", code_buf))
                code_buf = []
            else:
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_buf.append(lines[i])
                    i += 1
                blocks.append(("code", code_buf))
                code_buf = []
            i += 1
            continue

        if line.startswith("# ") and not line.startswith("## "):
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("|") and "|" in line[1:]:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if cells and not all(set(c) <= {"-", ":"} for c in cells):
                blocks.append(("table", cells))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(("bullet", line[2:].strip()))
        elif re.match(r"^\d+\.\s", line):
            blocks.append(("bullet", re.sub(r"^\d+\.\s", "", line).strip()))
        elif line.strip() == "---":
            blocks.append(("hr", ""))
        elif line.strip():
            blocks.append(("body", line.strip()))
        i += 1

    return blocks


def strip_md_inline(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text)
    return text


def _is_table_separator(cells: list[str]) -> bool:
    return all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip())


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown not found: {md_path}")

    md_text = md_path.read_text(encoding="utf-8")
    blocks = parse_markdown(md_text)

    pdf = TutorialPDF()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_title_page()
    pdf.add_page()

    skip_until_toc_done = False
    skip_preamble = True
    table_buf: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table_buf
        if table_buf:
            pdf.write_table_block(table_buf)
            table_buf = []

    for kind, content in blocks:
        if kind == "table" and isinstance(content, list):
            cells = [strip_md_inline(c) for c in content]
            if _is_table_separator(cells):
                continue
            table_buf.append(cells)
            continue

        flush_table()

        if kind == "h1" and isinstance(content, str):
            title = strip_md_inline(content)
            if "Table of Contents" in title:
                skip_until_toc_done = True
                continue
            if "Team Tutorial Guide" in title:
                continue
            if skip_until_toc_done:
                continue
            pdf.add_page()
            pdf.write_h1(title)
        elif kind == "h2" and isinstance(content, str):
            title = strip_md_inline(content)
            if "Table of Contents" in title:
                skip_until_toc_done = True
                continue
            if skip_until_toc_done and re.match(r"^\d+\.", title):
                skip_until_toc_done = False
            if skip_until_toc_done:
                continue
            if skip_preamble:
                if re.match(r"^1\.", title):
                    skip_preamble = False
                else:
                    continue
            pdf.write_h2(title)
        elif kind == "h3" and isinstance(content, str):
            if skip_until_toc_done or skip_preamble:
                continue
            pdf.write_h3(strip_md_inline(content))
        elif kind == "body" and isinstance(content, str):
            if skip_until_toc_done or skip_preamble:
                continue
            pdf.write_body(strip_md_inline(content))
        elif kind == "bullet" and isinstance(content, str):
            if skip_until_toc_done or skip_preamble:
                continue
            pdf.write_bullet(strip_md_inline(content))
        elif kind == "code" and isinstance(content, list):
            pdf.write_code_block(content)

    flush_table()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(pdf_path))


def main() -> int:
    try:
        build_pdf(MD_PATH, PDF_PATH)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Generated: {PDF_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
