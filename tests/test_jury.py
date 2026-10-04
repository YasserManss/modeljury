import json
from types import SimpleNamespace

from modeljury import Juror, convene
from modeljury.jury import parse_vote

OPTIONS = ["fraud", "legit"]


class FakeClient:
    """Stands in for openai.OpenAI; returns a canned reply or raises."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        content = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def juror(name, reply, **params):
    return Juror(model=name, client=FakeClient(reply), params=params)


def vote(choice, reason="because", confidence=0.9):
    return {"choice": choice, "confidence": confidence, "reason": reason}


def run(*jurors, **kw):
    return convene("Fraud?", "ticket", OPTIONS, list(jurors), **kw)


def test_unanimous_ships():
    r = run(juror("a", vote("legit")), juror("b", vote("legit")), juror("c", vote("legit")))
    assert r.verdict == "legit"
    assert not r.needs_review
    assert r.dissent == []


def test_any_dissent_triggers_review_by_default():
    r = run(juror("a", vote("legit")), juror("b", vote("fraud", "address changed")), juror("c", vote("legit")))
    assert r.verdict == "legit"
    assert r.needs_review
    assert r.dissent == [("b", "fraud", "address changed")]


def test_majority_is_the_looser_rule():
    r = run(juror("a", vote("legit")), juror("b", vote("fraud")), juror("c", vote("legit")))
    assert r.verdict == "legit"
    assert r.needs_review
    assert r.majority


def test_tie_is_hung_jury():
    r = run(juror("a", vote("legit")), juror("b", vote("fraud")))
    assert r.verdict is None
    assert r.needs_review


def test_failed_juror_is_recorded_and_triggers_review():
    r = run(juror("a", vote("legit")), juror("b", vote("legit")), juror("c", RuntimeError("timeout")))
    assert r.verdict == "legit"
    assert r.needs_review
    assert r.failed[0].juror == "c"
    assert "timeout" in r.failed[0].error


def test_all_fail():
    r = run(juror("a", RuntimeError("x")), juror("b", "not json"))
    assert r.verdict is None
    assert r.needs_review


def test_parse_tolerates_prose_and_case():
    v = parse_vote("a", 'Sure!\n```json\n{"choice": "LEGIT", "confidence": 0.7, "reason": "ok"}\n```', OPTIONS)
    assert v.choice == "legit"
    assert v.confidence == 0.7


def test_parse_rejects_unknown_choice():
    v = parse_vote("a", '{"choice": "maybe", "reason": "?"}', OPTIONS)
    assert v.choice is None
    assert "not in options" in v.error


def test_custom_prompt_is_formatted():
    j = juror("a", vote("legit"))
    convene("Fraud?", "ticket", OPTIONS, [j, juror("b", vote("legit"))], prompt="Q={question} E={evidence} O={options} {{json}}")
    assert j.client.calls[0]["messages"][0]["content"] == 'Q=Fraud? E=ticket O=["fraud", "legit"] {json}'


def test_temperature_defaults_to_zero():
    j = juror("a", vote("legit"))
    run(j, juror("b", vote("legit")))
    assert j.client.calls[0]["temperature"] == 0


def test_panel_params_reach_every_juror_and_juror_params_win():
    a = juror("a", vote("legit"))
    b = juror("b", vote("legit"), temperature=1.0, max_tokens=50)
    run(a, b, temperature=0.3, max_tokens=200, seed=7)
    assert {k: a.client.calls[0][k] for k in ("temperature", "max_tokens", "seed")} == {"temperature": 0.3, "max_tokens": 200, "seed": 7}
    assert {k: b.client.calls[0][k] for k in ("temperature", "max_tokens", "seed")} == {"temperature": 1.0, "max_tokens": 50, "seed": 7}


def test_none_drops_param():
    j = juror("a", vote("legit"), temperature=None)
    run(j, juror("b", vote("legit")))
    assert "temperature" not in j.client.calls[0]


class FakeAnthropic:
    """Stands in for anthropic.Anthropic."""

    def __init__(self, text, stop_reason="end_turn"):
        self.text, self.stop_reason = text, stop_reason
        self.calls = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.text)]
        return SimpleNamespace(content=content, stop_reason=self.stop_reason, stop_details=SimpleNamespace(category="cyber"))


def test_claude_juror_votes_and_skips_panel_params():
    from modeljury import Claude

    c = Claude("claude-opus-5-5", client=FakeAnthropic(json.dumps(vote("legit"))), params={"output_config": {"effort": "low"}})
    r = run(c, juror("b", vote("legit")), temperature=0.3, seed=7)
    assert r.verdict == "legit" and not r.needs_review
    call = c.client.calls[0]
    assert "temperature" not in call and "seed" not in call
    assert call["max_tokens"] == 16000
    assert call["output_config"] == {"effort": "low"}


def test_claude_refusal_is_a_failed_vote():
    from modeljury import Claude

    c = Claude("claude-opus-5-5", client=FakeAnthropic("", stop_reason="refusal"))
    r = run(c, juror("b", vote("legit")))
    assert r.needs_review
    assert "refused" in r.failed[0].error


def test_claude_string_becomes_claude_juror():
    from modeljury import Claude
    from modeljury.jury import _juror

    assert isinstance(_juror("claude-sonnet-5-5"), Claude)
    assert not isinstance(_juror("gpt-4o-mini"), Claude)


def test_majority_counts_the_whole_panel():
    assert run(juror("a", vote("legit")), juror("b", vote("legit")), juror("c", vote("fraud"))).majority
    # 2 of 3 is a majority even with one failure
    assert run(juror("a", vote("legit")), juror("b", vote("legit")), juror("c", RuntimeError("x"))).majority
    # 1 valid vote out of 3 is 100% agreement but not a majority
    r = run(juror("a", vote("legit")), juror("b", RuntimeError("x")), juror("c", RuntimeError("x")))
    assert r.verdict == "legit" and r.agreement == 1.0 and not r.majority
    # tie
    assert not run(juror("a", vote("legit")), juror("b", vote("fraud"))).majority


def test_plurality_with_many_options_is_not_majority():
    opts = ["a", "b", "c", "d"]
    jurors = [juror(str(i), vote(c)) for i, c in enumerate(["a", "a", "b", "c", "d"])]
    r = convene("?", "e", opts, jurors)
    assert r.verdict == "a" and r.agreement == 0.4 and not r.majority


def test_single_juror_warns():
    import pytest

    with pytest.warns(UserWarning, match="single juror"):
        run(juror("a", vote("legit")))


def test_parse_skips_think_block_with_braces():
    raw = '<think>Options are {fraud, legit}.</think>\n{"choice": "fraud", "confidence": 0.8, "reason": "address changed"}'
    v = parse_vote("r1", raw, OPTIONS)
    assert v.choice == "fraud" and v.reason == "address changed"


def test_parse_takes_outer_object_not_nested():
    v = parse_vote("a", '{"choice": "legit", "reason": "ok", "meta": {"x": 1}}', OPTIONS)
    assert v.choice == "legit"


def test_parse_takes_last_object():
    v = parse_vote("a", 'e.g. {"choice": "fraud"} ... final: {"choice": "legit", "reason": "ok"}', OPTIONS)
    assert v.choice == "legit"


def test_duplicate_names_are_numbered_without_mutating_jurors():
    a, b = juror("llama", vote("legit")), juror("llama", vote("fraud", "odd"))
    r = run(a, b, juror("gpt", vote("legit")))
    assert [v.juror for v in r.votes] == ["llama", "llama#2", "gpt"]
    assert b.name == "llama"


class NotFound(Exception):
    status_code = 404


def model_client(models, list_error=None):
    """A FakeClient whose create() 404s and whose models.list() returns models."""
    client = FakeClient(NotFound("model does not exist"))

    def list_models(**kwargs):
        if list_error:
            raise list_error
        return [SimpleNamespace(id=m) for m in models]

    client.models = SimpleNamespace(list=list_models)
    return client


def failed_error(model, client):
    r = run(Juror(model, client=client), juror("b", vote("legit")))
    return r.failed[0].error


def test_unknown_model_lists_available_models():
    err = failed_error("qwen-typo", model_client(["Qwen3-27B", "llama3.1"]))
    assert err.endswith("; available models: Qwen3-27B, llama3.1")


def test_unknown_model_suggests_close_matches_on_long_lists():
    models = [f"vendor/model-{i}" for i in range(50)] + ["meta-llama/llama-3.1-70b-instruct"]
    err = failed_error("meta-llama/llama-3.1-70b", model_client(models))
    assert "did you mean meta-llama/llama-3.1-70b-instruct" in err
    assert "(51 models available)" in err


def test_no_hint_when_listing_fails_or_model_exists():
    assert "available" not in failed_error("x", model_client([], list_error=NotFound("bad base_url")))
    assert "available" not in failed_error("llama3.1", model_client(["llama3.1"]))


def test_no_hint_for_other_errors():
    assert "available" not in failed_error("x", FakeClient(RuntimeError("timeout")))
