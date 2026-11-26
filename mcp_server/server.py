"""A dependency-free MCP server for the School Journalism PH skill pack.

Transport: JSON-RPC 2.0 over stdio, one JSON object per line (the MCP stdio
transport). No HTTP, no sockets, no third-party packages.

The design goal is progressive disclosure: `journalism_brief` is cheap and
answers the routing question, `get_skill` loads one full workflow, and
`get_reference` loads a deep reference only when a task needs it. The analysis
tools give a model a checkable loop, so improving a draft becomes measure, edit,
measure again instead of a single unaided guess.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable

from . import __version__
from .analysis import analyze_prose, check_facts, check_quotes, diff_meaning
from .ledger import publication_gate, validate_ledger
from .skills import SkillError, brief, list_skills, load_reference, load_skill

SERVER_NAME = "school-journalism-ph"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]


class McpError(Exception):
    """A protocol-level error that becomes a JSON-RPC error response."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class ToolInputError(ValueError):
    """A caller mistake that becomes a tool result with isError: true."""


def _log(message: str) -> None:
    if os.environ.get("MCP_SCHOOL_JOURNALISM_DEBUG"):
        print(f"[{SERVER_NAME}] {message}", file=sys.stderr, flush=True)


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)


def _require_text(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolInputError(f"'{key}' is required and must be a non-empty string")
    return value


# --------------------------------------------------------------------------- #
# Tool handlers
# --------------------------------------------------------------------------- #


def _tool_brief(args: dict[str, Any]) -> dict[str, Any]:
    skills = list_skills()
    text = brief().rstrip() + "\n\n## Installed skills\n\n" + "\n".join(
        f"- `{s['name']}` — {s['description']}" for s in skills
    )
    return {"text": text, "structured": {"skills": skills}}


def _tool_get_skill(args: dict[str, Any]) -> dict[str, Any]:
    name = _require_text(args, "name")
    try:
        skill = load_skill(name)
    except SkillError as exc:
        raise ToolInputError(str(exc)) from exc
    header = (
        f"# {skill['name']}\n\n{skill['description']}\n\n"
        f"Source: {skill['path']}\n\n---\n\n"
    )
    return {"text": header + skill["instruction"], "structured": skill}


def _tool_get_reference(args: dict[str, Any]) -> dict[str, Any]:
    name = _require_text(args, "name")
    try:
        ref = load_reference(name)
    except SkillError as exc:
        raise ToolInputError(str(exc)) from exc
    return {
        "text": f"<!-- {ref['path']} -->\n\n{ref['text']}",
        "structured": {"name": ref["name"], "path": ref["path"], "also_at": ref["also_at"]},
    }


def _tool_analyze(args: dict[str, Any]) -> dict[str, Any]:
    text = _require_text(args, "text")
    mode = str(args.get("mode", "feature"))
    if mode not in {"feature", "news", "any"}:
        raise ToolInputError("'mode' must be feature, news, or any")
    voice = args.get("voice_sample")
    if voice is not None and not isinstance(voice, str):
        raise ToolInputError("'voice_sample' must be a string when supplied")
    try:
        limit = int(args.get("max_findings", 40))
    except (TypeError, ValueError) as exc:
        raise ToolInputError("'max_findings' must be an integer") from exc
    result = analyze_prose(text, mode=mode, voice_sample=voice, max_findings=max(1, min(200, limit)))
    return {"text": _json(result), "structured": result}


def _tool_check_quotes(args: dict[str, Any]) -> dict[str, Any]:
    draft = _require_text(args, "draft")
    source = _require_text(args, "source_text")
    try:
        threshold = float(args.get("min_similarity", 0.6))
    except (TypeError, ValueError) as exc:
        raise ToolInputError("'min_similarity' must be a number") from exc
    result = check_quotes(draft, source, max(0.5, min(0.99, threshold)))
    return {"text": _json(result), "structured": result}


def _tool_check_facts(args: dict[str, Any]) -> dict[str, Any]:
    result = check_facts(_require_text(args, "draft"), _require_text(args, "source_text"))
    return {"text": _json(result), "structured": result}


def _tool_diff_meaning(args: dict[str, Any]) -> dict[str, Any]:
    result = diff_meaning(_require_text(args, "original"), _require_text(args, "edited"))
    return {"text": _json(result), "structured": result}


def _tool_validate_ledger(args: dict[str, Any]) -> dict[str, Any]:
    result = validate_ledger(_require_text(args, "ledger"))
    return {"text": _json(result), "structured": result}


def _tool_publication_gate(args: dict[str, Any]) -> dict[str, Any]:
    result = publication_gate(_require_text(args, "ledger"), args.get("issues"))
    return {"text": result["decision_block"], "structured": result}


# --------------------------------------------------------------------------- #
# Tool catalog
# --------------------------------------------------------------------------- #

_STR = {"type": "string"}

TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "journalism_brief",
        "title": "Journalism brief",
        "description": (
            "Start here. Returns one page: which skill fits the task, the workflow spine, the "
            "non-negotiables, and the required output sections. Cheap enough to call every time; "
            "load a full skill or reference only when the task needs it."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": _tool_brief,
    },
    {
        "name": "get_skill",
        "title": "Load a skill",
        "description": (
            "Return the complete SKILL.md workflow for `feature-writing` (plan, draft, critique, or "
            "revise a reported feature) or `journalism-humanizer` (faithful line edit with a "
            "verification record). Load this once at the start of a journalism task."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": ["feature-writing", "journalism-humanizer"],
                    "description": "Which skill to load.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "handler": _tool_get_skill,
    },
    {
        "name": "get_reference",
        "title": "Load a reference",
        "description": (
            "Return a deep reference document: `editorial-guardrails` (rules, NOT DO list, claim "
            "ledger fields, six statuses, escalation levels), `feature-craft` (diagnostic craft "
            "signals and rubric-use rules), or `verification-output` (ledger table and "
            "publication-decision block)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": ["editorial-guardrails", "feature-craft", "verification-output"],
                    "description": "Which reference to load.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "handler": _tool_get_reference,
    },
    {
        "name": "analyze_prose",
        "title": "Diagnose draft prose",
        "description": (
            "Deterministic surface diagnostics for a draft: machine-writing tells, stock phrases, "
            "invented interiority and inferred reactions, unattributed claims, hedging, inflated "
            "wording, rhythm (sentence-length variance, run-ons, repeated openers), adverb, passive "
            "and nominalization density. English and Filipino/Tagalog pattern lists are applied in "
            "the same pass, so a mixed draft needs no language setting. Optionally compares rhythm "
            "against a voice sample. Returns "
            "findings with line numbers and a specific fix technique — never rewritten text, because "
            "the model must supply wording grounded in the reporting."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The draft to diagnose."},
                "mode": {
                    "type": "string",
                    "enum": ["feature", "news", "any"],
                    "default": "feature",
                    "description": "Reporting context; affects labeling only.",
                },
                "voice_sample": {
                    "type": "string",
                    "description": "Optional sample of the target voice to compare rhythm and formality against.",
                },
                "max_findings": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 40,
                    "description": "Cap on returned findings; counts are always complete.",
                },
            },
            "required": ["text"],
            "additionalProperties": False,
        },
        "handler": _tool_analyze,
    },
    {
        "name": "check_quotes",
        "title": "Check quotation integrity",
        "description": (
            "Extract every direct quotation from the draft and locate it in the supplied notes, "
            "transcript, or document. Reports exact, altered (with a word-level diff and the closest "
            "source span), or not found. Use it before release; altered quotations are the most "
            "common way an edit changes what a source said."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "draft": {"type": "string", "description": "The draft containing the quotations."},
                "source_text": {
                    "type": "string",
                    "description": "The notes, transcript, or source document to compare against.",
                },
                "min_similarity": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 0.99,
                    "default": 0.6,
                    "description": "Similarity above which a non-exact match is reported as altered.",
                },
            },
            "required": ["draft", "source_text"],
            "additionalProperties": False,
        },
        "handler": _tool_check_quotes,
    },
    {
        "name": "check_facts",
        "title": "Locate numbers and names in sources",
        "description": (
            "List the numbers and candidate proper names in the draft that do not appear anywhere in "
            "the supplied source material, so each needs a locator or an UNCHECKED status. A locating "
            "aid: presence in notes is not support, and absence is not falsity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "draft": {"type": "string", "description": "The draft to scan."},
                "source_text": {"type": "string", "description": "All source material and notes for the draft."},
            },
            "required": ["draft", "source_text"],
            "additionalProperties": False,
        },
        "handler": _tool_check_facts,
    },
    {
        "name": "diff_meaning",
        "title": "Compare original and edited copy",
        "description": (
            "Diff an untouched draft against the edited draft for lost numbers, names, and verbatim "
            "quotations, added facts that exist only in the edit, and a drop in qualifier density "
            "(may, could, alleged, according to, at least, maaari, di-umano, raw, ayon sa). Use it "
            "to complete the meaning check "
            "instead of reading from memory."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "original": {"type": "string", "description": "The untouched original draft."},
                "edited": {"type": "string", "description": "The edited draft."},
            },
            "required": ["original", "edited"],
            "additionalProperties": False,
        },
        "handler": _tool_diff_meaning,
    },
    {
        "name": "validate_ledger",
        "title": "Validate a claim ledger",
        "description": (
            "Validate a claim ledger supplied as a JSON array or a markdown table: required fields, "
            "the six exact statuses, unique claim IDs, and a required action and gap for every "
            "non-SUPPORTED claim. Returns errors, warnings, and status counts."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ledger": {
                    "type": "string",
                    "description": "JSON array of claim objects or the markdown claim-ledger table.",
                }
            },
            "required": ["ledger"],
            "additionalProperties": False,
        },
        "handler": _tool_validate_ledger,
    },
    {
        "name": "publication_gate",
        "title": "Apply the publication gate",
        "description": (
            "Apply the pack's decision rules to a ledger and a list of escalation issues. Returns "
            "`NOT READY` when a material claim is PARTIALLY_SUPPORTED, CONFLICTED, CONTRADICTED, "
            "UNCHECKED, or UNSUPPORTED, or when a level 2-5 issue is unresolved; otherwise "
            "`READY FOR HUMAN EDITOR REVIEW`. Also returns a filled PUBLICATION DECISION block with "
            "the human editor's field left as PENDING HUMAN REVIEW. This tool can never approve "
            "publication."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ledger": {"type": "string", "description": "JSON array or markdown claim-ledger table."},
                "issues": {
                    "type": "array",
                    "description": "Open escalation issues (level 1-5) not already represented by a ledger row.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_id": {"type": "string"},
                            "level": {"type": "integer", "minimum": 1, "maximum": 5},
                            "reason": {"type": "string"},
                            "owner": {"type": "string"},
                        },
                        "required": ["level"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["ledger"],
            "additionalProperties": False,
        },
        "handler": _tool_publication_gate,
    },
)

TOOL_INDEX: dict[str, dict[str, Any]] = {tool["name"]: tool for tool in TOOLS}


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

PROMPTS: tuple[dict[str, Any], ...] = (
    {
        "name": "feature-draft",
        "title": "Draft or revise a reported feature",
        "description": "Run the feature-writing workflow on an assignment and reporting notes, with the analysis tools as a check loop.",
        "arguments": [
            {"name": "assignment", "description": "Audience, purpose, language, feature type, length, deadline, deliverable.", "required": True},
            {"name": "reporting", "description": "Supplied notes, quotations, records, and data.", "required": False},
            {"name": "rubric", "description": "The exact current contest or publication rubric, if any. Never guessed.", "required": False},
        ],
        "build": lambda a: (
            "Load the `feature-writing` skill and the `editorial-guardrails` reference before writing.\n\n"
            f"ASSIGNMENT\n{a.get('assignment', '')}\n\n"
            f"REPORTING\n{a.get('reporting') or '(none supplied)'}\n\n"
            f"RUBRIC\n{a.get('rubric') or '(none supplied — ask for the current official rules; do not invent weights)'}\n\n"
            "Work in this order: assignment intake and missing inputs; one-sentence angle; reporting audit; "
            "evidence-bound form and structure; then the requested deliverable. Before you finalize, call "
            "`analyze_prose` on your draft, `check_quotes` against the reporting, and `check_facts` against the "
            "reporting; revise what the findings justify. Then build the claim ledger, run `publication_gate`, "
            "and return the seven required sections. Do not invent scenes, quotations, motives, reactions, or "
            "rubric weights. Leave the final decision to a responsible human editor."
        ),
    },
    {
        "name": "line-edit",
        "title": "Faithful line edit with verification",
        "description": "Run the journalism-humanizer workflow: tighten the copy without changing what the reporting establishes.",
        "arguments": [
            {"name": "draft", "description": "The copy to edit.", "required": True},
            {"name": "evidence", "description": "Notes, transcripts, or documents the copy is based on.", "required": False},
            {"name": "style", "description": "Style guide or voice sample, if the outlet supplied one.", "required": False},
        ],
        "build": lambda a: (
            "Load the `journalism-humanizer` skill and the `editorial-guardrails` reference before editing.\n\n"
            "Keep an untouched copy of the original and build the claim map before you change a word.\n\n"
            f"DRAFT\n{a.get('draft', '')}\n\n"
            f"EVIDENCE\n{a.get('evidence') or '(none supplied — state the limit and mark affected claims UNCHECKED)'}\n\n"
            f"STYLE\n{a.get('style') or '(none supplied — do not imitate a voice)'}\n\n"
            "After editing, call `diff_meaning` on original versus edit, `check_quotes` against the evidence, and "
            "`analyze_prose` on the result. Keep only changes the findings justify. Then return the five required "
            "sections with the claim ledger, and run `publication_gate`. Never claim authorship, target a detector, "
            "or call copy publication-ready while a material issue is open."
        ),
    },
    {
        "name": "contest-review",
        "title": "Review against a supplied rubric",
        "description": "Map a feature to the exact official rubric without predicting a score.",
        "arguments": [
            {"name": "draft", "description": "The feature draft.", "required": True},
            {"name": "rubric", "description": "The official score sheet for the exact event, level, language, category, and year.", "required": True},
            {"name": "reporting", "description": "Supplied reporting notes for evidence checks.", "required": False},
        ],
        "build": lambda a: (
            "Load the `feature-writing` skill and read `feature-craft` (rubric-use rules) first.\n\n"
            f"RUBRIC (exact instrument)\n{a.get('rubric', '')}\n\n"
            f"DRAFT\n{a.get('draft', '')}\n\n"
            f"REPORTING\n{a.get('reporting') or '(none supplied)'}\n\n"
            "Record the rubric's organizer, year, level, language, and category. Preserve only the weights it "
            "states. For each criterion give: the requirement, the passage or claim ID that answers it, the gap, "
            "and one revision or reporting action. Do not add criteria, infer percentages, or predict a score or "
            "award. Ethics, accuracy, attribution, fairness, and privacy remain blocking regardless of the rubric. "
            "Run `analyze_prose` and `check_quotes` before finalizing, then return the seven required sections."
        ),
    },
)

PROMPT_INDEX = {p["name"]: p for p in PROMPTS}


# --------------------------------------------------------------------------- #
# JSON-RPC dispatch
# --------------------------------------------------------------------------- #


def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": payload["text"]}]}
    if payload.get("structured") is not None:
        result["structuredContent"] = payload["structured"]
    return result


def handle_request(method: str, params: dict[str, Any]) -> Any:
    """Dispatch one MCP request. Raises McpError for protocol failures."""
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        return {
            "protocolVersion": version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": __version__},
            "instructions": (
                "School Journalism PH: evidence-led feature writing and faithful journalism editing. "
                "Call journalism_brief first. Load one skill, then a reference only when needed. Use "
                "analyze_prose, check_quotes, check_facts, and diff_meaning as a measured edit loop, "
                "and publication_gate before any release recommendation. Never invent reporting; leave "
                "the publication decision to a responsible human editor."
            ),
        }

    if method == "ping":
        return {}

    if method == "tools/list":
        return {
            "tools": [
                {k: v for k, v in tool.items() if k != "handler"} for tool in TOOLS
            ]
        }

    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or name not in TOOL_INDEX:
            raise McpError(-32602, f"Unknown tool: {name!r}", {"available": sorted(TOOL_INDEX)})
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            raise McpError(-32602, "Tool arguments must be an object")
        handler: Callable[[dict[str, Any]], dict[str, Any]] = TOOL_INDEX[name]["handler"]
        try:
            return _tool_result(handler(args))
        except (ToolInputError, SkillError, ValueError) as exc:
            return {
                "content": [{"type": "text", "text": f"Input error: {exc}"}],
                "isError": True,
            }
        except Exception as exc:  # noqa: BLE001 - report, do not crash the server
            _log(f"tool {name} failed: {exc!r}")
            return {
                "content": [{"type": "text", "text": f"Internal error while running {name}: {exc}"}],
                "isError": True,
            }

    if method == "resources/list":
        from .skills import resource_catalog

        return {"resources": resource_catalog()}

    if method == "resources/read":
        uri = params.get("uri")
        if not isinstance(uri, str):
            raise McpError(-32602, "resources/read requires a string 'uri'")
        from .skills import read_resource

        try:
            return {"contents": [read_resource(uri)]}
        except SkillError as exc:
            raise McpError(-32602, str(exc)) from exc

    if method == "prompts/list":
        return {
            "prompts": [
                {k: v for k, v in prompt.items() if k != "build"} for prompt in PROMPTS
            ]
        }

    if method == "prompts/get":
        name = params.get("name")
        prompt = PROMPT_INDEX.get(name) if isinstance(name, str) else None
        if prompt is None:
            raise McpError(-32602, f"Unknown prompt: {name!r}", {"available": sorted(PROMPT_INDEX)})
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            raise McpError(-32602, "Prompt arguments must be an object")
        missing = [
            a["name"]
            for a in prompt["arguments"]
            if a.get("required") and not str(args.get(a["name"], "")).strip()
        ]
        if missing:
            raise McpError(-32602, f"Missing required prompt argument(s): {', '.join(missing)}")
        return {
            "description": prompt["description"],
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt["build"](args)}}
            ],
        }

    raise McpError(-32601, f"Method not found: {method}")


def handle_message(message: Any) -> dict[str, Any] | None:
    """Handle one decoded JSON-RPC message; return a response or None for notifications."""
    if not isinstance(message, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid Request"},
        }
    msg_id = message.get("id")
    is_notification = "id" not in message
    method = message.get("method")
    if not isinstance(method, str):
        if is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32600, "message": "Invalid Request: missing method"},
        }
    params = message.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    if is_notification:
        # notifications/initialized, notifications/cancelled, and anything else
        # are accepted silently; there is nothing to answer.
        _log(f"notification {method}")
        return None

    try:
        result = handle_request(method, params)
    except McpError as exc:
        error: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.data is not None:
            error["data"] = exc.data
        return {"jsonrpc": "2.0", "id": msg_id, "error": error}
    except Exception as exc:  # noqa: BLE001 - keep the transport alive
        _log(f"unhandled error for {method}: {exc!r}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32603, "message": f"Internal error: {exc}"},
        }
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(reader: Any = None, writer: Any = None) -> None:
    """Run the stdio loop until EOF."""
    reader = reader or sys.stdin
    writer = writer or sys.stdout
    _log("server started")
    for line in reader:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            writer.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {exc.msg}"},
                    }
                )
                + "\n"
            )
            writer.flush()
            continue
        response = handle_message(message)
        if response is not None:
            writer.write(json.dumps(response, ensure_ascii=False) + "\n")
            writer.flush()
    _log("server stopped (EOF)")


def self_test() -> dict[str, Any]:
    """Exercise the server end to end without a host."""
    sample = (
        "In today's fast-paced world, the student council plays a crucial role. "
        "She felt a wave of relief as the room fell silent. "
        "\u201cWe will not stop,\u201d she said. "
        "Experts say the program helped 120 students."
    )
    checks = {}
    checks["initialize"] = handle_request("initialize", {"protocolVersion": DEFAULT_PROTOCOL_VERSION})
    checks["tools"] = [t["name"] for t in handle_request("tools/list", {})["tools"]]
    checks["resources"] = [r["uri"] for r in handle_request("resources/list", {})["resources"]]
    checks["prompts"] = [p["name"] for p in handle_request("prompts/list", {})["prompts"]]
    checks["analyze"] = handle_request(
        "tools/call", {"name": "analyze_prose", "arguments": {"text": sample}}
    )["structuredContent"]["severity_totals"]
    checks["gate"] = handle_request(
        "tools/call",
        {
            "name": "publication_gate",
            "arguments": {
                "ledger": json.dumps(
                    [
                        {
                            "claim_id": "C-001",
                            "location": "P1",
                            "claim": "\u201cWe will not stop,\u201d she said.",
                            "claim_type": "direct quotation",
                            "evidence": "Recording 00:04:12",
                            "gap": "None identified after review.",
                            "status": "SUPPORTED",
                        },
                        {
                            "claim_id": "C-002",
                            "location": "P3",
                            "claim": "120 students were helped.",
                            "claim_type": "statistic",
                            "evidence": "None located",
                            "status": "UNCHECKED",
                            "gap": "No program record supplied.",
                            "action": "Obtain the attendance record.",
                        },
                    ]
                )
            },
        },
    )["structuredContent"]["decision"]
    return checks
