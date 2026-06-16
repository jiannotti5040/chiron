# Chiron — Public Grow (open `growth`)

This is the **open, community-contributable memory.** It runs on the same engine
as everything else in Chiron (`../chiron.py` + `../chiron_grow.py`); only the
configuration and the memory file live here. Anyone may grow it and contribute the
result back by **Pull Request** — that PR review is the gate that keeps the public
grow honest and stops it running off into junk.

```
grow-public/
  parameters.json        what to ingest + where from (edit this)
  chiron_memory.json     the growing public memory (committed; PR-reviewed)
  chiron_memory_clean.json   pristine seed — reset point
  chiron_grow_state.json the crawl cursor (created on first run; travels with the repo)
```

## Run it

From the **`Chiron/` folder** (where the engine lives), point the shared grower at
this folder's config:

```bash
cd Chiron
python3 chiron_grow.py --params grow-public/parameters.json            # continuous
python3 chiron_grow.py --params grow-public/parameters.json --once     # one pass
python3 chiron_grow.py --params grow-public/parameters.json --dry-run  # offline demo
python3 chiron_grow.py --params grow-public/parameters.json --reset    # back to clean seed
```

It pulls the current public memory, ingests, and (if `git.push` is on) commits
**both the memory and the crawl cursor** — saving locally *and* pushing.

## Regulatory & governmental law

A ready profile opens public legal corpora (constitutions, rights instruments,
statutes) into the memory under a `regulation` domain — the material the certifier
certifies high-stakes decisions against:

```bash
cd Chiron
python3 chiron_grow.py --params grow-public/profiles/regulatory.json --once
```

It crawls the seed legal texts (staying on-domain), reduces them to text, and
assimilates them as the `regulation` subject. Add your own jurisdictions by editing
`profiles/regulatory.json` → `source.seeds`.

## Structured data — OEIS (the engine's ideal food)

The invariant engine shines on structured sequences, not prose. A ready profile
feeds it the OEIS (On-Line Encyclopedia of Integer Sequences), where nearly every
entry collapses to a verified law:

```bash
cd Chiron
python3 chiron_grow.py --params grow-public/profiles/oeis.json --once
```

Each sequence's terms go straight to `collapse` — arithmetic, geometric, recurrence,
polynomial, and more become integral laws with high yield. Change the corpus via
`profiles/oeis.json` → `source.query` (e.g. `keyword:nice`).

## Any source — website, API, or wiki

Edit `parameters.json` → `source`:

- **`wikipedia`** (default) — no key; set a descriptive `user_agent`.
- **`web`** — set `source.name` to `"web"` and give `seeds` (a list of URLs).
  The grower fetches each page, reduces HTML to text, assimilates it, and follows
  its links as a self-extending frontier. `same_domain_only` keeps it on one site.
- **`api`** — set `source.name` to `"api"` with `list_url`, `items_path`
  (dot-path to the array), `id_field`, and optional `item_url_template`.

A ready-to-copy example of each lives under `source._alternatives` in
`parameters.json` (that key is ignored by the engine — it's there as a template).

## Contributing

See **CONTRIBUTING.md**. In short: fork → grow → open a PR. The maintainer merges.
Outside contributors grow **this** folder; everything else in the repo is
maintainer-operated.
