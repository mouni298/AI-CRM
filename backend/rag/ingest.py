"""KB ingestion — CRM knowledge base → chunks → embeddings → Chroma.

The deflection agent (M2) grounds its answers in whatever lands here. Embeddings
are local (Chroma's default MiniLM model) so ingestion needs no API key — only a
one-time model download on first run.

Idempotent: re-ingesting wipes and rebuilds the collection.
"""

from __future__ import annotations

import chromadb

from .. import config
from ..crm.base import CRMStore


def get_collection():
    """The persistent Chroma collection backing KB retrieval (local embeddings)."""
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    # Default embedding function = all-MiniLM-L6-v2, runs locally, no key needed.
    return client.get_or_create_collection(
        name=config.KB_COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def chunk_text(text: str, max_chars: int = 500, overlap: int = 60) -> list[str]:
    """Sentence-aware chunking: pack whole sentences up to max_chars, with a small
    overlap so a fact split across a boundary is still retrievable. KB articles are
    short, so most become a single chunk — the splitter matters for longer docs."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    chunks: list[str] = []
    buf = ""
    for sent in sentences:
        piece = sent if sent.endswith(".") else sent + "."
        if buf and len(buf) + 1 + len(piece) > max_chars:
            chunks.append(buf)
            buf = (buf[-overlap:] + " " + piece) if overlap else piece
        else:
            buf = f"{buf} {piece}".strip()
    if buf:
        chunks.append(buf)
    return chunks or [text]


def ingest_kb(store: CRMStore, reset: bool = True) -> int:
    """Load every KB article from the CRM, chunk + embed + store. Returns chunk count."""
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    if reset:
        try:
            client.delete_collection(config.KB_COLLECTION)
        except Exception:
            pass  # collection didn't exist yet
    collection = client.get_or_create_collection(
        name=config.KB_COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    ids, docs, metas = [], [], []
    for art in store.list_kb_articles():
        for i, chunk in enumerate(chunk_text(art.body)):
            ids.append(f"{art.id}::{i}")
            docs.append(chunk)
            metas.append(
                {
                    "article_id": art.id,
                    "title": art.title,
                    "chunk_index": i,
                    "tags": ",".join(art.tags),
                }
            )
    if ids:
        collection.add(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


if __name__ == "__main__":
    n = ingest_kb(config.get_store())
    print(f"Ingested {n} chunks into Chroma collection '{config.KB_COLLECTION}' "
          f"at {config.CHROMA_PATH}")
