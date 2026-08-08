# Chiron reconstruction record

**Status:** maintained evidence record, 2026-08-08. This document describes
the local implementation and its boundaries. It is not a product roadmap,
deployment announcement, or evidence for an unobserved integration.

## Decision: preserve one canonical verification path

The canonical computational sources are Python. The macOS app is a local
SwiftUI interface over those sources, not a Swift reimplementation of their
stamping logic. Every interface must preserve the source record and the
`VERIFIED` / `REFUTED` / `REFUSED` disposition rather than translating it
into a confidence score or a stronger claim.

| Concern | Source of truth | Derived or interface artifact |
|---|---|---|
| Exact invariant recovery | `Primus/src/primus/engine.py` | `Primus/invariant_engine.py` compatibility shim |
| Exact claim certification | `Primus/src/primus/certify.py` | CLI, MCP, and local HTTP responses |
| Chiron engines | `Chiron/*.py` | `Chiron Monolith/chiron_monolith.py` (generated) |
| Court-oriented decision records | `JDICert/cert_engine.py`, `JDICert/primer.py` | Chiron bridges and output records |
| Native interface | `App/Sources/` | `App/build/Chiron.app` local build artifact |
| Module index | `Chiron/manifest.json` | `docs/ENCYCLOPEDIA.md` |

`Chiron/chiron_memory.json` is untracked local runtime state and must not be
committed. The tracked clean-memory files are empty seeds, not a substitute
for a source corpus.

## Surface status

| Surface | Status | Boundary |
|---|---|---|
| Primus core | implemented-and-tested | Exact arithmetic, held-out verification, refusal, package CLI, stdio MCP, and local HTTP. |
| Chiron modules | implemented-and-tested | Local analysis, provenance, certification, adjudication, and a generated offline fold. |
| Chiron MCP | implemented-and-tested locally | stdio JSON-RPC with reviewed `attest`, `analyze`, `certify`, `collapse`, `trace`, and `catalog` tools; no arbitrary module dispatch. |
| Local provenance records | implemented-and-tested locally | Metadata-only records for bounded, regular UTF-8 files; no raw text persistence or network delivery. |
| macOS app | implemented-and-tested locally | SwiftUI invokes the local canonical vault through `Foundation.Process`; it contains no independent verifier. |
| Foundry/AIP boundary | unconfigured, non-delivering | Typed configuration/mapping boundary only. No supplied credentials, ontology IDs, endpoint, transport, or delivery evidence. |
| Cloud-provider adapters | configuration-gated | Code paths may be exercised offline; a live provider or account is not inferred without observed credentials and calls. |

No public service, remote trust boundary, distribution signing, notarization,
or third-party deployment is established by this record.

## Validation and regeneration

Run relevant gates before making a claim about the implementation. The normal
full battery and parity check are:

```bash
python3 bin/chiron test --full
python3 bin/chiron parity
```

For the local macOS app:

```bash
cd App && swift test --scratch-path /tmp/chiron-build
```

After a Chiron source change, rebuild the fold and capability records; never
hand-edit the monolith:

```bash
cd "Chiron Monolith" && python3 build_monolith.py && python3 chiron_monolith.py --selftest
cd .. && python3 Chiron/build_manifest.py --run && python3 Chiron/build_encyclopedia.py
```

The [operating manual](../notes/SOP.md) contains the wider gate battery and
release discipline.

## Security and deployment boundary

- MCP is a local stdio tool. It is not a remote unauthenticated API.
- Local HTTP services bind conservatively by default; CORS is not
  authentication, and no production endpoint is asserted here.
- The macOS app is a local operator interface. It has no bundled engine,
  provider credential, or distribution-readiness claim.
- A Foundry/AIP mapping becomes a real integration only after an authorized
  owner supplies the target ontology, transport, credentials, and a
  delivery-observation gate.

For the separate research evidence hierarchy, read
[RESEARCH_MAP.md](RESEARCH_MAP.md). For engine limits rather than planned
features, read [KNOWN_LIMITATIONS.md](../Chiron/docs/KNOWN_LIMITATIONS.md).
