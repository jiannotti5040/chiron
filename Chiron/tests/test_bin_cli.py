#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Contract gates for the public ``bin/chiron`` front door.

Run: ``python3 Chiron/tests/test_bin_cli.py``
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLI = os.path.join(ROOT, "bin", "chiron")


def _certificate(stdout):
    """The transparent launcher line precedes JSON emitted by Primus."""
    return json.loads(stdout[stdout.index("{"):])


def _verify(*args, input=None):
    return subprocess.run(
        [sys.executable, CLI, "verify", *args],
        cwd=ROOT,
        input=input,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_verify_uses_the_exact_primus_certificate_gate():
    proc = _verify("2+2=5", "--json", "--gate")
    assert proc.returncode == 1, proc.stderr
    cert = _certificate(proc.stdout)
    assert cert["schema"] == "primus.certificate/2"
    assert cert["counts"]["refuted"] == 1


def test_verify_streams_only_the_selected_file():
    chosen = "The sum of 2 and 3 is 5."
    with tempfile.TemporaryDirectory() as td:
        target = os.path.join(td, "chosen.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(chosen)
        with open(os.path.join(td, "unrelated.txt"), "w", encoding="utf-8") as handle:
            handle.write("2+2=5")
        proc = _verify(target, "--json", "--gate")
    assert proc.returncode == 0, proc.stderr
    cert = _certificate(proc.stdout)
    assert cert["input"]["sha256"] == hashlib.sha256(chosen.encode("utf-8")).hexdigest()
    assert cert["counts"]["refuted"] == 0


def test_verify_reads_stdin_and_refuses_directory_scope():
    proc = _verify("-", "--json", input="3*3=9")
    assert proc.returncode == 0, proc.stderr
    assert _certificate(proc.stdout)["counts"]["verified"] == 1
    with tempfile.TemporaryDirectory() as td:
        proc = _verify(td)
    assert proc.returncode == 2
    assert "not a directory" in proc.stdout


if __name__ == "__main__":
    fns = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for fn in fns:
        fn()
        print("ok -", fn.__name__)
    print("ALL PASSED (%d)" % len(fns))
