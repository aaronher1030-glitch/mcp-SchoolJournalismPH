"""Tests for scripts/validate.py against temporary fixtures and the real repository."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts import validate as validator  # noqa: E402


def build_fixture(root: Path) -> None:
    for rel in validator.REQUIRED_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n", encoding="utf-8")

    (root / "README.md").write_text(
        "# Test package\n\nA responsible human editor decides publication.\n\n## NOT DO\n\n1. Do not invent.\n",
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(".DS_Store\n/journalism-humanizer/\n", encoding="utf-8")
    (root / "journalism-humanizer").mkdir()

    guardrails = "# Editorial Guardrails\n\nDo not invent reporting.\n"
    for name in validator.EXPECTED_SKILLS:
        skill_dir = root / "skills" / name
        (skill_dir / "references").mkdir(parents=True, exist_ok=True)
        body = (
            f"# {name}\n\n## Overview\n\n"
            + ("This workflow edits or plans journalism without inventing facts. " * 6)
            + "\n"
        )
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A test skill for {name}.\n---\n\n{body}",
            encoding="utf-8",
        )
        (skill_dir / "references" / "editorial-guardrails.md").write_text(guardrails, encoding="utf-8")


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        build_fixture(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_valid_package_passes(self) -> None:
        self.assertEqual(validator.validate_repository(self.root), [])

    def test_name_directory_mismatch_fails(self) -> None:
        path = self.root / "skills" / "feature-writing" / "SKILL.md"
        text = path.read_text(encoding="utf-8").replace("name: feature-writing", "name: wrong-name")
        path.write_text(text, encoding="utf-8")
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("does not match" in error for error in errors), errors)

    def test_guardrail_mismatch_fails(self) -> None:
        (self.root / "skills" / "feature-writing" / "references" / "editorial-guardrails.md").write_text(
            "different", encoding="utf-8"
        )
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("guardrail" in error for error in errors), errors)

    def test_missing_documentation_fails(self) -> None:
        (self.root / "docs" / "MCP.md").unlink()
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("missing required file: docs/MCP.md" in e for e in errors), errors)

    def test_unignored_private_folder_fails(self) -> None:
        (self.root / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("journalism-humanizer" in error for error in errors), errors)

    def test_reincluded_private_folder_fails(self) -> None:
        (self.root / ".gitignore").write_text(
            "/journalism-humanizer/\n!/journalism-humanizer/\n", encoding="utf-8"
        )
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("re-include" in error for error in errors), errors)

    def test_placeholder_fails(self) -> None:
        path = self.root / "skills" / "feature-writing" / "references" / "editorial-guardrails.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\nTODO: finish this section\n", encoding="utf-8"
        )
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("placeholder" in error for error in errors), errors)

    def test_broken_relative_link_fails(self) -> None:
        (self.root / "README.md").write_text(
            (self.root / "README.md").read_text(encoding="utf-8")
            + "\n[missing](docs/NOT-THERE.md)\n",
            encoding="utf-8",
        )
        errors = validator.validate_repository(self.root)
        self.assertTrue(any("broken relative link" in error for error in errors), errors)


class RealRepositoryTests(unittest.TestCase):
    def test_repository_is_valid(self) -> None:
        self.assertEqual(validator.validate_repository(REPO_ROOT), [])

    def test_mcp_server_is_valid(self) -> None:
        self.assertEqual(validator.validate_mcp_server(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
