# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""Engine tests — collapse/verify, subject organization, save/load round-trip.
Run: python Chiron/tests/test_chiron.py   (or: pytest Chiron/tests)"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chiron


def test_collapse_fibonacci_is_verified():
    assert chiron.collapse([1, 1, 2, 3, 5, 8, 13, 21]).verified


def test_collapse_geometric_is_verified():
    assert chiron.collapse([2, 4, 8, 16, 32, 64]).verified


def test_collapse_arithmetic_is_verified():
    assert chiron.collapse([3, 6, 9, 12, 15, 18]).verified


def test_assimilate_subject_and_integral():
    o = chiron.Chiron()
    r = o.assimilate("powers of two 2 4 8 16 32 64 128", source="test:1", domain_hint="mathematics")
    assert r["domain"] == "mathematics"
    assert r["classification"] == "integral"


def test_prose_is_general_not_a_false_law():
    o = chiron.Chiron()
    r = o.assimilate("Founded in 1804, the town grew through 1850 and 1900.", source="test:2",
                     domain_hint="history")
    assert r["classification"] == "general"


def test_save_load_roundtrip_preserves_growth():
    o = chiron.Chiron()
    o.assimilate("2 4 8 16 32", source="test:3", domain_hint="math")
    p = os.path.join(tempfile.gettempdir(), "chiron_test_rt.json")
    o.save_memory(p)
    o2 = chiron.Chiron.load_memory(p)
    assert o2.growth["integral"] == o.growth["integral"]
    os.remove(p)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print("ok -", fn.__name__)
    print("ALL PASSED (%d)" % len(fns))
