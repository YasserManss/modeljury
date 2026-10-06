"""The setups being compared. Each one turns an item into a decision record.

A record holds: pred, needs_review (None if the setup can't flag), confidence,
latency_s, prompt_tokens, completion_tokens, error, and for panels the per-juror votes.

Setups that call paid APIs read their keys from environment variables and fail
with a clear message when one is missing.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from types import SimpleNamespace

from modeljury import Juror, convene
from modeljury.jury import PROMPT, parse_vote

LOCAL_URL = os.environ.get("LOCAL_BASE_URL", "http://localhost:8000/v1")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "Qwen3.8-27B-Abliterated")
OPENROUTER_URL = "https://openrouter.ai/api/v1"


class Recorder:
    """Wraps an OpenAI or Anthropic client and records latency and token usage per call."""

    def __init__(self, client):
        self._client = client
        self.calls: list[tuple[float, int, int]] = []
        if hasattr(client, "chat"):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._openai))
        if hasattr(client, "messages"):
            self.messages = SimpleNamespace(create=self._anthropic)
        self.models = client.models

    def _openai(self, **kwargs):
        start = time.perf_counter()
        resp = self._client.chat.completions.create(**kwargs)
        u = resp.usage  # occasionally missing from OpenRouter responses
        self.calls.append((time.perf_counter() - start, getattr(u, "prompt_tokens", 0),
                           getattr(u, "completion_tokens", 0)))
        return resp

    def _anthropic(self, **kwargs):
        start = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        u = resp.usage
        self.calls.append((time.perf_counter() - start, getattr(u, "input_tokens", 0),
                           getattr(u, "output_tokens", 0)))
        return resp


def _need(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise SystemExit(f"this setup needs the {var} environment variable")
    return value


def _openai_client(base_url: str, api_key: str):
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=api_key, max_retries=8)


class Panel:
    """A modeljury panel. Jurors are (model, params) pairs sharing one client."""

    def __init__(self, client, jurors: list[tuple[str, dict]]):
        self.client, self.jurors = client, jurors

    def decide(self, item: dict) -> dict:
        jurors = [Juror(m, client=Recorder(self.client), params=p) for m, p in self.jurors]
        r = convene(item["question"], item["evidence"], item["options"], jurors, timeout=300)
        votes = []
        for juror, vote in zip(jurors, r.votes):
            lat, pin, pout = juror.client.calls[-1] if juror.client.calls else (None, 0, 0)
            votes.append(dict(
                juror=vote.juror, choice=vote.choice, confidence=vote.confidence,
                latency_s=lat, prompt_tokens=pin, completion_tokens=pout, error=vote.error,
            ))
        latencies = [v["latency_s"] for v in votes if v["latency_s"] is not None]
        return dict(
            pred=r.verdict, needs_review=r.needs_review, majority=r.majority,
            confidence=r.agreement, latency_s=max(latencies) if latencies else None,
            prompt_tokens=sum(v["prompt_tokens"] for v in votes),
            completion_tokens=sum(v["completion_tokens"] for v in votes),
            votes=votes, error=None,
        )


class Single:
    """One model, one call, same prompt and parser as a modeljury juror."""

    def __init__(self, juror: Juror):
        self.juror = juror

    def decide(self, item: dict) -> dict:
        rec = Recorder(self.juror.client)
        j = type(self.juror)(self.juror.model, client=rec, params=self.juror.params)
        prompt = PROMPT.format(
            question=item["question"], evidence=item["evidence"],
            options=json.dumps(item["options"]),
        )
        try:
            raw = j.ask(prompt, 300, {})
        except Exception as e:
            return dict(pred=None, needs_review=None, confidence=None, latency_s=None,
                        prompt_tokens=0, completion_tokens=0, error=f"{type(e).__name__}: {e}")
        vote = parse_vote(j.model, raw, item["options"])
        lat, pin, pout = rec.calls[-1]
        return dict(pred=vote.choice, needs_review=None, confidence=vote.confidence,
                    latency_s=lat, prompt_tokens=pin, completion_tokens=pout, error=vote.error,
                    model=j.model)


def _choice_question(item: dict) -> dict:
    return {"answer": {
        "type": "choice", "instructions": item["question"],
        "criteria": {o: o for o in item["options"]},
    }}


def _from_choice_answer(answer: dict, latency: float, usage: dict, **extra) -> dict:
    probs = answer.get("probabilities") or {}
    return dict(
        pred=answer["choice"], needs_review=None, confidence=answer.get("confidence"),
        probability=max(probs.values()) if probs else None, latency_s=latency,
        prompt_tokens=usage.get("input_tokens", 0), completion_tokens=usage.get("output_tokens", 0),
        error=None, **extra,
    )


class Laya:
    """Laya, self-hosted. Calls are serialised so latency isn't skewed by contention."""

    def __init__(self):
        os.environ.setdefault("USE_TF", "0")
        from laya import Router

        self.router = Router(preload=True)
        self.lock = threading.Lock()

    def decide(self, item: dict) -> dict:
        with self.lock:
            start = time.perf_counter()
            # max_len 8192 so long items (JudgeBench) aren't cut off at the 512-token default
            out = self.router.predict(item["evidence"], _choice_question(item), max_len=8192)
            latency = time.perf_counter() - start
        usage = out.get("usage", {})
        return _from_choice_answer(
            out["answers"]["answer"], latency, usage, truncated=usage.get("truncated", False),
        )


class Jev:
    """TypeSafe Jev through the SystemOne API, either TypeSafe's own or OpenRouter's copy of it."""

    def __init__(self, url="https://api.typesafe.ai/v1/systemone", key_var="TYPESAFE_API_KEY",
                 model="jev-latest"):
        self.URL, self.key, self.model = url, _need(key_var), model

    def decide(self, item: dict) -> dict:
        body = json.dumps({
            "state": item["evidence"], "model": self.model, "questions": _choice_question(item),
        }).encode()
        for attempt in range(5):
            req = urllib.request.Request(self.URL, data=body, headers={
                "Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
            })
            start = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    out = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 529) and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                return dict(pred=None, needs_review=None, confidence=None, latency_s=None,
                            prompt_tokens=0, completion_tokens=0,
                            error=f"HTTP {e.code}: {e.read()[:200]!r}")
        latency = time.perf_counter() - start
        return _from_choice_answer(out["answers"]["answer"], latency, out.get("usage", {}))


def _local_panel():
    """Five copies of the local model. Juror 1 runs at temperature 0, so it doubles as the single-model baseline."""
    client = _openai_client(LOCAL_URL, "none")
    return Panel(client, [(LOCAL_MODEL, {"temperature": 0})] + [(LOCAL_MODEL, {"temperature": 1.0})] * 4)


# The fastest model from each of OpenAI, Google and Anthropic. GPT-6 Luna rejects temperature, so it's left out.
MIXED_PANEL = [
    ("openai/gpt-6-luna", {"temperature": None}),
    ("google/gemini-3.5-flash-lite", {"temperature": 0}),
    ("anthropic/claude-haiku-4.5", {"temperature": 0}),
]


def _mixed_panel():
    """Different model families via OpenRouter. PANEL_MODELS (comma-separated) overrides the default."""
    client = _openai_client(OPENROUTER_URL, _need("OPENROUTER_API_KEY"))
    if os.environ.get("PANEL_MODELS"):
        return Panel(client, [(m.strip(), {"temperature": 0}) for m in os.environ["PANEL_MODELS"].split(",")])
    return Panel(client, MIXED_PANEL)


FREE_PANEL = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "thinkingmachines/inkling-small:free",
]


def _free_panel():
    """Free OpenRouter models from three families. Rate-limited and queued, so only for checking the wiring."""
    client = _openai_client(OPENROUTER_URL, _need("OPENROUTER_API_KEY"))
    return Panel(client, [(m, {"temperature": 0}) for m in FREE_PANEL])


# Open-weight models from three companies, reasoning off so the panel stays fast.
NO_REASONING = {"temperature": 0, "extra_body": {"reasoning": {"enabled": False}}}
OPEN_PANEL = [
    ("qwen/qwen3.6-35b-a3b", NO_REASONING),
    ("google/gemma-4-26b-a4b-it", NO_REASONING),
    ("nvidia/nemotron-3.5-lightning", NO_REASONING),
]


def _open_panel():
    """Open-weight models via OpenRouter."""
    client = _openai_client(OPENROUTER_URL, _need("OPENROUTER_API_KEY"))
    return Panel(client, OPEN_PANEL)


# Five cheap models, one from each of five families, reasoning off so the panel stays fast.
OPENJURY = [
    ("deepseek/deepseek-v4.1-flash", NO_REASONING),
    # glm-5.3-flash rejects reasoning: {enabled: false}, so ask for the least of it instead
    ("z-ai/glm-5.3-flash", {"temperature": 0, "extra_body": {"reasoning": {"effort": "minimal"}}}),
    ("xiaomi/mimo-v2.6-flash", NO_REASONING),
    ("qwen/qwen3.8-flash", NO_REASONING),
    ("google/gemma-4-26b-a4b-it", NO_REASONING),
]


def _openjury():
    """Five cheap models from five companies, via OpenRouter."""
    client = _openai_client(OPENROUTER_URL, _need("OPENROUTER_API_KEY"))
    return Panel(client, OPENJURY)



def _large_claude():
    import anthropic

    from modeljury import Claude

    client = anthropic.Anthropic(api_key=_need("ANTHROPIC_API_KEY"))
    model = os.environ.get("LARGE_MODEL", "claude-opus-5-5")
    return Single(Claude(model, client=client, params={"max_tokens": 4096}))


def _large_opus():
    """Claude Opus 5.5 alone, via OpenRouter. It rejects temperature and always thinks."""
    client = _openai_client(OPENROUTER_URL, _need("OPENROUTER_API_KEY"))
    return Single(Juror("anthropic/claude-opus-5.5", client=client,
                        params={"temperature": None, "max_tokens": 16000}))


SETUPS = {
    "panel-local": _local_panel,
    "panel-mixed": _mixed_panel,
    "panel-free": _free_panel,
    "panel-open": _open_panel,
    "openjury": _openjury,
    "laya": Laya,
    "jev": Jev,
    "jev-openrouter": lambda: Jev(
        "https://openrouter.ai/api/v1/systemone", "OPENROUTER_API_KEY", "typesafe/jev-1.13"
    ),
    "large-claude": _large_claude,
    "large-opus": _large_opus,
}
