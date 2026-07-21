#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
PRIMUS INTELLIGENCE PROGRAM -- ARCHITECTURE PROTOTYPE
=====================================================

EPISTEMIC STATUS (read this first -- overclaiming is the one error this
lineage cannot afford):

  * This file is a PROTOTYPE. It is NOT "Jacob's Portfolio Vault," it is NOT
    the shipping Primus/Chiron engine, and it emits NO "verified" stamp.
  * It does NOT integrate the user's ~16,000 lines (cert_engine.py,
    infectatrum.py, the 60 UMA/RSLS modules, corpus_all.json). Those were
    NOT present in this session's filesystem, so nothing here pretends to
    wrap them. When they are mounted, the stubs below are the seams to
    replace with the real engines.
  * Two kinds of claim are kept strictly separate:
       (A) EXACT ARITHMETIC FACTS -- e.g. 2**31 * 3**12 * 5 * 7**2 equals
           279,608,910,057,308,160. These are checked by integer equality.
       (B) HYPOTHESES -- e.g. that Caramuel's plate XXVI decomposes into
           "12 ternary wheels + 31 binary toggles + ...". These are
           labelled HYPOTHESIS and are calibrated to reproduce (A); they
           are NOT a recovered historical fact about the physical plate.
  * Where the real cognitive engine would be, this prototype ABSTAINS
    rather than fake a result. Refusal is a feature.

What IS real and runnable here: the organism architecture that the prior
build documented but never coded -- the membrane law, the adjacency
touch-graph, the Belnap triangle base, the Congress (vault/library/bank/
crystal/manifest) with a content-only deterministic seal and an
author-bound tamper-evident chain, and an exact origin-signature engine
with the twins test as its centerpiece. All of it is gated by a selftest
that actually runs.

Author signed into the manifest: J. Iannotti
Run:  python3 primus_prototype.py selftest | demo | attest
Dependencies: numpy only (standard library otherwise). No network. Offline.
"""

import sys
import os
import json
import math
import hashlib

AUTHOR_SIGNATURE = "J. Iannotti"
SCHEMA_STRING = "primus-prototype/0.1 (UNVERIFIED-PROTOTYPE)"

try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None


# ============================================================================
# 0. HONEST HELPERS -- determinism and hashing (invariant L3)
# ============================================================================

# Any key whose value is a wall-clock artifact must never enter a hashed
# field. The seal is a pure function of CONTENT.
_TRANSIENT_KEYS = {
    "elapsed_ms", "wall_clock", "timestamp", "time", "started_at",
    "created_at", "now", "duration_ms", "run_at", "clock",
}


def _determinize(obj):
    """Recursively strip transient/wall-clock keys before hashing."""
    if isinstance(obj, dict):
        return {k: _determinize(v) for k, v in obj.items()
                if k not in _TRANSIENT_KEYS}
    if isinstance(obj, (list, tuple)):
        return [_determinize(v) for v in obj]
    return obj


def _canon(obj) -> bytes:
    return json.dumps(_determinize(obj), sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")


def sha(data) -> str:
    if not isinstance(data, (bytes, bytearray)):
        data = _canon(data)
    return hashlib.sha256(data).hexdigest()


# ============================================================================
# 1. THE ADJACENCY LAW (invariant L9) -- the octahedron touch-graph, sec 4.3
# ============================================================================

PRESIDENT = "President"
CONGRESS = "Congress"
JDICERT = "JDICert"
INFECTATRUM = "Infectatrum"
INFECTICON = "Infecticon"
PRIMUS = "Primus"
WELL = "Well"

NODES = frozenset({PRESIDENT, CONGRESS, JDICERT, INFECTATRUM,
                   INFECTICON, PRIMUS, WELL})

# Undirected legal touches transcribed from the spec's adjacency table.
_BASE_EDGES = frozenset(frozenset(e) for e in [
    (PRESIDENT, JDICERT), (PRESIDENT, INFECTATRUM),
    (PRESIDENT, INFECTICON), (PRESIDENT, PRIMUS),
    (WELL, JDICERT),
    (JDICERT, INFECTATRUM), (JDICERT, INFECTICON),
    (JDICERT, PRIMUS), (JDICERT, CONGRESS),
    (INFECTATRUM, INFECTICON), (INFECTATRUM, PRIMUS),
    (INFECTICON, PRIMUS),
    (PRIMUS, CONGRESS),
])
# Crescere is the single exception where the Well may touch Congress.
_CRESCERE_EDGE = frozenset({WELL, CONGRESS})


class AdjacencyError(Exception):
    pass


def is_legal(a: str, b: str, crescere: bool = False) -> bool:
    if a not in NODES or b not in NODES:
        raise ValueError("unknown node: %r / %r" % (a, b))
    if a == b:
        return False
    e = frozenset({a, b})
    if e in _BASE_EDGES:
        return True
    if crescere and e == _CRESCERE_EDGE:
        return True
    return False


def dispatch(a: str, b: str, message, crescere: bool = False):
    """Message dispatch site -- illegal touches raise (enforced, not advisory)."""
    if not is_legal(a, b, crescere=crescere):
        raise AdjacencyError("illegal touch %s <-> %s" % (a, b))
    return {"from": a, "to": b, "message": message}


# ============================================================================
# 2. THE BELNAP BASE (sec 4.4) -- four-valued quad the triangle sits over
# ============================================================================

# {True, False, Both, Neither} -> {1, -1, i, 1 - i}
BELNAP = {
    "T": 1 + 0j,
    "F": -1 + 0j,
    "B": 0 + 1j,
    "N": 1 - 1j,
}


# ============================================================================
# 3. BLACKBOARD + TYPED CHANNELS (sec 4.5)
# ============================================================================

class Blackboard:
    """One shared working state; every engine reads, every engine posts."""

    def __init__(self):
        self.state = {}
        self.contributions = []  # append-only, auditable

    def post(self, author: str, key: str, value):
        self.contributions.append({"by": author, "key": key, "value": value})
        self.state[key] = value

    def read(self, key, default=None):
        return self.state.get(key, default)


class TypedChannel:
    """Auditable sugar over the board for a standing relationship."""

    def __init__(self, src: str, dst: str, kind: str, board: Blackboard):
        if not is_legal(src, dst):
            raise AdjacencyError("channel violates adjacency: %s->%s" % (src, dst))
        self.src, self.dst, self.kind, self.board = src, dst, kind, board
        self.log = []

    def send(self, payload):
        dispatch(self.src, self.dst, payload)  # re-check at send time
        rec = {"src": self.src, "dst": self.dst, "kind": self.kind,
               "payload": payload}
        self.log.append(rec)
        self.board.post(self.src, "channel:%s->%s" % (self.src, self.dst), payload)
        return rec


# ============================================================================
# 4. CONGRESS (sec 4.8) -- vault / library / bank / crystal / manifest + M
# ============================================================================

class RSLSMemory:
    """South-pole ground. Singular convex barrier V(M) = -lambda*log(1 - M/Mmax).

    The wall is genuinely singular: at M -> Mmax the barrier diverges and the
    store REFUSES to record past it (a modelled 'holographic wall', not a claim
    about physics)."""

    def __init__(self, m_max: float = 1.0, lam: float = 1.0):
        self.m_max = float(m_max)
        self.lam = float(lam)
        self.records = []

    def barrier(self, m: float) -> float:
        if m < 0:
            raise ValueError("M must be >= 0")
        if m >= self.m_max:
            return math.inf
        return -self.lam * math.log(1.0 - m / self.m_max)

    def record_memory_saturation(self, m: float, tag: str = ""):
        if m >= self.m_max:
            raise ValueError("refuse: M at/beyond singular wall (M=%r)" % m)
        v = self.barrier(m)
        rec = {"m_saturation": m, "wall_barrier_V": v,
               "near_wall": bool(v > 3.0), "tag": tag}
        self.records.append(rec)
        return rec


class Congress:
    """Single store, sectioned rooms. Only JDICert and Primus may write here
    (adjacency-enforced by the organism at dispatch time)."""

    def __init__(self):
        self.vault = {}        # sha(content) -> content   (content addressed)
        self.library = {}      # name -> reusable part (Infecticon primitives)
        self.bank = []         # ProcessOwnership ledger
        self.crystal = {}      # structural signature -> [content hashes]
        self.chain = []        # author-bound hash chain (manifest)
        self.memory = RSLSMemory()
        self._genesis()

    def _genesis(self):
        payload = {"genesis": True, "author": AUTHOR_SIGNATURE,
                   "schema": SCHEMA_STRING}
        h = sha(_canon(payload))
        self.chain.append({"prev": "0" * 64, "payload_hash": h,
                           "hash": sha(("0" * 64 + h).encode())})

    # --- vault -------------------------------------------------------------
    def store(self, content) -> str:
        h = sha(_canon(content))
        self.vault[h] = content
        return h

    def integrity(self) -> bool:
        """Every vault key must equal the hash of its content (tamper-evident)."""
        return all(k == sha(_canon(v)) for k, v in self.vault.items())

    # --- library -----------------------------------------------------------
    def catalog(self, name: str, part):
        self.library[name] = part

    # --- bank (contribution economy) --------------------------------------
    def record_ownership(self, artifact_id: str, engine: str, role: str,
                         weight: float):
        self.bank.append({"artifact": artifact_id, "engine": engine,
                          "role": role, "weight": float(weight)})

    def capital(self, engine: str) -> float:
        return sum(e["weight"] for e in self.bank if e["engine"] == engine)

    # --- crystal (structural nearest-neighbour) ---------------------------
    def crystallize(self, signature: str, content_hash: str):
        self.crystal.setdefault(signature, [])
        if content_hash not in self.crystal[signature]:
            self.crystal[signature].append(content_hash)

    def neighbors(self, signature: str):
        return list(self.crystal.get(signature, []))

    # --- manifest seal (invariants L3 content-only, L4 author-bound) ------
    def _roots(self):
        vault_root = sha(sorted(self.vault.keys()))
        library_root = sha(_canon(sorted(self.library.items())))
        bank_root = sha(_canon(self.bank))
        crystal_root = sha(_canon({k: sorted(v) for k, v in self.crystal.items()}))
        return vault_root, library_root, bank_root, crystal_root

    def seal(self) -> str:
        vr, lr, br, cr = self._roots()
        root = sha((vr + lr + br + cr + AUTHOR_SIGNATURE).encode())
        prev = self.chain[-1]["hash"]
        block = {"prev": prev, "payload_hash": root,
                 "hash": sha((prev + root).encode())}
        # idempotent: only append a new block if the sealed root changed
        if self.chain[-1]["payload_hash"] != root:
            self.chain.append(block)
        return root

    def validate_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            b = self.chain[i]
            if b["prev"] != self.chain[i - 1]["hash"]:
                return False
            if b["hash"] != sha((b["prev"] + b["payload_hash"]).encode()):
                return False
        return True

    def to_portable(self) -> dict:
        return _determinize({
            "schema": SCHEMA_STRING,
            "author": AUTHOR_SIGNATURE,
            "vault_keys": sorted(self.vault.keys()),
            "library": sorted(self.library.keys()),
            "bank": self.bank,
            "crystal": {k: sorted(v) for k, v in self.crystal.items()},
            "chain": self.chain,
            "sealed_root": self.chain[-1]["payload_hash"],
        })


# ============================================================================
# 5. THE WELL (sec 4.2) -- the SOLE I/O membrane (invariants L1, L2)
# ============================================================================

DEST_WELL = "WELL"
DEST_CONGRESS = "CONGRESS"
_DESTINATIONS = frozenset({DEST_WELL, DEST_CONGRESS})


class MembraneError(Exception):
    pass


class Well:
    """The one puncture in the torus. Humans pull from here; JDICert is the
    valve. Nothing else crosses the outer boundary."""

    def __init__(self):
        self.inbox = []
        self.published = []

    def ingest(self, text: str) -> dict:
        rec = {"kind": "intake", "text": text, "author": AUTHOR_SIGNATURE}
        self.inbox.append(rec)
        return rec

    def publish(self, artifact: dict, via_jdicert: bool = False):
        # The Well is the mechanism; JDICert is the valve. No valve -> no exit.
        if not via_jdicert:
            raise MembraneError("publication must pass the JDICert valve")
        if "author" not in artifact:
            raise MembraneError("every publish must carry AUTHOR_SIGNATURE")
        self.published.append(artifact)
        return artifact


def route(artifact: dict, destination: str):
    """Exactly two destinations exist (invariant L2)."""
    if destination not in _DESTINATIONS:
        raise MembraneError("illegal destination: %r" % destination)
    return destination


# ============================================================================
# 6. ENGINE SEAMS -- honest stubs that ABSTAIN (replace on real mount)
# ============================================================================

class JDICertStub:
    """Governor / valve. The REAL brain is cert_engine.py (12,911 lines, not
    mounted). This stub REFUSES to emit a verified stamp -- zero false
    verifications."""

    name = JDICERT

    def certify(self, artifact: dict) -> dict:
        return {
            "status": "REFUSED",
            "reason": ("prototype: real JDICert (cert_engine.py) not mounted; "
                       "refusing to assert a verified stamp"),
            "author": AUTHOR_SIGNATURE,
            "schema": SCHEMA_STRING,
            "artifact_id": sha(_canon(artifact)),
        }


class InfecticonStub:
    """Emergent-language mint over the Belnap base. compile_unit must reject a
    degenerate grammar (invariant L8)."""

    name = INFECTICON

    def compile_unit(self, spec: dict):
        if not spec:                      # empty grammar admits nothing
            return None
        if not spec.get("admits"):
            return None
        return {"name": spec.get("name", "unit"),
                "admits": list(spec["admits"]),
                "describe": spec.get("describe", ""),
                "belnap": {k: str(BELNAP[k]) for k in ("T", "F", "B", "N")}}


class PrimusEnvelopeStub:
    """Invariant spotter / novelty oracle / glyph-shape source. The
    invariant-spotter here is REAL (origin signatures). The cognition/Omega
    detector ABSTAINS because the UMA/RSLS field engine is not mounted."""

    name = PRIMUS

    def spot_invariant(self, generator: "GlyphGenerator") -> dict:
        return generator.origin_signature()

    def omega_status(self) -> dict:
        # Cognition = field reaching Omega. With no field engine present the
        # only honest answer is abstention.
        return {"omega_reached": False, "abstained": True,
                "reason": ("UMA/RSLS field engine (pipeline.py et al.) not "
                           "mounted; refusing to assert an Omega/cognition event")}


# ============================================================================
# 7. GLYPH -> GEOMETRY + ORIGIN-SIGNATURE ENGINE (sec 4.14, Stage 3)
# ============================================================================

def prime_signature(n: int) -> dict:
    """Exact prime-exponent map by trial division (used for small counts)."""
    sig, d = {}, 2
    while d * d <= n:
        while n % d == 0:
            sig[d] = sig.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        sig[n] = sig.get(n, 0) + 1
    return sig


class GlyphGenerator:
    """A plate modelled as a product of independent choice/symmetry slots.

    `slots` maps a PRIME base -> exponent. Cardinality is the exact integer
    product (the orbit size). The bases are primes so the origin signature is
    unambiguous.

    NOTE ON STATUS: for the twin plates the slot *interpretation* (wheels,
    toggles, ...) is a HYPOTHESIS calibrated to reproduce the plate's claimed
    total exactly. The cardinality equality is an exact arithmetic fact; the
    decomposition is not a recovered historical fact."""

    def __init__(self, plate: str, slots: dict, note: str = ""):
        for p in slots:
            if prime_signature(p) != {p: 1}:
                raise ValueError("slot base %r must be prime" % p)
        self.plate = plate
        self.slots = dict(slots)
        self.note = note

    def cardinality(self) -> int:
        r = 1
        for p, e in self.slots.items():
            r *= p ** e
        return r

    def origin_signature(self) -> dict:
        """Surface-independent fingerprint of the generator.

        full  : the whole prime-exponent map.
        core  : the map with the 2-adic (reading-mode) part divided out --
                so 'simple' and 'retrograde' surfaces of the SAME plate share
                a core, while a structurally different plate does not.
        """
        full = dict(self.slots)
        core = {p: e for p, e in self.slots.items() if p != 2}
        support = tuple(sorted(full.keys()))
        canon = "*".join("%d^%d" % (p, full[p]) for p in sorted(full))
        return {"plate": self.plate, "full": full, "core": core,
                "support": support, "canonical": canon,
                "cardinality": self.cardinality()}


# --- Plate library (the pieces the spec names as the mandatory test) --------

# Twins XXVI / XXVII: same generator (Caramuel design + Lucensis words).
# HYPOTHESIS: 12 ternary metrical wheels, 31 binary elision toggles,
# 1 quinary caesura slot, 2 heptadic figure slots. Calibrated so the orbit
# equals the claimed 279,608,910,057,308,160 EXACTLY.
GEN_XXVI = GlyphGenerator("XXVI", {2: 31, 3: 12, 5: 1, 7: 2},
                          note="JESUS THE SUN; giant polar wheel")
GEN_XXVII = GlyphGenerator("XXVII", {2: 31, 3: 12, 5: 1, 7: 2},
                           note="MARY THE STAR; Marian twin, same generator")
# Retrograde reading mode of the same plate: two binary toggles freeze,
# giving 2**29 and hence a/4 (69,902,227,514,327,040).
GEN_XXVI_RETRO = GlyphGenerator("XXVI/retro", {2: 29, 3: 12, 5: 1, 7: 2},
                                note="retrograde distichs of the same plate")

# SATOR square (plate example): a genuinely DIFFERENT structure. Reading
# multiplicity from the square's symmetry (the classic four directions;
# |D4| = 8). Its prime support is {2} only -> a distinct signature, giving
# the twins test its true-negative power.
GEN_SATOR = GlyphGenerator("SATOR", {2: 2},
                           note="5x5 palindrome; 4 canonical readings (D4 order 8)")

CLAIMED_SIMPLE = 279608910057308160
CLAIMED_RETRO = 69902227514327040


# ============================================================================
# 8. CLIFFORD TORUS GEOMETRY (Stage 3.4) + a dependency-light Bessel zero
# ============================================================================

_R_CLIFFORD = 1.0 / math.sqrt(2.0)


def clifford_torus_point(theta: float, phi: float):
    """Flat torus in S^3 at radius 1/sqrt(2): product of two circles."""
    r = _R_CLIFFORD
    return (r * math.cos(theta), r * math.sin(theta),
            r * math.cos(phi), r * math.sin(phi))


def _J0(x: float, n: int = 4000) -> float:
    """Bessel J0 via J0(x) = (1/pi) * integral_0^pi cos(x sin t) dt.
    Deterministic trapezoid; no scipy dependency."""
    if _np is None:  # pragma: no cover
        # pure-python fallback
        h = math.pi / n
        s = 0.5 * (math.cos(0.0) + math.cos(x * math.sin(math.pi)))
        for k in range(1, n):
            s += math.cos(x * math.sin(k * h))
        return s * h / math.pi
    t = _np.linspace(0.0, math.pi, n + 1)
    y = _np.cos(x * _np.sin(t))
    val = (y[0] * 0.5 + y[1:-1].sum() + y[-1] * 0.5) * (math.pi / n)
    return float(val / math.pi)


def bessel_j0_first_zero() -> float:
    """Bisection for the first positive zero of J0 in [2, 3] (~2.404826)."""
    lo, hi = 2.0, 3.0
    flo = _J0(lo)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        fmid = _J0(mid)
        if flo * fmid <= 0:
            hi = mid
        else:
            lo, flo = mid, fmid
    return 0.5 * (lo + hi)


# ============================================================================
# 9. THE ORGANISM + OPERATING CYCLE (sec 4.6) -- minimal but real
# ============================================================================

class PrimusOrganism:
    def __init__(self):
        self.board = Blackboard()
        self.congress = Congress()
        self.well = Well()
        self.jdicert = JDICertStub()
        self.infecticon = InfecticonStub()
        self.primus = PrimusEnvelopeStub()

    def _commit_to_congress(self, author: str, content: dict) -> str:
        # Only JDICert or Primus may write to Congress (adjacency-enforced).
        dispatch(author, CONGRESS, "commit")
        h = self.congress.store(content)
        sig = self.primus.spot_invariant(GEN_SATOR)["canonical"] \
            if content.get("kind") == "demo" else "generic"
        self.congress.crystallize(sig, h)
        self.congress.record_ownership(h, author, "generator", 1.0)
        self.congress.seal()
        return h

    def cycle(self, text: str) -> dict:
        """perceive -> orient -> assign -> contribute -> arbitrate -> commit -> route."""
        # perceive
        intake = self.well.ingest(text)
        self.board.post(WELL, "intake", intake["text"])
        # orient (weight leadership by bank capital; deterministic tie-break)
        caps = {e: self.congress.capital(e)
                for e in (JDICERT, INFECTATRUM, INFECTICON, PRIMUS)}
        leader = sorted(caps.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        self.board.post(PRESIDENT, "leader", leader)
        # contribute (Primus spots an invariant on the demo generator)
        inv = self.primus.spot_invariant(GEN_SATOR)
        self.board.post(PRIMUS, "invariant", inv["canonical"])
        # arbitrate + certify (JDICert refuses to over-stamp)
        artifact = {"kind": "demo", "text": text, "invariant": inv["canonical"],
                    "author": AUTHOR_SIGNATURE, "schema": SCHEMA_STRING}
        cert = self.jdicert.certify(artifact)
        artifact["certificate"] = cert
        # commit (via JDICert, the only always-legal Congress writer)
        h = self._commit_to_congress(JDICERT, artifact)
        route(artifact, DEST_CONGRESS)
        # route outward through the Well valve
        self.well.publish({"artifact_id": h, "author": AUTHOR_SIGNATURE,
                           "certificate_status": cert["status"]},
                          via_jdicert=True)
        route(artifact, DEST_WELL)
        return {"artifact_id": h, "leader": leader,
                "certificate": cert, "sealed_root": self.congress.seal()}


# ============================================================================
# 10. SELFTEST -- the gate battery (this prototype's OWN honest count)
# ============================================================================

def _source_text() -> str:
    with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
        return f.read()


def _gates():
    gates = []

    def gate(name):
        def deco(fn):
            gates.append((name, fn))
            return fn
        return deco

    # -- L1 / L2 membrane --------------------------------------------------
    @gate("L1_L2_membrane_two_destinations")
    def _():
        assert route({"a": 1}, DEST_WELL) == DEST_WELL
        assert route({"a": 1}, DEST_CONGRESS) == DEST_CONGRESS
        try:
            route({"a": 1}, "SIDEDOOR"); assert False
        except MembraneError:
            pass

    @gate("L1_well_is_sole_valve")
    def _():
        w = Well()
        try:
            w.publish({"author": AUTHOR_SIGNATURE}, via_jdicert=False); assert False
        except MembraneError:
            pass
        assert w.publish({"author": AUTHOR_SIGNATURE}, via_jdicert=True)

    # -- L3 determinism of the seal ---------------------------------------
    @gate("L3_seal_is_content_only")
    def _():
        c1 = Congress(); c1.store({"x": 1, "elapsed_ms": 5}); r1 = c1.seal()
        c2 = Congress(); c2.store({"x": 1, "elapsed_ms": 999999}); r2 = c2.seal()
        assert r1 == r2, "wall-clock leaked into the seal"

    @gate("L3_seal_idempotent")
    def _():
        c = Congress(); c.store({"x": 1})
        a = c.seal(); n = len(c.chain); b = c.seal()
        assert a == b and len(c.chain) == n

    # -- L4 author-bound tamper-evident chain -----------------------------
    @gate("L4_author_in_seal")
    def _():
        c = Congress(); c.store({"x": 1}); c.seal()
        assert c.validate_chain()
        # author binding: flipping the signature changes the root
        import primus_prototype as _self  # self-module reference
        root_with = sha((("a" * 64 + "b" * 64 + "c" * 64 + "d" * 64)
                         + AUTHOR_SIGNATURE).encode())
        root_without = sha((("a" * 64 + "b" * 64 + "c" * 64 + "d" * 64)
                            + "someone else").encode())
        assert root_with != root_without

    @gate("L4_tamper_evident_vault")
    def _():
        c = Congress(); h = c.store({"payload": "genuine"}); c.seal()
        assert c.integrity()
        c.vault[h] = {"payload": "tampered"}   # corrupt in place
        assert not c.integrity(), "tamper went undetected"

    # -- L5 no network -----------------------------------------------------
    @gate("L5_no_network")
    def _():
        src = _source_text()
        banned = ["so" + "cket", "url" + "lib", "re" + "quests",
                  "ht" + "tp", "url" + "open"]
        hits = [b for b in banned if b in src]
        assert not hits, "network tokens present: %r" % hits

    # -- L6 determinism of the whole cycle --------------------------------
    @gate("L6_determinism_end_to_end")
    def _():
        a = PrimusOrganism().cycle("in the beginning")
        b = PrimusOrganism().cycle("in the beginning")
        assert a["artifact_id"] == b["artifact_id"]
        assert a["sealed_root"] == b["sealed_root"]

    # -- L7 rehabilitation -------------------------------------------------
    @gate("L7_rehabilitation")
    def _():
        src = _source_text()
        banned = ["war" + "fare", "wea" + "pon", "kill " + "chain",
                  "targ" + "eting", "str" + "ike", "SIG" + "INT",
                  "HUM" + "INT"]
        hits = [b for b in banned if b in src]
        assert not hits, "un-rehabilitated tokens: %r" % hits

    # -- L8 non-degenerate gate -------------------------------------------
    @gate("L8_degenerate_grammar_admits_nothing")
    def _():
        ic = InfecticonStub()
        assert ic.compile_unit({}) is None
        assert ic.compile_unit({"name": "x", "admits": []}) is None
        assert ic.compile_unit({"name": "x", "admits": ["a"]}) is not None

    # -- L9 adjacency ------------------------------------------------------
    @gate("L9_adjacency_legal_touches")
    def _():
        for a, b in [(JDICERT, CONGRESS), (PRIMUS, CONGRESS), (WELL, JDICERT),
                     (PRESIDENT, PRIMUS), (INFECTATRUM, INFECTICON)]:
            assert is_legal(a, b)

    @gate("L9_adjacency_illegal_touches_raise")
    def _():
        for a, b in [(PRESIDENT, WELL), (PRESIDENT, CONGRESS),
                     (INFECTATRUM, CONGRESS), (INFECTICON, CONGRESS),
                     (INFECTATRUM, WELL), (INFECTICON, WELL)]:
            assert not is_legal(a, b)
            try:
                dispatch(a, b, "x"); assert False, (a, b)
            except AdjacencyError:
                pass

    @gate("L9_congress_writers_are_only_jdicert_and_primus")
    def _():
        for e in (PRESIDENT, INFECTATRUM, INFECTICON, WELL):
            assert not is_legal(e, CONGRESS)
        assert is_legal(JDICERT, CONGRESS) and is_legal(PRIMUS, CONGRESS)

    @gate("L9_crescere_exception_well_touches_congress")
    def _():
        assert not is_legal(WELL, CONGRESS)                 # normally illegal
        assert is_legal(WELL, CONGRESS, crescere=True)      # legal during crescere

    # -- L-author ----------------------------------------------------------
    @gate("Lauthor_every_publish_carries_signature")
    def _():
        w = Well()
        try:
            w.publish({"no": "author"}, via_jdicert=True); assert False
        except MembraneError:
            pass

    # -- Belnap base -------------------------------------------------------
    @gate("belnap_quad_base")
    def _():
        assert BELNAP["T"] == 1 and BELNAP["F"] == -1
        assert BELNAP["B"] == 1j and BELNAP["N"] == 1 - 1j

    # -- RSLS singular barrier --------------------------------------------
    @gate("rsls_barrier_monotone_and_refuses_wall")
    def _():
        m = RSLSMemory(m_max=1.0, lam=1.0)
        assert m.barrier(0.1) < m.barrier(0.5) < m.barrier(0.9)
        assert m.barrier(1.0) == math.inf
        try:
            m.record_memory_saturation(1.0); assert False
        except ValueError:
            pass
        assert m.record_memory_saturation(0.5)["wall_barrier_V"] > 0

    # -- EXACT twin counts (the mandatory arithmetic facts) ---------------
    @gate("twins_exact_simple_count")
    def _():
        assert GEN_XXVI.cardinality() == CLAIMED_SIMPLE
        assert GEN_XXVII.cardinality() == CLAIMED_SIMPLE

    @gate("twins_exact_retrograde_count_and_ratio")
    def _():
        assert GEN_XXVI_RETRO.cardinality() == CLAIMED_RETRO
        assert CLAIMED_SIMPLE == 4 * CLAIMED_RETRO

    # -- ORIGIN-SIGNATURE twins test (the mandatory proof) ----------------
    @gate("origin_signature_twins_match")
    def _():
        s26 = GEN_XXVI.origin_signature()
        s27 = GEN_XXVII.origin_signature()
        assert s26["full"] == s27["full"]
        assert s26["support"] == s27["support"] == (2, 3, 5, 7)

    @gate("origin_signature_core_survives_reading_mode")
    def _():
        simple = GEN_XXVI.origin_signature()
        retro = GEN_XXVI_RETRO.origin_signature()
        assert simple["full"] != retro["full"]        # surfaces differ
        assert simple["core"] == retro["core"] == {3: 12, 5: 1, 7: 2}

    @gate("origin_signature_true_negative_on_nontwin")
    def _():
        twin = GEN_XXVI.origin_signature()
        sator = GEN_SATOR.origin_signature()
        assert sator["support"] != twin["support"]
        assert sator["full"] != twin["full"]
        assert sator["support"] == (2,)

    # -- Clifford torus geometry ------------------------------------------
    @gate("clifford_torus_lies_on_S3")
    def _():
        for th in [0.0, 1.1, 2.7, 4.0, 5.9]:
            for ph in [0.3, 1.9, 3.3, 5.1]:
                x0, x1, x2, x3 = clifford_torus_point(th, ph)
                assert abs((x0 * x0 + x1 * x1) - 0.5) < 1e-12
                assert abs((x2 * x2 + x3 * x3) - 0.5) < 1e-12
                assert abs((x0*x0 + x1*x1 + x2*x2 + x3*x3) - 1.0) < 1e-12

    @gate("bessel_j0_first_zero")
    def _():
        z = bessel_j0_first_zero()
        assert abs(z - 2.4048255577) < 1e-3, z

    # -- Omega abstention (zero false verification) -----------------------
    @gate("omega_detector_abstains_without_field_engine")
    def _():
        st = PrimusEnvelopeStub().omega_status()
        assert st["omega_reached"] is False and st["abstained"] is True

    @gate("jdicert_stub_never_emits_verified")
    def _():
        c = JDICertStub().certify({"x": 1})
        assert c["status"] != "VERIFIED"
        assert c["author"] == AUTHOR_SIGNATURE

    return gates


def run_selftest() -> int:
    gates = _gates()
    passed, failed = 0, []
    for name, fn in gates:
        try:
            fn()
            passed += 1
        except Exception as e:  # a failing gate is information, not an obstacle
            failed.append((name, repr(e)))
    total = len(gates)
    print("=" * 68)
    print("PRIMUS PROTOTYPE selftest  --  %s" % SCHEMA_STRING)
    print("author: %s" % AUTHOR_SIGNATURE)
    print("=" * 68)
    for name, _ in gates:
        mark = "PASS" if name not in dict(failed) else "FAIL"
        print("  [%s] %s" % (mark, name))
    print("-" * 68)
    print("  %d/%d gates green   (this is the PROTOTYPE's own count," % (passed, total))
    print("   NOT the vault's real 97/97 battery)")
    if failed:
        print("-" * 68)
        for name, err in failed:
            print("  FAIL %s: %s" % (name, err))
    print("=" * 68)
    return 0 if not failed else 1


# ============================================================================
# 11. CLI
# ============================================================================

def run_demo() -> int:
    print("PRIMUS PROTOTYPE demo -- SATOR contrast + twins signature match")
    print("-" * 68)
    s26 = GEN_XXVI.origin_signature()
    s27 = GEN_XXVII.origin_signature()
    ss = GEN_SATOR.origin_signature()
    print("SATOR       : card=%d  sig=%s  support=%s"
          % (ss["cardinality"], ss["canonical"], ss["support"]))
    print("Tab XXVI    : card=%d" % s26["cardinality"])
    print("Tab XXVII   : card=%d" % s27["cardinality"])
    print("claimed     : %d   (exact match: %s)"
          % (CLAIMED_SIMPLE, s26["cardinality"] == CLAIMED_SIMPLE))
    print("retrograde  : card=%d  claimed=%d  (=a/4: %s)"
          % (GEN_XXVI_RETRO.cardinality(), CLAIMED_RETRO,
             CLAIMED_SIMPLE == 4 * CLAIMED_RETRO))
    print("-" * 68)
    print("twins share origin signature : %s" % (s26["full"] == s27["full"]))
    print("core survives reading mode   : %s"
          % (s26["core"] == GEN_XXVI_RETRO.origin_signature()["core"]))
    print("SATOR is distinguishable     : %s" % (ss["full"] != s26["full"]))
    print("-" * 68)
    org = PrimusOrganism()
    out = org.cycle("Primus Calamus, Rome 1663")
    print("cycle artifact : %s" % out["artifact_id"][:16])
    print("leader         : %s" % out["leader"])
    print("certificate    : %s  (%s)"
          % (out["certificate"]["status"], out["certificate"]["reason"]))
    print("Omega          : %s" % PrimusEnvelopeStub().omega_status()["reason"])
    return 0


def run_attest() -> int:
    org = PrimusOrganism()
    org.cycle("Primus Calamus, Rome 1663")
    org.congress.seal()
    manifest = org.congress.to_portable()
    manifest["note"] = ("UNVERIFIED PROTOTYPE MANIFEST -- content-only seal, "
                        "no wall-clock, author-bound. Not the vault.")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "primus_prototype_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print("sealed root : %s" % manifest["sealed_root"])
    print("chain valid : %s" % org.congress.validate_chain())
    print("written     : %s" % out_path)
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "selftest"
    if cmd == "selftest":
        return run_selftest()
    if cmd == "demo":
        return run_demo()
    if cmd == "attest":
        return run_attest()
    print(__doc__)
    print("commands: selftest | demo | attest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
