# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
import glob, os, sys, zipfile

candidates = glob.glob("dist/*.whl") or glob.glob("**/*.whl", recursive=True)
if not candidates:
    sys.exit("FAIL: no .whl found under the workspace")

whl = max(candidates, key=os.path.getmtime)

with zipfile.ZipFile(whl) as z:
    names = z.namelist()

lic = [n for n in names if "LICENSE" in os.path.basename(n).upper()]
if not lic:
    sys.exit(f"FAIL: {os.path.basename(whl)} carries no LICENSE\n" + "\n".join(names))

print(f"OK: {os.path.basename(whl)} carries: {lic}")
