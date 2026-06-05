"""Central configuration + the CRMStore factory.

Everything that varies by environment lives here. The one knob that matters for
the "Airtable for feel / SQLite for reproducibility" decision is CRM_BACKEND.
"""

from __future__ import annotations

import functools
import os

from dotenv import load_dotenv

load_dotenv()


# --- CRM backend ------------------------------------------------------------
CRM_BACKEND = os.getenv("CRM_BACKEND", "sqlite").lower()  # "sqlite" | "airtable"
CRM_DB_PATH = os.getenv("CRM_DB_PATH", "data/crm.db")

# Airtable (only needed when CRM_BACKEND=airtable)
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")

# --- RAG --------------------------------------------------------------------
CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")
KB_COLLECTION = os.getenv("KB_COLLECTION", "kb_articles")  # Chroma requires len>=3

# --- LLM (Groq via ADK LiteLlm; provider-agnostic) --------------------------
# Tiered per the plan: cheap/fast model for triage/retrieval, strong for reasoning.
# LiteLlm reads the provider key (GROQ_API_KEY) from the environment automatically,
# so swapping providers is just a model-string change (e.g. "anthropic/..." with
# ANTHROPIC_API_KEY set instead).
MODEL_FAST = os.getenv("MODEL_FAST", "groq/llama-3.1-8b-instant")
MODEL_SMART = os.getenv("MODEL_SMART", "groq/llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- A2A --------------------------------------------------------------------
OUTREACH_A2A_URL = os.getenv("OUTREACH_A2A_URL", "http://localhost:8001")

# --- governance -------------------------------------------------------------
# Below this self-reported confidence, an agent must escalate to a human.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))


@functools.lru_cache(maxsize=1)
def get_store():
    """Return the configured CRMStore singleton (one-line backend swap)."""
    if CRM_BACKEND == "airtable":
        from .crm.airtable_store import AirtableStore

        return AirtableStore(AIRTABLE_API_KEY, AIRTABLE_BASE_ID)
    from .crm.sqlite_store import SqliteStore

    return SqliteStore(CRM_DB_PATH)
