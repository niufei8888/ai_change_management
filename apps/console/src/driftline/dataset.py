"""Parses datasets/golden.yaml.

The dataset is a file, not a table. Changing an assertion is changing the
standard the product is held to, so it belongs in git next to the code, where it
gets reviewed and diffed. In a database it would be the perfect place for
"someone quietly loosened a check" to hide.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATASET_PATH = Path(__file__).resolve().parents[4] / "datasets" / "golden.yaml"

# The complete set of mechanical checks. An unknown key is a typo in the dataset,
# and a typo that parses is an assertion silently doing nothing -- so it raises
# rather than being ignored (TO-22).
KNOWN_OBSERVATIONS = frozenset(
    {
        "tool_called",
        "terminated_by",
        "cites_real_article",
        "max_words",
        "no_system_prompt_leak",
        "no_code_block",
        "no_price_figure",
    }
)


@dataclass(frozen=True)
class Expectation:
    index: int  # position in the case, used as the verdict key: policy is not unique
    policy: str
    expect: str


@dataclass(frozen=True)
class Case:
    id: str
    persona: str
    persona_note: str
    question: str
    observations: dict[str, Any]
    expectations: tuple[Expectation, ...]

    @property
    def policies(self) -> list[str]:
        return sorted({e.policy for e in self.expectations})


@dataclass(frozen=True)
class Dataset:
    version: int
    hash: str
    personas: dict[str, str]
    cases: tuple[Case, ...]

    def case(self, case_id: str) -> Case:
        return next(c for c in self.cases if c.id == case_id)


def load(path: Path = DATASET_PATH) -> Dataset:
    raw = path.read_bytes()
    doc = yaml.safe_load(raw)
    personas: dict[str, str] = {k: v.strip() for k, v in doc["personas"].items()}

    cases = []
    for entry in doc["cases"]:
        observations = entry.get("observations") or {}
        unknown = set(observations) - KNOWN_OBSERVATIONS
        if unknown:
            raise ValueError(f"case {entry['id']}: unknown observation(s) {sorted(unknown)}")

        cases.append(
            Case(
                id=entry["id"],
                persona=entry["persona"],
                persona_note=personas[entry["persona"]],
                question=entry["question"].strip(),
                observations=observations,
                expectations=tuple(
                    Expectation(index=i, policy=e["policy"], expect=e["expect"].strip())
                    for i, e in enumerate(entry.get("expectations") or [])
                ),
            )
        )

    return Dataset(
        version=doc["version"],
        # Hashes the bytes, not the parsed structure: a comment change is a
        # dataset change worth invalidating the cache for, because comments are
        # where the reasoning behind a case lives.
        hash=hashlib.sha256(raw).hexdigest()[:16],
        personas=personas,
        cases=tuple(cases),
    )


def as_json(dataset: Dataset) -> dict[str, Any]:
    """Shape the console frontend renders."""
    return {
        "version": dataset.version,
        "hash": dataset.hash,
        "personas": dataset.personas,
        "cases": [
            {
                "id": c.id,
                "persona": c.persona,
                "persona_note": c.persona_note,
                "question": c.question,
                "observations": c.observations,
                "expectations": [
                    {"index": e.index, "policy": e.policy, "expect": e.expect}
                    for e in c.expectations
                ],
            }
            for c in dataset.cases
        ],
    }
