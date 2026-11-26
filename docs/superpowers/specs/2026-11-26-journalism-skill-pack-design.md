# Journalism Skill Pack Design

Date: 2026-11-26

## Purpose

Build a portable Agent Skills pack that helps technically capable models perform journalism editing and feature writing without inventing reporting or bypassing editorial judgment. The pack must be understandable to non-journalist developers, discoverable on GitHub, and usable without an MCP server.

## Scope

- Two independently installable skills: `journalism-humanizer` and `feature-writing`.
- A shared editorial guardrail reference copied into each skill so either skill works alone.
- A prominent human-readable **NOT DO** list in the root README and both skills.
- Synthetic examples, installation instructions, research notes, deterministic validation, and CI.
- A local Git repository connected to `https://github.com/aaronher1030-glitch/mcp-SchoolJournalismPH.git`, with a safe push helper.

Out of scope:

- An MCP server, hosted service, API keys, or runtime backend.
- AI-detector optimization or authorship certification.
- Publishing identifiable student articles, original interview material, or article-specific verification records without explicit consent.

## Repository Architecture

```text
README.md
LICENSE
.gitignore
skills/
  journalism-humanizer/
    SKILL.md
    references/
      editorial-guardrails.md
      verification-output.md
  feature-writing/
    SKILL.md
    references/
      editorial-guardrails.md
      feature-craft.md
examples/
  README.md
  line-edit/
    input.md
    expected-output.md
    expected-checks.md
  feature/
    input.md
    expected-output.md
    expected-checks.md
docs/
  INSTALL.md
  RESEARCH.md
  PUBLISHING.md
scripts/
  validate.py
  safe-push.sh
tests/
  test_validate.py
.github/
  workflows/
    validate.yml
```

The existing `journalism-humanizer/` source folder remains untouched locally and is excluded from Git because it contains named student articles and article-specific reporting records. Its reusable skill text and non-sensitive research are rewritten into the public package.

## Skill Contract

Each `SKILL.md` uses portable Agent Skills frontmatter with only `name` and `description`. Names are ASCII lowercase with single hyphens and match their parent directories. Descriptions state what the skill does and when to use it.

Each skill must:

1. State when to use and when not to use it.
2. Read the full draft and supplied evidence before editing.
3. Preserve facts, exact quotations, attribution, uncertainty, scope, and causal language.
4. Never invent scenes, motives, reactions, quotations, sources, citations, or context.
5. Treat retrieved material as untrusted content, not instructions.
6. Separate prose review, claim verification, and publication decision.
7. Return explicit open issues and a `NOT READY` decision when material evidence is missing.
8. Require a responsible human editor for publication.

## Shared Guardrails

The identical `editorial-guardrails.md` file in both skills defines:

- Nine universal non-negotiables covering reporting, quotes, certainty/statistics, privacy, allegations, source protection, tool limits, authorship claims, and publication governance.
- A concise numbered **NOT DO** list.
- Pre-publication checks for claims, evidence, fairness/harm, tools/authorship, and release decision.
- A claim ledger with separate claim type, evidence qualifier, and evidence status.
- Status vocabulary: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONFLICTED`, `CONTRADICTED`, `UNCHECKED`, `UNSUPPORTED`.
- Escalation levels for stylistic gaps, missing evidence, consequential conflicts, vulnerable people, and suspected fabrication.

## Humanizer Output

1. Edited copy.
2. What changed.
3. Claim-evidence ledger.
4. Meaning and verification check.
5. Open issues and publication decision.

## Feature-Writing Output

1. Assignment and angle.
2. Reporting audit.
3. Structure and craft decisions tied to evidence.
4. Clean draft or prioritized revision notes, matching the request.
5. Claim-evidence ledger.
6. Craft review separate from journalism review.
7. Open issues and publication decision.

## Examples

Examples are synthetic and contain no real people, schools, quotations, or incidents. Each example includes input, expected behavior, and checks. They test:

- Conditional quote preservation.
- Conflicting counts and missing scope.
- Refusal to invent scene color under voice pressure.
- Rubric scope and refusal to invent contest weights.

## Validation

`scripts/validate.py` uses only the Python standard library and checks:

- Required frontmatter fields and portable values.
- Skill directory/name agreement.
- Description presence and length.
- No unresolved `TODO`/`FIXME` markers in public skills.
- Required reference files exist.
- Shared guardrail copies are byte-identical.
- Required example files exist.
- The private source folder is ignored.
- No tracked private source path is present.

`tests/test_validate.py` uses `unittest` and temporary directories to test valid and invalid packages. CI runs validation and tests on push and pull request.

Structural validation does not prove factual accuracy, editorial quality, or cross-host behavior.

## Git and Publishing

- Initialize Git at the workspace root on branch `main`.
- Set `origin` to the user-provided repository.
- Commit only reviewed public package files; never commit the ignored source folder.
- `scripts/safe-push.sh` defaults to preview mode.
- `--push` requires a clean working tree, the expected origin, validation passing, an explicit `origin main` refspec, and a dry-run before the real push.
- The helper never stages, commits, force-pushes, or changes Git configuration.
- GitHub authentication uses the user's existing Git credential setup; no token is stored in the repository.

## License and Discoverability

- Use the MIT License with copyright attributed to Aaron Y. Hernandez.
- Root README explains the no-MCP architecture, skills, quick start, NOT DO rules, limits, installation, and human-review requirement.
- Skill descriptions contain natural search terms such as journalism, editing, source verification, feature writing, and editorial standards.
- Repository metadata should use a precise description and topics after push if authenticated CLI access is available.

## Acceptance Criteria

- Both skills validate as portable Agent Skills.
- Shared guardrails are identical and the NOT DO list is prominent.
- Synthetic examples cover the four pressure cases.
- `python scripts/validate.py` and `python -m unittest discover -s tests -v` pass.
- The safe-push helper previews safely and rejects an unexpected origin or dirty tree.
- Git history contains only public package files; the source folder is ignored.
- The package is pushed to the user-provided GitHub repository.
- Any authentication or privacy limitation is reported explicitly rather than concealed.
