# anysearch

## Source

- Upstream repository: `https://github.com/anysearch-ai/anysearch-skill.git`
- Upstream local checkout: `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill`
- Upstream path: `.`
- Upstream branch/ref: `main`
- Upstream snapshot commit: `4d6cef918e9338c9deef43b81ac0f7e22606825f`; time=`2026-08-21T16:00:26+08:00`; message=`Merge pull request #39 from anysearch-ai/feat_http-cli`


## Local Modifications

- Copied the minimal runnable package: `SKILL.md`, `.env.example`, `requirements.txt`, `runtime.conf.example`, `scripts/`, `LICENSE`, and `NOTICE`.
- Kept the upstream CLI scripts and shared schema files unchanged so Python, Node.js, Bash, and PowerShell entrypoints remain interchangeable.
- Omitted upstream CI files, test plans, generator tooling, repository documentation, and Git history from the global package.
- Added this README for source tracking, package scope, setup notes, and secrets policy.

## Prerequisites

- Network access to `https://api.anysearch.com`.
- Python 3.6+ with `requests` for `scripts/anysearch_cli.py`, or Node.js 12+ for the dependency-free JavaScript CLI.
- Bash 3.2+ with `curl` and `jq`, or PowerShell 5.1+, for the corresponding fallback entrypoints.
- API keys are optional; anonymous access is supported with lower limits.

## Secrets Policy

This package contains no API keys, account credentials, cookies, or machine-local runtime files. Keep optional `ANYSEARCH_API_KEY` values in ignored local configuration or the process environment. The current installation leaves AnySearch in anonymous mode until a user-managed key is configured.

## Minimal Invocation

```bash
python3 /path/to/anysearch/scripts/anysearch_cli.py search "query" --max_results 5
```
