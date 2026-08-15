# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Print the uma.bsd validation battery and controls as JSON."""
import json

from . import bsd_certificate
from .battery import CONTROLS, run_battery

if __name__ == "__main__":
    ok, results = run_battery()
    controls = {name: fn() for name, fn in CONTROLS.items()}
    print(json.dumps({
        "schema": "uma.bsd.battery/1",
        "battery_passed": ok,
        "controls_passed": all(controls.values()),
        "controls": controls,
        "curves": results,
    }, indent=2, default=str))
    raise SystemExit(0 if (ok and all(controls.values())) else 1)
