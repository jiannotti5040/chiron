#!/usr/bin/env python3
"""
Optional native hot-path loader, with an exact pure-Python fallback.

    python3 fastops.py        # self-test; prints which backend is active

If the Rust crate in ./chiron_fastops has been built (`cargo build --release`), this
loads the compiled shared library via ctypes and uses it. If not, it uses exact
pure-Python implementations, so the engine ALWAYS runs — native is an accelerator,
never a dependency. This mirrors the optional-C kernel already embedded in chiron.py.

Exposed:
  poly_degree(seq)          finite-difference degree of an integer sequence (-1 if not poly)
  hexameter_feet_ok(q)      does a quantity string ('L'/'S' or '1'/'0') form 6 hexameter feet?
  backend()                 'native (...)' or 'pure-python fallback'
"""
import os
import ctypes

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = None


def _load():
    global _LIB
    if _LIB is not None:
        return _LIB
    candidates = [
        "libchiron_fastops.dylib", "libchiron_fastops.so", "chiron_fastops.dll",
        os.path.join("chiron_fastops", "target", "release", "libchiron_fastops.dylib"),
        os.path.join("chiron_fastops", "target", "release", "libchiron_fastops.so"),
        os.path.join("chiron_fastops", "target", "release", "chiron_fastops.dll"),
    ]
    for name in candidates:
        p = os.path.join(_HERE, name)
        if os.path.exists(p):
            try:
                lib = ctypes.CDLL(p)
                lib.chiron_poly_degree.restype = ctypes.c_longlong
                lib.chiron_poly_degree.argtypes = [ctypes.POINTER(ctypes.c_longlong), ctypes.c_int]
                lib.chiron_hexameter_feet_ok.restype = ctypes.c_int
                lib.chiron_hexameter_feet_ok.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
                _LIB = lib
                return lib
            except Exception:
                pass
    _LIB = False
    return False


# ---- pure-Python fallbacks (exact; always available) ----------------------
def _py_poly_degree(seq):
    a = [int(x) for x in seq]
    n = len(a)
    for L in range(n):
        m = n - L
        if all(a[i] == a[0] for i in range(1, m)):
            return L
        a = [a[i + 1] - a[i] for i in range(m - 1)]
    return -1


def _quants(q):
    return [1 if c in "1Ll" else 0 for c in q]


def _py_hexameter_feet_ok(q):
    v = _quants(q)
    n = len(v)
    import sys
    sys.setrecursionlimit(10000)

    def rec(pos, foot):
        if foot == 6:
            return pos == n
        if foot <= 4 and pos + 3 <= n and v[pos] == 1 and v[pos + 1] == 0 and v[pos + 2] == 0 and rec(pos + 3, foot + 1):
            return True
        if pos + 2 <= n and v[pos] == 1 and v[pos + 1] == 1 and rec(pos + 2, foot + 1):
            return True
        if foot == 5 and pos + 2 <= n and v[pos] == 1 and v[pos + 1] == 0 and rec(pos + 2, foot + 1):
            return True
        return False

    return rec(0, 0)


# ---- public API (native when available, else pure-Python) -----------------
def poly_degree(seq):
    lib = _load()
    if lib and all(float(x).is_integer() for x in seq):
        n = len(seq)
        arr = (ctypes.c_longlong * n)(*[int(x) for x in seq])
        return int(lib.chiron_poly_degree(arr, n))
    return _py_poly_degree(seq)


def hexameter_feet_ok(q):
    lib = _load()
    if lib:
        b = bytes(_quants(q))
        arr = (ctypes.c_ubyte * len(b))(*b)
        return bool(lib.chiron_hexameter_feet_ok(arr, len(b)))
    return _py_hexameter_feet_ok(q)


def backend():
    return "native (compiled chiron_fastops)" if _load() else "pure-python fallback"


def _selftest():
    ok = True
    # poly_degree is the finite-difference (interpolation) degree: a true low-degree
    # polynomial reduces early; non-polynomial data of length n interpolates at n-1.
    cases = {(0, 1, 4, 9, 16, 25): 2, (0, 1, 8, 27, 64): 3, (2, 5, 8, 11): 1,
             (7, 7, 7, 7): 0, (2, 3, 5, 7, 11): 4}
    for seq, deg in cases.items():
        got = poly_degree(list(seq))
        ok &= (got == deg)
        print("  poly_degree%-22s -> %s  (want %s)  %s" % (str(seq), got, deg, "OK" if got == deg else "FAIL"))
    feet = {"LSSLSSLSSLSSLSSLL": True, "LLLLLLLLLLLL": True, "LSSLSS": False, "LSLSLSLSLSLS": False}
    for q, want in feet.items():
        got = hexameter_feet_ok(q)
        ok &= (got == want)
        print("  hexameter_feet_ok(%-18s) -> %-5s (want %s)  %s" % (q, got, want, "OK" if got == want else "FAIL"))
    print("backend:", backend())
    print("VERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
