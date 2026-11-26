"""Entry point: ``python -m mcp_server`` or ``python mcp_server/__main__.py``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running this file directly (python mcp_server/__main__.py) as well as
# as a module (python -m mcp_server).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server import __version__  # noqa: E402
from mcp_server.server import SERVER_NAME, self_test, serve  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=SERVER_NAME,
        description=(
            "MCP server for evidence-led feature writing and faithful journalism editing. "
            "Speaks JSON-RPC 2.0 over stdio."
        ),
    )
    parser.add_argument("--version", action="store_true", help="print the server version and exit")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run an offline end-to-end check and print JSON, then exit",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"{SERVER_NAME} {__version__}")
        return 0

    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0

    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    try:
        serve()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
