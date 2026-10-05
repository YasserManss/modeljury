"""Load benchmark datasets as uniform decision items.

Every item is a dict:
    id, dataset, question, evidence, options, label,
    human_agreement  # share of human annotators who chose the label, or None
"""

from __future__ import annotations

import ast
import csv
import io
import random
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from datasets import load_dataset

CACHE = Path(__file__).parent / ".cache"


def _item(dataset, id, question, evidence, options, label, human_agreement=None):
    return dict(
        id=f"{dataset}:{id}",
        dataset=dataset,
        question=question,
        evidence=evidence,
        options=options,
        label=label,
        human_agreement=human_agreement,
    )


def boolq():
    for i, r in enumerate(load_dataset("google/boolq", split="validation")):
        yield _item(
            "boolq", i, r["question"].rstrip("?") + "?", r["passage"],
            ["yes", "no"], "yes" if r["answer"] else "no",
        )


def vitaminc():
    labels = {"SUPPORTS": "supports", "REFUTES": "refutes", "NOT ENOUGH INFO": "not enough info"}
    for r in load_dataset("tals/vitaminc", split="validation"):
        yield _item(
            "vitaminc", r["unique_id"],
            f"Does the evidence support or refute this claim? Claim: {r['claim']}",
            r["evidence"], list(labels.values()), labels[r["label"]],
        )


def banking77():
    url = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv"
    rows = list(csv.DictReader(io.StringIO(_download(url, "banking77_test.csv").read_text())))
    options = sorted({r["category"] for r in rows})
    for i, r in enumerate(rows):
        yield _item(
            "banking77", i, "Which intent best describes this banking customer's message?",
            r["text"], options, r["category"],
        )


def judgebench():
    for r in load_dataset("ScalerLab/JudgeBench", split="gpt"):
        if r["label"] not in ("A>B", "B>A"):
            continue
        evidence = (
            f"Question:\n{r['question']}\n\nResponse A:\n{r['response_A']}\n\n"
            f"Response B:\n{r['response_B']}"
        )
        yield _item(
            "judgebench", r["pair_id"], "Which response answers the question correctly?",
            evidence, ["Response A", "Response B"], f"Response {r['label'][0]}",
        )


def chaosnli():
    """ChaosNLI MNLI subset: 100 human labels per item (CC BY-NC 4.0).

    The authors' Dropbox link is dead, so this reads the Hugging Face mirror of the same files.
    """
    names = {"e": "entailment", "n": "neutral", "c": "contradiction"}
    for r in load_dataset("earino/chaosnli", "mnli_m", split="validation"):
        counts = {k: v or 0 for k, v in _as_dict(r["label_counter"]).items()}
        example = _as_dict(r["example"])
        evidence = f"Premise: {example['premise']}\nHypothesis: {example['hypothesis']}"
        yield _item(
            "chaosnli", r["uid"],
            "Does the premise entail, contradict, or say nothing about the hypothesis?",
            evidence, list(names.values()), names[r["majority_label"]],
            human_agreement=counts[r["majority_label"]] / sum(counts.values()),
        )


def _as_dict(value):
    """Mirror columns may hold dicts or their string form."""
    return value if isinstance(value, dict) else ast.literal_eval(value)


def mhs():
    """Measuring Hate Speech: several annotators per comment. hatespeech is 0 no, 1 unclear, 2 yes."""
    votes, text = defaultdict(list), {}
    for r in load_dataset("ucberkeley-dlab/measuring-hate-speech", split="train"):
        votes[r["comment_id"]].append(r["hatespeech"] == 2)
        text[r["comment_id"]] = r["text"]
    for cid, v in votes.items():
        if len(v) < 3:
            continue
        hateful = sum(v) / len(v)
        label = "hateful" if hateful > 0.5 else "not hateful"
        yield _item(
            "mhs", cid, "Is this comment hate speech?", text[cid],
            ["hateful", "not hateful"], label, human_agreement=max(hateful, 1 - hateful),
        )


LOADERS = dict(
    boolq=boolq, vitaminc=vitaminc, banking77=banking77,
    judgebench=judgebench, chaosnli=chaosnli, mhs=mhs,
)


def sample(name: str, n: int, seed: int = 0) -> list[dict]:
    """A fixed random sample. mhs is stratified 50/50, since hateful comments are rare."""
    items = list(LOADERS[name]())
    rng = random.Random(seed)
    if name == "mhs":
        by_label = defaultdict(list)
        for it in items:
            by_label[it["label"]].append(it)
        half = n // 2
        picked = [it for lbl in sorted(by_label) for it in rng.sample(by_label[lbl], half)]
        rng.shuffle(picked)
        return picked
    return rng.sample(items, min(n, len(items)))


def label_counts(items):
    return Counter(it["label"] for it in items)


def _download(url: str, name: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "modeljury-benchmark"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            path.write_bytes(resp.read())
    return path
