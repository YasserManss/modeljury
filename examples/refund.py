"""Run a four-model panel: OpenAI-compatible endpoints plus Claude."""

import os

from modeljury import Claude, Juror, convene

jurors = [
    Juror("gpt-4o-mini"),  # uses OPENAI_BASE_URL / OPENAI_API_KEY
    Claude("claude-sonnet-5-5"),  # uses ANTHROPIC_API_KEY; needs modeljury[claude]
    Juror("llama3.1", base_url="http://localhost:11434/v1"),  # Ollama
    Juror(
        "meta-llama/llama-3.1-70b-instruct",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        name="openrouter-llama",
    ),
]

result = convene(
    question="Is this refund request fraudulent?",
    evidence="Order #1182 delivered 3 days ago. Customer says box arrived empty. "
    "Shipping address was changed an hour after purchase.",
    options=["fraud", "legit"],
    jurors=jurors,
)

print("verdict:     ", result.verdict)
print("agreement:   ", f"{result.agreement:.0%}")
print("needs review:", result.needs_review)
for juror, choice, reason in result.dissent:
    print(f"  dissent {juror}: {choice} — {reason}")
for v in result.failed:
    print(f"  failed  {v.juror}: {v.error}")
