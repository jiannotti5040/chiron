# Foundry / AIP integration boundary

**Status: implemented-and-tested offline contract; no live Foundry or AIP
connection is claimed.**

`Chiron/foundry_boundary.py` is a small, versioned boundary between Chiron's
core records and a separately authorized external ontology integration. It is
stdlib-only and intentionally has no network client, endpoint, credential
reader, SDK dependency, or Palantir-specific core type.

This separation is intentional: Chiron remains useful without an external
platform, and an external writer cannot make a Chiron claim look verified by
changing an ontology field.

## Contract

The contract version is `chiron.external-ontology/1`; its configuration and
mapping versions are separately named in the module. The typed `RecordKind`
catalog covers:

- `Source`, `Artifact`, `Claim`, `Evidence`, `Contradiction`, and
  `Transformation`;
- `EngineRun`, `ModelRun`, `Candidate`, and `Certificate`;
- `Disposition`, `Experiment`, and `UserDecision`.

`RecordLink` holds explicit relationships such as `supports`, `contradicts`,
`consumes`, `produces`, and `certifies`. For example, a Claim can link to
supporting or contradicting Evidence, an EngineRun can consume Artifacts and
produce Candidates, and a Certificate can certify a Claim or result.

Chiron claim outcomes remain exactly `VERIFIED`, `REFUTED`, or `REFUSED`.
The additional workflow values on a `Disposition` record (`PROVISIONAL`,
`ESCALATED`, and `UNSUPPORTED`) describe handling state only; they never turn
an unverified claim into a verified one.

The default mapping supplies clearly placeholder external object names such as
`chiron_claim`. They are not discovered ontology identifiers and must be
replaced with the authorized object types and field names of a real deployment.

## Safe modes in this repository

```bash
python3 Chiron/foundry_boundary.py
python3 Chiron/tests/test_foundry_boundary.py
```

`IntegrationConfig` supports only two modes:

- `unconfigured` returns `UNCONFIGURED`, with `delivery_confirmed=False`.
- `mock` returns `SIMULATED_NOT_DELIVERED`, with a deterministic batch digest
  and inspectable would-be objects, still with `delivery_confirmed=False`.

Neither result is a remote acknowledgement. There is intentionally no `live`
mode and no local fallback that silently writes elsewhere.

## What a real, separately deployed integration requires

Before an authorized team adds a transport outside the core boundary, it must
provide all of the following:

1. A named, authorized workspace and the actual ontology object-type and field
   mappings.
2. A secret-manager *reference* for credentials; never commit credential
   material into this repository or pass it through Chiron records.
3. A permission/approval reference covering object writes, actions, functions,
   datasets, and any agent execution in scope.
4. An audit-log and redaction/retention policy for every external write.
5. An approved transport implementation and its dependency review, timeout,
   rate-limit, retry, and idempotency policies.
6. Development-environment tests that prove the mapping, authorization
   boundaries, action semantics, and audit trail before production use.

`assess_live_readiness()` can report absent references, but even a complete set
of references returns `LIVE_TRANSPORT_NOT_INCLUDED`. It deliberately does not
claim readiness or establish a network connection. A live integration should
be introduced as a separately reviewed adapter with observed evidence of those
requirements.
