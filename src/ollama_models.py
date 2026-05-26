from __future__ import annotations

import time
from dataclasses import dataclass

import ollama

import config

_CACHE_TTL_SECONDS = 30
_cache: dict[str, tuple[float, list[str], list[str]]] = {}


@dataclass(frozen=True)
class ModelLists:
    all_models: list[str]
    embedding_models: list[str]
    chat_models: list[str]
    error: str | None = None


def _model_capabilities(name: str) -> list[str]:
    try:
        info = ollama.show(name)
        caps = getattr(info, "capabilities", None) or []
        return list(caps)
    except Exception:
        return []


def _classify_by_name(name: str) -> str | None:
    lower = name.lower()
    if "embed" in lower:
        return "embedding"
    if any(x in lower for x in ("vision", "vl", "mmproj")):
        return "vision"
    return None


def _is_embedding_model(name: str, caps: list[str]) -> bool:
    if "embedding" in caps:
        return True
    if "completion" in caps or "chat" in caps or "tools" in caps:
        return False
    guess = _classify_by_name(name)
    return guess == "embedding"


def _is_chat_model(name: str, caps: list[str]) -> bool:
    if "embedding" in caps and "completion" not in caps and "chat" not in caps:
        return False
    if "completion" in caps or "chat" in caps or "tools" in caps:
        return True
    guess = _classify_by_name(name)
    if guess == "embedding":
        return False
    if guess == "vision":
        return True
    return "embed" not in name.lower()


def list_models(*, refresh: bool = False) -> ModelLists:
    cache_key = config.OLLAMA_HOST
    now = time.time()
    if not refresh and cache_key in _cache:
        ts, embed, chat = _cache[cache_key]
        if now - ts < _CACHE_TTL_SECONDS:
            all_names = sorted(set(embed) | set(chat))
            return ModelLists(all_models=all_names, embedding_models=embed, chat_models=chat)

    try:
        response = ollama.list()
    except Exception as exc:
        return ModelLists(
            all_models=[],
            embedding_models=[],
            chat_models=[],
            error=f"Cannot reach Ollama: {exc}",
        )

    names = sorted({m.model for m in response.models if m.model})
    embedding: list[str] = []
    chat: list[str] = []

    for name in names:
        caps = _model_capabilities(name)
        if _is_embedding_model(name, caps):
            embedding.append(name)
        if _is_chat_model(name, caps):
            chat.append(name)

    if not embedding and config.OLLAMA_EMBED_MODEL not in embedding:
        for name in names:
            if config.OLLAMA_EMBED_MODEL.split(":")[0] in name and name not in embedding:
                embedding.append(name)

    if not chat:
        for name in names:
            if name not in embedding:
                chat.append(name)

    _cache[cache_key] = (now, embedding, chat)
    return ModelLists(
        all_models=names,
        embedding_models=embedding,
        chat_models=chat,
    )


def default_embed_choice(lists: ModelLists) -> str | None:
    if not lists.embedding_models:
        return None
    target = config.OLLAMA_EMBED_MODEL
    for name in lists.embedding_models:
        if name == target or name.startswith(target.split(":")[0]):
            return name
    return lists.embedding_models[0]


def default_chat_choice(lists: ModelLists) -> str | None:
    if not lists.chat_models:
        return None
    target = config.OLLAMA_CHAT_MODEL
    for name in lists.chat_models:
        if name == target or name.startswith(target.split(":")[0]):
            return name
    return lists.chat_models[0]
