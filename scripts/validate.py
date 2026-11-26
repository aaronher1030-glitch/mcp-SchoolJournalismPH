#!/usr/bin/env python3
"""Validate the public package. Standard library only.

Two layers:

- ``validate_repository(root)`` checks shape, metadata, reference parity, links,
  examples, and privacy rules without importing anything from the package. It is
  safe to run against a temporary fixture.
- ``validate_mcp_server(root)`` imports the server from that root and checks the
  tool registry, prompts, and resources actually work.

Exit status is 0 only when both layers report no errors.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    ".gitignore",
    ".mcp.json",
    "docs/QUICK-BRIEF.md",
    "docs/MCP.md",
    "docs/INSTALL.md",
    "docs/RESEARCH.md",
    "docs/PUBLISHING.md",
    "examples/README.md",
    "examples/line-edit/input.md",
    "examples/line-edit/expected-output.md",
    "examples/line-edit/expected-checks.md",
    "examples/feature/input.md",
    "examples/feature/expected-output.md",
    "examples/feature/expected-checks.md",
    "mcp_server/__init__.py",
    "mcp_server/__main__.py",
    "mcp_server/server.py",
    "mcp_server/analysis.py",
    "mcp_server/ledger.py",
    "mcp_server/skills.py",
    "scripts/validate.py",
    "scripts/safe-push.sh",
    "tests/test_analysis.py",
    "tests/test_ledger.py",
    "tests/test_server.py",
    "tests/test_validate.py",
    ".github/workflows/validate.yml",
)

EXPECTED_SKILLS = ("journalism-humanizer", "feature-writing")
REQUIRED_REFERENCES = ("editorial-guardrails.md",)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|FIXME|TBD|XXX|PLACEHOLDER|LOREM IPSUM)\b", re.IGNORECASE)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

SKIP_LINK_DIRS = ("journalism-humanizer", ".git", ".superpowers", "__pycache__")


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, parts[2]


def _relative_links(text: str) -> list[str]:
    """Return relative link targets, ignoring code fences and external URLs."""
    stripped = FENCE_RE.sub("", text)
    out = []
    for match in LINK_RE.finditer(stripped):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#", "tel:")):
            continue
        if "{" in target or "<" in target:
            continue
        target = target.split("#", 1)[0]
        if not target:
            continue
        out.append(target.replace("%20", " "))
    return out


def _check_links(root: Path, errors: list[str]) -> None:
    candidates = [root / "README.md", root / "examples" / "README.md"]
    candidates += sorted((root / "docs").glob("*.md"))
    candidates += sorted((root / "examples").glob("*/*.md"))
    candidates += sorted((root / "skills").glob("*/*.md"))
    candidates += sorted((root / "skills").glob("*/references/*.md"))
    for path in candidates:
        if not path.is_file():
            continue
        for target in _relative_links(path.read_text(encoding="utf-8")):
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                try:
                    shown = path.relative_to(root)
                except ValueError:
                    shown = path
                errors.append(f"{shown}: broken relative link -> {target}")


def validate_repository(root: Path) -> list[str]:
    """Check package structure, metadata, references, examples, and privacy rules."""
    root = Path(root)
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        errors.append("missing skills/ directory")
    else:
        found = sorted(p.name for p in skills_dir.iterdir() if p.is_dir())
        for expected in EXPECTED_SKILLS:
            if expected not in found:
                errors.append(f"missing skill directory: skills/{expected}")

    for path in sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []:
        skill_dir = path.parent
        text = path.read_text(encoding="utf-8")
        meta, body = _frontmatter(text)

        unknown = set(meta) - {"name", "description"}
        if unknown:
            errors.append(
                f"{path.relative_to(root)}: non-portable frontmatter field(s): {', '.join(sorted(unknown))}"
            )

        name = meta.get("name", "")
        if not name:
            errors.append(f"{path.relative_to(root)}: missing 'name' frontmatter")
        else:
            if not NAME_RE.match(name):
                errors.append(f"{path.relative_to(root)}: name '{name}' must be lowercase ASCII with single hyphens")
            if len(name) > 64:
                errors.append(f"{path.relative_to(root)}: name exceeds 64 characters")
            if name != skill_dir.name:
                errors.append(f"{path.relative_to(root)}: name '{name}' does not match directory '{skill_dir.name}'")

        description = meta.get("description", "")
        if not description:
            errors.append(f"{path.relative_to(root)}: missing 'description' frontmatter")
        elif len(description) > 1024:
            errors.append(f"{path.relative_to(root)}: description exceeds 1024 characters")

        if len(body.strip()) < 200:
            errors.append(f"{path.relative_to(root)}: body is too short to be a usable workflow")

        for required in REQUIRED_REFERENCES:
            if not (skill_dir / "references" / required).is_file():
                errors.append(f"{path.relative_to(root)}: missing references/{required}")

        for markdown in [path, *sorted((skill_dir / "references").glob("*.md"))]:
            content = markdown.read_text(encoding="utf-8")
            if PLACEHOLDER_RE.search(content):
                errors.append(f"{markdown.relative_to(root)}: unresolved placeholder marker")

    guardrails = [
        skills_dir / name / "references" / "editorial-guardrails.md"
        for name in EXPECTED_SKILLS
    ]
    if all(p.is_file() for p in guardrails):
        first = guardrails[0].read_bytes()
        for other in guardrails[1:]:
            if other.read_bytes() != first:
                errors.append(
                    "guardrail copies differ: "
                    f"{guardrails[0].relative_to(root)} and {other.relative_to(root)} must be byte-identical"
                )

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        rules = [ln.strip() for ln in gitignore.read_text(encoding="utf-8").splitlines()]
        if "/journalism-humanizer/" not in rules:
            errors.append(".gitignore: must ignore the private source folder with '/journalism-humanizer/'")
        if any(rule.startswith("!") and "journalism-humanizer" in rule for rule in rules):
            errors.append(".gitignore: must not re-include the private source folder")

    readme = root / "README.md"
    if readme.is_file():
        content = readme.read_text(encoding="utf-8")
        if "NOT DO" not in content:
            errors.append("README.md: must contain the prominent NOT DO list")
        if "human" not in content.lower() or "editor" not in content.lower():
            errors.append("README.md: must state the responsible human editor requirement")

    for path in root.glob("examples/*/*.md"):
        if PLACEHOLDER_RE.search(path.read_text(encoding="utf-8")):
            errors.append(f"{path.relative_to(root)}: unresolved placeholder marker")

    _check_links(root, errors)
    return errors


def validate_mcp_server(root: Path) -> list[str]:
    """Import the server from ``root`` and check tools, prompts, and resources."""
    errors: list[str] = []
    root = Path(root)
    if not (root / "mcp_server" / "server.py").is_file():
        return ["missing mcp_server/server.py"]

    previous_path = list(sys.path)
    removed = {name: sys.modules.pop(name) for name in list(sys.modules) if name == "mcp_server" or name.startswith("mcp_server.")}
    sys.path.insert(0, str(root))
    try:
        server = importlib.import_module("mcp_server.server")
        ledger = importlib.import_module("mcp_server.ledger")

        tools = getattr(server, "TOOLS", ())
        if not tools:
            errors.append("mcp_server: no tools registered")
        names = [t.get("name") for t in tools]
        if len(names) != len(set(names)):
            errors.append("mcp_server: duplicate tool names")
        for tool in tools:
            for field in ("name", "description", "inputSchema", "handler"):
                if not tool.get(field):
                    errors.append(f"mcp_server: tool {tool.get('name', '?')} missing '{field}'")
            schema = tool.get("inputSchema", {})
            if schema.get("type") != "object":
                errors.append(f"mcp_server: tool {tool.get('name')} inputSchema must be an object schema")
            if "properties" not in schema:
                errors.append(f"mcp_server: tool {tool.get('name')} inputSchema has no properties")
            if not callable(tool.get("handler")):
                errors.append(f"mcp_server: tool {tool.get('name')} handler is not callable")
            if not str(tool.get("name", "")).replace("_", "").isalnum():
                errors.append(f"mcp_server: tool name {tool.get('name')!r} must be snake_case ASCII")

        listed = {t["name"] for t in server.handle_request("tools/list", {})["tools"]}
        if listed != set(n for n in names if n):
            errors.append("mcp_server: tools/list does not match the registry")

        doc = root / "docs" / "MCP.md"
        if doc.is_file():
            documented = doc.read_text(encoding="utf-8")
            for name in sorted(listed):
                if f"`{name}`" not in documented:
                    errors.append(f"docs/MCP.md: tool '{name}' is not documented")

        prompts = getattr(server, "PROMPTS", ())
        if len(prompts) < 1:
            errors.append("mcp_server: no prompts registered")
        for prompt in prompts:
            if not callable(prompt.get("build")):
                errors.append(f"mcp_server: prompt {prompt.get('name')} has no builder")
            if not prompt.get("arguments"):
                errors.append(f"mcp_server: prompt {prompt.get('name')} declares no arguments")

        try:
            resources = server.handle_request("resources/list", {})["resources"]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"mcp_server: resources/list failed: {exc}")
            resources = []
        if not resources:
            errors.append("mcp_server: no resources registered")
        for resource in resources:
            uri = resource.get("uri", "")
            try:
                contents = server.handle_request("resources/read", {"uri": uri})["contents"]
            except Exception as exc:  # noqa: BLE001
                errors.append(f"mcp_server: resources/read failed for {uri}: {exc}")
                continue
            if not contents or not contents[0].get("text", "").strip():
                errors.append(f"mcp_server: resource {uri} returned no text")

        if getattr(ledger, "STATUSES", None) != (
            "SUPPORTED",
            "PARTIALLY_SUPPORTED",
            "CONFLICTED",
            "CONTRADICTED",
            "UNCHECKED",
            "UNSUPPORTED",
        ):
            errors.append("mcp_server/ledger.py: the six evidence statuses changed")

        gate = server.handle_request(
            "tools/call",
            {
                "name": "publication_gate",
                "arguments": {
                    "ledger": (
                        '[{"claim_id":"C-1","location":"P1","claim":"x","claim_type":"fact",'
                        '"evidence":"e","status":"UNCHECKED","gap":"g","action":"a"}]'
                    )
                },
            },
        )
        decision = gate.get("structuredContent", {}).get("decision")
        if decision != "NOT READY":
            errors.append("mcp_server: publication gate must return NOT READY for an unchecked material claim")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"mcp_server: import or self-check failed: {exc}")
    finally:
        for name in [m for m in sys.modules if m == "mcp_server" or m.startswith("mcp_server.")]:
            del sys.modules[name]
        sys.modules.update(removed)
        sys.path[:] = previous_path

    return errors


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parent.parent

    errors = validate_repository(root)
    if not errors:
        errors = validate_mcp_server(root)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
