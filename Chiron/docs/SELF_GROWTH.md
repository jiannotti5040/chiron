# Self-growth, on a leash

Chiron can extend itself, but it is built so it **can improve itself and never take
anything away.** Three guarantees enforce that, and they are gated off by default.

## The three guarantees

1. **Proposal sandbox — never direct mutation.** Self-change ideas are emitted as
   *quarantined proposals*, written aside, never applied in place. You inspect them
   first (`proposals`); nothing touches the running source until you act.
2. **Reversible patches — a backup before every change.** Applying a proposal first
   writes a reversible backup of the file it would change. `rollback-proposal`
   restores the previous state exactly. No change is one-way.
3. **Mandatory self-test gate — green or it is reverted.** A proposal is applied
   **only if the full embedded self-test still passes afterward**. If any gate goes
   red, the change is automatically rolled back. A regression cannot survive.

## Off by default

Autonomous self-editing runs only when the operator sets
`CHIRON_ALLOW_SELF_EDIT=1`. Without it, self-growth is entirely operator-initiated:
the engine can *propose*, but a human decides. The executive that reaches the
network is a separate, also-off-by-default switch (`PRESIDENT_ALLOW_NETWORK=1`).

## Concept growth (additive, not source change)

Separately from source proposals, Chiron grows **cross-domain concepts** from
already-proven laws — recognizing that the same structural skeleton recovered in
two domains is one rule wearing two disguises. This adds knowledge to the Congress;
it does not modify code, and it is always safe to run.

## Commands

```bash
python3 chiron.py grow-concepts --memory chiron_memory.json   # form cross-domain concepts from proven laws
python3 chiron.py self-growth                                 # concepts, multi-domain families, self-edit status
python3 chiron.py proposals                                   # list quarantined self-change proposals
python3 chiron.py apply-proposal <id>                         # apply ONE — only if backup taken AND self-test stays green
python3 chiron.py rollback-proposal <id>                      # restore the pre-change backup
```

## What it cannot do

It cannot remove a capability, bypass the self-test gate, apply a change without a
recoverable backup, or edit itself silently. The boundary is the point: growth is
allowed; loss and stealth are not. See **[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)**
for the honest scope — this is bounded, operator-gated self-improvement, not
autonomous emergence.
