# Handoff prompt

Copy everything below the line into a fresh session.

---

You are taking over an in-progress engineering mandate on my repository. Read
before you write.

**Repo:** `~/Desktop/Intellectual/Jacob-s-Portfolio-Vault`
**Branch:** `chiron/mandate-20260809` (18 commits ahead of `origin/main`)

## Read these first, in this order

1. `AGENTS.md` — the law. **Zero false verifications.** Refusal is a feature.
   When recall and honesty conflict, choose honesty.
2. `notes/SOP.md` — the gate battery and release discipline.
3. `docs/MANDATE_STATUS.md` — what is done, what is not, with observed
   evidence. §17 lists exactly what remains. Trust this over any summary.
4. `docs/CONTINUATION.md` — how to restart, and known environment blockers.

## Establish a baseline before changing anything

```bash
cd ~/Desktop/Intellectual/Jacob-s-Portfolio-Vault
python3 bin/chiron test --full          # expect: GATE BATTERY GREEN, 54/54
cd App && swift test --scratch-path /tmp/chiron-build   # expect: 33 green
```

If either is red on a clean checkout, stop and tell me. Do not proceed.

## Your job

Implement mandate §16: a real **problem-solving mode**. Today the system
verifies and refuses; it does not generate. Build `solve`, `explore`, and
`compare` as distinct verbs in the **Python core** — not in Swift, because a
second implementation of the stamping path is forbidden by `AGENTS.md`.

Compose the engines that already exist rather than writing new ones:
`Chiron/conjecture.py`, `Primus/src/primus/engine.py` (collapse),
`Primus/src/primus/certify.py`, `Chiron/cross_examine.py`.

A `solve` run must: formalize the problem, extract knowns and unknowns, choose
applicable engines, generate candidates, test them, search for counterexamples,
rank what survives, and return the best-supported result **with lineage and
stated limitations**. Preserve intermediate state so a result can be inspected
and reproduced. A candidate that cannot be exactly checked is returned as a
candidate, never as a verdict.

Expose it through the CLI, the MCP server, and the `/v1` service **in the same
change**, so it lands on every interface at once instead of one.

## Rules I am not flexible on

- **No `Co-Authored-By` trailers.** Do not add yourself to commit messages.
- **Stay inside this repository.** Sibling directories on this machine are
  separate, finished projects with their own licences and their own privacy
  posture. Do not read from, write to, or vendor code between them.
- Never widen a tolerance, mute a gate, or convert a refusal into a score to
  get green. A failing gate is information.
- Never hand-edit `Chiron Monolith/chiron_monolith.py`; regenerate it.
- Never `git add -A` at the repo root.
- Do not claim something works until you have run it and seen the output.
  Paste the output. If you did not run it, say so.
- Do not tell me a task is complete when part of it is unfinished. Say which
  part, and why.

## Known environment blockers

- `xcodebuild test` stalls with no output and `simctl install` hangs;
  CoreSimulator is wedged. Plain `xcodebuild build` works. The fix needs my
  password: `sudo pkill -9 -f CoreSimulator`. Ask me to run it; do not burn ten
  minutes retrying.
- Xcode is a beta at `~/Downloads/Xcode-beta.app`.

## What I want from you at the end

Short and checkable: what you ran, what the output was, what you committed, and
what you did not finish. No summaries of work you did not do.
