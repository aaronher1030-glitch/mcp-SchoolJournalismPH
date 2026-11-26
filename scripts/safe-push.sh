#!/usr/bin/env bash
# Preview-first push helper.
#
#   bash scripts/safe-push.sh          # status, validation, planned command
#   bash scripts/safe-push.sh --push   # dry-run, then push origin main
#
# It never stages, commits, force-pushes, or changes Git configuration.
set -euo pipefail

EXPECTED_ORIGIN="https://github.com/aaronher1030-glitch/mcp-SchoolJournalismPH.git"
EXPECTED_BRANCH="main"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PUSH=0
for arg in "$@"; do
  case "$arg" in
    --push) PUSH=1 ;;
    -h|--help)
      sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: bash scripts/safe-push.sh [--push]" >&2
      exit 2
      ;;
  esac
done

cd "$ROOT"

if [ ! -d .git ]; then
  echo "No Git repository at $ROOT. This helper never initializes one." >&2
  exit 1
fi

origin="$(git remote get-url origin 2>/dev/null || true)"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
dirty="$(git status --porcelain)"

echo "Repository: $ROOT"
echo "Branch:     ${branch:-<none>}"
echo "Origin:     ${origin:-<none>}"
if [ -n "$dirty" ]; then
  echo "Working tree: DIRTY"
  echo "$dirty" | sed 's/^/  /'
else
  echo "Working tree: clean"
fi

if [ "$PUSH" -eq 1 ]; then
  if [ "$origin" != "$EXPECTED_ORIGIN" ]; then
    echo "Refusing to push: origin is not $EXPECTED_ORIGIN" >&2
    exit 1
  fi
  if [ "$branch" != "$EXPECTED_BRANCH" ]; then
    echo "Refusing to push: branch is '$branch', expected '$EXPECTED_BRANCH'" >&2
    exit 1
  fi
  if [ -n "$dirty" ]; then
    echo "Refusing to push: commit or discard the changes above first." >&2
    exit 1
  fi
fi

echo
echo "Running validation..."
python scripts/validate.py

if [ "$PUSH" -eq 0 ]; then
  echo
  echo "Preview only. Nothing was sent. Planned command:"
  echo "  git push origin $EXPECTED_BRANCH"
  echo "Re-run with --push to publish."
  exit 0
fi

echo
echo "Dry run:"
git push --dry-run origin "$EXPECTED_BRANCH"

echo
echo "Pushing:"
git push origin "$EXPECTED_BRANCH"

echo
echo "Done. Remote branch $EXPECTED_BRANCH now matches the local commit."
git log --oneline -1
