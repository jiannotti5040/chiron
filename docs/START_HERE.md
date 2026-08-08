# Start here

Chiron is a local macOS workspace around an exact-checking Python core. Start
with the boundary, not a slogan:

- **VERIFIED** means a defined check succeeded exactly on the supplied record.
- **REFUTED** means a defined check failed.
- **REFUSED** means the requested claim is outside the implemented, warranted
  scope.

A passing check is never a blanket statement that a document, model response,
or theory is true.

## Try the core

From a checkout:

```bash
python3 -m pip install ./Primus

primus collapse "1 1 2 3 5 8 13 21 34 55"
printf '%s\n' 'The sum of 2 and 3 is 5; 2^10 = 1025.' | primus certify - --gate
```

`collapse` searches explicit sequence families and verifies a candidate only
when it reproduces held-out terms exactly. `certify` checks only the claim
forms it recognizes and reports its coverage; uncheckable prose is not
blessed by a pass.

For the local native interface:

```bash
cd App
swift run chiron-app
```

It requires macOS 14+, Swift 6, and a usable local Python installation. See
the [macOS operator guide](../App/README.md) for file handling, test commands,
and bundle behavior.

## Read the evidence in order

1. [README](../README.md) — scope and local entry points.
2. [External validation](../Primus/EXTERNAL_VALIDATION.md) — historical
   false stamps, root-cause repairs, and repeatable OEIS protocols.
3. [Known limitations](../Chiron/docs/KNOWN_LIMITATIONS.md) — explicit
   abstention and scope boundaries.
4. [Research map](RESEARCH_MAP.md) — what is executable evidence, a bounded
   computation, or experimental theory.
5. [Reconstruction record](RECONSTRUCTION.md) — current interface boundaries
   and validation commands.

The project includes a paper draft and broader theory material. Those are
useful reading, but they are not substitutes for a reproducible gate or an
independent empirical result. The research map links each record to its proper
evidentiary tier.

## Verify the checkout

```bash
python3 bin/chiron test --full
python3 bin/chiron parity
```

If either command fails, treat that as a result to investigate—not as a
reason to weaken a check. For the source-of-truth and regeneration rules, see
[the operating manual](../notes/SOP.md).
