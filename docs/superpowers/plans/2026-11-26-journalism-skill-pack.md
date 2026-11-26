# Journalism Skill Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a portable, validated journalism Agent Skills pack with explicit editorial guardrails, examples, documentation, and a safe Git push workflow.

**Architecture:** Two self-contained skill directories sit under `skills/`; each carries the same guardrail reference so it can be installed alone. Standard-library Python validation and synthetic examples provide deterministic checks, while a preview-first shell helper protects the GitHub publishing workflow.

**Tech Stack:** Markdown, YAML frontmatter, Python 3 standard library, unittest, GitHub Actions, Bash, Git.

**Spec:** `docs/superpowers/specs/2026-11-26-journalism-skill-pack-design.md`

## Global Constraints

- Public package root: `C:\Users\Ma Christine\Downloads\JOURNALISM`.
- Remote: `https://github.com/aaronher1030-glitch/mcp-SchoolJournalismPH.git`.
- Default branch: `main`.
- Skill names: `journalism-humanizer`, `feature-writing`.
- Portable frontmatter fields only: `name`, `description`.
- Evidence statuses: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONFLICTED`, `CONTRADICTED`, `UNCHECKED`, `UNSUPPORTED`.
- Private source folder `journalism-humanizer/` must remain ignored and uncommitted.
- No MCP server, API keys, detector targeting, invented reporting, or automatic staging/committing in the push helper.
- Python validator must use only the standard library.
- All examples must be synthetic.
- Human publication approval is mandatory.

---

### Task 1: Core Skills and Shared Guardrails

**Files:**
- Create: `skills/journalism-humanizer/SKILL.md`
- Create: `skills/journalism-humanizer/references/editorial-guardrails.md`
- Create: `skills/journalism-humanizer/references/verification-output.md`
- Create: `skills/feature-writing/SKILL.md`
- Create: `skills/feature-writing/references/editorial-guardrails.md`
- Create: `skills/feature-writing/references/feature-craft.md`

**Interfaces:**
- Consumes: The design spec and existing source skill text in `journalism-humanizer/SKILL.md` and `journalism-humanizer/feature-writing/SKILL.md`.
- Produces: Two portable skills with identical `editorial-guardrails.md` files and stable claim-status vocabulary.

- [ ] **Step 1: Write the shared guardrail reference**

Include the authority statement, nine universal rules, twelve-item NOT DO list, five pre-publication check groups, claim-ledger fields, six evidence statuses, and five escalation levels exactly as defined in the spec.

- [ ] **Step 2: Write the humanizer skill**

Use this frontmatter shape:

```yaml
---
name: journalism-humanizer
description: Edit journalism copy for clarity, rhythm, and voice while preserving facts, exact quotations, attribution, sourcing, uncertainty, and scope. Use for news stories, features, captions, scripts, newsletters, or any draft that needs a faithful line edit and verification record.
---
```

Include when to use, when not to use, workflow, required output, and a short NOT DO summary linking to `references/editorial-guardrails.md`.

- [ ] **Step 3: Write the feature-writing skill**

Use this frontmatter shape:

```yaml
---
name: feature-writing
description: Plan, draft, critique, or revise reported journalism features with a clear angle, reader interest, strong structure, and ethical evidence-led storytelling. Use for profiles, human-interest, explanatory, service, and campus-press features, including work governed by a supplied contest rubric.
---
```

Include assignment intake, angle, reporting audit, evidence-bound form, structure, controlled prose, separate journalism/craft review, required output, rubric-scope warning, and a short NOT DO summary linking to the shared guardrails.

- [ ] **Step 4: Add focused references**

`verification-output.md` defines the claim-ledger table and publication-decision block. `feature-craft.md` defines diagnostic craft signals and rubric-use rules without inventing universal weights.

- [ ] **Step 5: Verify skill structure and guardrail parity**

Run:

```bash
python -c "from pathlib import Path; a=Path('skills/journalism-humanizer/references/editorial-guardrails.md').read_bytes(); b=Path('skills/feature-writing/references/editorial-guardrails.md').read_bytes(); assert a == b"
```

Expected: exit code 0.

- [ ] **Step 6: Review and commit**

Review for fabricated guidance, vague claims, and missing output sections. Commit only Task 1 files.

---

### Task 2: Human Entry Point, Examples, and Documentation

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `examples/README.md`
- Create: `examples/line-edit/input.md`
- Create: `examples/line-edit/expected-output.md`
- Create: `examples/line-edit/expected-checks.md`
- Create: `examples/feature/input.md`
- Create: `examples/feature/expected-output.md`
- Create: `examples/feature/expected-checks.md`
- Create: `docs/INSTALL.md`
- Create: `docs/RESEARCH.md`
- Create: `docs/PUBLISHING.md`

**Interfaces:**
- Consumes: Task 1 skill contracts and guardrail vocabulary.
- Produces: A GitHub-ready README, synthetic fixtures, installation/publishing instructions, research notes, MIT license, and ignore rules.

- [ ] **Step 1: Write the root README**

Include: one-sentence purpose, explicit “no MCP server” note, skill catalog, quick start, prominent NOT DO list, required human review, limits, repository map, installation link, validation commands, publishing link, and license.

- [ ] **Step 2: Write synthetic examples**

Line-edit input must contain a conditional quotation, two conflicting counts with different scopes, and a sparse hearing note under pressure to add color. Expected output must preserve the quote condition, keep counts separate, mark missing scope unchecked, and refuse invented reactions.

Feature input must ask for a campus-press feature without supplying a rubric. Expected output must request the current official rubric, avoid universal weights, and tie any scene or angle to supplied evidence.

- [ ] **Step 3: Write installation and publishing docs**

`INSTALL.md` covers portable `.agents/skills/`, Claude `.claude/skills/`, Cursor `.cursor/skills/`, Gemini `.gemini/skills/`, and Qoder `.qoder/skills/` locations, plus manual `SKILL.md` fallback. State that actual host behavior varies and no MCP is required.

`PUBLISHING.md` documents initialization, origin setup, review/commit, preview, push, and authentication failure handling. It must say the helper never stages or commits automatically.

- [ ] **Step 4: Update research notes**

Retain useful journalism sources and separate optional MCP research from the portable pack. Correct stale paths and identify the Agent Skills specification, GitHub skill documentation, SPJ ethics code, Pulitzer guidance, and Nieman craft guidance as references.

- [ ] **Step 5: Add license and ignore rules**

Use MIT License with `Copyright (c) 2026 Aaron Y. Hernandez`. Ignore `.DS_Store`, `Thumbs.db`, `__pycache__/`, `*.pyc`, `.env`, and the entire existing `journalism-humanizer/` source folder.

- [ ] **Step 6: Review and commit**

Check that every relative link resolves and no real student article text appears in examples. Commit only Task 2 files.

---

### Task 3: Deterministic Validator, Tests, and CI

**Files:**
- Create: `scripts/validate.py`
- Create: `tests/test_validate.py`
- Create: `.github/workflows/validate.yml`

**Interfaces:**
- Consumes: The repository layout and portable metadata contract.
- Produces: `validate_repository(root: Path) -> list[str]` and a CLI exiting 0 for valid packages and 1 for invalid packages.

- [ ] **Step 1: Write failing validator tests**

Include tests for:

```python
def test_valid_minimal_package_passes(self):
    errors = validate_repository(self.valid_root)
    self.assertEqual(errors, [])

def test_name_directory_mismatch_fails(self):
    self.write_skill("wrong-name")
    errors = validate_repository(self.valid_root)
    self.assertTrue(any("does not match" in error for error in errors))

def test_guardrail_mismatch_fails(self):
    Path(self.valid_root, "skills/feature-writing/references/editorial-guardrails.md").write_text("different", encoding="utf-8")
    errors = validate_repository(self.valid_root)
    self.assertTrue(any("guardrail" in error for error in errors))
```

The fixture must create both skills, references, examples, `.gitignore`, and a `journalism-humanizer/` directory to test ignore behavior.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: import failure because `scripts/validate.py` does not exist yet.

- [ ] **Step 3: Implement the validator**

Implement `validate_repository(root: Path) -> list[str]` with checks for required files, frontmatter parsing, ASCII name pattern, 1–64 character name, 1–1024 character description, directory/name agreement, required references, byte-identical guardrails, synthetic example files, unresolved markers, private-folder ignore rule, and absence of tracked private paths in `.gitignore` exceptions.

CLI:

```bash
python scripts/validate.py
```

Print each error prefixed with `ERROR:` and exit 1; otherwise print `Validation passed.` and exit 0.

- [ ] **Step 4: Run tests and validator**

Run:

```bash
python -m unittest discover -s tests -v
python scripts/validate.py
```

Expected: all tests pass and `Validation passed.`

- [ ] **Step 5: Add CI**

Use GitHub Actions with `actions/checkout@v4`, `actions/setup-python@v5`, Python 3.12, and the two commands above. Trigger on push and pull request.

- [ ] **Step 6: Review and commit**

Review validator failures for clarity and ensure no third-party dependency was added. Commit only Task 3 files.

---

### Task 4: Safe Push Helper and Git Setup

**Files:**
- Create: `scripts/safe-push.sh`
- Modify: `.gitignore` only if review finds a missing local artifact pattern.

**Interfaces:**
- Consumes: `scripts/validate.py`, Git metadata, and the expected remote URL.
- Produces: A preview-first helper with `--push` as the only publishing mode.

- [ ] **Step 1: Write helper behavior tests as shell scenarios**

Document and exercise these cases in `docs/PUBLISHING.md`:

1. No arguments prints status, validation result, branch, origin, and planned `git push origin main` without network access.
2. `--push` on a dirty tree exits before validation or network access.
3. `--push` with an unexpected origin exits before network access.
4. `--push` with failed validation exits before network access.
5. Unknown options exit with usage text.

- [ ] **Step 2: Implement `safe-push.sh`**

The script must:

- Resolve the repository root from its own location.
- Require `.git` to exist; do not initialize automatically.
- Require origin to equal the expected HTTPS URL.
- Require branch `main`.
- Reject force-push flags and unknown options.
- Run `python scripts/validate.py`.
- Require a clean tree with `git diff --quiet` and `git diff --cached --quiet`.
- In preview mode, print status and planned command, then exit.
- In `--push` mode, run `git push --dry-run origin main`, then `git push origin main`.
- Never run `git add`, `git commit`, `git config`, or `git push --force`.

- [ ] **Step 3: Make executable and test preview**

Run:

```bash
chmod +x scripts/safe-push.sh
bash scripts/safe-push.sh
```

Expected: preview only, no network publication.

- [ ] **Step 4: Review and commit**

Review shell quoting, Windows/Git Bash compatibility, and failure exits. Commit the helper.

---

### Task 5: Integration, Review, Commit, and Push

**Files:**
- Modify: Any public package file required to resolve integration findings.
- Do not modify or commit: `journalism-humanizer/`.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: A validated public repository pushed to `origin/main`.

- [ ] **Step 1: Run full local verification**

```bash
python scripts/validate.py
python -m unittest discover -s tests -v
bash -n scripts/safe-push.sh
bash scripts/safe-push.sh
```

Expected: validation passes, tests pass, shell syntax passes, and preview reports the expected remote and branch.

- [ ] **Step 2: Run independent review**

Dispatch a fresh reviewer to check spec coverage, privacy exclusions, portable metadata, link integrity, NOT DO prominence, helper safety, and absence of placeholders. Apply only verified findings.

- [ ] **Step 3: Initialize Git if needed**

```bash
git init -b main
git remote add origin https://github.com/aaronher1030-glitch/mcp-SchoolJournalismPH.git
```

If Git or origin already exists, verify rather than overwrite.

- [ ] **Step 4: Confirm ignored source folder**

```bash
git check-ignore -v journalism-humanizer
git status --short
```

Expected: the source folder is ignored and no private article path appears in status.

- [ ] **Step 5: Stage reviewed public files and commit**

Stage explicit paths only. Review `git diff --cached` before committing. Use a concise commit message such as `feat: publish portable journalism skill pack`.

- [ ] **Step 6: Push with the helper**

```bash
bash scripts/safe-push.sh --push
```

If authentication fails, report the exact failure and leave the validated commit intact; do not store credentials or alter authentication settings.

- [ ] **Step 7: Verify remote state**

```bash
git status --short --branch
git ls-remote origin refs/heads/main
```

Expected: clean working tree and remote `main` at the local commit.

- [ ] **Step 8: Final report**

Report repository URL, commit SHA, validation/test results, pushed files, and the explicit privacy exclusion for the source folder.
