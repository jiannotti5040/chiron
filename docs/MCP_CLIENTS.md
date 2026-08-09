# Using the vault from a coding agent

Chiron speaks MCP over stdio. Any compliant client can call the same six tools
the CLI calls, because both go through `Chiron/mcp_server.py:_IMPL`.

## What is actually exposed

`initialize` reports `chiron.mcp/2`, protocol `2025-06-18`. `tools/list`
returns six tools, and nothing else is reachable — there is no arbitrary
module dispatch, by design.

| Tool | Contract | Use it for |
|---|---|---|
| `attest` | `chiron.attestation/1` | which supplied input produced each span of your own output |
| `analyze` | `chiron.full_stack/1` | every applicable stage over one text |
| `certify` | `primus.certificate/2` | gate checkable claims; pass = `counts.refuted == 0` |
| `collapse` | — | the canonical exact invariant, or an honest refusal |
| `trace` | `chiron.trace/1` | why a surface did or did not collapse; never stamps |
| `catalog` | `chiron.catalog/2` | the reviewed static allowlist and its authority metadata |

Two properties worth knowing before you wire this in. A **refusal is a
result**, not an error — `REFUSED` means no exact checker covers the claim, and
it exits 0. And `attest` reports **origin and verdict as independent facts**: a
span can trace to a source with cosine 1.00 and still be `REFUSED`, because
attribution and checkability are different questions. Never report such a span
as unattributed.

`attest` is also not an AI detector. It returns no probability that text is
machine-written; that measurement does not exist.

## Claude Code — verified

Both servers are connected and answering on Claude Code 2.1.216:

```bash
claude mcp list
```

```
chiron: python3 …/Chiron/mcp_server.py - ✔ Connected
primus: python3 -m primus.mcp_server - ✔ Connected
```

The repository ships a project-scoped `.mcp.json`, which Claude Code loads when
its working directory is the vault root. Its paths are relative for exactly
that reason.

### Known conflict

`claude mcp list` currently reports `chiron` defined in **two scopes** with
different endpoints — user scope with an absolute path, project scope with a
relative one. OAuth tokens are stored per endpoint, so the two do not share
state. Keep one:

```bash
claude mcp remove chiron -s user
```

Keep the *user* entry instead if you want the vault available from any working
directory; in that case remove the project one. This has not been done for you
because it edits configuration outside the repository.

## Codex — configuration written, not verified

`codex` is **not installed on this machine** (`command not found`), so the
configuration below is written from the documented TOML shape and has not been
executed. Treat it as untested until `codex mcp list` confirms it.

Project scope, `.codex/config.toml` in the vault root:

```toml
[mcp_servers.chiron]
command = "python3"
args = ["Chiron/mcp_server.py"]
```

User scope, `~/.codex/config.toml` — absolute path, since the working
directory is not the vault:

```toml
[mcp_servers.chiron]
command = "python3"
args = ["/Users/jacobiannotti/Desktop/Intellectual/Jacob-s-Portfolio-Vault/Chiron/mcp_server.py"]
```

## Any other client

```bash
chiron mcp
```

Serves the same thing on stdin/stdout. This verb does not print the
`[chiron] $ …` delegation banner that every other verb prints — that banner
goes to stderr here, because stdio MCP requires stdout to carry framed
JSON-RPC and nothing else.

Verify a client-independent handshake:

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 | python3 bin/chiron mcp 2>/dev/null
```

## Why there are two servers

`primus` exposes the seed engine — `certify`, `collapse`, `conjecture`.
`chiron` exposes the flagship surface, which includes `certify` and `collapse`
delegating to that same Primus core plus `attest`, `analyze`, and `trace`.

If you are wiring up one server, wire up `chiron`. `primus` remains because it
is what the published `primus-intelligence` package ships, and it must keep
working on its own for anyone who installed only that.
