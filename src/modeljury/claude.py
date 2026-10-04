"""Claude jurors through the native Anthropic Messages API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .jury import Juror


@dataclass
class Claude(Juror):
    """A Claude model, e.g. Claude("claude-opus-5-5").

    Credentials come from ANTHROPIC_API_KEY or an `ant auth login` profile
    unless api_key is given. Panel-wide kwargs are OpenAI parameters, so they
    are not sent here; put Messages API options in params instead, e.g.
    params={"output_config": {"effort": "low"}}. Requires modeljury[claude].
    """

    def ask(self, prompt: str, timeout: float, params: dict[str, Any]) -> str:
        if self.client is None:
            from anthropic import Anthropic

            kwargs = {"api_key": self.api_key, "base_url": self.base_url}
            self.client = Anthropic(**{k: v for k, v in kwargs.items() if v is not None})
        merged = {"max_tokens": 16000, "timeout": timeout, **self.params}
        resp = self.client.messages.create(
            **{k: v for k, v in merged.items() if v is not None},
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError(f"refused: {getattr(resp.stop_details, 'category', None)}")
        return "".join(b.text for b in resp.content if b.type == "text")
