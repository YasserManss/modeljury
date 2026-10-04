# modeljury

Ask several models instead of one. Ship when they agree, send to a human when they don't.

## Getting started

Python 3.10 or newer.

```sh
pip install modeljury
# with Claude support
pip install "modeljury[claude]"
```

Point it at any OpenAI-compatible endpoint (OpenAI, Ollama, vLLM, OpenRouter, ...) and
convene a panel. This one uses three models served by a local Ollama:

```python
from modeljury import Juror, convene

local = "http://localhost:11434/v1"
result = convene(
    question="Is this review spam?",
    evidence="'Best product ever!!! Visit cheap-deals.example for 90% off!!!'",
    options=["spam", "not spam"],
    jurors=[Juror(m, base_url=local) for m in ["llama3.1", "qwen3", "mistral"]],
)

print(result.verdict, result.needs_review)
for juror, choice, reason in result.dissent:
    print(f"{juror} disagreed: {choice}, {reason}")
```

For hosted models, set `OPENAI_API_KEY` (and `OPENAI_BASE_URL` for non-OpenAI providers) or
pass `api_key=` and `base_url=` to each `Juror`. For Claude, set `ANTHROPIC_API_KEY`.

## Usage

```python
from modeljury import Juror, convene

result = convene(
    question="Is this refund request fraudulent?",
    evidence=ticket_text,
    options=["fraud", "legit"],
    jurors=[
        Juror("gpt-4o-mini"),
        Juror("llama3.1", base_url="http://localhost:11434/v1"),
        Juror("mistral-small", base_url="https://api.mistral.ai/v1", api_key="..."),
    ],
)

result.verdict       # "legit", or None on a hung jury
result.majority      # True: the verdict won more than half of the whole panel
result.needs_review  # True
result.dissent       # [("mistral-small", "fraud", "Shipping address changed after purchase")]
result.failed        # jurors that errored or gave an invalid answer
```

Any endpoint that speaks the OpenAI chat completions API works. A plain string juror
(`"gpt-4o-mini"`) uses `OPENAI_BASE_URL` and `OPENAI_API_KEY`.

## Examples

These are real runs: five copies of one local 27B model, sampled at `temperature=1.0`.
The evidence is slightly trimmed here, and the quoted reasons are the model's own words.
A mixed panel of different models would disagree more often. See the warning at the end.

### Refund with mixed signals

```python
convene(
    question="Should this refund be approved?",
    evidence="Customer of 6 years, 40 prior orders, 2 prior refunds (both legitimate). "
    "Claims a $1,900 laptop arrived with a cracked screen. The photo's EXIF date is "
    "2 days before delivery. Courier marked it 'left at door', no signature. "
    "Customer says their phone clock is wrong and offers to send the laptop back.",
    options=["approve", "deny", "escalate"],
    jurors=jurors,
)
```

**escalate, 4–1, needs review.** The majority wanted the EXIF date checked. The dissent
made the case for approving:

> ✗ approve: *Strong 6-year history with only 2 prior refunds outweighs the EXIF
> inconsistency, which is plausibly explained by the customer's claim of a misconfigured
> phone clock.*

### Bug triage across four teams

```python
convene(
    question="Which team should own this bug report?",
    evidence="'After upgrading to v4.2, CSV exports from the dashboard are missing every "
    "row created after 11pm. Only affects customers in Australia. Started the same day we "
    "moved the export job to a new server.'",
    options=["Frontend", "Data", "Infra", "Billing"],
    jurors=jurors,
)
```

**Data, 4–1, needs review.** Four jurors blamed timezone logic in the export pipeline.
The dissent was the only one that used the strongest clue:

> ✗ Infra: *The bug started immediately after moving the export job to a new server,
> and the time-based filtering error likely stems from a timezone configuration issue
> on that new infrastructure.*

A reviewer who reads only the dissent knows where to look first.

### Merging a fast but risky cache

```python
convene(
    question="Should this pull request be merged as is?",
    evidence="Adds a cache in front of the user-permissions lookup: p99 latency drops "
    "from 900ms to 40ms. TTL is 10 minutes. Tests pass. A revoked admin keeps admin "
    "rights for up to 10 minutes. Revocations happen about 3 times a month, and last "
    "week's outage was caused by the slow lookup.",
    options=["merge", "request changes", "merge with follow-up ticket"],
    jurors=jurors,
)
```

**merge with follow-up ticket, 5–0, ships.** All five weighed the latency gain against
the 10-minute window and asked for a ticket to add cache invalidation on revocation.

### Satire or threat

```python
convene(
    question="Does this post violate the policy against threats of violence?",
    evidence="Policy: remove credible threats of violence. Satire and hyperbole are allowed. "
    "Post, replying to a council member's parking fee increase: 'If they raise parking "
    "again I swear I'll show up at the next meeting and make sure he never votes on "
    "anything again 🙂'. Author has no prior violations and often jokes about local politics.",
    options=["violates", "allowed"],
    jurors=jurors,
)
```

**allowed, 5–0, ships.** This is the warning. The post names a target and a place, and
a human moderator might well escalate it. All five jurors dismissed it for the same
reason, mostly the smiley. Copies of one model share the same blind spots, so their
agreement is weaker evidence than it looks. Use jurors from different model families,
because a unanimous vote only means something if the jurors could have disagreed.

## Model options

Extra keyword arguments to `convene()` go to every juror's `chat.completions.create` call.
A juror's own `params` override them. `temperature` defaults to `0`.

```python
convene(..., temperature=0.3, max_tokens=200, jurors=[
    Juror("gpt-4o-mini"),                                       # temperature=0.3, max_tokens=200
    Juror("o4-mini", params={"temperature": None,               # None drops a param
                             "reasoning_effort": "low"}),       # adds a model-specific option
    Juror("qwen3", base_url="http://localhost:8000/v1",
          params={"temperature": 0.7, "extra_body": {"top_k": 20}}),  # overrides temperature
])
```

## Claude

Claude uses the native Anthropic Messages API. Install the extra with `pip install modeljury[claude]`.

```python
from modeljury import Claude

jurors = [
    "gpt-4o-mini",
    "claude-sonnet-5-5",                                         # any "claude-..." string works
    Claude("claude-opus-5-5", params={"output_config": {"effort": "low"}}),
]
```

- Credentials come from `ANTHROPIC_API_KEY` or an `ant auth login` profile, unless you pass `api_key=`.
- Panel-wide kwargs are OpenAI parameters, so Claude jurors don't receive them. Put Messages API
  options in `params` instead. Current Claude models reject `temperature`, so none is sent.
- `max_tokens` defaults to 16000. Set it lower with `params={"max_tokens": ...}` if you need a cost cap.
  Thinking counts toward it.
- If Claude refuses, the vote is recorded in `result.failed` and the decision goes to review.

## Self-signed certificates and custom clients

For a server with a self-signed or internal certificate, point `verify` at the certificate.
`verify=False` turns certificate checks off entirely. It works, but then anyone on the network
path can read the API key and evidence, so prefer the certificate. `Claude` takes the same option.

```python
Juror("my-model", base_url="https://my-server:8000/v1", verify="/path/to/ca.pem")
Juror("my-model", base_url="https://my-server:8000/v1", verify=False)
```

For anything else, such as a proxy, pass your own SDK client with `client=`. The juror's
`base_url`, `api_key` and `verify` are then ignored, so set them on the client. Use the SDK's
`DefaultHttpxClient` rather than a plain `httpx.Client`, so its timeouts and limits are kept.

```python
from openai import OpenAI, DefaultHttpxClient

client = OpenAI(base_url="...", api_key="...", http_client=DefaultHttpxClient(proxy="http://proxy:3128"))
Juror("my-model", client=client)
```

## Custom prompt

`prompt=` takes a `str.format` template with `{question}`, `{evidence}` and `{options}`.
Double any literal braces (`{{` and `}}`). The default is `modeljury.PROMPT`. Your template
must still ask for `{"choice": ..., "confidence": ..., "reason": ...}` JSON, because that's what the parser reads.

## Rules

1. Each juror picks one allowed option and gives a one-line reason.
2. The verdict is the option with the most votes.
3. `needs_review` is true unless every juror returned the same valid choice.
4. A tie is a hung jury: no verdict, review needed.

`agreement` is the winning option's votes divided by valid votes. A juror that errors, refuses or
answers with an option that isn't allowed is left out of the count and listed in `result.failed`.

## Outcomes

Three jurors, options `fraud` / `legit`:

| Votes | `verdict` | `agreement` | `majority` | `needs_review` | Why |
|---|---|---|---|---|---|
| legit, legit, legit | legit | 100% | ✅ | ❌ | Everyone agrees: ships without review |
| legit, legit, fraud | legit | 67% | ✅ | ✅ | Dissent; the reason is in `dissent` |
| legit, fraud, *failed* | `None` | 50% | ❌ | ✅ | Tie, so hung jury |
| legit, legit, *failed* | legit | 100% | ✅ | ✅ | A juror failed |
| legit, *failed*, *failed* | legit | 100% | ❌ | ✅ | Only one valid vote out of three |
| *failed* ×3 | `None` | 0% | ❌ | ✅ | No valid votes |

`verdict` is the plurality winner, so with three or more options it can win without a majority:
five votes split A, A, B, C, D give verdict A with 40% agreement and `majority` false.
`majority` counts the whole panel, failed jurors included, so it means more than half of
all jurors chose the verdict.

`needs_review` is the strict rule. For a looser one, check `majority` or `agreement` yourself:

```python
if not result.majority:            # ship any decision that more than half the panel backs
    send_to_human(result)
```

A single juror can't dissent, so its decisions only go to review when it fails. `convene()` warns if you pass only one juror.

## Notes

- If a model name is wrong, the juror's error in `result.failed` lists the models the endpoint serves, or suggests the closest names when there are more than 20.
- Jurors with the same name (e.g. `llama3.1` on two endpoints) are recorded as `llama3.1`, `llama3.1#2`, ...
- `timeout` applies to each attempt. The OpenAI and Anthropic SDKs retry failed calls twice, so one juror can take up to three times `timeout`.

## Develop

```sh
uv sync
uv run pytest
```

## License

MIT. See [LICENSE](https://github.com/YasserManss/modeljury/blob/main/LICENSE).
