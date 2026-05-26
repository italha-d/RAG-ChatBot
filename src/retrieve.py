from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import config
from src.store import get_collection


@dataclass(frozen=True)
class RetrievedPassage:
    ref_id: int
    text: str
    source_path: str
    start_line: int
    end_line: int
    distance: float | None

    @property
    def source_name(self) -> str:
        return Path(self.source_path).name

    @property
    def location_label(self) -> str:
        if self.start_line == self.end_line:
            return f"{self.source_name}:L{self.start_line}"
        return f"{self.source_name}:L{self.start_line}-{self.end_line}"

    def format_for_prompt(self) -> str:
        header = f"[{self.ref_id}] {self.location_label}"
        divider = "-" * len(header)
        return f"{header}\n{divider}\n{self.text}"


def retrieve(query: str, top_k: int | None = None) -> list[RetrievedPassage]:
    k = top_k or config.TOP_K
    collection = get_collection()
    if collection.count() == 0:
        return []

    result = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0] or [None] * len(documents)

    passages: list[RetrievedPassage] = []
    for idx, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), start=1):
        if not doc or not meta:
            continue
        passages.append(
            RetrievedPassage(
                ref_id=idx,
                text=doc,
                source_path=str(meta.get("source_path", "unknown")),
                start_line=int(meta.get("start_line", 0)),
                end_line=int(meta.get("end_line", 0)),
                distance=float(dist) if dist is not None else None,
            )
        )
    return passages
