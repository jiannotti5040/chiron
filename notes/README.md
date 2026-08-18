# docs/ — the vault's papers and records

Two kinds of documents live here: **living references** that describe where the
project is going, and **published working records** — point-in-time internal
notes tracked deliberately, because this project's paper trail (including its
misses) is part of what it is selling.

## The operator's papers — start here

| Document | What it is |
|---|---|
| [SOP.md](SOP.md) | **The instruction manual — the documentation IS the interface.** Part I: operating procedures for every engine, à la carte and dashboard-free — recover rules, gate LLM pipelines, audit candor, governed decisions, bounded-agency campaigns, grow the memory on your own corpus, ship as one file / plugins / HTTP / MCP — each with a real captured session. Part II: maintaining the vault — the gate battery, change playbooks, the defect-response protocol (the 07-11→12 night as worked example), releasing, troubleshooting |
| [DICTIONARY.md](DICTIONARY.md) | The vault's vocabulary — every load-bearing term (collapse, stamp, holdout, drift, parity, Congress, heartbeat…), hand-curated |
| [ENCYCLOPEDIA.md](ENCYCLOPEDIA.md) | Every module, A–Z — **generated from the manifest + lexicon** (`python3 Chiron/build_encyclopedia.py`), so it cannot drift from the code |

## Living references

| Document | What it is |
|---|---|
| [HORIZON.md](HORIZON.md) | The long map: what is proven, what is prototype, what is theory — three horizons with falsifiable gates. Diagram: [horizon.svg](horizon.svg) |
| [STRESS_TEST.md](STRESS_TEST.md) | The adversary's record: 23 probes that try to break the vault, the two holes they found, and what is *not* yet tested |
| [Mathematical_Compendium.pdf](Mathematical_Compendium.pdf) | The mathematics underneath the engines, in one place ([source](Mathematical_Compendium.tex)) |

## Published working records (point-in-time; kept honest, not current)

| Record | Date | Why it's public |
|---|---|---|
| [AFTER_ACTION_2026-07-04.md](AFTER_ACTION_2026-07-04.md) | 07-04 | The day the vault went public: five defects found-and-fixed pre-users, and what caught each |
| [STATUS_REPORT_2026-07-04.md](STATUS_REPORT_2026-07-04.md) | 07-04 | End-of-day verification totals, all reproducible by command |
| [EXTERNAL_VALIDATION_ADDENDUM_2026-07-07.md](EXTERNAL_VALIDATION_ADDENDUM_2026-07-07.md) | 07-07 | A live false verification, published while still open — since RESOLVED (v0.5.1). The "falsified again, repaired again" entry |
| [WHAT_PRIMUS_NEEDS.md](WHAT_PRIMUS_NEEDS.md) | 07-07 | The grounded roadmap: outward reach over inward growth |
| [RELEASE_AND_REACH.md](RELEASE_AND_REACH.md) · [SHOW_HN.md](SHOW_HN.md) | 07-08 | Release/announcement working drafts |

The project's validation history proper lives in
[`Primus/EXTERNAL_VALIDATION.md`](../Primus/EXTERNAL_VALIDATION.md); the
certificate contract in [`Primus/SCHEMA.md`](../Primus/SCHEMA.md); the paper in
[`Paper/`](../Paper/).
