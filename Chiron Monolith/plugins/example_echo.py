#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
example_echo — the minimal plugin: proves the monolith runs external files
and that they can import the embedded spine. Nothing here stamps anything.

    python3 chiron_monolith.py example_echo hello world
    python3 chiron_monolith.py example_echo selftest
"""
import sys


def main(argv):
    if argv and argv[0] == "selftest":
        # gate 1: we are running as a plugin (an external file), not embedded
        ok_external = "plugins" in __file__.replace("\\", "/")
        # gate 2: the embedded spine is importable from a plugin
        try:
            import chiron_events                      # light-touch embedded import
            bus = chiron_events.Bus()
            bus.subscribe("t", lambda p: p)
            ok_spine = bus.publish("t", "x") == ["x"]
        except Exception:
            ok_spine = False
        print("  [%s] runs as an external plugin file" % ("PASS" if ok_external else "FAIL"))
        print("  [%s] can import the embedded spine" % ("PASS" if ok_spine else "FAIL"))
        print("example_echo selftest: %d/2 gates green" % sum([ok_external, ok_spine]))
        return 0 if (ok_external and ok_spine) else 1
    print(" ".join(argv) if argv else "(echo: nothing to say)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
