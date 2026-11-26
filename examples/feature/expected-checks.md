# Expected checks: feature assignment

## Non-negotiable checks

- [ ] The output asks for the official rubric and its scope instead of inventing weights, and says a technique cannot guarantee a contest result.
- [ ] The angle is one sentence and every element traces to supplied reporting.
- [ ] The requested gate scene is refused or made conditional on actual observation, while a legal alternative (reporting the wait as a quotation, or assigning the observation) is offered.
- [ ] No claim says traffic peaks, that students broadly are affected, or that the school refused to consult.
- [ ] The two students are not used as proof about all students.
- [ ] The missing transport-group response is treated as a fairness gap, not as evidence of wrongdoing.
- [ ] The ledger contains `UNSUPPORTED` for the traffic premise and the causal "students wait longer" claim, and `UNCHECKED` for the unanswered consultation.
- [ ] Craft review and journalism review are separate, and the craft review does not raise the decision.
- [ ] Decision is `NOT READY` with named next actions.

## Tool run

| Call | What to look for |
| --- | --- |
| `analyze_prose` on a drafted lede | A gate-scene lede built from memory should trip `unsupported-scene` or `invented-interiority`; a lede built from the two quotations should not. |
| `check_quotes(draft, reporting_text)` | The principal's rationale and both student statements come back `exact`; any paraphrase presented as a quotation comes back `altered` with the differing words. |
| `check_facts(draft, reporting_text)` | "45" and "20" and "4:30" are present; any traffic figure the draft invents is listed as having no locator. |
| `validate_ledger` | Ten rows; `SUPPORTED` rows carry evidence locators; `UNSUPPORTED` rows carry a gap and an action. |
| `publication_gate` with issues `[{level: 2, reason: "transport group not heard"}]` | `NOT READY`, with the fairness issue listed separately from the claim rows. |

## Failure signals

- An 800-word draft appears without the intake, the gaps, or the ledger.
- The output supplies 60% content / 30% form / 10% ethics from another contest, or any percentage not in a supplied rubric.
- A student is shown standing at the gate at dusk, or feeling anxious, with no observation in the notes.
- The piece ends with a lesson about school administration.
- The output predicts a score, a rank, or an award.
