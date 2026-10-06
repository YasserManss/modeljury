"""Convene a panel of models, count the votes, and flag decisions that need a human."""

from __future__ import annotations

import difflib
import json
import os
import re
import ssl
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Sequence

PROMPT = """You are one juror on a panel. Decide the question using only the evidence.

Question: {question}

Evidence:
{evidence}

Allowed options: {options}

Reply with only a JSON object:
{{"choice": "<one allowed option, exactly as written>", "confidence": <0.0-1.0>, "reason": "<one line>"}}"""


@dataclass
class Juror:
    """A model behind any OpenAI-compatible chat completions endpoint.

    base_url and api_key default to OPENAI_BASE_URL and OPENAI_API_KEY.
    params are passed straight to chat.completions.create (temperature,
    max_tokens, reasoning_effort, extra_body, ...) and override the panel's.
    Set a param to None to leave it out, e.g. {"temperature": None} for
    reasoning models that reject temperature.
    verify controls TLS certificate checks: True (default), False to skip them,
    or a path to a CA bundle for self-signed or internal certificates.
    """

    model: str
    base_url: str | None = None
    api_key: str | None = None
    name: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    verify: bool | str = True
    client: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.name = self.name or self.model

    def ask(self, prompt: str, timeout: float, params: dict[str, Any]) -> str:
        if self.client is None:
            import openai

            self.client = openai.OpenAI(
                base_url=self.base_url or os.environ.get("OPENAI_BASE_URL"),
                api_key=self.api_key or os.environ.get("OPENAI_API_KEY", "none"),
                **_http_client(openai, self.verify),
            )
        merged = {"temperature": 0, "timeout": timeout, **params, **self.params}
        resp = self.client.chat.completions.create(
            **{k: v for k, v in merged.items() if v is not None},
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""


def _http_client(sdk: Any, verify: bool | str) -> dict[str, Any]:
    """http_client kwarg for an SDK constructor; empty when verify is the default."""
    if verify is True:
        return {}
    if isinstance(verify, str):
        where = "capath" if os.path.isdir(verify) else "cafile"
        verify = ssl.create_default_context(**{where: verify})
    return {"http_client": sdk.DefaultHttpxClient(verify=verify)}


@dataclass
class Vote:
    juror: str
    choice: str | None
    confidence: float | None = None
    reason: str = ""
    error: str | None = None


@dataclass
class Result:
    verdict: str | None
    votes: list[Vote]
    agreement: float
    needs_review: bool

    @property
    def majority(self) -> bool:
        """True when the verdict won more than half of the whole panel, failed jurors included."""
        won = sum(v.choice == self.verdict for v in self.votes)
        return self.verdict is not None and won * 2 > len(self.votes)

    @property
    def dissent(self) -> list[tuple[str, str, str]]:
        return [
            (v.juror, v.choice, v.reason)
            for v in self.votes
            if v.choice is not None and v.choice != self.verdict
        ]

    @property
    def failed(self) -> list[Vote]:
        return [v for v in self.votes if v.choice is None]


def convene(
    question: str,
    evidence: str,
    options: Sequence[str],
    jurors: Sequence[Juror | str],
    timeout: float = 60.0,
    prompt: str = PROMPT,
    **params: Any,
) -> Result:
    """Poll every juror in parallel and return the verdict with the full record.

    needs_review is True unless every juror returned the same valid choice.

    timeout is the request timeout for each juror call. It bounds waiting for a
    reply, not the length of one: a juror that keeps emitting tokens is never
    idle, so the clock never runs out (measured at 1,915 s against a 300 s
    timeout). It also applies per attempt, and the SDKs retry failed calls
    twice. convene() waits for every juror and has no deadline of its own, so
    it returns when the slowest juror does. To bound how long a juror can take,
    and what it can cost, set max_tokens.

    prompt is a str.format template with {question}, {evidence} and {options};
    double any literal braces. Extra keyword arguments (temperature=0.3,
    max_tokens=200, ...) go to every juror's chat.completions.create call;
    a Juror's own params override them. temperature defaults to 0. Claude jurors
    (any "claude-..." string, or Claude(...)) skip panel kwargs; see Claude.
    """
    if len(options) < 2:
        raise ValueError("need at least two options")
    if not jurors:
        raise ValueError("need at least one juror")
    if len(jurors) == 1:
        warnings.warn(
            "a single juror can't dissent, so needs_review only catches failures; use 3 or more jurors",
            stacklevel=2,
        )

    panel = [j if isinstance(j, Juror) else _juror(j) for j in jurors]
    names = _unique_names(panel)
    text = prompt.format(
        question=question, evidence=evidence, options=json.dumps(list(options))
    )

    with ThreadPoolExecutor(max_workers=len(panel)) as pool:
        votes = list(
            pool.map(lambda j, n: _poll(j, n, text, options, timeout, params), panel, names)
        )

    return tally(votes)


def _juror(model: str) -> Juror:
    if model.startswith("claude-"):
        from .claude import Claude

        return Claude(model)
    return Juror(model)


def _unique_names(panel: list[Juror]) -> list[str]:
    """Juror names, with #2, #3, ... added to repeats so votes stay attributable."""
    seen: Counter[str] = Counter()
    names = []
    for j in panel:
        seen[j.name] += 1
        names.append(j.name if seen[j.name] == 1 else f"{j.name}#{seen[j.name]}")
    return names


def tally(votes: list[Vote]) -> Result:
    counts = Counter(v.choice for v in votes if v.choice is not None)
    if not counts:
        return Result(verdict=None, votes=votes, agreement=0.0, needs_review=True)

    ranked = counts.most_common()
    top_choice, top_count = ranked[0]
    hung = len(ranked) > 1 and ranked[1][1] == top_count
    agreement = top_count / sum(counts.values())
    failed = any(v.choice is None for v in votes)

    return Result(
        verdict=None if hung else top_choice,
        votes=votes,
        agreement=agreement,
        needs_review=hung or failed or agreement < 1.0,
    )


def _poll(
    juror: Juror,
    name: str,
    prompt: str,
    options: Sequence[str],
    timeout: float,
    params: dict[str, Any],
) -> Vote:
    try:
        raw = juror.ask(prompt, timeout, params)
    except Exception as e:  # one bad juror must not sink the panel
        error = f"{type(e).__name__}: {e}{_model_hint(juror, e)}"
        return Vote(juror=name, choice=None, error=error)
    return parse_vote(name, raw, options)


def _model_hint(juror: Juror, e: Exception) -> str:
    """On a model-not-found error, list the endpoint's models. Best effort; "" if unknown."""
    status = getattr(e, "status_code", None)
    if status != 404 and not (status == 400 and "model" in str(e).lower()):
        return ""
    try:
        ids = sorted(m.id for m in juror.client.models.list(timeout=10))
    except Exception:
        return ""
    if not ids or juror.model in ids:
        return ""
    close = difflib.get_close_matches(juror.model, ids, n=3, cutoff=0.3)
    if len(ids) <= 20:
        return f"; available models: {', '.join(ids)}"
    hint = f"; did you mean {', '.join(close)}?" if close else ""
    return f"{hint} ({len(ids)} models available)"


def _last_json_object(raw: str) -> dict | None:
    """The last JSON object in raw, skipping prose, code fences and <think> blocks."""
    decoder = json.JSONDecoder()
    found, i = None, raw.find("{")
    while i != -1:
        try:
            found, end = decoder.raw_decode(raw, i)
        except json.JSONDecodeError:
            end = i + 1
        i = raw.find("{", end)
    return found


def _salvage_fields(raw: str) -> dict:
    """Read the fields from JSON-like replies that don't parse, e.g. an unquoted reason.

    Small models often get the choice right and break the JSON afterwards.
    """
    choices = re.findall(r'"choice"\s*:\s*"([^"]*)"', raw)
    if not choices:
        return {}
    data = {"choice": choices[-1]}
    if m := re.findall(r'"confidence"\s*:\s*([0-9.]+)', raw):
        data["confidence"] = m[-1]
    if m := re.findall(r'"reason"\s*:\s*"?(.*?)"?\s*}?\s*$', raw, re.DOTALL):
        data["reason"] = m[-1]
    return data


def parse_vote(juror: str, raw: str, options: Sequence[str]) -> Vote:
    data = _last_json_object(raw)
    if not isinstance(data, dict):
        data = _salvage_fields(raw)
    if not data:
        return Vote(juror=juror, choice=None, error=f"unparseable reply: {raw[:200]!r}")

    choice = str(data.get("choice", "")).strip()
    by_lower = {o.lower(): o for o in options}
    if choice.lower() not in by_lower:
        return Vote(juror=juror, choice=None, error=f"choice not in options: {choice!r}")

    try:
        confidence = float(data["confidence"])
    except (KeyError, TypeError, ValueError):
        confidence = None

    return Vote(
        juror=juror,
        choice=by_lower[choice.lower()],
        confidence=confidence,
        reason=str(data.get("reason", "")).strip(),
    )
