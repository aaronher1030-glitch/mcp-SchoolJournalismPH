# Installation

Two ways to use this pack: as MCP tools (recommended, gives the model the checks) or as plain Agent Skills (no server, portable across hosts).

## Option 1 — MCP server

```bash
git clone https://github.com/aaronher1030-glitch/mcp-SchoolJournalismPH.git
cd mcp-SchoolJournalismPH
python -m mcp_server --self-test
```

Requires Python 3.9+. There is nothing to install: the server uses only the standard library.

Register it with your host — `claude mcp add school-journalism-ph -- python -m mcp_server` from the repository root, or the JSON blocks in [MCP.md](MCP.md). Then ask the model to call `journalism_brief` before writing.

Host behavior varies. Some clients surface tools automatically, some require a restart, and some need the server enabled per conversation. If the tools do not appear, check the host's MCP log first; a stdio server that exits immediately is almost always a wrong working directory or `PYTHONPATH`.

## Option 2 — Skills only

Each skill is a directory with a `SKILL.md` and a `references/` folder. Copy the skill directory into the location your host reads:

| Host | Location |
| --- | --- |
| Portable Agent Skills | `.agents/skills/<skill-name>/` |
| Claude Code | `.claude/skills/<skill-name>/` |
| Cursor | `.cursor/skills/<skill-name>/` |
| Gemini CLI | `.gemini/skills/<skill-name>/` |
| Qoder | `.qoder/skills/<skill-name>/` |

For example, for Claude Code:

```bash
mkdir -p .claude/skills
cp -r skills/feature-writing .claude/skills/
cp -r skills/journalism-humanizer .claude/skills/
```

Or install one skill only. Each carries its own copy of `editorial-guardrails.md`, so neither depends on the other.

Hosts that do not support skills at all can still use the pack: paste `SKILL.md` and the reference it links into the conversation, or point the model at it with `@`.

## Which skill to install

- **Feature writing** — planning, drafting, and critiquing reported features. Install this if the work is "write me a feature" or "review this feature".
- **Journalism humanizer** — line-editing existing copy with a verification record. Install this if the work is "tighten this" or "make this read like a person wrote it".

Both is normal: draft with `feature-writing`, then run `journalism-humanizer` on the result.

## Optional: project instructions

If your host reads `AGENTS.md` or `CLAUDE.md`, a short pointer helps the model choose correctly:

```markdown
For journalism drafting, editing, or critique, load the skill in
`.claude/skills/feature-writing` (drafting) or `.claude/skills/journalism-humanizer`
(line editing) before writing. Never invent scenes, quotations, sources, or
certainty. Return `NOT READY` when material evidence is missing, and leave the
publication decision to a responsible human editor.
```

## Verify the install

```bash
python scripts/validate.py
python -m unittest discover -s tests -v
```

`validate.py` checks structure, frontmatter, guardrail parity, and the server's tool registry. It cannot tell you whether the host loaded the skill.

## Updating

```bash
git pull
python -m mcp_server --self-test
```

If you copied skills into `.claude/skills`, re-copy after pulling. The MCP server reads from the repository, so it updates in place.
