# Deploying the engine endpoint (Fly.io / Render notes)

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see LICENSE.md).**
Status: implemented-and-tested locally (`test_engine_server.py`, 18/18 over
real HTTP). These are deploy NOTES — nothing below has been provisioned;
deploying is an explicit owner action.

## What gets deployed, and what never leaves

`primus.engine_server` — request in, certificate out. The engine source is
in the container but is **never serialized**: responses are certificate JSON
only; exceptions surface as a REFUSED envelope carrying the exception type
name, never a message or traceback; the only GET route is `/health`; there
is no file serving of any kind. Hard budgets at the door: 128 KiB bodies,
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

## Render

New → Web Service → "Deploy from a Git repository" is NOT recommended (the
vault is private and Render would hold a clone); prefer "Deploy an existing
image" from a private registry you push the image to. Set the env table
above in the dashboard; health check path `/health`; instance type Starter
is plenty (the engine is CPU-light at these budgets).

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
