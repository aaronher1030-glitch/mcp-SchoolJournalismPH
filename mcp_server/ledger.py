"""Claim-ledger parsing, validation, and the publication gate.

The gate implements the decision rules in
`skills/journalism-humanizer/references/verification-output.md` as code, so a
model cannot talk itself into a release decision that the evidence does not
support. It can only ever return:

    READY FOR HUMAN EDITOR REVIEW   or   NOT READY

Never approval. The final decision field is always left for a human editor.
"""

from __future__ import annotations

import json
import re
from typing import Any

STATUSES = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONFLICTED",
    "CONTRADICTED",
    "UNCHECKED",
    "UNSUPPORTED",
)

BLOCKING_STATUSES = {
    "PARTIALLY_SUPPORTED",
    "CONFLICTED",
    "CONTRADICTED",
    "UNCHECKED",
    "UNSUPPORTED",
}

REQUIRED_FIELDS = (
    "claim_id",
    "location",
    "claim",
    "claim_type",
    "evidence",
    "status",
)

FIELD_SYNONYMS = {
    "claim id": "claim_id",
    "claim_id": "claim_id",
    "id": "claim_id",
    "draft location": "location",
    "location": "location",
    "claim as written": "claim",
    "claim": "claim",
    "claim type": "claim_type",
    "claim_type": "claim_type",
    "type": "claim_type",
    "evidence and locator": "evidence",
    "evidence": "evidence",
    "evidence locator": "evidence",
    "evidence qualifier": "qualifier",
    "qualifier": "qualifier",
    "scope and time": "scope",
    "scope": "scope",
    "evidence status": "status",
    "status": "status",
    "conflict or gap": "gap",
    "gap": "gap",
    "required action": "action",
    "action": "action",
    "material": "material",
}

ESCALATION_LEVELS = {
    1: "Stylistic gap",
    2: "Missing evidence",
    3: "Consequential conflict",
    4: "Vulnerable person or serious harm risk",
    5: "Suspected fabrication",
}


def _canonical_key(raw: str) -> str | None:
    return FIELD_SYNONYMS.get(re.sub(r"\s+", " ", raw.strip().lower()))


def _rows_from_json(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("claims", "ledger", "rows"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            raise ValueError("JSON ledger object must contain a 'claims' array")
    if not isinstance(payload, list):
        raise ValueError("JSON ledger must be an array of claim objects")
    rows = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("each claim must be a JSON object")
        row: dict[str, Any] = {}
        for key, value in item.items():
            canonical = _canonical_key(str(key))
            if canonical:
                row[canonical] = value
        rows.append(row)
    return rows


def _rows_from_markdown(raw: str) -> list[dict[str, Any]]:
    lines = [ln for ln in raw.splitlines() if ln.strip().startswith("|")]
    if not lines:
        raise ValueError("no markdown table rows found")
    header_cells = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    keys = [_canonical_key(c) for c in header_cells]
    rows: list[dict[str, Any]] = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue
        row = {}
        for key, cell in zip(keys, cells):
            if key:
                row[key] = cell
        rows.append(row)
    return rows


def parse_ledger(raw: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse a JSON or markdown claim ledger into canonical rows."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("ledger must be a non-empty JSON array or markdown table")
    errors: list[str] = []
    text = raw.strip()
    if text.startswith("[") or text.startswith("{"):
        rows = _rows_from_json(json.loads(text))
    else:
        rows = _rows_from_markdown(text)

    clean: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        if not row:
            errors.append(f"row {i}: no recognizable claim-ledger columns")
            continue
        status = str(row.get("status", "")).strip()
        row["status"] = status.upper() if status else ""
        material = row.get("material", True)
        if isinstance(material, str):
            row["material"] = material.strip().lower() not in {"false", "no", "0", "non-material", "nonmaterial"}
        elif not isinstance(material, bool):
            row["material"] = True
        clean.append(row)
    return clean, errors


def validate_ledger(raw: str) -> dict[str, Any]:
    """Validate ledger shape, vocabulary, and required handling."""
    rows, errors = parse_ledger(raw)
    warnings: list[str] = []

    if not rows:
        errors.append("ledger is empty: a source list is not a claim ledger")

    seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        label = row.get("claim_id") or f"row {i}"

        for field in REQUIRED_FIELDS:
            value = row.get(field)
            if value is None or str(value).strip() == "":
                errors.append(f"{label}: missing required field '{field}'")

        claim_id = str(row.get("claim_id", "")).strip()
        if claim_id:
            if claim_id in seen:
                errors.append(f"{label}: duplicate claim ID")
            seen.add(claim_id)

        status = str(row.get("status", "")).strip()
        if status and status not in STATUSES:
            errors.append(
                f"{label}: status '{status}' is not one of {', '.join(STATUSES)}"
            )

        if status in STATUSES:
            action = str(row.get("action", "")).strip()
            gap = str(row.get("gap", "")).strip()
            if status != "SUPPORTED" and not action:
                errors.append(
                    f"{label}: status {status} requires a 'required action' (retain, revise, narrow, attribute, corroborate, remove, or hold)"
                )
            if status != "SUPPORTED" and not gap:
                errors.append(
                    f"{label}: status {status} requires a 'conflict or gap' entry, or 'None identified' after review"
                )
            if status == "SUPPORTED" and not str(row.get("evidence", "")).strip():
                errors.append(f"{label}: SUPPORTED requires an evidence locator")
            if status == "UNCHECKED" and not action:
                warnings.append(f"{label}: name the check still needed so the editor can run it")

        if not str(row.get("qualifier", "")).strip():
            warnings.append(f"{label}: no evidence qualifier (who supplies it, and its limits)")
        if not str(row.get("scope", "")).strip():
            warnings.append(f"{label}: no scope and time (people, place, period, units, denominator)")

    counts = {s: 0 for s in STATUSES}
    for row in rows:
        status = str(row.get("status", "")).strip()
        if status in counts:
            counts[status] += 1

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "rows": len(rows),
        "status_counts": counts,
        "material_blocking": sum(
            1
            for r in rows
            if r.get("material", True) and str(r.get("status", "")).strip() in BLOCKING_STATUSES
        ),
    }


def _coerce_issues(issues: Any) -> list[dict[str, Any]]:
    if issues in (None, "", []):
        return []
    if isinstance(issues, str):
        try:
            issues = json.loads(issues)
        except json.JSONDecodeError as exc:
            raise ValueError(f"issues must be JSON: {exc}") from exc
    if not isinstance(issues, list):
        raise ValueError("issues must be an array")
    out = []
    for item in issues:
        if not isinstance(item, dict):
            raise ValueError("each issue must be an object with level, reason, and optional claim_id")
        try:
            level = int(item.get("level", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("issue level must be an integer 1-5") from exc
        if level not in ESCALATION_LEVELS:
            raise ValueError("issue level must be an integer 1-5")
        out.append(
            {
                "claim_id": str(item.get("claim_id", "")).strip(),
                "level": level,
                "label": ESCALATION_LEVELS[level],
                "reason": str(item.get("reason", "")).strip(),
                "owner": str(item.get("owner", "Responsible human editor")).strip(),
            }
        )
    return out


def publication_gate(raw_ledger: str, issues: Any = None) -> dict[str, Any]:
    """Return the strongest defensible decision, with blocking reasons."""
    validation = validate_ledger(raw_ledger)
    rows, _ = parse_ledger(raw_ledger)
    issue_list = _coerce_issues(issues)

    blocking_claims = [
        row
        for row in rows
        if row.get("material", True) and str(row.get("status", "")).strip() in BLOCKING_STATUSES
    ]
    blocking_issues = [i for i in issue_list if i["level"] >= 2]

    blockers: list[dict[str, str]] = []
    for row in blocking_claims:
        blockers.append(
            {
                "kind": "claim",
                "id": str(row.get("claim_id", "")).strip() or "(no ID)",
                "reason": f"{row.get('status')}: {row.get('gap') or 'gap not stated'}",
                "action": str(row.get("action", "")).strip() or "Obtain evidence, narrow, attribute, or remove.",
            }
        )
    for issue in blocking_issues:
        blockers.append(
            {
                "kind": "issue",
                "id": issue["claim_id"] or "(unassigned)",
                "reason": f"Level {issue['level']} — {issue['label']}: {issue['reason'] or 'reason not stated'}",
                "action": f"Refer to {issue['owner']} before release.",
            }
        )

    if not validation["valid"]:
        blockers.insert(
            0,
            {
                "kind": "ledger",
                "id": "(ledger)",
                "reason": "The claim ledger is invalid: " + "; ".join(validation["errors"][:4]),
                "action": "Fix every ledger error before requesting a decision.",
            },
        )

    decision = "NOT READY" if blockers else "READY FOR HUMAN EDITOR REVIEW"

    counts = validation["status_counts"]
    block_text = (
        "PUBLICATION DECISION\n\n"
        "Review date:\n"
        "Assistant review scope:\n"
        "Evidence reviewed:\n"
        "Ledger status counts: "
        + "; ".join(f"{s} {counts.get(s, 0)}" for s in STATUSES)
        + "\n"
        "Meaning and quotation check:\n"
        "Journalism review:\n"
        "Craft review (feature work only; separate from journalism review):\n"
        "Open issues and escalation levels:\n"
        f"Decision: {decision}\n"
        "Blocking claim IDs and reasons: "
        + ("; ".join(f"{b['id']} — {b['reason']}" for b in blockers) if blockers else "None identified after review")
        + "\n"
        "Required next actions and evidence: "
        + ("; ".join(b["action"] for b in blockers) if blockers else "None identified after review")
        + "\n"
        "Responsible human editor:\n"
        "Human editor's final decision and date: PENDING HUMAN REVIEW\n"
    )

    return {
        "decision": decision,
        "blocking": blockers,
        "non_blocking_issues": [i for i in issue_list if i["level"] == 1],
        "status_counts": counts,
        "ledger_validation": {
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        },
        "decision_block": block_text,
        "rules_applied": [
            "NOT READY when a material claim is PARTIALLY_SUPPORTED, CONFLICTED, CONTRADICTED, UNCHECKED, or UNSUPPORTED.",
            "NOT READY when an open escalation level 2-5 issue is unresolved.",
            "Level 1 stylistic issues do not block release.",
            "Even READY FOR HUMAN EDITOR REVIEW is not approval; only the responsible human editor decides.",
        ],
        "disclaimer": (
            "This gate reads the ledger and issues you supplied. It cannot detect a claim you forgot to list, "
            "a fabricated source entered as SUPPORTED, or a fairness problem nobody recorded."
        ),
    }
