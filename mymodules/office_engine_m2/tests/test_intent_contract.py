"""Neutral tests for the Candidate B Intent/Expected Effect contract."""

import hashlib
import importlib
import json
import unittest

from odoo.addons.office_engine_m2.services.intent_contract import (
    IntentContractError,
    bind_intent,
    canonicalize_expected_effect,
    confirmation_receipt_id,
    digest_json,
    normalize_interpretation,
)
from odoo.addons.office_engine_m2.services.candidate_validator import _office_verify


def _effect(parent_id=1, source_sha=None, *, value=15, scope=None, assertions=None, unknowns=None):
    source_sha = source_sha or "a" * 64
    effect = {
        "schema_version": "1",
        "parent_version_id": parent_id,
        "input_sha256": source_sha,
        "target_scopes": scope or [{"kind": "cell", "sheet": "Data", "address": "A1"}],
        "allowed_change_kinds": ["cell_value"],
        "expected_assertions": assertions if assertions is not None else [{
            "kind": "cell_value", "sheet": "Data", "address": "A1", "value_type": "number", "value": value,
        }],
        "unknowns": list(unknowns or []),
    }
    payload = {key: value for key, value in effect.items() if key != "effect_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    effect["effect_digest"] = hashlib.sha256(encoded).hexdigest()
    return effect


class TestIntentContract(unittest.TestCase):
    def setUp(self):
        self.explicit = {
            "summary": "Set one explicitly identified value.",
            "target_scope": {"description": "One explicit target", "basis": "explicit"},
            "assumptions": [],
            "unknowns": [],
        }

    def test_interpretation_is_small_and_rejects_ambiguous_or_unknown_targets(self):
        normalized = normalize_interpretation(self.explicit)
        self.assertEqual(normalized["target_scope"]["basis"], "explicit")
        with self.assertRaises(IntentContractError):
            normalize_interpretation({**self.explicit, "untrusted_user_id": 7})
        ambiguous = {**self.explicit, "target_scope": {"description": "One of several", "basis": "ambiguous"}}
        self.assertEqual(normalize_interpretation(ambiguous)["target_scope"]["basis"], "ambiguous")

    def test_expected_effect_is_delegated_to_cb03_and_bound_to_parent_and_bytes(self):
        effect = _effect()
        clean, digest = canonicalize_expected_effect(effect, parent_version_id=1, input_sha256="a" * 64)
        self.assertEqual(clean["effect_digest"], digest)
        self.assertEqual(clean["parent_version_id"], 1)
        with self.assertRaises(IntentContractError):
            canonicalize_expected_effect(effect, parent_version_id=2, input_sha256="a" * 64)
        with self.assertRaises(IntentContractError):
            canonicalize_expected_effect(effect, parent_version_id=1, input_sha256="b" * 64)

    def test_unbound_agent_effect_is_sealed_to_current_version_by_service(self):
        declared = {
            "target_scopes": [{"kind": "cell", "sheet": "Data", "address": "Z42"}],
            "allowed_change_kinds": ["cell_value"],
            "expected_assertions": [{
                "kind": "cell_value", "sheet": "Data", "address": "Z42",
                "value_type": "string", "value": "Updated label",
            }],
            "unknowns": [],
        }
        canonical, digest = canonicalize_expected_effect(
            declared, parent_version_id=83, input_sha256="c" * 64
        )
        self.assertEqual(canonical["schema_version"], "1")
        self.assertEqual(canonical["parent_version_id"], 83)
        self.assertEqual(canonical["input_sha256"], "c" * 64)
        self.assertEqual(canonical["effect_digest"], digest)
        self.assertEqual(canonical["target_scopes"], declared["target_scopes"])
        # The canonical result can be replayed by the subsequent edit call,
        # while a stale parent, bytes fingerprint or caller digest still fails.
        self.assertEqual(
            canonicalize_expected_effect(canonical, parent_version_id=83, input_sha256="c" * 64),
            (canonical, digest),
        )
        with self.assertRaises(IntentContractError):
            canonicalize_expected_effect(canonical, parent_version_id=84, input_sha256="c" * 64)
        with self.assertRaises(IntentContractError):
            canonicalize_expected_effect(canonical, parent_version_id=83, input_sha256="d" * 64)
        tampered = {**canonical, "effect_digest": "0" * 64}
        with self.assertRaises(IntentContractError):
            canonicalize_expected_effect(tampered, parent_version_id=83, input_sha256="c" * 64)

    def test_effect_does_not_accept_an_alternate_unbounded_shape(self):
        with self.assertRaises(IntentContractError):
            canonicalize_expected_effect(
                {
                    "targets": ["xlsx:Data!Z42"],
                    "allowed_changes": ["replace the value"],
                    "assertions": ["Data!Z42 equals Updated label"],
                    "unknowns": [],
                },
                parent_version_id=83,
                input_sha256="c" * 64,
            )

    def test_binding_and_confirmation_digest_change_with_effect_or_revision(self):
        binding = bind_intent(
            intent_message_id=9, thread_id=7, session_id=3, parent_version_id=1,
            input_sha256="a" * 64, interpretation=self.explicit, effect_digest="b" * 64,
        )
        first = confirmation_receipt_id(binding, owner_id=2, session_revision=1, proposal_revision=0, document_revision=1)
        changed = bind_intent(
            intent_message_id=9, thread_id=7, session_id=3, parent_version_id=1,
            input_sha256="a" * 64, interpretation=self.explicit, effect_digest="c" * 64,
        )
        second = confirmation_receipt_id(changed, owner_id=2, session_revision=1, proposal_revision=0, document_revision=1)
        stale_revision = confirmation_receipt_id(binding, owner_id=2, session_revision=1, proposal_revision=0, document_revision=2)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, stale_revision)

    def test_model_confirmation_decision_is_bound_without_local_risk_classification(self):
        common = {
            "intent_message_id": 9,
            "thread_id": 7,
            "session_id": 3,
            "parent_version_id": 1,
            "input_sha256": "a" * 64,
            "interpretation": self.explicit,
            "effect_digest": "b" * 64,
        }
        no_confirmation = bind_intent(**common, confirmation_required=False, confirmation_reason="")
        model_requested = bind_intent(
            **common,
            confirmation_required=True,
            confirmation_reason="The model identified a material risk.",
        )
        self.assertNotEqual(no_confirmation["intent_digest"], model_requested["intent_digest"])
        pending = confirmation_receipt_id(
            model_requested, owner_id=2, session_revision=1, proposal_revision=0, document_revision=1,
        )
        confirmed = confirmation_receipt_id(
            model_requested, owner_id=2, session_revision=1, proposal_revision=0, document_revision=1,
            decision_message_id=10, confirmed_by_user_id=2,
        )
        different_message = confirmation_receipt_id(
            model_requested, owner_id=2, session_revision=1, proposal_revision=0, document_revision=1,
            decision_message_id=11, confirmed_by_user_id=2,
        )
        different_user = confirmation_receipt_id(
            model_requested, owner_id=2, session_revision=1, proposal_revision=0, document_revision=1,
            decision_message_id=10, confirmed_by_user_id=3,
        )
        self.assertNotEqual(pending, confirmed)
        self.assertNotEqual(confirmed, different_message)
        self.assertNotEqual(confirmed, different_user)

