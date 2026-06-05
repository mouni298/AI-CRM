"""Thin helper to run a single-shot ADK agent and get a validated structured result.

ADK agents run inside a Runner with a session. For our agents each "run" is one
ticket/lead, so this wraps the boilerplate: spin up an InMemoryRunner, send the
prompt, collect the final response, and validate it against the agent's schema.
"""

from __future__ import annotations

import asyncio
import re
from typing import Type, TypeVar

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
_APP = "crm"
_MAX_RETRIES = 6


def _is_rate_limit(err: Exception) -> bool:
    s = str(err).lower()
    return "rate_limit" in s or "429" in s or "too many requests" in s


def _retry_after(err: Exception, fallback: float) -> float:
    """Honour the provider's 'try again in Xs' hint when present."""
    m = re.search(r"try again in ([0-9.]+)\s*s", str(err))
    return float(m.group(1)) + 0.3 if m else fallback


def _extract_json(text: str) -> str:
    """Be forgiving: strip code fences and grab the outermost {...} block."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else text


async def run_structured(
    agent: LlmAgent, prompt: str, schema: Type[T], *, session_id: str = "s"
) -> T:
    """Run `agent` on `prompt` once and return its output validated as `schema`.

    Retries with backoff on provider rate limits (429) — Groq's free tier has a
    low tokens-per-minute cap, so bursty agent runs need to back off and retry.
    """
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    for attempt in range(_MAX_RETRIES):
        runner = InMemoryRunner(agent=agent, app_name=_APP)
        # fresh session per attempt so a retry never collides with prior state
        await runner.session_service.create_session(
            app_name=_APP, user_id="u", session_id=f"{session_id}-{attempt}"
        )
        final_text = ""
        try:
            async for event in runner.run_async(
                user_id="u", session_id=f"{session_id}-{attempt}", new_message=message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = event.content.parts[0].text or ""
        except Exception as err:  # noqa: BLE001 — narrow to rate limits below
            if _is_rate_limit(err) and attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_retry_after(err, fallback=2.0 * (attempt + 1)))
                continue
            raise
        return schema.model_validate_json(_extract_json(final_text))

    raise RuntimeError("run_structured exhausted retries")  # pragma: no cover
