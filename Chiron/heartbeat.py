#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
heartbeat.py — the vault's pulse: all of it at once, always (HORIZON.md H1→H2 bridge).

Until now the vault only moved when a human clicked. The heartbeat removes the
harness from the TEMPO while leaving it exactly where the constitution requires —
on the TRUTH. Each beat, unattended, the organism:

  INWARD   reads one of its own organs (a module or guide, rotating through the
           whole body) and grows what it can exactly verify into its own living
           memory (`artifacts/heart_congress.json`) — the vault growing on itself,
           through the same gate everything passes: verified or refused.
  OUTWARD  takes one grower pass at the world — dry-run by default; set
           CHIRON_HEART_LIVE=1 to let verified knowledge land in the Congress.
  REFLEX   runs one rotating gate from the battery (ledger, epistemic, semic
           energy, density, formal soundness, seed↔fold drift) — continuous
           self-verification instead of episodic; every 8th beat runs full
           spine↔fold parity.
  WITNESS  records every movement in the run ledger, then emits THE VAULT
           CERTIFICATE (`artifacts/vault/latest.json`): one signed self-statement
           of the whole organism — what it is, what it knows, what it proved this
           beat, what it refused, and what would falsify it.

What the heartbeat may NEVER do, by construction: stamp anything unverified,
edit its own source (self-edit stays quarantined behind CHIRON_ALLOW_SELF_EDIT
and the President), or touch the committed Congress without CHIRON_HEART_LIVE=1.
A failed movement is recorded as a failure and the certificate says so —
the heart does not flatter the body.

    python3 heartbeat.py once                  # one beat, then stop
    python3 heartbeat.py serve --interval 600  # the living loop (Ctrl-C stops)
    python3 heartbeat.py status                # last beat + certificate summary
    python3 heartbeat.py selftest              # hermetic gates (no real movements)

Status: implemented & tested.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
# When running from inside the fold, the sibling script FILES live in Chiron/ —
# resolve organs and reflex scripts against whichever body actually has them.
_SPINE = _HERE if os.path.isfile(os.path.join(_HERE, "grow_clean.py")) else \
    os.path.join(os.path.dirname(_HERE), "Chiron")
sys.path.insert(0, _HERE)
import run_ledger  # noqa: E402

ARTS = os.path.join(_HERE, "artifacts")
STATE = os.path.join(ARTS, "heart_state.json")
HEART_CONGRESS = os.path.join(ARTS, "heart_congress.json")
VAULT_CERT = os.path.join(ARTS, "vault", "latest.json")
MONOLITH = os.path.join(os.path.dirname(_HERE), "Chiron Monolith", "chiron_monolith.py")
PY = sys.executable or "python3"

# The reflex rotation: cheap, real gates. Every 8th beat: full spine<->fold parity.
REFLEXES = [
    ("run_ledger", [PY, os.path.join(_SPINE, "run_ledger.py"), "selftest"]),
    ("epistemic", [PY, os.path.join(_SPINE, "epistemic.py"), "selftest"]),
    ("semic_energy", [PY, os.path.join(_SPINE, "semic_energy.py"), "selftest"]),
    ("density_emotion", [PY, os.path.join(_SPINE, "density_emotion.py"), "selftest"]),
    ("formal_check", [PY, os.path.join(_SPINE, "formal_check.py")]),
    ("drift_check", [PY, os.path.join(os.path.dirname(_HERE), "Primus", "drift_check.py")]),
]


def _state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"beat": 0}


def _save_state(st):
    os.makedirs(ARTS, exist_ok=True)
    json.dump(st, open(STATE, "w", encoding="utf-8"))


def _body():
    """The organism's readable organs, in stable order — what INWARD rotates through."""
    organs = sorted(
        os.path.join(_SPINE, f) for f in os.listdir(_SPINE)
        if f.endswith(".py") and not f.startswith("_"))
    docs = os.path.join(_SPINE, "docs")
    if os.path.isdir(docs):
        organs += sorted(os.path.join(docs, f) for f in os.listdir(docs) if f.endswith(".md"))
    return organs


def _run(argv, timeout, cwd=None):
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=cwd or _HERE, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0, out[-400:].strip().replace("\n", " · ")[-240:], time.time() - t0
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s", time.time() - t0
    except Exception as e:
        return False, f"error: {e}", time.time() - t0


# ---------------------------------------------------------------- movements
def move_inward(beat, timeout=60):
    organs = _body()
    organ = organs[beat % len(organs)] if organs else None
    if not organ:
        return False, "no organs found", None
    ok, tail, secs = _run([PY, os.path.join(_SPINE, "grow_clean.py"), "file", organ,
                           "--store", HEART_CONGRESS], timeout)
    name = os.path.relpath(organ, _SPINE)
    return ok, f"read own organ {name} -> heart congress · {tail[-120:]}", secs


def move_outward(beat, timeout=90):
    live = os.environ.get("CHIRON_HEART_LIVE") == "1"
    argv = [PY, os.path.join(_SPINE, "chiron_grow.py"), "--params",
            os.path.join(_SPINE, "grow-public", "parameters.json"), "--once"]
    if not live:
        argv.append("--dry-run")
    ok, tail, secs = _run(argv, timeout)
    return ok, f"{'LIVE' if live else 'dry'} grower pass · {tail[-140:]}", secs


def move_reflex(beat, timeout=120):
    if beat % 8 == 0 and os.path.isfile(MONOLITH):
        cli = os.path.join(os.path.dirname(_HERE), "bin", "chiron")
        ok, tail, secs = _run([PY, cli, "parity"], timeout)
        return ok, f"reflex spine<->fold parity · {tail[-120:]}", secs
    name, argv = REFLEXES[beat % len(REFLEXES)]
    ok, tail, secs = _run(argv, timeout)
    return ok, f"reflex {name} · {tail[-140:]}", secs


# ---------------------------------------------------------------- the certificate
def _sha(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except OSError:
        return None


def _congress_stats(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        out = {"size_mb": round(os.path.getsize(path) / 1e6, 3)}
        for k in ("domains", "laws", "concepts"):
            v = d.get(k)
            if isinstance(v, (list, dict)):
                out[k] = len(v)
        return out
    except Exception:
        return None


def vault_certificate(beat, movements):
    """One signed self-statement of the whole organism. Green only if every
    movement this beat was green — the certificate does not flatter."""
    manifest = {}
    try:
        manifest = json.load(open(os.path.join(_HERE, "manifest.json"), encoding="utf-8")).get("summary", {})
    except Exception:
        pass
    cert = {
        "artifact": "vault",
        "claim": "this organism moves on its own pulse and stamps only what it exactly verifies",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "beat": beat,
        "incarnation": run_ledger.incarnation(),
        "fold_hash": _sha(MONOLITH),
        "all_movements_green": all(m["ok"] for m in movements),
        "movements": movements,
        "body": {"modules": len([f for f in os.listdir(_HERE) if f.endswith('.py')]),
                 "manifest": manifest},
        "memory": {"congress": _congress_stats(os.path.join(_HERE, "chiron_memory.json")),
                   "heart_congress": _congress_stats(HEART_CONGRESS)},
        "ledger_height": len(run_ledger.read(100000)),
        "what_was_discovered": "; ".join(
            f"{m['name']}: {'ok' if m['ok'] else 'REFUSED/FAILED'}" for m in movements),
        "what_would_falsify": ("any VERIFIED stamp an external replay cannot reproduce exactly; "
                               "any behavioral difference between spine and fold; any entry in "
                               "either congress lacking exact held-out verification; any beat "
                               "reported green here whose ledger records a failure"),
    }
    body = json.dumps(cert, sort_keys=True, separators=(",", ":")).encode("utf-8")
    cert["self_hash"] = hashlib.sha256(body).hexdigest()[:16]
    os.makedirs(os.path.dirname(VAULT_CERT), exist_ok=True)
    json.dump(cert, open(VAULT_CERT, "w", encoding="utf-8"), indent=2)
    return cert


# ---------------------------------------------------------------- the beat
def beat_once(movers=None, quiet=False):
    st = _state()
    beat = st["beat"] = st.get("beat", 0) + 1
    movers = movers or [("inward", move_inward), ("outward", move_outward), ("reflex", move_reflex)]
    movements = []
    for name, fn in movers:
        ok, verdict, secs = fn(beat)
        movements.append({"name": name, "ok": bool(ok), "verdict": verdict,
                          "seconds": None if secs is None else round(secs, 2)})
        run_ledger.record(f"heartbeat.{name}", ["beat", str(beat)], ok=ok,
                          verdict=verdict[:200], seconds=secs, source="heartbeat",
                          certificate="artifacts/vault/latest.json")
        if not quiet:
            print(f"  [{'OK ' if ok else 'FAIL'}] {name:8} {verdict[:110]}", flush=True)
    cert = vault_certificate(beat, movements)
    st["last_utc"] = cert["generated_utc"]
    _save_state(st)
    if not quiet:
        mark = "GREEN" if cert["all_movements_green"] else "NOT GREEN (recorded honestly)"
        print(f"  beat {beat} {mark} — vault certificate refreshed (#{cert['self_hash']})", flush=True)
    return cert


def serve(interval):
    print(f"the heart is beating — every {interval}s; Ctrl-C stops it. "
          f"(outward is {'LIVE' if os.environ.get('CHIRON_HEART_LIVE') == '1' else 'dry-run'}; "
          f"set CHIRON_HEART_LIVE=1 to let verified knowledge land)", flush=True)
    try:
        while True:
            print(f"\n♥ beat at {time.strftime('%H:%M:%S')}", flush=True)
            beat_once()
            time.sleep(max(30, interval))
    except KeyboardInterrupt:
        print("\nthe heart rests.")
    return 0


# ---------------------------------------------------------------- gates
def _selftest():
    import tempfile
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    global STATE, VAULT_CERT, HEART_CONGRESS
    keep = STATE, VAULT_CERT, HEART_CONGRESS
    with tempfile.TemporaryDirectory() as td:
        STATE = os.path.join(td, "state.json")
        VAULT_CERT = os.path.join(td, "vault", "latest.json")
        HEART_CONGRESS = os.path.join(td, "heart.json")
        run_ledger.LEDGER = os.path.join(td, "ledger.jsonl")

        # hermetic movements: no subprocesses, no real congress
        green = [("inward", lambda b: (True, "stub organ read", 0.01)),
                 ("reflex", lambda b: (True, "stub gate green", 0.01))]
        c1 = beat_once(movers=green, quiet=True)
        ok("a beat produces the vault certificate", os.path.isfile(VAULT_CERT))
        ok("certificate is green when every movement is green", c1["all_movements_green"] is True)
        ok("certificate carries a self-hash and incarnation",
           len(c1.get("self_hash", "")) == 16 and c1["incarnation"] in ("spine", "fold"))
        ok("movements are memorialized in the ledger",
           len(run_ledger.read(10, path=run_ledger.LEDGER)) == 2)
        ok("falsifier names the replay condition", "replay" in c1["what_would_falsify"])

        mixed = [("inward", lambda b: (True, "ok", 0.01)),
                 ("reflex", lambda b: (False, "gate refused", 0.01))]
        c2 = beat_once(movers=mixed, quiet=True)
        ok("the certificate does not flatter: one failure -> NOT green",
           c2["all_movements_green"] is False)
        ok("the failure is a first-class movement record",
           any(m["ok"] is False for m in c2["movements"]))
        ok("beats are counted monotonically", c2["beat"] == c1["beat"] + 1)
        ok("state survives between beats", _state()["beat"] == c2["beat"])
        organs = _body()
        ok("the body enumerates its own organs (modules + guides)",
           len(organs) > 50 and any(p.endswith("heartbeat.py") for p in organs))
    STATE, VAULT_CERT, HEART_CONGRESS = keep

    passed = sum(1 for _, c in checks if c)
    print("heartbeat self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="The vault's pulse.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("once")
    sub.add_parser("selftest")
    sub.add_parser("status")
    sv = sub.add_parser("serve")
    sv.add_argument("--interval", type=int, default=600)
    args = ap.parse_args(argv)
    if args.cmd == "once":
        cert = beat_once()
        return 0 if cert["all_movements_green"] else 1
    if args.cmd == "serve":
        return serve(args.interval)
    if args.cmd == "status":
        st = _state()
        print(f"beats so far: {st.get('beat', 0)} · last: {st.get('last_utc', 'never')}")
        try:
            c = json.load(open(VAULT_CERT, encoding="utf-8"))
            print(f"vault certificate #{c['self_hash']} · green={c['all_movements_green']} · "
                  f"incarnation={c['incarnation']} · ledger={c['ledger_height']}")
        except Exception:
            print("no vault certificate yet — run `heartbeat.py once`")
        return 0
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
