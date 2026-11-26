# Research Notes

What this pack is built on, and what each source actually supports. Research run 2026-11-23 and 2026-11-24; links were checked during those runs and not re-verified for this revision. Re-check maintenance and availability before depending on any third-party tool.

## Protocols and packaging

- **Model Context Protocol.** The specification defines JSON-RPC 2.0 over stdio, tool/resource/prompt primitives, and capability negotiation. This server implements the stdio transport by hand so the pack needs no client library. Spec: <https://modelcontextprotocol.io/specification>. The protocol is versioned; this server negotiates `2025-06-18` and accepts `2025-03-26` and `2024-11-05`.
- **Agent Skills.** A skill is a directory with a `SKILL.md` carrying `name` and `description` frontmatter, plus optional references and scripts. Portable skills use only those two fields, which is why this pack avoids host-specific keys. Reference: <https://docs.claude.com/en/docs/agents-and-tools/agent-skills>.
- **Progressive disclosure.** The efficiency argument for skills is that a short description is always loaded and the full instructions only when relevant. This pack applies the same idea inside the server: brief, then skill, then reference, then tools. Anthropic's guidance on verification loops in agent work — gather context, act, check, correct — is the model for the measured edit loop: <https://claude.com/resources/articles/building-verification-loops-in-claude-code-with-skills>.

## Editing approach

- **[`hannsxpeter/humanizer`](https://github.com/hannsxpeter/humanizer)** — MIT-licensed prompt-based skill for revising AI-sounding prose: faithful meaning, a pre-edit scan for formulaic patterns, optional voice matching, and a meaning check. This pack does not copy it; it adds the journalism layer the upstream skill does not have: exact quotations, attribution, sourcing, uncertainty, scope, and a per-claim verification record. The upstream skill is an editing aid, not evidence that a text is true or human-written.
- **The pattern lists in `mcp_server/analysis.py`** are drawn from the common failure modes described across that skill, Nieman's craft guidance, and ordinary newsroom editing practice. They are heuristics, not a validated detector, and they are deliberately few and readable so an editor can disagree with a specific rule.

## Craft and standards

- **SPJ Code of Ethics** — accuracy, minimizing harm, independence, accountability: <https://www.spj.org/spj-code-of-ethics/>. The guardrails' privacy, harm, attribution, and accountability rules follow this structure.
- **Pulitzer Prize Feature Writing** — writing quality, originality, concision; the FAQ states category definitions are general guidance with no universal fixed rubric: <https://www.pulitzer.org/prize-winners-by-category/211>, <https://www.pulitzer.org/page/frequently-asked-questions>. This is why the pack refuses to invent weights.
- **Nieman Storyboard** on [reporting and writing scenes](https://niemanstoryboard.org/2023/04/20/narrative-journalism-reporting-writing-scenes/) and [story structure](https://niemanstoryboard.org/2022/02/02/sticking-a-story-together-and-nailing-the-structure/): scenes come from observation and notes; structure is chosen to serve the theme. The craft reference's "atmosphere without observation" failure mode comes from this.
- **DepEd Caraga 2026 RSPC score sheet** — one regional Philippine campus-press example with stated weights (30% form/style, 60% content, 10% ethics): <https://caraga.deped.gov.ph/wp-content/uploads/2026/01/Memo-2026-RSPC-Final-3signedsigned.pdf>. It is regional and year-specific. It is cited as an example of what a rubric looks like, never as a national default, and the pack refuses to apply it to a different event.

## Fact-checking tools: what they can and cannot do

These were considered for integration and are **not** bundled. The server does no network access.

- **World Bank Data360 MCP** — <https://github.com/worldbank/data360-mcp>. Searches indicator definitions and coverage and retrieves time series. Useful only when a claim matches a supported indicator, geography, and period; it cannot verify quotations, local incidents, or causal claims.
- **Chequeado Datilia** — <https://github.com/chequeado/datilia>. A journalism workflow that extracts statistical claims and consults Data360. Its README describes it as a prototype with statistical, country-level coverage. Good design reference, not a general fact-checker.
- **source-pack-mcp** — <https://github.com/SarutobiSasuke8/source-pack-mcp>. Assembles fetched pages into source-linked facts and quotes, and states that extraction confidence is not truth. An early project; inspect before adopting.

The reason none of these is wired in: a journalism tool that silently adds a citation is more dangerous than one that reports a gap. `check_facts` therefore reports *absence of a locator*, which is honest, rather than *presence of a match*, which would not be support.

## Design consequence

Everything in this repository is built so the model cannot launder an unsupported claim into a confident sentence. The prose tools return techniques, not replacement text. The ledger tool rejects a status outside the six. The gate can only return `NOT READY` or `READY FOR HUMAN EDITOR REVIEW`. The strongest claim anywhere is "the evidence I was shown supports this wording", and a human decides the rest.
