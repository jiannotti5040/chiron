# Using the vault from Claude (or any MCP client)

**Author: Jacob Iannotti. Apache-2.0 (see LICENSE).**

Two MCP servers ship in this repository. Both speak newline-delimited
JSON-RPC 2.0 over stdio, both are dependency-free, and both hold the same
line: nothing is stamped that cannot be exactly proved, and refusal is a
result rather than a failure.

| Server | Tools | Contract |
|---|---|---|
| `chiron` | `attest` · `analyze` · `certify` · `catalog` · `call` | `chiron.attestation/1`, `chiron.full_stack/1` |
| `primus` | `certify` · `collapse` · `conjecture` | `primus.certificate/2` |

## Register

From a clone of this repository, the checked-in `.mcp.json` is picked up
automatically by Claude Code. To register them by hand instead:

```bash
claude mcp add chiron --scope user -- python3 "$PWD/Chiron/mcp_server.py"
```

```bash
claude mcp add primus --scope user --env PYTHONPATH="$PWD/Primus/src" -- python3 -m primus.mcp_server
```

Check them with `claude mcp list`; both should report Connected. For Claude
Desktop, put the same command and args in `claude_desktop_config.json`.

## The tool that matters: `attest`

The other tools read a text. `attest` reads *an answer together with the
things that produced it*, and that is a different question:

> Of the words in this answer, which came from the documents I was given,
> and which did I supply?

```jsonc
{
  "name": "attest",
  "arguments": {
    "output": "<the answer that was just written>",
    "input_paths": ["notes/source.md", "data/report.txt"]
  }
}
```

Every span comes back `VERIFIED`, `REFUTED`, or `REFUSED`, with the closest
input named and the content words that trace to nothing listed as novel.
With no candidate inputs, every span is `REFUSED` — that is the contract,
not a bug, because attribution is only meaningful relative to sources you
name.

**It is not a detector.** It reports no probability that text is
machine-written. That measurement does not exist, and a guess dressed as
evidence is the failure this repository was built to refuse.

## Files are first-class

Every tool that takes `text` also takes `path`, and `attest` takes
`input_paths`. Pass the two together and never both for the same slot —
that is an error, not a silent preference.

Bounds are stated rather than implied: files are read to 2,000,000 bytes,
text to 400,000 characters, and at most 32 candidate inputs are accepted.
When a file is truncated, the record says so.

## Reading the results

- `certify` — gate on `counts.refuted == 0`, and read `coverage`. A pass
  means only that nothing checkable was refuted. The remainder is
  *unverified*, which is not the same as false.
- `analyze` — a stage that cannot apply reports `SKIPPED` with the reason;
  one that raised reports `ERROR`. Neither is a pass. `stages_run` always
  equals the number of results.
- `attest` — report `REFUSED` spans to the reader as unattributed. Dropping
  them turns an honest gap into a false clean bill.
- `catalog` then `call` — reach any individual module. `call` is dispatch
  only: you get exactly what the module returned, or the exception type it
  raised, never a substitute value.

## Gates

```bash
python3 Chiron/mcp_server.py selftest    # 17/17
python3 Primus/test_mcp_server.py        # 11/11, live subprocess over stdio
```
