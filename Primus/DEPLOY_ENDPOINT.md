# Deploying the engine endpoint (Fly.io / Render notes)

**Author: Jacob Iannotti. Apache-2.0 (see LICENSE).**
Status: implemented-and-tested locally (`test_engine_server.py`, 33/33 over
real HTTP). These are deploy NOTES — nothing below has been provisioned;
deploying is an explicit owner action.

## What gets deployed, and what never leaves

`primus.engine_server` — request in, certificate out. The engine source is
in the container but is **never serialized**: responses are certificate JSON
only; exceptions surface as a REFUSED envelope carrying the exception type
name, never a message or traceback; routing is a closed table with no
catch-all (`GET /`, `GET /health`, and the three tool POSTs — anything else
is a 404, a wrong method is a 405 with `Allow:`); no error path ever emits
HTML, a traceback, or an echo of the caller's request; there is no file
serving of any kind. Hard budgets at the door: 128 KiB bodies,
the certify/conjecture sequence caps (256 terms), per-IP and global
rate limits, bounded concurrency — everything over budget is REFUSED.

## Container

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY Primus/ /app/Primus/
RUN pip install --no-cache-dir numpy && pip install --no-cache-dir ./Primus
# gplearn is OPTIONAL: without it /conjecture's GP fallback honestly REFUSES
# when the exact engine abstains. Add `pip install gplearn` to enable it.
EXPOSE 8790
CMD ["python3", "-m", "primus.engine_server", "--host", "0.0.0.0", "--port", "8790"]
```

Build context is the vault root (so `COPY Primus/` resolves). Nothing else
from the vault goes into the image.

## Environment

| Var | Meaning | Suggested public value |
|---|---|---|
| `CHIRON_API_TOKEN` | require `Authorization: Bearer <token>` on every POST | set one unless you intend an open demo |
| `CHIRON_RATE_PER_MIN` | per-IP requests/minute | 30 |
| `CHIRON_RATE_GLOBAL_PER_MIN` | total requests/minute | 240 |
| `CHIRON_MAX_CONCURRENCY` | simultaneous engine calls | 4 |
| `CHIRON_TRUST_FORWARDED` | `1` to take client IP from `X-Forwarded-For` | `1` on Fly/Render (their proxy sets it); NEVER when exposed directly |

## Fly.io

```toml
# fly.toml
app = "chiron-engine"
[build]
[http_service]
  internal_port = 8790
  force_https = true
  auto_stop_machines = true      # scale-to-zero: free-ish when idle
  auto_start_machines = true
  min_machines_running = 0
[env]
  CHIRON_TRUST_FORWARDED = "1"
```

```
fly launch --no-deploy        # from the vault root, with the Dockerfile above
fly secrets set CHIRON_API_TOKEN=<token>
fly deploy
curl https://chiron-engine.fly.dev/health
```

## Render (Blueprint — the committed path)

A `render.yaml` Blueprint and a `Dockerfile` live at the vault root, so Render
can provision the whole service from this repo. Steps:

1. Render dashboard → **New → Blueprint**.
2. **Connect a repository** → authorize your host's GitHub app for `chiron`
   (this grants Render read access to the private repo so it can build — the
   running service still exposes only the API, never source).
3. Pick this repo; Render reads `render.yaml` and shows the `chiron-engine`
   web service. Click **Apply**.
4. First build takes a few minutes (numpy install). When it's live, hit
   `http://localhost:8790/health` (exact host shown in the
   dashboard).

The Blueprint is **open by design** (no token — the value is public eval on
caller input) but bounded: per-IP 20/min, global 120/min, concurrency 2, the
certify input caps, REFUSED over budget. To lock it down, add
`CHIRON_API_TOKEN` in the dashboard (Environment tab) — no code redeploy — and
clients send `Authorization: Bearer <token>`. `gplearn` is intentionally not
installed, so `/conjecture` honestly REFUSES when the exact engine abstains;
add it to the Dockerfile if you want GP proposals (costs memory on free tier).

Free instance note: it spins down after ~15 min idle and cold-starts on the
next request (a few seconds). Fine for a demo; bump `plan` in `render.yaml`
for always-on.

### Alternative: prebuilt image (keeps Render off the source repo)

If you'd rather not give Render read access to the repo, build locally/in CI
and push to a registry (GHCR), then point a Render service at
`runtime: image`. The image still contains the engine (any runner does), but
Render never clones the repo. More steps; the Blueprint above is simpler.

## Smoke, from anywhere

The public repo ships the client: `eval/remote.py`.

```
python3 eval/remote.py --url https://<host> health
python3 eval/remote.py --url https://<host> collapse "1 1 2 3 5 8 13 21 34 55 89 144"
python3 eval/remote.py --url https://<host> collapse "2 3 5 7 11 13 17 19 23 29 31 37"
CHIRON_API_TOKEN=<token> python3 eval/remote.py --url https://<host> certify "2+2=5"
```

Expected: Fibonacci verifies, primes come back honestly unstamped. If you
publish the URL, publish the rate budget next to it — refusing over-budget
requests loudly is part of the contract, not an outage.
