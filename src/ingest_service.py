from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import config
from src.documents import load_chunks_from_path
from src.store import collection_count, get_collection, upsert_chunks


@dataclass
class IngestResult:
    files_indexed: int = 0
    chunks_added: int = 0
    total_chunks: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.chunks_added > 0

    def summary(self) -> str:
        if self.chunks_added:
            return (
                f"Indexed **{self.files_indexed}** file(s), "
                f"**{self.chunks_added}** new chunk(s). "
                f"Knowledge base total: **{self.total_chunks}** chunks."
            )
        if self.skipped:
            return "No text could be extracted from the uploaded file(s)."
        return "No files were provided."


def accepted_upload_suffixes() -> set[str]:
    return config.TEXT_EXTENSIONS | config.OFFICE_EXTENSIONS


def ingest_paths(
    paths: list[Path],
    *,
    reset: bool = False,
    embed_model: str | None = None,
) -> IngestResult:
    result = IngestResult()
    collection = get_collection(reset=reset, embed_model=embed_model)

    for path in paths:
        path = path.resolve()
        if not path.is_file():
            result.skipped.append(f"{path.name} (not a file)")
            continue

        chunks = load_chunks_from_path(path, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        if not chunks:
            result.skipped.append(path.name)
            continue

        upsert_chunks(collection, chunks)
        result.files_indexed += 1
        result.chunks_added += len(chunks)

    result.total_chunks = collection_count(collection)
    return result


def persist_upload(temp_path: str | Path) -> Path | None:
    """Copy an uploaded temp file into the permanent uploads folder."""
    src = Path(temp_path)
    if not src.is_file():
        return None

    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.UPLOADS_DIR / src.name
    if dest.exists():
        dest = config.UPLOADS_DIR / f"{src.stem}_{uuid4().hex[:8]}{src.suffix}"

    shutil.copy2(src, dest)
    return dest


def ingest_uploads(
    file_paths: list[str | Path],
    *,
    reset: bool = False,
    embed_model: str | None = None,
) -> IngestResult:
    saved: list[Path] = []
    result = IngestResult()

    for raw in file_paths or []:
        if not raw:
            continue
        dest = persist_upload(raw)
        if dest:
            saved.append(dest)

    if not saved:
        result.total_chunks = collection_count(get_collection())
        return result

    inner = ingest_paths(saved, reset=reset, embed_model=embed_model)
    result.files_indexed = inner.files_indexed
    result.chunks_added = inner.chunks_added
    result.total_chunks = inner.total_chunks
    result.skipped = inner.skipped
    return result


def clear_knowledge_base(*, delete_uploads: bool = False) -> int:
    collection = get_collection(reset=True)
    if delete_uploads and config.UPLOADS_DIR.exists():
        shutil.rmtree(config.UPLOADS_DIR)
        config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return collection_count(collection)
