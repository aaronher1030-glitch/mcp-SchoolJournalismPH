"""Read the skill pack from disk, so the server and the skills share one source of truth."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
BRIEF_PATH = ROOT / "docs" / "QUICK-BRIEF.md"

SKILL_NAMES = ("journalism-humanizer", "feature-writing")


class SkillError(Exception):
    """Raised when a requested skill or reference is not in the pack."""


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
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
    return meta, parts[2].lstrip("\n")


def skill_paths() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(
        p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
    )


def list_skills() -> list[dict[str, Any]]:
    """Return name, description, and available references for each skill."""
    out: list[dict[str, Any]] = []
    for path in skill_paths():
        text = (path / "SKILL.md").read_text(encoding="utf-8")
        meta, _ = _split_frontmatter(text)
        refs = sorted(p.stem for p in (path / "references").glob("*.md")) if (path / "references").is_dir() else []
        out.append(
            {
                "name": meta.get("name", path.name),
                "description": meta.get("description", ""),
                "references": refs,
            }
        )
    return out


def load_skill(name: str) -> dict[str, Any]:
    """Return the full SKILL.md for a skill in the pack."""
    normalized = (name or "").strip().lower()
    if normalized not in SKILL_NAMES:
        raise SkillError(
            f"Unknown skill '{name}'. Available: {', '.join(SKILL_NAMES)}."
        )
    path = SKILLS_DIR / normalized / "SKILL.md"
    if not path.is_file():
        raise SkillError(f"Skill file missing: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    return {
        "name": meta.get("name", normalized),
        "description": meta.get("description", ""),
        "path": path.relative_to(ROOT).as_posix(),
        "instruction": body.strip(),
    }


_REFERENCE_ALIASES = {
    "guardrails": "editorial-guardrails",
    "editorial-guardrails": "editorial-guardrails",
    "craft": "feature-craft",
    "feature-craft": "feature-craft",
    "verification": "verification-output",
    "verification-output": "verification-output",
    "output": "verification-output",
}


def load_reference(name: str) -> dict[str, Any]:
    """Return a reference document by short name, from whichever skill carries it."""
    key = re.sub(r"^references?/", "", (name or "").strip().lower())
    canonical = _REFERENCE_ALIASES.get(key, key)
    for path in skill_paths():
        candidate = path / "references" / f"{canonical}.md"
        if candidate.is_file():
            others = [
                p.relative_to(ROOT).as_posix()
                for p in SKILLS_DIR.glob(f"*/references/{canonical}.md")
            ]
            return {
                "name": canonical,
                "path": candidate.relative_to(ROOT).as_posix(),
                "also_at": [o for o in others if o != candidate.relative_to(ROOT).as_posix()],
                "text": candidate.read_text(encoding="utf-8"),
            }
    available = sorted(
        {p.stem for p in SKILLS_DIR.glob("*/references/*.md")}
    )
    raise SkillError(
        f"Unknown reference '{name}'. Available: {', '.join(available) or 'none'}."
    )


def brief() -> str:
    """Return the one-page routing brief, or a short fallback if it is missing."""
    if BRIEF_PATH.is_file():
        return BRIEF_PATH.read_text(encoding="utf-8")
    return (
        "# Journalism brief\n\n"
        "Load the `feature-writing` skill to plan or draft a feature, or the "
        "`journalism-humanizer` skill to line-edit copy. Read "
        "`editorial-guardrails` before either. Never invent scenes, quotations, "
        "sources, or certainty. Return `NOT READY` when material evidence is missing, "
        "and leave the final decision to a responsible human editor.\n"
    )


def resource_catalog() -> list[dict[str, str]]:
    """Describe every skill and reference as an MCP resource."""
    resources = [
        {
            "uri": "journalism://brief",
            "name": "Journalism brief",
            "description": "One-page routing brief: which skill, the workflow spine, and the non-negotiables.",
            "mimeType": "text/markdown",
        }
    ]
    for path in skill_paths():
        name = path.name
        text = (path / "SKILL.md").read_text(encoding="utf-8")
        meta, _ = _split_frontmatter(text)
        resources.append(
            {
                "uri": f"skill://{name}",
                "name": meta.get("name", name),
                "description": meta.get("description", f"The {name} skill."),
                "mimeType": "text/markdown",
            }
        )
    for path in sorted(SKILLS_DIR.glob("*/references/*.md")):
        stem = path.stem
        uri = f"reference://{stem}"
        if any(r["uri"] == uri for r in resources):
            continue
        resources.append(
            {
                "uri": uri,
                "name": stem.replace("-", " ").capitalize(),
                "description": f"Reference document carried by the {path.parent.parent.name} skill.",
                "mimeType": "text/markdown",
            }
        )
    return resources


def read_resource(uri: str) -> dict[str, str]:
    """Resolve a resource URI to its text."""
    if uri == "journalism://brief":
        return {"uri": uri, "mimeType": "text/markdown", "text": brief()}
    if uri.startswith("skill://"):
        skill = load_skill(uri[len("skill://") :])
        header = (
            f"<!-- {skill['path']} -->\n"
            f"# {skill['name']}\n\n{skill['description']}\n\n"
        )
        return {"uri": uri, "mimeType": "text/markdown", "text": header + skill["instruction"]}
    if uri.startswith("reference://"):
        ref = load_reference(uri[len("reference://") :])
        return {"uri": uri, "mimeType": "text/markdown", "text": ref["text"]}
    raise SkillError(f"Unknown resource URI '{uri}'.")
