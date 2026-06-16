# Growing Chiron — `chiron_grow.py`

**Architect & sole owner: Jacob Iannotti. Proprietary — all rights reserved.**

`chiron_grow.py` is the **shared grower**: one local, network-capable engine that
feeds Chiron continuously. It is deliberately separate from the monolith —
`chiron.py` stays offline and deterministic; only this runner reaches the network,
and only when you run it. The same engine drives any grow by pointing `--params` at
that grow's folder.

Each pass it:

1. (optionally) **pulls** the current memory from GitHub,
2. ingests from the configured **source** — Wikipedia, any website, or any JSON API,
3. feeds each item through `assimilate` under its **subject** — which spawns or
   extends a domain, classifies it **integral vs general**, recognizes reuse, and
   grows the memory; linked items become a self-extending **frontier**, so it keeps
   discovering,
4. **grows cross-domain concepts** from what it has now proven,
5. **pushes** the grown memory back when it fills (saving **locally and** to
   GitHub), and
6. **resumes** where it left off — three ways over: a local cursor, that cursor
   committed to git, and the memory's own `ingested_sources` ledger.

It **auto-compacts** past `max_congress_mb`, so it runs forever without bloating the
repo.

## The two grows

| Grow | Folder | Who runs it | Notes |
|---|---|---|---|
| **Public** | `grow-public/` | anyone, via Pull Request | open contribution; see `grow-public/README.md` + `CONTRIBUTING.md` |
| **Private** | `grow-private/` | the owner only | the true *growth*; see `grow-private/README.md` |

```bash
cd Chiron
python3 chiron_grow.py --params grow-public/parameters.json            # public grow
python3 chiron_grow.py --params grow-private/parameters.json           # private grow
python3 chiron_grow.py --params grow-public/profiles/regulatory.json --once   # laws -> 'regulation' domain
```

Flags (any profile): `--dry-run` (offline demo, no network/git), `--once` (single
pass), `--reset` (clean seed + clear cursor). Background it with
`nohup python3 chiron_grow.py --params <cfg> > grow.log 2>&1 &` and watch with
`tail -f grow.log`; stop with `pkill -f chiron_grow.py`.

## Any source — `source` in `parameters.json`

- **`wikipedia`** — no API key; set a descriptive `user_agent` with your contact.
- **`web`** — `source.name:"web"`, give `seeds` (URLs); it reduces HTML to text and
  follows links (`same_domain_only` keeps it on one site); `domain_label` names the
  subject.
- **`api`** — `source.name:"api"` with `list_url`, `items_path` (dot-path to the
  array), `id_field`, optional `item_url_template`.
- **`oeis`** — `source.name:"oeis"` with a `query` (default `keyword:core`). Feeds the
  engine **structured integer sequences** — its ideal food: nearly every sequence
  collapses to a verified law (arithmetic, geometric, recurrence, polynomial…), so
  this is the source that best showcases what Chiron actually does. Ready profile:
  `python3 chiron_grow.py --params grow-public/profiles/oeis.json --once`.

Wikipedia fetches are **batched** (≈20 articles per request) and skip
disambiguation/list/index pages; each item is capped at `max_chars_per_item` so the
memory stays value-dense. Other knobs: `topics`, `articles_per_topic`,
`links_per_article`, `frontier_per_pass`, `push_when_mb`, `max_congress_mb`,
`rate_limit_seconds`, and
`git` (`push` / `pull_first` / `branch`).

## Notes

- **macOS SSL.** The stock python.org build ships without a CA bundle, so the first
  HTTPS call can raise `CERTIFICATE_VERIFY_FAILED`. The grower handles this: it uses
  `certifi` if installed, otherwise falls back to unverified TLS for these read-only
  public fetches (printing one `[ssl]` line) and keeps running. To verify properly,
  run Python's `Install Certificates.command` or `pip3 install certifi`; set
  `source.verify_ssl` to control it.
- **Resume is robust.** The crawl cursor (`chiron_grow_state.json`) travels with the
  repo, and the memory carries its own ledger of everything eaten — so a fresh
  clone or a second machine never re-ingests what's already there.
- **Self-growth runs as it grows.** Each pass it grows cross-domain concepts; deeper
  self-growth (proposing and applying changes to its own code) is gated by a
  reversible backup + a GREEN self-test and is documented in the main `README.md`.
- Stop anytime with Ctrl-C — it saves and pushes before exiting.
