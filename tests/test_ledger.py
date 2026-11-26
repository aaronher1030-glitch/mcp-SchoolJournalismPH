"""Tests for claim-ledger validation and the publication gate."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp_server.ledger import (  # noqa: E402
    STATUSES,
    parse_ledger,
    publication_gate,
    validate_ledger,
)

SUPPORTED_ROW = {
    "claim_id": "C-001",
    "location": "Paragraph 1",
    "claim": "The last class ends at 4:10.",
    "claim_type": "fact",
    "evidence": "Recording 00:02:10",
    "qualifier": "Principal, recorded",
    "scope": "School-wide, from November 3",
    "status": "SUPPORTED",
    "gap": "None identified after review",
    "action": "Retain",
}


def unchecked_row(claim_id: str = "C-002") -> dict:
    return {
        "claim_id": claim_id,
        "location": "Paragraph 3",
        "claim": "120 students were affected.",
        "claim_type": "statistic",
        "evidence": "None located",
        "status": "UNCHECKED",
        "gap": "No transport record supplied",
        "action": "Obtain the attendance record",
    }


class LedgerParsingTests(unittest.TestCase):
    def test_json_rows_are_canonicalized(self) -> None:
        rows, errors = parse_ledger(json.dumps([{"Claim ID": "C-9", "Evidence status": "supported"}]))
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["claim_id"], "C-9")
        self.assertEqual(rows[0]["status"], "SUPPORTED")

    def test_markdown_table_is_parsed(self) -> None:
        table = (
            "| Claim ID | Draft location | Claim as written | Claim type | Evidence and locator | Evidence status | Conflict or gap | Required action |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| C-001 | P1 | 120 students | statistic | none | UNCHECKED | no record | obtain record |\n"
        )
        rows, errors = parse_ledger(table)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["claim_id"], "C-001")
        self.assertEqual(rows[0]["status"], "UNCHECKED")

    def test_rejects_empty_input(self) -> None:
        with self.assertRaises(ValueError):
            parse_ledger("   ")

    def test_six_statuses_unchanged(self) -> None:
        self.assertEqual(len(STATUSES), 6)
        self.assertIn("PARTIALLY_SUPPORTED", STATUSES)


class LedgerValidationTests(unittest.TestCase):
    def test_complete_supported_row_is_valid(self) -> None:
        result = validate_ledger(json.dumps([SUPPORTED_ROW]))
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["status_counts"]["SUPPORTED"], 1)

    def test_invalid_status_is_rejected(self) -> None:
        row = dict(SUPPORTED_ROW, status="verified")
        result = validate_ledger(json.dumps([row]))
        self.assertFalse(result["valid"])
        self.assertTrue(any("is not one of" in error for error in result["errors"]))

    def test_unchecked_requires_action_and_gap(self) -> None:
        row = dict(unchecked_row(), action="", gap="")
        result = validate_ledger(json.dumps([row]))
        self.assertFalse(result["valid"])
        joined = " ".join(result["errors"])
        self.assertIn("required action", joined)
        self.assertIn("conflict or gap", joined)

    def test_duplicate_ids_are_rejected(self) -> None:
        result = validate_ledger(json.dumps([SUPPORTED_ROW, dict(SUPPORTED_ROW)]))
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicate" in error for error in result["errors"]))

    def test_empty_ledger_is_invalid(self) -> None:
        result = validate_ledger("[]")
        self.assertFalse(result["valid"])


class PublicationGateTests(unittest.TestCase):
    def test_supported_ledger_is_ready_for_human_review(self) -> None:
        result = publication_gate(json.dumps([SUPPORTED_ROW]))
        self.assertEqual(result["decision"], "READY FOR HUMAN EDITOR REVIEW")
        self.assertEqual(result["blocking"], [])
        self.assertIn("PENDING HUMAN REVIEW", result["decision_block"])

    def test_unchecked_material_claim_blocks(self) -> None:
        result = publication_gate(json.dumps([SUPPORTED_ROW, unchecked_row()]))
        self.assertEqual(result["decision"], "NOT READY")
        self.assertEqual(result["blocking"][0]["id"], "C-002")
        self.assertIn("Obtain the attendance record", result["decision_block"])

    def test_level_two_issue_blocks(self) -> None:
        result = publication_gate(json.dumps([SUPPORTED_ROW]), [{"level": 2, "reason": "transport group not heard"}])
        self.assertEqual(result["decision"], "NOT READY")
        self.assertEqual(result["blocking"][0]["kind"], "issue")

    def test_level_one_issue_does_not_block(self) -> None:
        result = publication_gate(json.dumps([SUPPORTED_ROW]), [{"level": 1, "reason": "rhythm"}])
        self.assertEqual(result["decision"], "READY FOR HUMAN EDITOR REVIEW")
        self.assertEqual(len(result["non_blocking_issues"]), 1)

    def test_invalid_ledger_cannot_be_ready(self) -> None:
        result = publication_gate('[{"claim_id": "C-1"}]')
        self.assertEqual(result["decision"], "NOT READY")
        self.assertEqual(result["blocking"][0]["kind"], "ledger")

    def test_non_material_unchecked_row_does_not_block(self) -> None:
        row = dict(unchecked_row("C-003"), material=False)
        result = publication_gate(json.dumps([SUPPORTED_ROW, row]))
        self.assertEqual(result["decision"], "READY FOR HUMAN EDITOR REVIEW")

    def test_gate_never_approves(self) -> None:
        result = publication_gate(json.dumps([SUPPORTED_ROW]))
        self.assertNotIn(result["decision"], {"APPROVED", "READY", "PUBLISH"})
        self.assertIn("not approval", " ".join(result["rules_applied"]))

    def test_issue_level_must_be_one_to_five(self) -> None:
        with self.assertRaises(ValueError):
            publication_gate(json.dumps([SUPPORTED_ROW]), [{"level": 9, "reason": "x"}])


if __name__ == "__main__":
    unittest.main()
