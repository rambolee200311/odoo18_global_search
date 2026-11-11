"""Replay the two historical synthetic Route B candidates through the verifier."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from office_verify import VerificationBudget, VerificationPolicy, verify_candidate_output


ROOT = Path(__file__).resolve().parent
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def main() -> None:
    source = (ROOT / "cc07-route-b-v1-input-42f92959aa.xlsx").read_bytes()
    assertions = []
    rows = (
        (2, "CC07-SYN-42f92959aa-Ava Example", "+1-555-0101", "cc07-syn-42f92959aa-ava@example.invalid"),
        (3, "CC07-SYN-42f92959aa-Mia Example", "+1-555-0103", "cc07-syn-42f92959aa-mia@example.invalid"),
        (4, "CC07-SYN-42f92959aa-Noah Example", "+1-555-0102", "cc07-syn-42f92959aa-noah@example.invalid"),
    )
    for row, name, phone, email in rows:
        for column, value in zip("ABC", (name, phone, email)):
            assertions.append({
                "kind": "cell_value", "sheet": "Contacts", "address": f"{column}{row}",
                "value_type": "string", "value": value,
            })
    effect = {
        "schema_version": "1",
        "parent_version_id": 0,
        "input_sha256": hashlib.sha256(source).hexdigest(),
        "target_scopes": [{"kind": "range", "sheet": "Contacts", "start": "A2", "end": "C4"}],
        "allowed_change_kinds": ["cell_value"],
        "expected_assertions": assertions,
        "unknowns": [],
    }
    effect["effect_digest"] = hashlib.sha256(
        json.dumps(effect, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()

    output = []
    for candidate_id, filename in ((2353, "candidate-2353-failed.xlsx"), (2354, "candidate-2354-failed.xlsx")):
        candidate = (ROOT / filename).read_bytes()
        report = verify_candidate_output(
            source,
            candidate,
            "synthetic.xlsx",
            MIME,
            effect,
            policy=VerificationPolicy(enabled_formats=("xlsx",)),
            budget=VerificationBudget(),
        )
        output.append({
            "candidate_id": candidate_id,
            "input_sha256": report.input_sha256,
            "output_sha256": report.output_sha256,
            "validation_result": report.validation_result,
            "error": report.error,
            "actual_effects": list(report.actual_effects),
        })
    path = ROOT / "ATR-RUN-025-historical-candidate-replay.json"
    path.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
