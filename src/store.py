from __future__ import annotations

from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

import config
from src.documents import TextChunk


def _embedding_function(model_name: str | None = None) -> OllamaEmbeddingFunction:
    return OllamaEmbeddingFunction(
        url=config.OLLAMA_HOST,
        model_name=model_name or config.OLLAMA_EMBED_MODEL,
    )


def get_client() -> chromadb.PersistentClient:
    config.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_PATH))


def _read_stored_embed_model(client: chromadb.PersistentClient) -> str | None:
    try:
        collection = client.get_collection(config.COLLECTION_NAME)
        return (collection.metadata or {}).get("embed_model")
    except Exception:
        return None


def get_collection(
    *,
    reset: bool = False,
    embed_model: str | None = None,
) -> chromadb.Collection:
    client = get_client()

    if reset:
        try:
            client.delete_collection(config.COLLECTION_NAME)
        except ValueError:
            pass

    stored = None if reset else _read_stored_embed_model(client)
    if embed_model:
        model = embed_model
    elif stored:
        model = stored
    else:
        model = config.OLLAMA_EMBED_MODEL

    embed_fn = _embedding_function(model)
    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine", "embed_model": model},
    )

    if (
        embed_model
        and stored
        and stored != embed_model
        and collection.count() > 0
        and not reset
    ):
        raise ValueError(
            f"Knowledge base was built with embedding model '{stored}', "
            f"but '{embed_model}' is selected. Enable **Replace entire knowledge base** "
            f"and re-ingest, or switch back to '{stored}'."
        )

    return collection


def indexed_embed_model() -> str | None:
    try:
        return _read_stored_embed_model(get_client())
    except Exception:
        return None


def chunk_to_metadata(chunk: TextChunk) -> dict[str, Any]:
    return {
        "source_path": chunk.source_path,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "chunk_index": chunk.chunk_index,
    }


def upsert_chunks(collection: chromadb.Collection, chunks: list[TextChunk]) -> int:
    if not chunks:
        return 0

    batch_size = 64
    added = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[c.chunk_id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[chunk_to_metadata(c) for c in batch],
        )
        added += len(batch)
    return added


def collection_count(collection: chromadb.Collection) -> int:
    return collection.count()
