# MCP Server Reference

`mcp_server/` is a Model Context Protocol server for the skills in this repository. JSON-RPC 2.0 over stdio, Python standard library only, no network calls, no API keys.

## Requirements

Python 3.9 or newer. Nothing else. Verify:

```bash
python -m mcp_server --version     # school-journalism-ph 1.0.0
python -m mcp_server --self-test   # runs initialize, tools, resources, prompts, a scan, and the gate
```

Run the server with:

```bash
python -m mcp_server
```

It reads one JSON object per line on stdin and writes one per line on stdout. It logs nothing to stdout, so a host can parse it safely. Set `MCP_SCHOOL_JOURNALISM_DEBUG=1` to get diagnostics on stderr.

## Protocol surface

| Method | Behavior |
| --- | --- |
| `initialize` | Negotiates `2025-06-18` (or the client's version when supported: `2025-03-26`, `2024-11-05`) and returns server capabilities and instructions. |
| `ping` | Returns `{}`. |
| `tools/list`, `tools/call` | Nine tools, listed below. |
| `resources/list`, `resources/read` | The skills, references, and the brief as read-only markdown. |
| `prompts/list`, `prompts/get` | Three workflow prompts. |
| notifications | Accepted silently (`notifications/initialized`, `notifications/cancelled`, and others). |

Unknown methods return `-32601`; bad arguments return `-32602`; caller mistakes inside a tool return a normal tool result with `isError: true` so the conversation can continue.

## Tools

### `journalism_brief`

No arguments. Returns `docs/QUICK-BRIEF.md` plus the installed skill list. This is the cheap first call: about a page, enough to route the task without loading 6,000 words of references.

### `get_skill`

`name`: `feature-writing` | `journalism-humanizer`. Returns the full `SKILL.md` body.

### `get_reference`

`name`: `editorial-guardrails` | `feature-craft` | `verification-output`. Returns the reference text and its path. `editorial-guardrails` exists in both skills byte-identically; the response lists both copies under `also_at`.

### `analyze_prose`

`text` (required), `mode` (`feature`|`news`|`any`), `voice_sample` (optional), `max_findings` (1–200).

Returns:

- `stats` — words, sentences, paragraphs, average and standard deviation of sentence length, longest sentence, sentences over 40 words, adverb/passive/nominalization/em-dash density per 1,000 words.
- `findings` — each with `rule`, `severity`, `line`, `match`, `excerpt`, `note`, and a `fix` technique. Categories: formulaic openers, slop phrases, pseudo-profundity, invented interiority, inferred physical reactions, generic scene beats, unattributed claims, mechanical transitions, inflated wording, stacked hedging, empty intensifiers, editorializing, loaded adjectives, news clichés, vague quantities, plus rhythm findings (monotony, run-ons, dense paragraphs, repeated openers, adverb/passive/nominalization density, em-dash overuse).
- `signal` — `mechanical`, `mixed`, or `clear`, with the reasons. Diagnostic only.
- `voice_comparison` — when a sample is supplied, measured rhythm and formality deltas, not an imitation.

Every rule is a heuristic over surface text. The tool deliberately returns no rewritten prose: wording must come from the reporting, not from a pattern library.

### `check_quotes`

`draft`, `source_text`, `min_similarity` (0.5–0.99, default 0.6).

Extracts double- and single-quoted spans, normalizes whitespace and quote glyphs, then locates each in the source: exact, altered with a word-level `differences` list and the closest `source_span`, or `not_found`. `not_found` means "no record in the material you supplied" — it is not a fabrication finding.

### `check_facts`

`draft`, `source_text`. Lists draft numbers and candidate proper names that do not appear in the supplied material, so each needs a locator or `UNCHECKED`. Presence is not support; absence is not falsity.

### `diff_meaning`

`original`, `edited`. Reports lost and added numbers and names, quotations that no longer appear verbatim, qualifier density per 1,000 words (`may`, `could`, `alleged`, `according to`, `at least`, …), and a `risk` level.

### `validate_ledger`

`ledger` as a JSON array of claim objects or the markdown claim-ledger table. Accepts human column headers (`Claim ID`, `Evidence status`, …) or snake_case keys. Checks required fields, the six exact statuses, duplicate IDs, and the required action and gap on every non-`SUPPORTED` row. Returns errors, warnings, counts, and the number of material blocking rows.

### `publication_gate`

`ledger`, plus optional `issues` (`claim_id`, `level` 1–5, `reason`, `owner`).

Implements the rules in `verification-output.md`:

- `NOT READY` if a material claim is `PARTIALLY_SUPPORTED`, `CONFLICTED`, `CONTRADICTED`, `UNCHECKED`, or `UNSUPPORTED`.
- `NOT READY` if any level 2–5 issue is open. Level 1 (stylistic) does not block.
- Otherwise `READY FOR HUMAN EDITOR REVIEW`.

Returns `blocking` with an action per item, `decision_block` ready to paste, and `rules_applied`. The human editor's line stays `PENDING HUMAN REVIEW`, and no input can make this tool return an approval.

## Resources

| URI | Content |
| --- | --- |
| `journalism://brief` | `docs/QUICK-BRIEF.md` |
| `skill://feature-writing` | The feature workflow |
| `skill://journalism-humanizer` | The line-edit workflow |
| `reference://editorial-guardrails` | Shared rules and escalation levels |
| `reference://feature-craft` | Craft signals and rubric-use rules |
| `reference://verification-output` | Ledger table and decision block |

## Prompts

| Prompt | Arguments | Use |
| --- | --- | --- |
| `feature-draft` | `assignment` (required), `reporting`, `rubric` | Runs the feature workflow with the analysis tools as a check loop. |
| `line-edit` | `draft` (required), `evidence`, `style` | Runs the humanizer workflow with `diff_meaning` and `check_quotes` before returning. |
| `contest-review` | `draft`, `rubric` (both required) | Maps a feature to the exact supplied rubric without predicting a score. |

## Host setup

### Claude Code

From the repository root:

```bash
claude mcp add school-journalism-ph -- python -m mcp_server
claude mcp list
```

Or use the committed `.mcp.json` (project scope) by approving it on first start.

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "school-journalism-ph": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": { "PYTHONPATH": "C:/absolute/path/to/mcp-SchoolJournalismPH" }
    }
  }
}
```

On macOS or Linux, use `/absolute/path/to/mcp-SchoolJournalismPH`. `PYTHONPATH` lets `-m mcp_server` resolve from any working directory; otherwise set `cwd` if your host supports it, or pass the script path directly:

```json
{ "command": "python", "args": ["C:/absolute/path/to/mcp-SchoolJournalismPH/mcp_server/__main__.py"] }
```

### Cursor

`.cursor/mcp.json` in the project, or the same block in Cursor's global MCP settings:

```json
{
  "mcpServers": {
    "school-journalism-ph": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": { "PYTHONPATH": "${workspaceFolder}" }
    }
  }
}
```

### VS Code (Copilot agent mode)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "school-journalism-ph": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": { "PYTHONPATH": "${workspaceFolder}" }
    }
  }
}
```

### Any other host

Any MCP client that supports stdio works. The command is `python`, the argument is `-m mcp_server`, and the working directory (or `PYTHONPATH`) must be this repository.

## Efficiency notes

The server is built for a short context budget:

- `journalism_brief` is about 900 words; a full skill is about 1,300; a reference is 1,500–3,000. Load in that order and only as far as the task needs.
- Tool responses return counts in full but cap repeated examples, so a draft with 40 slop phrases does not produce 40 near-identical entries.
- `analyze_prose` returns fix *techniques*, not replacement sentences. That keeps the response small and prevents a pattern library from writing the story.
- The gate returns the decision block already filled, so the model does not need a second pass to format it.

## Limits

The server is deterministic text processing. It does not know journalism, it does not read the web, and it does not verify anything. It flags patterns and applies rules you can read in `mcp_server/analysis.py` and `mcp_server/ledger.py`. Treat every result as a prompt to look, and keep the human editor in the loop.
