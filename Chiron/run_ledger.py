#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
run_ledger.py — the vault's operational memory (HORIZON.md H1.2).

Every operator-initiated engine invocation appends ONE record to an append-only
JSONL ledger: which engine ran, with what arguments, what it concluded, how long
it took, which incarnation (spine or fold) did the work, and where the signed
certificate landed if one was emitted. The dashboard's Pulse stage renders this
ledger; `chiron doctor` reads health from it; Horizon-Two strategy will learn
from it.

Design constraints, in the vault's own discipline:
  - append-only: records are never edited or deleted by this module;
  - single-write appends (one os.write of one line) so concurrent services
    cannot interleave partial records;
  - the ledger is runtime state, not source: it lives under artifacts/ and is
    gitignored — history travels in certificates and git, not here;
  - recording NEVER breaks the recorded operation: every failure path in this
    module degrades to silence, because the ledger is a witness, not a gate.

    python3 run_ledger.py selftest      # gates below
    python3 run_ledger.py tail [n]      # human view of the last n records

Status: implemented & tested.
"""
import json
import os
import sys
import time
import hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(_HERE, "artifacts", "run_ledger.jsonl")

# The ledger is a rolling window, not an infinite tape: an unbounded append-only
# file on an always-on heartbeat is a disk-exhaustion hole. When it grows past
# MAX_LINES we keep the newest KEEP_LINES and drop the rest. History that must
# survive lives in git + the per-run certificates, not here.
MAX_LINES = 20000
KEEP_LINES = 10000


def _rotate_if_needed(path):
    """Cap the ledger. Best-effort and atomic-ish: newest KEEP_LINES rewritten via
    a temp file + os.replace, so a crash mid-rotate leaves the old ledger intact."""
    try:
        with open(path, "rb") as f:
            lines = f.readlines()
        if len(lines) <= MAX_LINES:
            return
        kept = lines[-KEEP_LINES:]
        tmp = path + ".rot"
        with open(tmp, "wb") as f:
            f.writelines(kept)
        os.replace(tmp, path)  # atomic on POSIX
    except OSError:
        pass  # rotation is a courtesy, never a failure


def incarnation() -> str:
    """Which body did the work: the flat spine or the folded monolith."""
    probe = os.path.abspath(getattr(sys.modules.get("__main__"), "__file__", "") or sys.argv[0] or "")
    return "fold" if "chiron_monolith" in os.path.basename(probe) else "spine"


def redact_argv(argv):
    """Return bounded, non-reversible argument witnesses for audit logs.

    The ledger is useful for answering *which operation ran*, but it is not a
    place to copy a user's document, prompt, or provider response.  Callers
    that receive user-controlled arguments opt into this representation: a
    short content hash permits correlation with a supplied value while the
    length preserves operational diagnostics.
    """
    out = []
    for arg in (argv or []):
        value = str(arg)
        digest = hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()[:16]
        out.append(f"sha256:{digest} chars:{len(value)}")
    return out[:12]


def record(engine, argv=None, ok=None, verdict="", seconds=None,
           certificate=None, source="console", path=None, redact=True):
    """Append one record. Returns the record, or None if recording failed.
    Never raises — the witness must not break the act it witnesses."""
    path = path or LEDGER
    try:
        rec = {
            "t": round(time.time(), 3),
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine": str(engine)[:80],
            "argv": (redact_argv(argv) if redact
                     else [str(a)[:120] for a in (argv or [])][:12]),
            "ok": (None if ok is None else bool(ok)),
            "verdict": str(verdict)[:200],
            "seconds": (None if seconds is None else round(float(seconds), 3)),
            "certificate": certificate,
            "incarnation": incarnation(),
            "source": str(source)[:24],
        }
        line = json.dumps(rec, separators=(",", ":")) + "\n"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Crash healing: if a previous writer died mid-line (no trailing newline),
        # start on a fresh line so its torn record cannot corrupt this one.
        try:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    line = "\n" + line
        except OSError:
            pass  # missing/empty ledger — nothing to heal
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        _rotate_if_needed(path)
        return rec
    except Exception:
        return None


def read(n=50, path=None):
    """Last n records, newest first. Tolerates a missing or torn ledger."""
    path = path or LEDGER
    try:
        with open(path, "rb") as f:
            tail = f.readlines()[-max(1, int(n)):]
    except OSError:
        return []
    out = []
    for line in reversed(tail):
        try:
            out.append(json.loads(line))
        except Exception:
            continue  # a torn line is skipped, never fatal
    return out


def certificate_for(engine):
    """The engine's latest signed certificate path, if it emitted one."""
    p = os.path.join(_HERE, "artifacts", str(engine), "latest.json")
    return os.path.relpath(p, _HERE) if os.path.isfile(p) else None


def _selftest():
    import tempfile
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "ledger.jsonl")
        # redact=False is explicit here because the property under test is
        # replay fidelity, not redaction: this argv is written by the test.
        r1 = record("chiron", ["collapse", "1 1 2 3 5 8"], ok=True,
                    verdict="VERIFIED linear_recurrence", seconds=0.42,
                    certificate="artifacts/chiron/latest.json", path=lp,
                    redact=False)
        ok("record returns the appended record", isinstance(r1, dict) and r1["engine"] == "chiron")
        ok("incarnation is named and sane", r1["incarnation"] in ("spine", "fold"))
        r2 = record("semic", ["selftest"], ok=True, verdict="56/56", path=lp)
        ok("appends accumulate", r2 is not None and len(read(10, path=lp)) == 2)
        got = read(10, path=lp)
        ok("newest first", got[0]["engine"] == "semic" and got[1]["engine"] == "chiron")
        # replay: what was recorded is exactly what is read back (the falsifier in HORIZON.md)
        ok("replay reproduces the record exactly",
           got[1]["verdict"] == "VERIFIED linear_recurrence" and got[1]["ok"] is True
           and got[1]["argv"] == ["collapse", "1 1 2 3 5 8"])
        # a torn line (crash mid-write) must not poison the ledger
        with open(lp, "a", encoding="utf-8") as f:
            f.write('{"t": 1, "engine": "torn')
        ok("torn line is skipped, not fatal", len(read(10, path=lp)) == 2)
        r3 = record("chiron", None, ok=False, verdict="exit 1", path=lp)
        ok("failures are first-class records", r3 is not None and read(1, path=lp)[0]["ok"] is False)
        # The default must be the safe one. A caller that forwards user text
        # and forgets the flag is the realistic failure, so redaction is what
        # happens when nobody chose.
        r5 = record("cli", ["never-copy-this-either"], ok=True, path=lp)
        ok("redaction is the DEFAULT, not an opt-in",
           "never-copy-this-either" not in json.dumps(r5, sort_keys=True))
        secret = "never-copy-this-user-text"
        r4 = record("cli", [secret], ok=True, path=lp, redact=True)
        rendered = json.dumps(r4, sort_keys=True)
        ok("redacted argv preserves a witness without storing user text",
           secret not in rendered and r4["argv"] == redact_argv([secret]))
        ok("recording never raises on a bad path", record("x", path=os.path.join(td, "no", "dir", "deep",
           "x" * 300, "l.jsonl")) is None or True)
        ok("read of a missing ledger is empty, not an error", read(5, path=os.path.join(td, "absent")) == [])

    passed = sum(1 for _, c in checks if c)
    print("run_ledger self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["selftest"]:
        return 0 if _selftest() else 1
    if argv[:1] == ["tail"]:
        n = int(argv[1]) if len(argv) > 1 else 20
        for r in read(n):
            mark = {True: "ok  ", False: "FAIL", None: "·   "}[r.get("ok")]
            print(f"{r.get('utc','')}  [{mark}] {r.get('incarnation','?'):5} "
                  f"{r.get('engine',''):20} {r.get('verdict','')[:60]}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
