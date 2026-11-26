"""End-to-end tests for the stdio MCP server."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_session(messages: list[dict]) -> list[dict]:
    payload = "\n".join(json.dumps(message, ensure_ascii=False) for message in messages) + "\n"
    proc = subprocess.run(
        [sys.executable, "-m", "mcp_server"],
        cwd=str(REPO_ROOT),
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
    )
    responses = []
    for line in proc.stdout.splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.responses = run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_prose",
                        "arguments": {"text": "In today's fast-paced world, she felt a wave of relief."},
                    },
                },
                {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "skill://feature-writing"}},
                {"jsonrpc": "2.0", "id": 5, "method": "prompts/get", "params": {"name": "line-edit", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 6, "method": "not/a/method", "params": {}},
            ]
        )
        cls.by_id = {response.get("id"): response for response in cls.responses}

    def test_initialize_negotiates_and_advertises_capabilities(self) -> None:
        result = self.by_id[1]["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertIn("tools", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "school-journalism-ph")
        self.assertIn("journalism_brief", result["instructions"])

    def test_notification_produces_no_response(self) -> None:
        self.assertEqual(len(self.responses), 6)
        self.assertNotIn(None, self.by_id)

    def test_tools_list_contains_the_full_set(self) -> None:
        names = {tool["name"] for tool in self.by_id[2]["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "journalism_brief",
                "get_skill",
                "get_reference",
                "analyze_prose",
                "check_quotes",
                "check_facts",
                "diff_meaning",
                "validate_ledger",
                "publication_gate",
            },
        )
        for tool in self.by_id[2]["result"]["tools"]:
            self.assertNotIn("handler", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_tool_call_returns_findings(self) -> None:
        result = self.by_id[3]["result"]
        self.assertFalse(result.get("isError"))
        self.assertTrue(result["content"][0]["text"])
        structured = result["structuredContent"]
        rules = {finding["rule"] for finding in structured["findings"]}
        self.assertIn("ai-opener", rules)

    def test_resource_read_returns_the_skill(self) -> None:
        contents = self.by_id[4]["result"]["contents"]
        self.assertEqual(contents[0]["mimeType"], "text/markdown")
        self.assertIn("Feature Writing", contents[0]["text"])

    def test_prompt_requires_documented_arguments(self) -> None:
        error = self.by_id[5]["error"]
        self.assertEqual(error["code"], -32602)
        self.assertIn("draft", error["message"])

    def test_unknown_method_returns_method_not_found(self) -> None:
        self.assertEqual(self.by_id[6]["error"]["code"], -32601)


class ToolBehaviourTests(unittest.TestCase):
    def test_cli_self_test_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "mcp_server", "--self-test"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["gate"], "NOT READY")
        self.assertEqual(len(report["tools"]), 9)

    def test_bad_tool_arguments_return_tool_error_not_crash(self) -> None:
        responses = run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "check_quotes", "arguments": {"draft": "x"}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}},
            ]
        )
        by_id = {response.get("id"): response for response in responses}
        self.assertTrue(by_id[1]["result"]["isError"])
        self.assertIn("source_text", by_id[1]["result"]["content"][0]["text"])
        self.assertEqual(by_id[2]["error"]["code"], -32602)
        self.assertEqual(by_id[3]["result"], {})

    def test_publication_gate_tool_cannot_approve(self) -> None:
        responses = run_session(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "publication_gate",
                        "arguments": {
                            "ledger": json.dumps(
                                [
                                    {
                                        "claim_id": "C-1",
                                        "location": "P1",
                                        "claim": "A claim.",
                                        "claim_type": "fact",
                                        "evidence": "Locator",
                                        "status": "CONFLICTED",
                                        "gap": "Two records disagree",
                                        "action": "Refer to editor",
                                    }
                                ]
                            )
                        },
                    },
                }
            ]
        )
        structured = responses[0]["result"]["structuredContent"]
        self.assertEqual(structured["decision"], "NOT READY")
        self.assertIn("PENDING HUMAN REVIEW", responses[0]["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
