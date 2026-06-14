# Contributing to the Public Grow

The public Congress is open to outside contribution **through Pull Requests** — the
review step is deliberate: it lets the project accept new knowledge from anyone
while keeping a human gate so the public grow can't be polluted or steered
off-course. Direct write access is not granted; that is the point.

## How to contribute

1. **Fork** this repository.
2. **Grow** the public Congress on your fork:
   ```bash
   cd Chiron
   python3 chiron_grow.py --params grow-public/parameters.json --once
   ```
   Point `source` at whatever you like (a wiki, a website, or a JSON API — see
   `grow-public/README.md`). Be polite to sources: keep `rate_limit_seconds` ≥ 0.5
   and set a descriptive `user_agent` with your contact.
3. **Commit** the updated `grow-public/chiron_memory.json` (and
   `grow-public/chiron_grow_state.json`).
4. **Open a Pull Request** describing what you ingested and from where.

## What gets merged

- Growth produced by the unmodified engine (`chiron.py` / `chiron_grow.py`).
- Material from sources that are legal to read and redistribute as derived,
  compressed knowledge.
- Changes confined to `grow-public/`.

## What does not

- Edits to the engine, the private grow, or any other folder (open a separate,
  clearly-scoped PR for engine changes).
- Memory files produced by a modified engine, or that fail to load
  (`python3 chiron.py attest --memory grow-public/chiron_memory.json` must succeed).
- Anything that can't state its provenance.

## Merging is idempotent

Two contributors can grow in parallel. Verified laws are owner-bound,
order-independent records that pool without trust:

```bash
python3 chiron.py merge their_congress.json --memory grow-public/chiron_memory.json
```

so the maintainer can pool contributions rather than pick one.

The engine, the private grow, and the rest of the repository are operated only by
the maintainer.
