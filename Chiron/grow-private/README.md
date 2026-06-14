# Chiron — Private Grow (`crescere`)

This is the **operator's own growing Congress** — the true *crescere* (Latin: "to
grow"). It runs on the same shared engine as the public grow; only this folder's
configuration and memory are private to the operator. **Operated only by Jacob
Iannotti.** Outside contributors use `../grow-public/` instead.

```
grow-private/
  parameters.json        what to ingest + where from
  chiron_memory.json     the growing private Congress
  chiron_memory_clean.json   pristine seed — reset point
  chiron_grow_state.json the crawl cursor (created on first run)
```

## Run it

From the **`Chiron/` folder**:

```bash
cd Chiron
python3 chiron_grow.py --params grow-private/parameters.json            # continuous
python3 chiron_grow.py --params grow-private/parameters.json --once     # one pass
python3 chiron_grow.py --params grow-private/parameters.json --dry-run  # offline demo
python3 chiron_grow.py --params grow-private/parameters.json --reset    # back to clean seed
```

Background it and watch the log:

```bash
nohup python3 chiron_grow.py --params grow-private/parameters.json > grow.log 2>&1 &
tail -f grow.log
# stop with:  pkill -f chiron_grow.py
```

It pulls, ingests, auto-compacts past `max_congress_mb`, and pushes the grown
Congress + crawl cursor (saving locally and to GitHub). Resume is robust: the local
cursor, the cursor committed to git, and the Congress's own `ingested_sources`
ledger all keep it from re-ingesting anything it has already eaten.

## Sources

Same options as the public grow (`wikipedia` / `web` / `api`) — edit
`parameters.json` → `source`. The private grow defaults to a broad Wikipedia sweep.
