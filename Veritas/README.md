# Veritas — the knowledge-and-wisdom engine

**Author: Jacob Iannotti. Licensed under PolyForm Noncommercial 1.0.0 — free to use, modify, and share for any noncommercial purpose; commercial rights reserved (see the repository-root [LICENSE.md](../LICENSE.md)).**

Veritas is the exact-arithmetic heart of the invariant work: *collapse* a codified
surface to its minimal generator, test whether two surfaces *share* one hidden
generator across any disguise (*same_origin*), and *cast* a generator into a new
surface. It pairs that recovery with the **wisdom half** — multi-hypothesis ranking
of competing generators, a residual taxonomy for whatever cannot be compressed, an
O(1) constant-time transcoder between quintillion-scale combinatorial spaces, and a
Human Translation Layer that renders every finding as *what was discovered, why it
is believed, and what would falsify it.*

## Where the source lives

Veritas began as a standalone, standard-library-only engine and was then
**consolidated natively into Chiron** — it is no longer a separate program. Its full,
readable implementation lives inside the monolith at **`../Chiron/chiron.py`** (the
invariant engine + wisdom layer), where it is exercised by the embedded gate suite:

```bash
cd ../Chiron
python3 chiron.py collapse 1 1 2 3 5 8 13     # recover + prove a generator
python3 chiron.py topk 1 4 9 16 25            # ranked competing hypotheses
python3 chiron.py same-origin "1 2 3" :: "9 18 27"   # provable shared generator
python3 chiron.py explain 2 4 8 16 32         # machine view + Human Translation Layer
python3 chiron.py selftest                    # invariant-operation gates (23/23)
```

This folder marks Veritas as the named organ and points to its living source; the
engine itself is verified and owner-signed inside Chiron.
