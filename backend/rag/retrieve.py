"""Retrieval + grounded answering — the read side of the RAG core.

retrieve()  : query → top-k KB chunks with sources (no LLM, no key).
answer()    : retrieve → synthesize a cited answer that refuses when unsupported
              (needs an Anthropic key; provider-agnostic via litellm).

The M2 deflection agent reuses retrieve() as a tool and adds confidence-based
escalation on top.
"""

from __future__ import annotations

from dataclasses import dataclass

import litellm

from .. import config
from .ingest import get_collection


@dataclass
class Chunk:
    text: str
    article_id: str
    title: str
    score: float  # 1 - cosine distance; higher = more relevant


def retrieve(query: str, k: int = 4) -> list[Chunk]:
    """Top-k KB chunks for a query, most relevant first. Pure retrieval — no LLM."""
    res = get_collection().query(query_texts=[query], n_results=k)
    if not res["ids"] or not res["ids"][0]:
        return []
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    return [
        Chunk(
            text=doc,
            article_id=meta["article_id"],
            title=meta["title"],
            score=round(1 - dist, 3),
        )
        for doc, meta, dist in zip(docs, metas, dists)
    ]


_SYSTEM = (
    "You are a support knowledge assistant. Answer ONLY from the provided sources. "
    "Cite the article id in square brackets after each claim, e.g. [kb-003]. "
    "If the sources do not contain the answer, reply exactly: "
    "\"I don't have enough information to answer that.\" Do not use outside knowledge."
)


def _format_sources(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[{c.article_id}] {c.title}\n{c.text}" for c in chunks)


def answer(query: str, k: int = 4) -> dict:
    """Grounded, cited answer. Retrieval works without a key; synthesis needs Claude."""
    chunks = retrieve(query, k)
    sources = [
        {"article_id": c.article_id, "title": c.title, "score": c.score} for c in chunks
    ]
    if not chunks:
        return {
            "answer": "I don't have enough information to answer that.",
            "sources": [],
            "grounded": False,
        }

    resp = litellm.completion(
        model=config.MODEL_SMART,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": f"Sources:\n{_format_sources(chunks)}\n\nQuestion: {query}",
            },
        ],
        api_key=config.ANTHROPIC_API_KEY or None,
        temperature=0,
    )
    text = resp["choices"][0]["message"]["content"]
    return {
        "answer": text,
        "sources": sources,
        # crude grounding signal for M1; M2 replaces this with a verification pass
        "grounded": "[kb-" in text,
    }
