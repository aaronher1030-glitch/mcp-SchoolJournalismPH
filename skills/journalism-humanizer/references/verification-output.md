# Verification Output

Use this reference to report evidence review without confusing prose quality, claim support, and publication approval. Apply the full [editorial guardrails](editorial-guardrails.md) first.

## Claim-ledger table

Create one row per material claim, including claims in headlines, captions, and scripts. Split a sentence when its clauses need separate evidence. Keep the claim as written so a later editor can locate it. If an edit changes the claim, update the row and reassess its status.

| Claim ID | Draft location | Claim as written | Claim type | Evidence and locator | Evidence qualifier | Scope and time | Evidence status | Conflict or gap | Required action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-001 | Paragraph 2 | Exact assertion or quotation | Fact / direct quotation / paraphrase / attribution / statistic / causal claim / allegation / observation / interpretation | Source title or ID plus page, paragraph, table, URL, note ID, or recording timecode | Who or what supplies it; direct or indirect; authority and coverage limits | People, place, period, units, denominator, and other boundaries | One exact status from the table below | Contradiction, missing context, absent corroboration, or `None identified` after review | Retain / revise / narrow / attribute / corroborate / remove / hold, with the needed evidence if open |

### Status values

Use exactly one value per row:

- `SUPPORTED` — adequate evidence supports the wording and scope reviewed.
- `PARTIALLY_SUPPORTED` — only part, a narrower scope, or weaker certainty is supported; identify and resolve the remainder.
- `CONFLICTED` — credible evidence or accounts disagree; preserve their sources and scopes.
- `CONTRADICTED` — reliable evidence directly conflicts with the claim as written.
- `UNCHECKED` — verification is incomplete or necessary evidence is unavailable; name the check needed.
- `UNSUPPORTED` — review found no adequate evidence; do not retain the claim as established fact.

Do not substitute `verified`, `disputed`, `false`, a percentage confidence, or a blank cell for a status. The full definitions and handling rules are in [editorial-guardrails.md](editorial-guardrails.md#six-evidence-statuses).

## Meaning and verification check

After the ledger, report these checks explicitly:

1. **Meaning comparison** — compare the untouched draft with the edited copy passage by passage. List any change to facts, quotation wording, attribution, uncertainty, scope, or causality, or state that none was identified after review.
2. **Quotation integrity** — identify every direct quotation checked and its recording, transcript, note, or document locator. State whether each remains exact. For indirect speech, identify the source and confirm that no qualification was added or removed.
3. **Evidence coverage** — state which claims were checked, which could not be checked, what sources were used, and any limits on those sources. A prose pass is not an evidence pass.
4. **Unresolved issues** — map each material gap or conflict to its claim ID, escalation level, required reporting or decision, and responsible human owner.

Never describe the whole article as true merely because some rows are `SUPPORTED`. Do not perform or claim a check when the needed source was unavailable.

## Publication-decision block

Copy and complete this block at the end of the response. Do not omit fields; write `Not applicable` with a reason where a field does not apply.

```text
PUBLICATION DECISION

Review date:
Assistant review scope:
Evidence reviewed:
Ledger status counts: SUPPORTED __; PARTIALLY_SUPPORTED __; CONFLICTED __; CONTRADICTED __; UNCHECKED __; UNSUPPORTED __
Meaning and quotation check:
Journalism review:
Craft review (feature work only; separate from journalism review):
Open issues and escalation levels:
Decision: READY FOR HUMAN EDITOR REVIEW | NOT READY
Blocking claim IDs and reasons:
Required next actions and evidence:
Responsible human editor:
Human editor's final decision and date: PENDING HUMAN REVIEW
```

### Decision rules

- Choose `NOT READY` when material evidence is missing, unsupported, conflicted, contradicted, or only partially supports the wording. A material missing quotation record or source scope is enough to block release.
- Also choose `NOT READY` when a serious fairness, privacy, source-protection, legal, or suspected-fabrication issue awaits responsible human review.
- Choose `READY FOR HUMAN EDITOR REVIEW` only when no unresolved material issue remains within the stated review scope. This means the assistant review is complete enough for editorial consideration; it does not mean approved or published.
- If evidence supports a narrower or differently qualified statement, make that change, reassess the claim, and record what happened. Do not mark the original claim `SUPPORTED` merely because a replacement is supportable.
- The responsible human editor completes the final decision and date after independent review. The assistant must never fill that field as approval.
