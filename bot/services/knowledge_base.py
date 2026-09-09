"""Compatibility facade for the V40 RAG knowledge base."""
from __future__ import annotations

from typing import Any

from bot.services import rag


def refresh_index() -> None:
    rag.refresh_index()


def search_knowledge(query: str, limit: int = 5) -> list[dict[str, str]]:
    return [
        {
            "source": str(item["source"]),
            "score": str(item["score"]),
            "snippet": str(item["text"]),
        }
        for item in rag.search(query, limit)
    ]


def format_knowledge_results(query: str, limit: int = 5) -> str:
    results = rag.search(query, limit)
    if not results:
        return "اطلاعات مرتبطی در پایگاه دانش داخلی پیدا نشد."
    lines = [f"📚 نتایج پایگاه دانش برای: {query}", ""]
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. {item['source']}#{item['chunk']} (score={item['score']})")
        lines.append(str(item["text"])[:900])
        lines.append("")
    return "\n".join(lines)[:5000]


def knowledge_stats() -> dict[str, int]:
    return rag.index_stats()
