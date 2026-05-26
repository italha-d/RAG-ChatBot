from __future__ import annotations

import re

import ollama

import config
from src.retrieve import RetrievedPassage, retrieve

SYSTEM_PROMPT = """You are a precise offline research assistant. You answer ONLY using the numbered source passages provided.

Rules (strict):
1. Every factual claim must include an inline citation like [1], [2], or [1][3] immediately after the claim.
2. Do NOT include quoted text, source sentences, or passages in the answer body — only the citation number in square brackets.
   Good: The refund window is 30 days [1].
   Bad:  The refund window is 30 days [1] — "Returns are accepted within 30 days".
3. Do NOT paraphrase inside quotation marks. Quotes must be exact substrings of the passage text.
4. Do NOT invent facts, sources, or quotes. If the passages do not contain enough information, say so clearly.
5. Prefer short, direct answers. Quote only the minimum relevant sentence(s).
6. Do not list raw passages at the end; inline quotes in the answer are enough."""

USER_PROMPT_TEMPLATE = """Question:
{query}

Source passages (quote only from these):
{context}

Write your answer with inline [N] citations."""


def build_context(passages: list[RetrievedPassage]) -> str:
    return "\n\n".join(p.format_for_prompt() for p in passages)


def _extract_cited_refs(answer: str) -> list[int]:
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def _normalize_quotes(text: str) -> str:
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("«", '"')
        .replace("»", '"')
    )


def _add_quote(store: dict[int, list[str]], ref: int, quote: str) -> None:
    text = re.sub(r"\s+", " ", quote.strip())
    if not text or len(text) < 8:
        return
    existing = store.setdefault(ref, [])
    if text not in existing:
        existing.append(text)


def _extract_quotes_by_ref(answer: str) -> dict[int, list[str]]:
    """Pull quoted strings tied to each [N] citation in the answer."""
    text = _normalize_quotes(answer)
    by_ref: dict[int, list[str]] = {}

    patterns = [
        r"\[(\d+)\][^\n\"']{0,160}?\"([^\"]+)\"",
        r"\[(\d+)\][^\n\"']{0,160}?'([^']+)'",
        r"\"([^\"]+)\"[^\[]{0,80}\[(\d+)\]",
        r"'([^']+)'[^\[]{0,80}\[(\d+)\]",
        r"\[(\d+)\]\s*[-–:]\s*\"([^\"]+)\"",
        r"\[(\d+)\]\s*\(\s*\"([^\"]+)\"\s*\)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            groups = match.groups()
            if len(groups) != 2:
                continue
            if groups[0].isdigit():
                ref_str, quote = groups
            else:
                quote, ref_str = groups
            _add_quote(by_ref, int(ref_str), quote)

    return by_ref


def _split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block or block.startswith("--- Page"):
            continue
        parts = re.split(r"(?<=[.!?])\s+", block)
        for part in parts:
            part = part.strip()
            if len(part) >= 12:
                sentences.append(part)
    return sentences


def _token_set(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\b[a-z0-9]{3,}\b", text.lower())}


def _overlap_score(left: str, right: str) -> float:
    a, b = _token_set(left), _token_set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _context_near_citation(answer: str, ref: int) -> str:
    pattern = rf"\[{ref}\]"
    for match in re.finditer(pattern, answer):
        start = max(0, answer.rfind("\n", 0, match.start()) + 1)
        end_match = re.search(r"\n\n", answer[match.end() :])
        end = match.end() + (end_match.start() if end_match else len(answer) - match.end())
        end = min(len(answer), match.end() + 280)
        start = max(0, match.start() - 180)
        return answer[start:end]
    return answer


def _relevant_sentences_from_passage(
    passage: RetrievedPassage,
    answer: str,
    query: str,
    *,
    max_sentences: int = 2,
) -> list[str]:
    """Pick sentence(s) from the passage that best match the answer near [N]."""
    sentences = _split_sentences(passage.text)
    if not sentences:
        snippet = passage.text.strip()
        return [snippet[:300]] if snippet else []

    context = _context_near_citation(answer, passage.ref_id)
    scored: list[tuple[float, str]] = []
    for sentence in sentences:
        score = (
            _overlap_score(sentence, context) * 3.0
            + _overlap_score(sentence, query) * 1.5
            + _overlap_score(sentence, answer) * 0.5
        )
        scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)
    chosen: list[str] = []
    for score, sentence in scored:
        if len(chosen) >= max_sentences:
            break
        if score < 0.03 and chosen:
            continue
        if sentence not in chosen:
            chosen.append(sentence)

    if not chosen and sentences:
        chosen = [sentences[0]]
    return chosen[:max_sentences]


def _find_verbatim_quote(quote: str, passage_text: str) -> bool:
    normalized_quote = re.sub(r"\s+", " ", quote.strip())
    if not normalized_quote:
        return False
    normalized_passage = re.sub(r"\s+", " ", passage_text)
    return normalized_quote in normalized_passage or quote.strip() in passage_text


def _quotes_for_citation(
    ref: int,
    answer: str,
    passage: RetrievedPassage,
    query: str,
    quotes_by_ref: dict[int, list[str]],
) -> tuple[list[str], bool]:
    """
    Return (quotes, from_inline).
    from_inline True if taken from answer; False if inferred from passage.
    """
    inline = list(quotes_by_ref.get(ref, []))
    verified = [q for q in inline if _find_verbatim_quote(q, passage.text)]
    if verified:
        return verified, True

    inferred = _relevant_sentences_from_passage(passage, answer, query)
    return inferred, False


def format_source_appendix(
    answer: str,
    passages: list[RetrievedPassage],
    query: str = "",
) -> str:
    """Append verbatim quotes or the most relevant source sentence(s) per [N]."""
    cited = _extract_cited_refs(answer)
    quotes_by_ref = _extract_quotes_by_ref(answer)
    if not cited:
        return answer

    by_ref = {p.ref_id: p for p in passages}
    lines = [answer.rstrip(), "", "---", "", "## Quoted sources", ""]

    for ref in cited:
        passage = by_ref.get(ref)
        if not passage:
            lines.append(f"**[{ref}]** — (citation not found in retrieved passages)")
            lines.append("")
            continue

        quotes, from_inline = _quotes_for_citation(
            ref, answer, passage, query, quotes_by_ref
        )

        lines.append(f"**[{ref}]** `{passage.location_label}`")
        lines.append("")
        if quotes:
            note = "" if from_inline else " *(from source)*"
            for quote in quotes:
                lines.append(f"> \"{quote}\"{note}")
        else:
            lines.append("> *(Could not locate a matching sentence in the source.)*")
        lines.append("")

    return "\n".join(lines).rstrip()


def validate_quotes_in_answer(
    answer: str,
    passages: list[RetrievedPassage],
) -> list[str]:
    """Return warnings when quoted strings in the answer are not verbatim in cited passages."""
    warnings: list[str] = []
    by_ref = {p.ref_id: p for p in passages}

    for ref, quotes in _extract_quotes_by_ref(answer).items():
        passage = by_ref.get(ref)
        if passage is None:
            warnings.append(f"[{ref}] cited but not in retrieved passages.")
            continue
        for quote in quotes:
            if not _find_verbatim_quote(quote, passage.text):
                warnings.append(
                    f'Quote under [{ref}] is not verbatim in source: "{quote[:80]}..."'
                )
    return warnings


def ask(
    query: str,
    *,
    top_k: int | None = None,
    include_sources: bool = True,
    model: str | None = None,
) -> dict:
    passages = retrieve(query, top_k=top_k)
    if not passages:
        return {
            "answer": (
                "No documents are indexed yet. "
                "Upload files in the sidebar and click **Add to knowledge base**, "
                "or run `python -m src ingest <folder>` from the terminal."
            ),
            "passages": [],
            "warnings": [],
        }

    context = build_context(passages)
    user_prompt = USER_PROMPT_TEMPLATE.format(query=query, context=context)
    chat_model = model or config.OLLAMA_CHAT_MODEL

    response = ollama.chat(
        model=chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.1},
    )

    answer = response["message"]["content"].strip()
    warnings = validate_quotes_in_answer(answer, passages)

    if include_sources:
        answer = format_source_appendix(answer, passages, query=query)

    return {
        "answer": answer,
        "passages": passages,
        "warnings": warnings,
        "model": chat_model,
    }
