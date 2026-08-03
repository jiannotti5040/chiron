# Gate your agent's output — an MCP server, free, 30 seconds

**Author: Jacob Iannotti. Apache-2.0 (see [../LICENSE.md](../LICENSE.md)) — free for any noncommercial use.**

Your agent asserts things. Some of those assertions are checkable. This is an
MCP server that checks them exactly and **refuses** when it can't, so a
"probably right" answer never silently becomes a released one.

It runs locally, offline, with no API key and no account.

## Install

```bash
pip install primus-intelligence
```

**Claude Code** — one command:

```bash
claude mcp add primus -- primus-mcp
```

**Claude Desktop / Cursor / any MCP client** — add to your config
(`claude_desktop_config.json` on Desktop):

```json
{
  "mcpServers": {
    "primus": {
      "command": "primus-mcp"
    }
  }
}
```

Restart the client. That's it — three tools appear.

## What you get

| Tool | Give it | You get back |
|---|---|---|
| **`certify`** | any text (typically a model's answer) | every checkable claim marked `VERIFIED` / `REFUTED` / `REFUSED`, plus the **coverage boundary** — how much of the text was checkable at all |
| **`collapse`** | an integer sequence or string surface | the exact recovered rule, *proven on held-out terms it never saw* — or an honest refusal |
| **`conjecture`** | an integer sequence | guess-and-prove: a search proposes closed forms, an exact gate stamps only what reproduces every term exactly |

`certify` currently checks: integer and rational arithmetic (including
powers), percentages, primality, binomial coefficients, gcd/lcm, modular
arithmetic, date arithmetic, sums and averages of listed numbers, integer
sequence continuations, and integer runs.

## Use it in one line

Once installed, ask your agent:

> *"Use the primus certify tool on your last answer before you give it to me."*

Or wire it into an agent loop as a release condition:

```
gate on   counts.refuted == 0
treat     the unverifiable remainder as unverified — not as safe
read      coverage before trusting a pass
```

That third line matters. A `certify` pass means **nothing checkable was
refuted** — not that the text is true. Coverage tells you how much of it the
gate could even see. The tool is built to make that distinction impossible to
lose.

## What it will not do

- It does not certify arbitrary prose, opinions, or judgment calls.
- It does not do regulatory compliance or legal conclusions.
- A high coverage number is not a safety score.
- Free for noncommercial use; commercial use is licensed — see
  [LICENSES.md](../LICENSES.md).

## Try it before installing

The same engine runs in your browser, no install:
**[jiannotti5040.github.io/chiron](https://jiannotti5040.github.io/chiron/)**

## Verify the tool itself

The MCP layer is gated: **11/11** handshake gates drive the real server
process over real stdio JSON-RPC (initialize / tools/list / tools/call for
every tool, plus unknown-tool and ping). The engine behind it has a published
zero-false-verification record on external data —
**22 stamped / 22 externally correct / 0 false stamps / 12 refusals** on the
current frozen eval, which you can reproduce yourself in two minutes:

```bash
git clone https://github.com/jiannotti5040/chiron && cd chiron
python3 eval/grade.py
```

Every count reconciled in [`BATTERIES.md`](BATTERIES.md).

## Worked example

Input to `certify`:

> "97 is prime, 2+2=5, and gcd(12, 18) = 6."

Output (real run, `primus-intelligence` from PyPI):

```
counts: {"checkable": 3, "verified": 2, "refuted": 1, "refused": 0}
```

Three checkable claims found. Two hold. One is exactly false — and it is
named, not averaged away.
