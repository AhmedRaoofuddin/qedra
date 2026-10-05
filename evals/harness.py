"""Golden-set evaluation harness.

Runs qedra against every example that ships an expected.json and reports accuracy plus
precision and recall for violation detection. Because the solver's verdicts are ground truth,
this measures whether the encoding and pipeline report what they should, and whether any finding
appears that the golden set did not anticipate (a hallucination, which must stay at zero).

Run:  python evals/harness.py
Exit code is non-zero if any example disagrees with its expected outcome.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from qedra.adapters.ingest import load_architecture
from qedra.application.policy import Policy
from qedra.application.verify import verify

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@dataclass
class Tally:
    checked: int = 0
    correct: int = 0
    true_pos: int = 0   # expected VIOLATED, reported VIOLATED
    false_pos: int = 0  # reported VIOLATED, expected otherwise
    false_neg: int = 0  # expected VIOLATED, reported otherwise
    hallucinated: int = 0  # reported a finding id the golden set did not list

    def precision(self) -> float:
        denom = self.true_pos + self.false_pos
        return self.true_pos / denom if denom else 1.0

    def recall(self) -> float:
        denom = self.true_pos + self.false_neg
        return self.true_pos / denom if denom else 1.0


def _evaluate_example(directory: Path, tally: Tally) -> list[str]:
    expected = json.loads((directory / "expected.json").read_text(encoding="utf-8"))["findings"]
    architecture = load_architecture(directory)
    report = verify(architecture, Policy.baseline())
    actual = {f.id: f.verdict.value for f in report.findings}

    problems: list[str] = []
    for finding_id, want in expected.items():
        tally.checked += 1
        got = actual.get(finding_id)
        if got == want:
            tally.correct += 1
        else:
            problems.append(f"{directory.name}:{finding_id} expected {want}, got {got}")
        if want == "VIOLATED" and got == "VIOLATED":
            tally.true_pos += 1
        elif want == "VIOLATED" and got != "VIOLATED":
            tally.false_neg += 1
        elif want != "VIOLATED" and got == "VIOLATED":
            tally.false_pos += 1

    for finding_id in actual:
        if finding_id not in expected:
            tally.hallucinated += 1
            problems.append(f"{directory.name}:{finding_id} was not expected (hallucination)")
    return problems


def main() -> int:
    tally = Tally()
    problems: list[str] = []
    for directory in sorted(p.parent for p in EXAMPLES.glob("*/expected.json")):
        problems.extend(_evaluate_example(directory, tally))

    accuracy = tally.correct / tally.checked if tally.checked else 1.0
    print("qedra golden-set evaluation")
    print(f"  properties checked : {tally.checked}")
    print(f"  accuracy           : {accuracy:.1%}")
    print(f"  precision          : {tally.precision():.1%}")
    print(f"  recall             : {tally.recall():.1%}")
    print(f"  hallucinated       : {tally.hallucinated}")
    if problems:
        print("\nmismatches:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nAll examples match their expected verdicts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
