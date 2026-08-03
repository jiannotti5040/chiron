#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
primus.conjecture — guess-and-prove: a stochastic proposer behind the exact gate.

The engine (`primus.engine.collapse`) searches an explicit, finite hypothesis
class and refuses everything outside it. This module widens what can be
ATTEMPTED without widening what can be STAMPED: a genetic-programming
symbolic regressor (gplearn) proposes closed-form candidates, and every
candidate must then survive the same discipline the engine lives by —

  * float constants are snapped to exact integers/rationals (Fractions);
  * the snapped expression is evaluated in EXACT rational arithmetic;
  * it must reproduce EVERY supplied term exactly, including a suffix of
    terms withheld from the search entirely (the proof-by-prediction);
  * candidates with more snapped constants than held-out terms are REFUSED
    (the h >= p evidence rule, applied to closed forms);
  * anything else — no surviving candidate, non-integer values, division
    by zero, growth past the exact-arithmetic bounds — is REFUSED.

The stochastic search NEVER touches the stamping path. gplearn proposes;
only the exact verifier stamps. If gplearn is not installed, the proposer
degrades to an honest REFUSED — never an error, never a guess.

WHAT A VERIFIED CONJECTURE MEANS (and does not): the expression reproduces
all N supplied terms exactly, including the H final terms the search never
saw. That certifies fit to the given data. It does NOT certify the
sequence's true generator — no finite prefix can. The certificate says so.

Usage:
    from primus.conjecture import conjecture, verify_closed_form
    cert = conjecture([0, 2, 130, 2190, 16388, ...])     # engine-refused input
    cert["status"], cert.get("expression")

    $ primus conjecture "1 2 4 8 16 32 64 128"
    $ python3 -m primus.conjecture selftest
"""
from __future__ import annotations

import json
import re
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA = "primus.conjecture/1"

# Exact-arithmetic work bounds. These mirror primus.certify's adversarial
# bounds (documented in SCHEMA.md); they are duplicated here by value so the
# exact core stays import-cycle-free (certify lazily imports THIS module for
# the closed_form claim kind).
MAX_SEQ_TERMS = 256          # longer inputs are REFUSED, not searched
MAX_INT_DIGITS = 4_096       # any intermediate beyond this is discarded
MAX_POW_EXP = 64             # ^ exponent bound (parser); GP never emits ^
MAX_EXPR_CHARS = 512         # parser input cap
MAX_EXPR_DEPTH = 32          # parser + evaluator recursion cap
MAX_PROGRAM_NODES = 64       # GP candidates longer than this are skipped
MAX_SNAP_CONSTANTS = 4       # candidates with more float leaves are skipped
MAX_POPULATION = 4_096       # GP work bounds (deterministic caps)
MAX_GENERATIONS = 64
MAX_RESTARTS = 8
MIN_HOLDOUT = 3

_CAVEAT = ("the expression reproduces all supplied terms exactly, including "
           "the final holdout terms withheld from the search; this certifies "
           "fit to the given data, not the sequence's true generator")


class ClosedFormError(ValueError):
    """Raised when an expression cannot be parsed/checked within bounds."""


class _Undefined(ArithmeticError):
    """Internal: expression undefined at some index (division by zero)."""


class _Overflow(ArithmeticError):
    """Internal: intermediate value exceeded exact-arithmetic bounds."""


# ===========================================================================
# 1. THE EXACT CORE — no gplearn, no floats, no randomness.
#    Expression trees over {n, rational constants, + - * / ^int}.
#    This is the only part of the module that can say "exactly matches".
# ===========================================================================
# Tree shape: ("n",) | ("c", Fraction) | (op, left, right) with op in
# {"add","sub","mul","div"} | ("pow", base, int_exponent >= 0).

def _digits_ok(f: Fraction) -> bool:
    return (len(str(abs(f.numerator))) <= MAX_INT_DIGITS
            and len(str(f.denominator)) <= MAX_INT_DIGITS)


def eval_tree(tree: Tuple, n: Fraction, _depth: int = 0) -> Fraction:
    """Exact rational evaluation. Raises _Undefined on a pole, _Overflow
    past the digit bound, ClosedFormError past the depth bound."""
    if _depth > MAX_EXPR_DEPTH:
        raise ClosedFormError("expression exceeds depth bound")
    op = tree[0]
    if op == "n":
        return n
    if op == "c":
        return tree[1]
    if op == "pow":
        base = eval_tree(tree[1], n, _depth + 1)
        exp = tree[2]
        if exp < 0 or exp > MAX_POW_EXP:
            raise ClosedFormError("exponent outside bounds")
        # bound the result BEFORE computing: digits(base^exp) ~ exp*digits(base)
        if exp * max(len(str(abs(base.numerator))), len(str(base.denominator))) > MAX_INT_DIGITS:
            raise _Overflow("power exceeds exact-arithmetic bounds")
        return base ** exp
    a = eval_tree(tree[1], n, _depth + 1)
    b = eval_tree(tree[2], n, _depth + 1)
    if op == "add":
        r = a + b
    elif op == "sub":
        r = a - b
    elif op == "mul":
        r = a * b
    elif op == "div":
        if b == 0:
            raise _Undefined("division by zero")
        r = a / b
    else:
        raise ClosedFormError(f"unknown operator {op!r}")
    if not _digits_ok(r):
        raise _Overflow("intermediate exceeds exact-arithmetic bounds")
    return r


def fold_constants(tree: Tuple) -> Tuple:
    """Exactly fold every n-free subtree. Deterministic; raises the same
    bounded errors as eval_tree (a folding failure discards the candidate)."""
    op = tree[0]
    if op in ("n", "c"):
        return tree
    if op == "pow":
        base = fold_constants(tree[1])
        if base[0] == "c":
            return ("c", eval_tree(("pow", base, tree[2]), Fraction(0)))
        return ("pow", base, tree[2])
    a, b = fold_constants(tree[1]), fold_constants(tree[2])
    if a[0] == "c" and b[0] == "c":
        return ("c", eval_tree((op, a, b), Fraction(0)))
    return (op, a, b)


def simplify(tree: Tuple, passes: int = 3) -> Tuple:
    """Bounded local rewrites for readability: fold constants, drop +0 / *1 /
    *0 / -self identities. Soundness note: a rewrite may WIDEN the domain
    (e.g. (n-n) hides no pole but 0*(1/(n-3)) -> 0 removes one), which is
    safe here ONLY because every candidate is exact-verified AFTER
    simplification — the tree that is checked is the tree that is printed."""
    def one(t: Tuple) -> Tuple:
        if t[0] in ("n", "c"):
            return t
        if t[0] == "pow":
            base = one(t[1])
            if t[2] == 1:
                return base
            if t[2] == 0:
                return ("c", Fraction(1))
            return ("pow", base, t[2])
        op, a, b = t[0], one(t[1]), one(t[2])
        za = a == ("c", Fraction(0))
        zb = b == ("c", Fraction(0))
        ia = a == ("c", Fraction(1))
        ib = b == ("c", Fraction(1))
        if op == "add":
            if za:
                return b
            if zb:
                return a
        elif op == "sub":
            if zb:
                return a
            if a == b:
                return ("c", Fraction(0))
        elif op == "mul":
            if za or zb:
                return ("c", Fraction(0))
            if ia:
                return b
            if ib:
                return a
        elif op == "div":
            if za and not zb:
                return ("c", Fraction(0))
            if ib:
                return a
            if a == b and not zb:
                return ("c", Fraction(1))
        return (op, a, b)

    for _ in range(passes):
        new = one(fold_constants(tree))
        if new == tree:
            break
        tree = new
    return tree


def _frac_str(f: Fraction) -> str:
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def render_tree(tree: Tuple) -> str:
    """Canonical, unambiguous infix rendering (fully parenthesized binaries)."""
    op = tree[0]
    if op == "n":
        return "n"
    if op == "c":
        f = tree[1]
        return _frac_str(f) if f >= 0 else f"({_frac_str(f)})"
    if op == "pow":
        return f"{render_tree(tree[1])}^{tree[2]}"
    sym = {"add": " + ", "sub": " - ", "mul": "*", "div": "/"}[op]
    return f"({render_tree(tree[1])}{sym}{render_tree(tree[2])})"


def count_constants(tree: Tuple) -> int:
    if tree[0] == "c":
        return 1
    if tree[0] in ("n",):
        return 0
    if tree[0] == "pow":
        return count_constants(tree[1])
    return count_constants(tree[1]) + count_constants(tree[2])


# ------------------------------------------------------------------ parser
# Grammar (for human-written claims and round-tripping our own output):
#   expr   := term (('+'|'-') term)*
#   term   := factor (('*'|'/') factor)*
#   factor := '-' factor | atom ('^' INT)?
#   atom   := INT | 'n' | '(' expr ')'
_TOKEN = re.compile(r"\s*(\d+|[n()+\-*/^])")


def parse_expression(text: str) -> Tuple:
    """Parse a closed-form expression into an exact tree. Bounded: input
    length, token count, nesting depth, exponent size. Raises
    ClosedFormError on anything outside the grammar or the bounds."""
    if not isinstance(text, str):
        raise ClosedFormError("expression must be a string")
    if len(text) > MAX_EXPR_CHARS:
        raise ClosedFormError("expression exceeds length bound")
    tokens: List[str] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ClosedFormError(f"unexpected character {text[pos]!r}")
        tokens.append(m.group(1))
        pos = m.end()
    if not tokens:
        raise ClosedFormError("empty expression")
    if any(t.isdigit() and len(t) > MAX_INT_DIGITS for t in tokens):
        raise ClosedFormError("integer literal exceeds exact-arithmetic bounds")
    idx = 0

    def peek() -> Optional[str]:
        return tokens[idx] if idx < len(tokens) else None

    def take() -> str:
        nonlocal idx
        idx += 1
        return tokens[idx - 1]

    def expr(depth: int) -> Tuple:
        if depth > MAX_EXPR_DEPTH:
            raise ClosedFormError("expression exceeds depth bound")
        node = term(depth + 1)
        while peek() in ("+", "-"):
            op = "add" if take() == "+" else "sub"
            node = (op, node, term(depth + 1))
        return node

    def term(depth: int) -> Tuple:
        if depth > MAX_EXPR_DEPTH:
            raise ClosedFormError("expression exceeds depth bound")
        node = factor(depth + 1)
        while peek() in ("*", "/"):
            op = "mul" if take() == "*" else "div"
            node = (op, node, factor(depth + 1))
        return node

    def factor(depth: int) -> Tuple:
        if depth > MAX_EXPR_DEPTH:
            raise ClosedFormError("expression exceeds depth bound")
        if peek() == "-":
            take()
            return ("sub", ("c", Fraction(0)), factor(depth + 1))
        node = atom(depth + 1)
        if peek() == "^":
            take()
            neg = False
            if peek() == "-":
                take()
                neg = True
            t = peek()
            if t is None or not t.isdigit():
                raise ClosedFormError("exponent must be an integer literal")
            take()
            if neg:
                raise ClosedFormError("negative exponents are not judged")
            exp = int(t)
            if exp > MAX_POW_EXP:
                raise ClosedFormError("exponent outside bounds")
            node = ("pow", node, exp)
        return node

    def atom(depth: int) -> Tuple:
        if depth > MAX_EXPR_DEPTH:
            raise ClosedFormError("expression exceeds depth bound")
        t = peek()
        if t is None:
            raise ClosedFormError("unexpected end of expression")
        if t == "(":
            take()
            node = expr(depth + 1)
            if peek() != ")":
                raise ClosedFormError("unbalanced parentheses")
            take()
            return node
        if t == "n":
            take()
            return ("n",)
        if t.isdigit():
            take()
            return ("c", Fraction(int(t)))
        raise ClosedFormError(f"unexpected token {t!r}")

    tree = expr(0)
    if idx != len(tokens):
        raise ClosedFormError(f"trailing tokens near {tokens[idx]!r}")
    return tree


def verify_closed_form(expression: str, terms: Sequence[int],
                       offset: int = 0) -> Dict[str, Any]:
    """Exactly check `a(n) = expression` against terms at n = offset, offset+1, ...

    Returns {"status": VERIFIED|REFUTED|REFUSED, ...detail}. VERIFIED means
    every term matched exactly in rational arithmetic. REFUTED means some
    term did not (including: the expression is undefined at a required n, or
    takes a non-integer value where an integer term stands). REFUSED means
    the check could not be performed within bounds (parse error, work caps).
    No probabilistic outcome exists.
    """
    if len(terms) > MAX_SEQ_TERMS:
        return {"status": "REFUSED",
                "reason": f"run exceeds the {MAX_SEQ_TERMS}-term bound"}
    if len(terms) < 1:
        return {"status": "REFUSED", "reason": "no terms to check"}
    if not all(isinstance(t, int) and not isinstance(t, bool) for t in terms):
        return {"status": "REFUSED", "reason": "terms must be integers"}
    if any(len(str(abs(t))) > MAX_INT_DIGITS for t in terms):
        return {"status": "REFUSED", "reason": "term exceeds exact-arithmetic bounds"}
    try:
        tree = parse_expression(expression)
        tree = fold_constants(tree)
    except ClosedFormError as exc:
        return {"status": "REFUSED", "reason": f"unparseable expression: {exc}"}
    except (_Undefined, _Overflow) as exc:
        return {"status": "REFUSED", "reason": f"constant fold failed: {exc}"}
    for i, t in enumerate(terms):
        nval = Fraction(offset + i)
        try:
            v = eval_tree(tree, nval)
        except _Undefined:
            return {"status": "REFUTED", "n": offset + i, "expected": t,
                    "reason": f"expression undefined at n={offset + i}"}
        except _Overflow:
            return {"status": "REFUSED",
                    "reason": "intermediate exceeds exact-arithmetic bounds"}
        except ClosedFormError as exc:
            return {"status": "REFUSED", "reason": str(exc)}
        if v != t:
            got = _frac_str(v)
            return {"status": "REFUTED", "n": offset + i, "expected": t,
                    "got": got}
    return {"status": "VERIFIED", "checked_terms": len(terms), "offset": offset,
            "expression": f"a(n) = {render_tree(tree)}"}


# ===========================================================================
# 2. THE PROPOSER — gplearn genetic programming (OPTIONAL, never stamping).
# ===========================================================================
def _gplearn_available() -> bool:
    try:
        import gplearn  # noqa: F401
        return True
    except ImportError:
        return False


def _sklearn_compat() -> None:
    """gplearn <= 0.4.2 calls BaseEstimator._validate_data, removed in
    scikit-learn 1.6; restore it as a thin wrapper (same shim as
    bench_symreg_external.py). Harmless no-op on newer gplearn."""
    from sklearn.base import BaseEstimator
    if hasattr(BaseEstimator, "_validate_data"):
        return
    from sklearn.utils.validation import validate_data as _vd

    def _validate_data(self, X="no_validation", y="no_validation", **kw):
        return _vd(self, X=X, y=y, **kw)

    BaseEstimator._validate_data = _validate_data


def _tree_from_program(program) -> Optional[Tuple]:
    """Convert a gplearn prefix program into a raw tree whose float
    constants are kept as ("float", value) placeholders. Returns None for
    programs outside our exact language or size bounds."""
    from gplearn.functions import _Function
    flat = program.program
    if len(flat) > MAX_PROGRAM_NODES:
        return None
    it = iter(flat)

    def build(depth: int):
        if depth > MAX_EXPR_DEPTH:
            raise ClosedFormError("program exceeds depth bound")
        node = next(it)
        if isinstance(node, _Function):
            if node.name not in ("add", "sub", "mul", "div") or node.arity != 2:
                raise ClosedFormError(f"operator {node.name!r} outside the exact language")
            left = build(depth + 1)
            right = build(depth + 1)
            return (node.name, left, right)
        if isinstance(node, float):
            return ("float", float(node))
        # feature index; we train on the single feature X0 = n
        return ("n",)

    try:
        tree = build(0)
    except (ClosedFormError, StopIteration):
        return None
    try:
        next(it)
        return None            # trailing nodes: malformed program
    except StopIteration:
        return tree


def _float_leaves(tree: Tuple) -> int:
    if tree[0] == "float":
        return 1
    if tree[0] in ("n", "c"):
        return 0
    return _float_leaves(tree[1]) + _float_leaves(tree[2])


def _snap_variants(tree: Tuple) -> List[Tuple]:
    """All exact trees obtainable by snapping each float constant to (a) the
    nearest integer and (b) the nearest small rational. Deterministic order;
    bounded by MAX_SNAP_CONSTANTS floats -> at most 2^MAX_SNAP_CONSTANTS."""
    if tree[0] == "float":
        c = tree[1]
        opts = []
        for f in (Fraction(round(c)), Fraction(c).limit_denominator(64)):
            if f not in [o[1] for o in opts]:
                opts.append(("c", f))
        return opts
    if tree[0] in ("n", "c"):
        return [tree]
    lefts = _snap_variants(tree[1])
    rights = _snap_variants(tree[2])
    return [(tree[0], a, b) for a in lefts for b in rights]


def _exact_match_all(tree: Tuple, terms: Sequence[int]) -> bool:
    """True iff the tree reproduces EVERY term exactly (n indexed from 0)."""
    for i, t in enumerate(terms):
        try:
            if eval_tree(tree, Fraction(i)) != t:
                return False
        except (ArithmeticError, ClosedFormError):
            return False
    return True


def _propose(train: Sequence[int], population: int, generations: int,
             seed: int, const_range: Optional[Tuple[float, float]]) -> List[Tuple]:
    """One GP run; returns deduplicated candidate trees (floats unsnapped).
    The pool mixes best-by-fitness and shortest-by-length finalists — exact
    structure often hides among the short programs, not the best fits.
    Everything here is heuristic; nothing here stamps."""
    import warnings
    import numpy as np
    _sklearn_compat()
    from gplearn.genetic import SymbolicRegressor

    X = np.arange(len(train), dtype=float).reshape(-1, 1)
    y = np.array([float(t) for t in train])
    est = SymbolicRegressor(
        population_size=population, generations=generations,
        function_set=("add", "sub", "mul", "div"),
        parsimony_coefficient=0.001, const_range=const_range,
        random_state=seed, verbose=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        np_err = np.seterr(all="ignore")
        try:
            est.fit(X, y)
        finally:
            np.seterr(**np_err)

    def _fit_of(p):
        f = getattr(p, "raw_fitness_", None)
        f = float(f) if f is not None else float("inf")
        return float("inf") if f != f else f     # NaN -> inf (stable order)

    final_gen = [p for p in (est._programs[-1]
                             if getattr(est, "_programs", None) else [])
                 if p is not None]
    pool = [est._program]
    pool += sorted(final_gen, key=lambda p: (_fit_of(p), p.length_, str(p)))[:24]
    pool += sorted(final_gen, key=lambda p: (p.length_, _fit_of(p), str(p)))[:24]
    seen, out = set(), []
    for prog in pool:
        key = str(prog)
        if key in seen:
            continue
        seen.add(key)
        tree = _tree_from_program(prog)
        if tree is not None and _float_leaves(tree) <= MAX_SNAP_CONSTANTS:
            out.append(tree)
    return out


# ===========================================================================
# 3. THE PIPELINE — engine first, then guess-and-prove, then refuse.
# ===========================================================================
def conjecture(terms: Sequence[int], *, seed: int = 0, population: int = 1500,
               generations: int = 20, holdout: int = 4, restarts: int = 2,
               engine_first: bool = True,
               _force_no_gp: bool = False) -> Dict[str, Any]:
    """Guess-and-prove closed-form recovery with exact verification.

    Stage 0: `primus.engine.collapse` on the full input — if the engine
    already stamps, its (stronger, MDL-disciplined) result is returned and
    the stochastic proposer is never consulted.

    Stage 1: gplearn proposes candidates from `terms[:-holdout]` only.

    Stage 2: every candidate is constant-snapped and must reproduce ALL
    terms exactly — including the `holdout` suffix the search never saw —
    in exact rational arithmetic, under the h >= p evidence rule
    (holdout >= snapped constants + 1). First survivor is returned
    VERIFIED; no survivor is an honest REFUSED.

    `engine_first=False` disables only the stage-0 early return (the engine
    is still run and recorded in the certificate for attribution). The
    stamping bar is identical either way; the flag exists so the GP path
    can be exercised on inputs an engine with richer families would
    otherwise answer first.
    """
    from primus.engine import collapse

    base: Dict[str, Any] = {
        "schema": SCHEMA,
        "params": {"seed": seed, "population": population,
                   "generations": generations, "holdout": holdout,
                   "restarts": restarts},
    }

    # ---- input validation (exactness contract) ---------------------------
    terms = list(terms)
    if len(terms) > MAX_SEQ_TERMS:
        return {**base, "status": "REFUSED",
                "reason": f"input exceeds the {MAX_SEQ_TERMS}-term bound"}
    if not all(isinstance(t, int) and not isinstance(t, bool) for t in terms):
        return {**base, "status": "REFUSED",
                "reason": "terms must be integers — the exact contract does "
                          "not judge approximate data"}
    if any(len(str(abs(t))) > MAX_INT_DIGITS for t in terms):
        return {**base, "status": "REFUSED",
                "reason": "term exceeds exact-arithmetic bounds"}
    holdout = max(MIN_HOLDOUT, int(holdout))
    if len(terms) < holdout + 5:
        return {**base, "status": "REFUSED",
                "reason": f"need at least {holdout + 5} terms "
                          f"({holdout} holdout + 5 train)"}
    population = min(max(2, int(population)), MAX_POPULATION)
    generations = min(max(1, int(generations)), MAX_GENERATIONS)
    restarts = min(max(1, int(restarts)), MAX_RESTARTS)

    # ---- stage 0: the engine goes first ----------------------------------
    engine_summary: Dict[str, Any] = {}
    try:
        inv = collapse(terms)
        engine_summary = {"model_class": inv.model_class,
                          "verified": bool(inv.verified)}
        if inv.verified and engine_first:
            return {**base, "status": "VERIFIED", "source": "engine",
                    "engine": engine_summary,
                    "note": "the engine's finite-class search already stamps "
                            "this input; the stochastic proposer was not "
                            "consulted"}
    except Exception as exc:
        engine_summary = {"declined": type(exc).__name__, "verified": False}
    base["engine"] = engine_summary

    # ---- stage 1+2: guess, then prove or refuse ---------------------------
    if _force_no_gp or not _gplearn_available():
        return {**base, "status": "REFUSED",
                "reason": "engine abstains and the conjecture stage is "
                          "unavailable (gplearn not installed); refusing "
                          "rather than guessing"}

    train = terms[:-holdout]
    tried = 0
    # Per attempt, two proposal phases: constant-free first (the cleaner
    # exact language — powers and integer polynomials need no constants),
    # then the default constant range. A survivor short-circuits everything.
    for attempt in range(restarts):
        for const_range in (None, (-1.0, 1.0)):
            candidates = _propose(train, population, generations,
                                  seed + attempt, const_range)
            for raw in candidates:
                n_const = _float_leaves(raw)
                if holdout < n_const + 1:
                    continue    # h >= p: not enough held-out evidence
                for variant in _snap_variants(raw):
                    tried += 1
                    try:
                        folded = simplify(fold_constants(variant))
                    except (ArithmeticError, ClosedFormError):
                        continue
                    if not _exact_match_all(folded, terms):
                        continue
                    expression = render_tree(folded)
                    # independent re-check through the public text path —
                    # the stamp must survive its own round trip
                    recheck = verify_closed_form(expression, terms)
                    if recheck["status"] != "VERIFIED":
                        continue
                    return {**base, "status": "VERIFIED",
                            "source": "gp+exact-holdout",
                            "expression": f"a(n) = {expression}",
                            "n_constants": count_constants(folded),
                            "holdout_terms": holdout,
                            "terms_checked": len(terms),
                            "seed_used": seed + attempt,
                            "phase": ("const-free" if const_range is None
                                      else "with-constants"),
                            "candidates_checked": tried,
                            "caveat": _CAVEAT,
                            "claim_text": f"a(n) = {expression} matches "
                                          + ", ".join(str(t) for t in terms)}
        # restart with the next seed
    return {**base, "status": "REFUSED",
            "reason": f"no proposed closed form survived exact verification "
                      f"({tried} snapped candidates checked against all "
                      f"{len(terms)} terms, {holdout} of them search-holdout); "
                      f"refusing rather than returning the best wrong guess"}


def render(cert: Dict[str, Any]) -> str:
    lines = ["PRIMUS CONJECTURE  (guess-and-prove: stochastic proposer, exact stamp)"]
    if cert["status"] == "VERIFIED" and cert.get("source") == "engine":
        lines.append("  [VERIFIED — by the engine, not the proposer] "
                     + cert["engine"]["model_class"])
        lines.append("  " + cert.get("note", ""))
    elif cert["status"] == "VERIFIED":
        lines.append(f"  [VERIFIED] {cert['expression']}")
        lines.append(f"  proof: exact reproduction of all {cert['terms_checked']} "
                     f"terms, including {cert['holdout_terms']} never shown to "
                     f"the search (seed {cert['seed_used']}, "
                     f"{cert['candidates_checked']} candidates checked)")
        lines.append("  caveat: " + cert["caveat"])
    else:
        lines.append("  [REFUSED] " + cert.get("reason", ""))
    return "\n".join(lines)


# ===========================================================================
# 4. GATES
# ===========================================================================
# The GP-path gates run with the stage-0 early return ENABLED in the seed
# copy (whose polynomial family caps at degree 6, so a degree-7 target
# proves genuinely added capability) and DISABLED in the Chiron twin (whose
# polynomial family is uncapped and therefore subsumes GP's rational-
# function language — there the gates prove pipeline integrity, and the
# certificate discloses the engine's own verdict alongside the GP stamp).
_GATE_ENGINE_FIRST = True


def _selftest() -> int:
    """Offline gates for the conjecture layer. Returns count of failures.
    The exact-core gates always run; the GP-path gates run when gplearn is
    importable and assert the degraded path when it is not."""
    fails = 0

    def gate(name: str, cond: bool) -> None:
        nonlocal fails
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        fails += 0 if cond else 1

    # ---- exact core (deterministic, dependency-free) ----------------------
    v = verify_closed_form("n*(n+1)/2", [0, 1, 3, 6, 10, 15, 21])
    gate("closed form verified (triangulars)", v["status"] == "VERIFIED")
    v = verify_closed_form("n*(n+1)/2", [0, 1, 3, 6, 10, 15, 22])
    gate("wrong closed form refuted with counterexample",
         v["status"] == "REFUTED" and v["n"] == 6 and v["expected"] == 22)
    v = verify_closed_form("n*n + 1", [1, 2, 5, 10, 17], offset=0)
    gate("offset-0 quadratic verified", v["status"] == "VERIFIED")
    v = verify_closed_form("6/(3 - n)", [2, 3, 6, 99])
    gate("pole refuted, not crashed (undefined at n=3)",
         v["status"] == "REFUTED" and "undefined" in v.get("reason", ""))
    v = verify_closed_form("n/2", [0, 1, 1, 2, 2])
    gate("non-integer value refuted exactly (1/2 != 1)",
         v["status"] == "REFUTED" and v.get("got") == "1/2")
    v = verify_closed_form("(" * 200 + "n" + ")" * 200, [0, 1, 2])
    gate("depth bomb refused, not crashed", v["status"] == "REFUSED")
    v = verify_closed_form("n^70", [0, 1, 2])
    gate("oversize exponent refused", v["status"] == "REFUSED")
    v = verify_closed_form("9" * 5000 + " + n", [0, 1, 2])
    gate("oversize literal refused", v["status"] == "REFUSED")
    v = verify_closed_form("2^n", [1, 2, 4])
    gate("non-constant exponent outside the grammar refused",
         v["status"] == "REFUSED")
    # the zero-false-verification gate: a good float approximation must die
    # at the exact bar. Binet-with-rounded-constants for Fibonacci:
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    v = verify_closed_form("(89*n*n - 311*n + 366)/144", fib)
    gate("approximate fit refuted, never stamped", v["status"] == "REFUTED")

    # ---- pipeline: input contract -----------------------------------------
    c = conjecture([1.5, 2, 3, 4, 5, 6, 7, 8, 9])       # type: ignore[list-item]
    gate("float input refused (exact contract)", c["status"] == "REFUSED")
    c = conjecture([1, 2, 3])
    gate("too-short input refused", c["status"] == "REFUSED")
    c = conjecture([0, 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121],
                   _force_no_gp=True)
    gate("engine-stamped input returns source=engine (GP not consulted)",
         c["status"] == "VERIFIED" and c["source"] == "engine")
    c = conjecture([7, 2, 9, 4, 4, 8, 3, 1, 6, 5, 5, 9], _force_no_gp=True)
    gate("engine abstains + no gplearn -> honest REFUSED",
         c["status"] == "REFUSED" and "gplearn" in c["reason"])

    # ---- GP path (contract gates: whatever GP proposes must survive exact
    # verification; they assert the degraded path when gplearn is absent) ---
    if _gplearn_available():
        # a(n) = n^7: outside every engine family (poly deg 7 > 6, C-finite
        # order 8 > 4, P-recursive ratio pdeg 7 > 3 — the engine lands on an
        # UNVERIFIED holonomic and abstains) but inside GP's constant-free
        # mul-chain reach.
        target = [n**7 for n in range(14)]
        c = conjecture(target, seed=0, population=1500, generations=20,
                       restarts=2, engine_first=_GATE_ENGINE_FIRST)
        ok = (c["status"] == "VERIFIED" and c["source"] == "gp+exact-holdout")
        gate("engine-refused target: GP proposes, exact gate stamps", ok)
        if ok:
            expr = c["expression"][len("a(n) = "):]
            v = verify_closed_form(expr, target)
            gate("stamped expression survives independent re-verification",
                 v["status"] == "VERIFIED")
            # determinism of the surviving attempt: rerun from the seed that
            # produced the stamp; the certificate must reproduce exactly
            c2 = conjecture(target, seed=c["seed_used"], population=1500,
                            generations=20, restarts=1,
                            engine_first=_GATE_ENGINE_FIRST)
            gate("determinism: same seed, same certificate",
                 c2.get("expression") == c["expression"]
                 and c2.get("phase") == c.get("phase"))
        else:
            gate("stamped expression survives independent re-verification", False)
            gate("determinism: same seed, same certificate", False)
        c = conjecture([7, 2, 9, 4, 4, 8, 3, 1, 6, 5, 5, 9, 2, 7],
                       seed=0, population=400, generations=8, restarts=1)
        gate("random control: GP proposes, exact gate refuses every candidate",
             c["status"] == "REFUSED")
    else:
        print("  [note] gplearn not installed — GP-path gates assert the "
              "degraded contract instead")
        c = conjecture([n**7 for n in range(14)],
                       engine_first=_GATE_ENGINE_FIRST)
        gate("engine-refused target degrades to honest REFUSED",
             c["status"] == "REFUSED" and "gplearn" in c["reason"])

    total = 16 if _gplearn_available() else 15
    print(f"  conjecture gates: {total - fails}/{total} passed")
    return fails


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("selftest", "--selftest"):
        return 1 if _selftest() else 0
    if not args:
        print(__doc__)
        return 0
    raw = args[0]
    ints = re.findall(r"-?\d+", raw)
    if not ints:
        print("usage: python3 -m primus.conjecture \"1 2 4 8 16 ...\" | selftest")
        return 2
    cert = conjecture([int(x) for x in ints])
    if "--json" in args:
        print(json.dumps(cert, indent=2, default=str))
    else:
        print(render(cert))
    return 0 if cert["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
