# Security model

**Status: evidence record for this checkout, 2026-08-08.** Every control below
was read in the source that implements it, and the file is named so a reader
can check the claim rather than trust it. Controls that do **not** exist are
listed as plainly as the ones that do.

This document does not assert a deployed system. There is no project-operated
public endpoint, no issued credential, and no production identity system.

## The asset actually being protected

Chiron's value is one property: **a `VERIFIED` stamp has never been false on
external data.** The primary security goal follows from that and is unusual —
the worst outcome is not data loss or downtime. It is a *false stamp*.

An attacker who makes Chiron certify something it did not exactly check has
destroyed the product. An attacker who makes Chiron refuse has caused an
inconvenience. Every trade-off below resolves in that direction.

## Trust boundaries

| Boundary | Trusted | Not trusted |
|---|---|---|
| Canonical engine | The Python vault in this checkout, and the interpreter the operator selected | Any text it is asked to certify |
| MCP | The reviewed static tool allowlist | Tool arguments; any file path a caller names |
| Local `/v1` service | The loopback process the operator started | Request bodies; `Origin` headers; HTTP methods |
| Native clients | The versioned envelope and certificate schema | Response bodies before schema validation |
| File ingestion | The user's explicit selection | File contents, encoding, and size |
| Model assistance | Nothing | **Everything the model emits** |

The last row is the important one. Model output is treated as hostile input,
not as a privileged suggestion.

## Controls that exist

### MCP (`Chiron/mcp_server.py`)

- **Static reviewed allowlist.** Six tools — `attest`, `analyze`, `certify`,
  `collapse`, `trace`, `catalog`. Arbitrary vault module or function dispatch
  is intentionally unavailable, so a caller cannot reach an unreviewed code
  path by naming it. `catalog` reports this posture in its own output.
- **Declared authority per tool.** Each tool carries `authority`,
  `side_effects`, and a `provenance` pointer to its canonical implementation.
  All six are `readOnlyHint: true`, `destructiveHint: false`,
  `openWorldHint: false`.
- **Local stdio transport.** It is a subprocess tool, not a network listener,
  and there is no remote MCP transport to authenticate.
- **Bounded file reads.** Tools that accept a path read only the caller-named
  file, bounded by `MAX_FILE_BYTES`.

### Local `/v1` service (`Primus/src/primus/engine_server.py`)

- Binds `127.0.0.1` by default.
- **Closed route set** — eight entries, fixed at import in the `ROUTES` dict
  (`engine_server.py:311-320`); anything not a key 404s at `:521-524`, with no
  catch-all and no prefix match. The versioned surface is `GET
  /v1/capabilities`, `POST /v1/collapse`, `POST /v1/certify`; the unversioned
  legacy surface is `GET /`, `GET /health`, `POST /collapse`, `POST /certify`,
  `POST /conjecture`. No path arguments, dynamic tool names, file operations,
  or server-side action routes.
- **Bounded bodies** at 128 KiB at the HTTP door, before parsing.
- **Strict body validation**: each POST permits exactly its one field; unknown
  fields, wrong JSON types, and non-integer sequence items are refused with a
  `400` before the engine is called.
- **CORS off by default**; one exact origin may be opted in. Wildcards and
  reflected origins are unsupported. CORS is documented as *not*
  authentication.
- `CHIRON_API_TOKEN` sets one optional static bearer for POSTs, documented as
  a local development control only.

### Native clients (`App/Sources/ChironService/LocalServiceClient.swift`)

- **Transport policy**: HTTPS required, with a plaintext exception for literal
  `127.0.0.1` / `::1` only. `localhost` is deliberately rejected — it is a
  resolver name and can be remapped.
- URLs carrying a user, password, query, or fragment are rejected.
- **Redirects are blocked** at the transport, and a 3xx is refused before
  envelope parsing, so user text and an `Authorization` header can never be
  forwarded to a host the endpoint policy never checked.
- **Response bounds** are enforced while streaming *and* re-checked after, so
  a substitute transport cannot bypass the budget.
- **Schema pinning**: envelope schema, request-id shape, operation, engine
  schema, tool name, and certificate schema are all validated. Drift is an
  error, not a warning.
- **No fallback.** A failed request never silently degrades to a local guess.
- Credentials are fetched per request from an injected closure; the client has
  no string-token initializer and persists nothing.

### Credential storage (`iOS/ChironMobile/KeychainTokenStore.swift`)

- Tokens live in Keychain with
  `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` — not synced, not available
  before first unlock — and are scoped to the exact endpoint base URL.
- No token is embedded in the repository, project, or app defaults.
- The bearer is sent on POSTs only; a capabilities read never discloses a
  credential to an intermediary that might log GET requests.

### File ingestion (`App/Sources/ChironApp/FileInput.swift`)

- User-selected only, through the system picker or drop.
- Reads are bounded to 8 MiB and read `maxBytes + 1` so truncation is
  *detected* rather than silently accepted; a truncated read is surfaced and
  disqualifies the file from a canonical source record.
- Invalid UTF-8 is rejected rather than replacement-decoded.
- A source record's content hash is re-checked against the imported file, and
  a mismatch raises `fileChangedAfterImport` instead of attaching stale
  provenance.

### Model assistance (`App/Sources/ChironIntelligence/`)

- The on-device model runs entirely on device; text is not sent to a provider.
- **A verdict is unrepresentable.** `ProposedClaim` has no status, score,
  confidence, or correction field, and the `@Generable` schema gives the model
  no vocabulary for deciding anything.
- **Grounding** rejects any span not present in the source, and always carries
  the *document's* bytes forward rather than the model's rendering of them.
  This is the prompt-injection and hallucination boundary: text a model
  invented cannot become a certified claim, because it is not in the document.
- The proposer target depends on nothing else in the package, so it cannot
  reach a client, an engine, or a certificate.

## Threats, and what answers them

| Threat | Answer | Residual risk |
|---|---|---|
| Model invents a claim and it gets certified as the user's | Grounding filter; verbatim source bytes carried forward | A model can still *omit* a real claim. Recall is not a safety property here, but it is a quality one. |
| Injected instructions inside an ingested document | Document text is data: it is certified, never executed, and the proposer's output is re-checked against the document itself | An operator can still act on what they read. The system does not obey it. |
| MCP caller reaches an unreviewed vault module | Static allowlist; no dynamic dispatch | A reviewed tool's own file-path argument is still attacker-influenced; reads are bounded but a caller can name any readable file the user can read. |
| Credential exfiltration via redirect | Redirects blocked at transport and refused before parsing | None known for this path. |
| Plaintext credential over the network | HTTPS required except literal loopback | An operator can still point at a hostile HTTPS endpoint. |
| Oversized or hostile body causing DoS | 128 KiB door, bounded response streaming, anchored regex scans, deterministic work bounds | A local operator can always exhaust their own machine. |
| Silently truncated evidence | Truncation is detected and disqualifies canonical provenance | None known for this path. |
| Secret committed to the repository | Scanned this session: no API-key, token, or private-key patterns in tracked files; no `.env`/`.pem`/`.p12` tracked | A scan is a point-in-time result, not a guarantee. |

## Controls that do **not** exist

Stated plainly, because absence documented is worth more than absence implied.

- **No remote MCP transport, and therefore no remote MCP authentication.**
- **No production identity system.** The static bearer has no rotation,
  revocation, scoping, expiry, issuer/audience validation, or audit trail.
- **No TLS termination** in the local server. A public deployment needs a
  gateway outside this process. Rate limiting is *not* absent: `class Limiter`
  (`engine_server.py:139-163`) enforces a thread-safe sliding one-minute window
  per key and globally, wired as the handler default `Limiter(30, 240)` at
  `:349` and enforced at `:654-659`. It is in-process and per-instance, so it
  bounds a single server, not a fleet.
- **No sandbox entitlement, hardened runtime, notarization, or distribution
  signing.** Bundles are ad-hoc signed and are rejected by Gatekeeper.
- **SBOM: generated, and gated.** `ci/sbom.py` derives the dependency surface
  from declarations in the tree — `Primus/pyproject.toml`, `Chiron/manifest.json`,
  `App/Package.swift` — with no network lookup, so it runs offline and in CI.
  Observed: **0** third-party Swift packages, **1** required Python package
  (`numpy>=1.22`, imported at module level in `Primus/src/primus/engine.py:52`),
  **2** optional (`gplearn>=0.4.2`, `scikit-learn>=1.3`, behind the
  `conjecture` extra, which degrades to an honest `REFUSED` without them), and
  **10** vault modules importing beyond the standard library.

  `python3 ci/sbom.py --check` fails if any module imports a third-party
  package that nothing declares or guards, and it is a gate in the battery.
  That is the part that matters: this paragraph previously claimed the Python
  core was pure standard library, which was false, and nothing would have
  caught it. A declared range is reported as a range — pinning it here would
  invent precision the repository does not record.
- **No audit log of MCP invocations.** Neither `Chiron/mcp_server.py` nor the
  Primus MCP server records an invocation ledger. The `/v1` HTTP service does
  log: `_access()` (`engine_server.py:434-450`) emits one structured line per
  request carrying `ip`, `method`, `path`, `status`, `in_bytes`, and a 16-hex
  `in_sha256` prefix of the request body — enough to correlate a request
  without retaining its content.

## Reporting

Security-relevant findings about this checkout belong in the repository's
issue tracker under the maintainer's coordinated-disclosure preference. This
document does not establish a security-response commitment or an SLA.
