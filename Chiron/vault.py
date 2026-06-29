#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
vault.py — one command to run the whole thing.

The portfolio grew several optional local services (the engine console, a function launcher, a
chat assistant, grow control, LLM-assisted growth). Starting them by hand means juggling terminals
and ports. This starts them all, prints ONE url to open, and stops them all on Ctrl-C. You never
need to remember the ports.

    python3 vault.py                 # start everything, open http://127.0.0.1:8765
    python3 vault.py --core          # just the engine + console (no LLM / aux services)
    python3 vault.py selftest

Open http://127.0.0.1:8765 and use the tabs. That single console reaches the rest:
  Analyze / Run / Chat / Feed (grow) / Growth / What it knows.
The LLM features (Chat, President grow) need a free key: export GROW_LLM_API_KEY=...
"""
import os
import sys
import time
import signal
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))

# name, script, port, required-core?
SERVICES = [
    ("engine + console",        "chiron.py",          8765, True,  ["serve"]),
    ("launcher  (Run tab)",     "console_server.py",  8768, False, ["serve"]),
    ("assistant (Chat tab)",    "assistant_server.py", 8769, False, ["serve"]),
    ("grow control (Feed tab)", "grow_control.py",    8767, False, ["serve"]),
    ("LLM grow (President tab)", "president_grow.py",  8766, False, ["serve"]),
]
MAIN_URL = "http://127.0.0.1:8765"


def _cmd(script, args):
    return [sys.executable, os.path.join(_HERE, script), *args]


def up(core_only=False, spawn=subprocess.Popen):
    procs = []
    print("starting the vault…\n")
    for name, script, port, required, args in SERVICES:
        if core_only and not required:
            continue
        path = os.path.join(_HERE, script)
        if not os.path.isfile(path):
            print(f"  SKIP {name:26} (missing {script})")
            continue
        try:
            p = spawn(_cmd(script, args), cwd=_HERE, start_new_session=True)
            procs.append((name, port, p))
            print(f"  up   {name:26} :{port}")
        except Exception as e:
            print(f"  SKIP {name:26} ({e})")
    print(f"\n  ► OPEN  {MAIN_URL}   — the console; its tabs reach everything else.")
    print("  ► LLM features (Chat, President) need:  export GROW_LLM_API_KEY=…")
    print("  ► Ctrl-C to stop everything.\n")
    return procs


def down(procs):
    pids = [getattr(p, "pid", None) for _, _, p in procs]
    for pid in pids:
        if not pid:
            continue
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
    for _ in range(20):
        if not any(pid and _pid_alive(pid) for pid in pids):
            break
        time.sleep(0.1)
    for pid in pids:
        if pid and _pid_alive(pid):
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
    print("\nstopped all services.")


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    ports = [s[2] for s in SERVICES]
    ok("ports are all distinct", len(set(ports)) == len(ports))
    ok("exactly one core (required) service", sum(1 for s in SERVICES if s[3]) == 1)
    ok("the core service is the engine console", next(s for s in SERVICES if s[3])[1] == "chiron.py")
    ok("every service script exists", all(os.path.isfile(os.path.join(_HERE, s[1])) for s in SERVICES))

    # start/stop lifecycle with a dummy spawner (no real servers, no network)
    started = []

    class _Dummy:
        def __init__(self, cmd, **kw):
            self.proc = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(20)"],
                                         start_new_session=True)
            self.pid = self.proc.pid
            started.append(self.pid)
    procs = up(spawn=_Dummy)
    ok("starts all five services (dummy)", len(procs) == 5)
    ok("dummy services are running", all(p.proc.poll() is None for _, _, p in procs))
    down(procs)
    ended = 0
    for _, _, p in procs:
        try:
            p.proc.wait(timeout=2)
            ended += 1
        except Exception:
            pass
    ok("Ctrl-C path stops them all", ended == len(procs))

    passed = sum(1 for _, c in checks if c)
    print("\nvault self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    # clean any stragglers
    for pid in started:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    return passed == len(checks)


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the whole vault with one command.")
    ap.add_argument("cmd", nargs="?", default=None)
    ap.add_argument("--core", action="store_true", help="engine + console only")
    args = ap.parse_args(argv)
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    procs = up(core_only=args.core)
    if not procs:
        return 1
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        down(procs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
