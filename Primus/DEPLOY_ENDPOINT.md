# Engine endpoint boundary notes

**Status: local HTTP service implemented and tested; public/mobile deployment
not implemented.** `python3 test_engine_server.py` drives the endpoint over
real local sockets (48/48 gates at this revision). That validates the engine
wrapper and the `/v1` wire contract — it does not provision, authenticate, or
operate an internet-facing service.

## Supported posture today

Run the service on loopback, where it is private to the machine by default:

```bash
cd Primus
PYTHONPATH=src python3 -m primus.engine_server --host 127.0.0.1 --port 8790
```

The closed legacy routes are `GET /`, `GET /health`, and `POST`
`/collapse`, `/certify`, and `/conjecture`. The small versioned boundary for a
future native client is documented in [MOBILE_API.md](MOBILE_API.md):
`GET /v1/capabilities`, `POST /v1/collapse`, and `POST /v1/certify`.

The server enforces bounded bodies, exact engine limits, a closed route table,
rate/concurrency budgets, fixed-string errors, and no source/exception/input
reflection on error paths. It changes nothing on a stamping path. CORS is off
by default; an owner can configure exactly one browser origin with
`CHIRON_CORS_ORIGIN`. Native clients do not need CORS.

The two `429` refusal classes include standard retry guidance: `Retry-After:
60` for a rate budget and `Retry-After: 1` for a temporarily saturated
concurrency gate. These are conservative local hints, not a public-service
availability guarantee.

## What the static bearer is — and is not

`CHIRON_API_TOKEN` makes each `POST` require one fixed
`Authorization: Bearer` value. It is a development/local deployment control,
not mobile authentication. In particular, it does not provide an identity
issuer, token expiration, audience or scope checks, secure mobile storage,
rotation, revocation, gateway audit logs, TLS termination, or distributed
abuse controls. Do not embed it in an application binary.

`CHIRON_TRUST_FORWARDED=1` only changes which source IP feeds the rate limiter.
Set it only behind a proxy you operate and know overwrites
`X-Forwarded-For`; it is not an authentication feature.

## Before a public or iOS deployment

No public endpoint, cloud provider integration, or native iOS network client
is claimed by this repository. A future deployment must supply and validate,
outside `primus.engine_server`:

- TLS termination and a network policy that exposes only the intended v1
  routes;
- an authenticated gateway issuing short-lived, scoped credentials and
  enforcing audience/issuer validation, rotation, revocation, and audit logs;
- request-size, rate, abuse, and observability controls at the deployment
  edge; and
- a separate native client test suite that preserves JSON certificate values
  without float rounding or client-side re-verification.

The existing Dockerfile and any historical PaaS notes are not a validated
mobile deployment recipe. Choosing a non-loopback bind or putting this
process behind a public proxy is an explicit operator decision outside the
tested boundary above, not an authorization implied by this document.

## Verify the local boundary

```bash
cd Primus
python3 test_engine_server.py
```

The test covers legacy compatibility, v1 envelopes and strict body shapes,
closed routes, auth behavior, CORS default-deny/exact-origin opt-in, bounded
hostile requests, and error no-leak behavior.
