# Publishing

How the repository is validated, committed, and pushed.

## Before pushing

```bash
python scripts/validate.py
python -m unittest discover -s tests -v
python -m mcp_server --self-test
```

All three must pass. Validation is structural: it proves the package is shaped correctly, not that the journalism advice is sound.

## What is excluded

`/journalism-humanizer/` is ignored. That folder holds named student articles and article-specific reporting records from the source project. They are not part of the public package, and the reusable skill text was rewritten into `skills/` without them. Do not publish it without the consent of the people named in those documents.

Verify the exclusion before any commit that could touch it:

```bash
git check-ignore -v journalism-humanizer
git status --short
```

## Commit

Stage explicit paths, never `git add -A`, and read the staged diff before committing:

```bash
git add README.md LICENSE .gitignore .mcp.json mcp_server skills examples docs scripts tests .github
git diff --cached --stat
git commit -m "feat: add MCP server and complete the journalism skill pack"
```

## Push helper

`scripts/safe-push.sh` previews by default and only publishes with an explicit flag.

```bash
bash scripts/safe-push.sh          # status, validation, branch, origin, planned command
bash scripts/safe-push.sh --push   # dry-run, then push origin main
```

It refuses to run when:

- the working tree is dirty (uncommitted changes),
- `origin` is not the expected repository,
- the branch is not `main`,
- validation fails,
- an unknown option is supplied.

It never stages, commits, force-pushes, changes Git configuration, or stores credentials. Authentication uses your existing Git credential helper.

## If authentication fails

The helper exits before the real push and leaves the commit intact. Common causes:

- **HTTPS credentials missing or expired.** Use a personal access token as the password when Git prompts, or configure SSH and change the remote.
- **`git@github.com` with no key.** `ssh -T git@github.com` will say so.
- **Windows credential manager holding a stale account.** Clear it in Credential Manager and retry.

The helper reports the exact failure. Do not put a token in the repository, in `.mcp.json`, or in a commit message.

## After pushing

```bash
git status --short --branch
git ls-remote origin refs/heads/main
```

The remote `main` must match the local commit. CI (`.github/workflows/validate.yml`) runs the validator, the tests, and the server self-test on every push.

## Repository metadata

If GitHub CLI is authenticated, set the description and topics once:

```bash
gh repo edit --description "MCP server and Agent Skills for evidence-led journalism: feature writing, faithful line edits, quotation and claim checks, and a publication gate." \
  --add-topic journalism --add-topic mcp --add-topic mcp-server --add-topic agent-skills \
  --add-topic feature-writing --add-topic editing --add-topic fact-checking --add-topic philippines
```

This is optional and not part of the push helper.
