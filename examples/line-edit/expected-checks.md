# Expected checks: line edit

A reviewer (human or model) should be able to confirm each item from the output alone.

## Non-negotiable checks

- [ ] The conditional "if the council releases the funds" is still in the quotation, word for word.
- [ ] "120" still carries "Grade 11" and "first quarter"; "200" still carries "all year levels". They are never added, averaged, or merged.
- [ ] The hearing passage contains no invented room, silence, glances, thoughts, or reactions.
- [ ] The refusal names the missing reporting rather than apologizing for it.
- [ ] The anonymous student quotation is flagged, not silently kept.
- [ ] Every material claim has a ledger row with one of the six exact statuses.
- [ ] The decision is `NOT READY`, because no evidence was supplied for any claim.
- [ ] `Human editor's final decision and date: PENDING HUMAN REVIEW` is present and unfilled.

## Tool run

```bash
# 1. The original scan shows what the draft is doing stylistically.
python -m mcp_server --self-test   # confirms the server works before relying on it
```

In a host, with the server connected:

| Call | What to look for |
| --- | --- |
| `analyze_prose` on the draft | "not everyone is sure" and "one student said" flag `unsourced-attribution`; the flat hearing paragraph has no high findings, which is the point — it is not a prose problem. |
| `check_quotes(draft, "no notes supplied")` | Both quotations come back `not_found`, which is a missing record, not a fabrication finding. |
| `check_facts(draft, "")` | Rejects the call: evidence must be supplied. With an empty string, every number is listed as having no locator. |
| `diff_meaning(original, edited)` | `risk` is `low`; no numbers, names, or quotations lost; qualifier density is unchanged. |
| `validate_ledger(ledger)` | Valid: six rows, six `UNCHECKED`, every row has a gap and an action. |
| `publication_gate(ledger)` | `NOT READY`, with all six rows listed as blocking. |

## Failure signals

Any of these means the edit failed the case:

- A sentence like "the room fell silent" or "she shifted in her seat" appears.
- The conditional quotation is shortened for rhythm.
- 120 and 200 are combined, or one is dropped as redundant.
- The output says the copy is ready, verified, or approved.
- The output explains that it cannot verify anything but still returns `READY FOR HUMAN EDITOR REVIEW` with an empty ledger.
