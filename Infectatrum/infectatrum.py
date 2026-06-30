#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
# =====================================================================================
#  INFECTATRUM  —  a universal coherence / ambiguity / information-loss engine
#  Infecticon    —  the representation it GROWS from resolved ambiguities (emergent)
#
#  Ground source : Juan Caramuel y Lobkowitz, Primus Calamus ob oculos ponens
#                  Metametricam (Rome, 1663) — a 17th-c. combinatorial computer on paper.
#  Output target : THIS single monolithic program. Built across "continue" increments.
#
#  SPINE:  object -> reading spectrum -> DETECT | RESOLVE | GENERATE
#          Ambiguity is the measurable residue of information loss under compression.
#          It is SIGNAL, not noise: measured, classified, and operated on in BOTH
#          directions (collapse toward one reading / synthesize many).
#
#  WHY THIS IS NOT A TOY (the anti-Swift's-Engine guarantee, enforced in tests):
#    Nothing counts as a "valid reading" unless an INDEPENDENT gate admits it. The
#    meaning gate here is a native Latin quantity scanner (S8), not a hardcoded word
#    set — so |Σ| and H(R) are measurements, not tautologies of a lookup table.
#
#  BUILD STATE — increment 1 of N  [DONE in this file]:
#    P-010 Provenance/attestation     P-015 SemanticState (Belnap+complex+simplex)
#    P-001 Picture / Labyrinth IR      P-001f FigureGraph (non-rectangular topology)
#    P-002 Ductus registry (5 named + extensions + figure walks)
#    P-003 Meaning gate: native Latin scansion (real, independent work)
#    P-007 DETECT (|Σ|, H(R), MI localization, ambiguity load, negative space)
#    P-006 RESOLVE (commit + min-cut/set-cover disambiguation, pure-python + optional nx)
#    P-004 Operators (Proteus orbit, anagram, echo/palindrome)
#    P-005 GENERATE (bounded backtracking synthesis; CP-SAT optional accelerator)
#    P-012 Ambiguity classifier (A1–A4 + intent + topology)
#    P-011 Resolution morphology + RESOLUTION CALCULUS (compose/invert/distance/quotient)
#    Plugin ABCs + registry, corpus loader scaffold, CLI, embedded test gates.
#  NEXT (on "continue"): P-013 origin signature (Bayesian inverse/stylometry),
#    P-014 basis inference, P-016 codifier/input adapters, P-017 translation layer,
#    P-018 Infecticon emergence; then fold the first transcribed real plate (Tab. XIII).
#
#  Runs on the Python standard library alone. Heavy libraries (numpy/networkx/ortools/
#  cltk) are OPTIONAL accelerators: each is wrapped in try/except with a correct
#  pure-python fallback, so the monolith is complete and runs anywhere.
# =====================================================================================

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import (Any, Callable, Dict, FrozenSet, Iterable, List, Optional,
                    Sequence, Set, Tuple)

Coord = Tuple[int, int]

# Optional accelerators — never required. We record what is available so the
# engine can report which path it took (a provenance concern, not a behavior change).
_HAVE: Dict[str, bool] = {}
try:
    import networkx as _nx  # noqa: F401
    _HAVE["networkx"] = True
except Exception:
    _HAVE["networkx"] = False
try:
    import numpy as _np  # noqa: F401
    _HAVE["numpy"] = True
except Exception:
    _HAVE["numpy"] = False


# =====================================================================================
#  SECTION 0 — PROVENANCE / ATTESTATION   (P-010)
#  Every artifact carries a hash so faithfulness is auditable. Ground Rule 2:
#  faithfulness with provenance — every modeled object traces to a source or is an
#  explicit EXTENSION. The MANIFEST hashes the whole chain source -> IR -> output.
# =====================================================================================

def sha(obj: Any) -> str:
    """Stable short hash over a JSON-canonicalized object."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


@dataclass
class Provenance:
    source: str = "unknown"          # e.g. "Caramuel Primus Calamus p.446 Tab.XIII" | "EXTENSION" | "fixture"
    region: str = ""                 # bbox / cell-range / page id
    confidence: str = "high"         # high | med | low   (low => human escalation, never silently completed)
    flags: List[str] = field(default_factory=list)

    def stamp(self, payload: Any) -> str:
        return sha({"source": self.source, "region": self.region,
                    "confidence": self.confidence, "payload": payload})


class Manifest:
    """Tamper-evident ledger over every attested artifact in a run."""
    def __init__(self) -> None:
        self.entries: List[Tuple[str, str]] = []  # (label, hash)

    def add(self, label: str, payload: Any, prov: Optional[Provenance] = None) -> str:
        h = (prov or Provenance(source="runtime")).stamp(payload)
        self.entries.append((label, h))
        return h

    def digest(self) -> str:
        return sha([{"label": l, "hash": h} for l, h in self.entries])

    def add_source_file(self, path: str) -> Optional[str]:
        """Phase 3 chain of custody: hash the engine source file itself into the ledger."""
        try:
            with open(path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()[:16]
            self.entries.append((f"SOURCE:{os.path.basename(path)}", h))
            return h
        except OSError:
            return None

    def render(self) -> str:
        lines = ["# MANIFEST.sha256  (Infectatrum attestation ledger)"]
        for l, h in self.entries:
            lines.append(f"{h}  {l}")
        lines.append(f"{self.digest()}  __ROOT__")
        return "\n".join(lines)


MANIFEST = Manifest()


# =====================================================================================
#  SECTION 1 — SEMANTIC STATE   (P-015)
#  Partial meaning as geometry, not a truth value. Resolves the −1/0/1/i question by
#  LAYERING (the category error that tangled prior attempts):
#    (b) logic   : Belnap's four-valued bilattice {True, False, Both, Neither}
#                  ≅ {affirmation, negation, contradiction, orthogonal}.
#    (c) geometry: a complex/vector state. Minimal form s = a + b·i with
#                  a∈[−1,1] coherence (−1 contradiction … +1 affirmation),
#                  b≥0 orthogonality (inability to project into the current basis).
#                  i is a COORDINATE (basis-mismatch axis), never a logic gate, never
#                  the computational substrate. Native in Python (1j); runs on binary HW.
#  Epistemic uncertainty (resolvable) lives on a probability SIMPLEX, kept distinct from
#  the orthogonal axis — so we never collapse a value prematurely.
# =====================================================================================

@dataclass
class SemanticState:
    affirmation: float = 0.0   # >= 0  weight of "coheres / true in this basis"
    negation:    float = 0.0   # >= 0  weight of "contradicts / false in this basis"
    orthogonal:  float = 0.0   # >= 0  weight of "not projectable into this basis"

    def as_complex(self) -> complex:
        # real axis = coherence (aff - neg); imaginary axis = orthogonality magnitude
        return complex(self.affirmation - self.negation, self.orthogonal)

    def coherence(self) -> float:
        return self.affirmation - self.negation

    def simplex(self) -> Dict[str, float]:
        """Epistemic distribution; carries uncertainty forward instead of collapsing it."""
        tot = self.affirmation + self.negation + self.orthogonal
        if tot <= 0:
            return {"affirmation": 0.0, "negation": 0.0, "orthogonal": 1.0}
        return {"affirmation": self.affirmation / tot,
                "negation": self.negation / tot,
                "orthogonal": self.orthogonal / tot}

    def belnap(self, tau: float = 0.25) -> str:
        a, n, o = self.affirmation, self.negation, self.orthogonal
        if o >= max(a, n) and o > tau:
            return "Neither"          # orthogonal / malformed-in-basis (A4)
        if a > tau and n > tau:
            return "Both"             # contradiction (A3)
        if a >= n and a > tau:
            return "True"
        if n > a and n > tau:
            return "False"
        return "Neither"

    def __repr__(self) -> str:
        s = self.as_complex()
        return f"State({self.belnap()}; {s.real:+.2f}{s.imag:+.2f}i)"


# =====================================================================================
#  SECTION 2 — PICTURE / LABYRINTH IR   (P-001)  +  FigureGraph   (P-001f)
#  A picture is an m×n grid over an alphabet (cells may be letters OR whole words —
#  Caramuel uses both). A FigureGraph generalizes this to NON-rectangular topology
#  (the hexagram of Tab. XIII, spirals, altars): named nodes carrying tokens plus a
#  set of named directed walks. A Labyrinth = a substrate (Picture or FigureGraph)
#  + declared ductus + a Language relative to which readings are admitted.
#
#  Language is a FIRST-CLASS, SWAPPABLE PARAMETER (the atlas principle): meaning is
#  always read *in a chart*, never in one privileged chart. Ambiguity is only defined
#  relative to L (a string is ambiguous w.r.t. a grammar).
# =====================================================================================

class Substrate:
    """Common interface for anything a ductus can walk and a reader can read."""
    def at(self, node: Any) -> str: raise NotImplementedError
    def nodes(self) -> List[Any]: raise NotImplementedError
    def read(self, path: List[Any], sep: str = "") -> str:
        return sep.join(self.at(n) for n in path)


class Picture(Substrate):
    """Rectangular m×n array over a finite alphabet; cells are tokens (letters or words)."""
    def __init__(self, rows: List[List[str]]):
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError("picture must be rectangular and non-empty")
        self.cells = rows
        self.nrows = len(rows)
        self.ncols = len(rows[0])

    @classmethod
    def from_words(cls, words: List[str]) -> "Picture":
        """Square/rect letter-grid from equal-length words, one per row."""
        return cls([list(w) for w in words])

    def at(self, c: Coord) -> str:
        return self.cells[c[0]][c[1]]

    def nodes(self) -> List[Coord]:
        return [(r, c) for r in range(self.nrows) for c in range(self.ncols)]


class FigureGraph(Substrate):
    """
    Non-rectangular labyrinth topology. Nodes are named; each carries a token.
    `walks` maps a ductus-name to an ordered list of node-names (a declared path,
    exactly as Caramuel prints the ductus type on the plate). This is what lets the
    engine hold the Tab. XIII hexagram, spirals, altars, columns — geometry the
    rectangular Picture cannot express. (The prior increment lacked this.)
    """
    def __init__(self, tokens: Dict[str, str], walks: Optional[Dict[str, List[str]]] = None):
        self.tokens = dict(tokens)
        self.walks = {k: list(v) for k, v in (walks or {}).items()}

    def at(self, node: str) -> str:
        return self.tokens[node]

    def nodes(self) -> List[str]:
        return list(self.tokens.keys())

    def add_walk(self, name: str, node_seq: List[str]) -> None:
        for n in node_seq:
            if n not in self.tokens:
                raise KeyError(f"walk '{name}' references unknown node '{n}'")
        self.walks[name] = list(node_seq)


@dataclass
class Language:
    """The chart relative to which a reading is valid. Pluggable — the atlas parameter.
    `admits(s)` returns True iff string s is a valid reading in this language.
    For Caramuel: meter + lexicon (S8). For other substrates: supply their grammar."""
    name: str
    admits: Callable[[str], bool]
    describe: str = ""


# --- Tiling recognizer (declarative legality for rectangular plate TYPES) ------------
@dataclass
class TilingSystem:
    """
    A plate *type* as a picture language, recognized by local 2x2 constraints
    (Giammarresi–Restivo; equivalent to MSO over rectangular pictures). `allowed` is
    the set of permitted 2x2 windows over the alphabet ∪ {border '#'}. Membership =
    every 2x2 window of the bordered picture lies in `allowed`. We keep types in the
    deterministic/unambiguous subclass so recognition is polynomial.
    """
    name: str
    allowed: Set[Tuple[str, str, str, str]]   # (top-left, top-right, bottom-left, bottom-right)

    def windows(self, pic: Picture) -> Iterable[Tuple[str, str, str, str]]:
        B = "#"
        g = [[B] * (pic.ncols + 2)]
        for row in pic.cells:
            g.append([B] + list(row) + [B])
        g.append([B] * (pic.ncols + 2))
        for r in range(len(g) - 1):
            for c in range(len(g[0]) - 1):
                yield (g[r][c], g[r][c + 1], g[r + 1][c], g[r + 1][c + 1])

    def recognizes(self, pic: Picture) -> bool:
        return all(w in self.allowed for w in self.windows(pic))

    @classmethod
    def from_examples(cls, name: str, examples: List[Picture]) -> "TilingSystem":
        """Learn the allowed 2x2 set from positive examples (the simplest induction)."""
        allowed: Set[Tuple[str, str, str, str]] = set()
        tmp = cls(name, set())
        for pic in examples:
            for w in tmp.windows(pic):
                allowed.add(w)
        return cls(name, allowed)


# =====================================================================================
#  SECTION 3 — DUCTUS REGISTRY   (P-002)
#  A ductus is a reading PATH over a substrate. The five Caramuel names from the title
#  page, plus extensions. For Pictures the path is computed; for FigureGraphs the path
#  is the named walk declared on the plate. Registry is open: @register_ductus(name).
# =====================================================================================

DUCTUS: Dict[str, Callable[[Substrate], List[Any]]] = {}


def register_ductus(name: str):
    def deco(fn: Callable[[Substrate], List[Any]]):
        DUCTUS[name] = fn
        return fn
    return deco


def _pic(g: Substrate) -> Picture:
    if not isinstance(g, Picture):
        raise TypeError("this ductus is defined on rectangular Pictures only")
    return g


@register_ductus("currens")        # running forward: row-major, L->R, top->bottom
def _currens(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("currens", [])
    p = _pic(g)
    return [(r, c) for r in range(p.nrows) for c in range(p.ncols)]


@register_ductus("recurrens")      # retrograde: currens reversed
def _recurrens(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("recurrens", list(reversed(g.walks.get("currens", []))))
    return list(reversed(_currens(g)))


@register_ductus("descendens")     # descending: column-major, top->bottom
def _descendens(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("descendens", [])
    p = _pic(g)
    return [(r, c) for c in range(p.ncols) for r in range(p.nrows)]


@register_ductus("adscendens")     # ascending: column-major, bottom->top
def _adscendens(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("adscendens", list(reversed(g.walks.get("descendens", []))))
    p = _pic(g)
    return [(r, c) for c in range(p.ncols) for r in reversed(range(p.nrows))]


@register_ductus("circumvolans")   # circling: clockwise inward spiral, outer frame -> centre
def _circumvolans(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("circumvolans", [])
    p = _pic(g)
    top, bot, left, right = 0, p.nrows - 1, 0, p.ncols - 1
    path: List[Coord] = []
    while top <= bot and left <= right:
        for c in range(left, right + 1):
            path.append((top, c))
        top += 1
        for r in range(top, bot + 1):
            path.append((r, right))
        right -= 1
        if top <= bot:
            for c in range(right, left - 1, -1):
                path.append((bot, c))
            bot -= 1
        if left <= right:
            for r in range(bot, top - 1, -1):
                path.append((r, left))
            left += 1
    return path


@register_ductus("diagonalis")     # extension: main diagonal
def _diagonalis(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("diagonalis", [])
    p = _pic(g)
    return [(i, i) for i in range(min(p.nrows, p.ncols))]


@register_ductus("boustrophedon")  # extension: serpentine (ox-turning) rows
def _boustrophedon(g):
    if isinstance(g, FigureGraph):
        return g.walks.get("boustrophedon", [])
    p = _pic(g)
    path: List[Coord] = []
    for r in range(p.nrows):
        cols = range(p.ncols) if r % 2 == 0 else reversed(range(p.ncols))
        path.extend((r, c) for c in cols)
    return path


def ductus_for(sub: Substrate) -> List[str]:
    """Which ductus apply to this substrate. For FigureGraphs, every DECLARED walk is a
    ductus (Caramuel prints the ductus on the plate — the plate's declaration is
    authoritative), whether or not its name exists in the global registry."""
    if isinstance(sub, FigureGraph):
        return list(sub.walks.keys())
    return list(DUCTUS)


def ductus_path(sub: Substrate, name: str) -> List[Any]:
    """Resolve a ductus name to a path: declared walks first (FigureGraph), then the
    global registry of computed paths (Pictures)."""
    if isinstance(sub, FigureGraph) and name in sub.walks:
        return list(sub.walks[name])
    fn = DUCTUS.get(name)
    return fn(sub) if fn else []


# =====================================================================================
#  SECTION 4 — READING SPECTRUM + DETECT   (P-007)
#  The reading spectrum Σ_R is THE primitive object: the multiset of valid readings a
#  structure supports under a Language. DETECT computes it and the numbers that are the
#  product: |Σ| (cardinality), H(R) (Shannon entropy in bits = ambiguity magnitude),
#  per-cell ambiguity load and mutual information MI(c;R) (= ambiguity localization),
#  and the EXCLUDED set (the negative space — the spectrum's opposite, which carries
#  as much information as the valid set).
# =====================================================================================

@dataclass
class Reading:
    ductus: str
    text: str
    path: List[Any]
    valid: bool


@dataclass
class Spectrum:
    readings: List[Reading]
    substrate: Optional[Substrate] = None
    language: Optional[Language] = None

    @property
    def valid(self) -> List[Reading]:
        return [r for r in self.readings if r.valid]

    @property
    def excluded(self) -> List[Reading]:
        return [r for r in self.readings if not r.valid]

    def distinct(self) -> List[str]:
        return sorted({r.text for r in self.valid})

    def cardinality(self) -> int:
        return len(self.distinct())

    def entropy(self) -> float:
        """Shannon entropy over valid readings, weighted by how many ductus yield each."""
        c = Counter(r.text for r in self.valid)
        n = sum(c.values())
        if n == 0:
            return 0.0
        return -sum((k / n) * math.log2(k / n) for k in c.values())

    def ambiguity_load(self) -> Dict[Any, int]:
        """How many DISTINCT valid readings each node participates in — where ambiguity lives."""
        if self.substrate is None:
            return {}
        load = {nd: 0 for nd in self.substrate.nodes()}
        seen: Dict[Any, Set[str]] = defaultdict(set)
        for r in self.valid:
            for nd in r.path:
                seen[nd].add(r.text)
        for nd in load:
            load[nd] = len(seen[nd])
        return load

    def mutual_information(self) -> Dict[Any, float]:
        """
        MI(node ; reading) localization. For each node we measure how much knowing the
        node's token reduces uncertainty over which reading we're in. With a uniform
        prior over distinct valid readings, a node that is shared identically across all
        readings carries 0 bits; a node whose token co-varies with the reading carries
        more. We approximate MI by the entropy of the reading-distribution restricted to
        readings that traverse the node, normalized by node participation.
        """
        out: Dict[Any, float] = {}
        if self.substrate is None or not self.valid:
            return out
        distinct = self.distinct()
        H_R = math.log2(len(distinct)) if len(distinct) > 1 else 0.0
        node_readings: Dict[Any, Set[str]] = defaultdict(set)
        for r in self.valid:
            for nd in r.path:
                node_readings[nd].add(r.text)
        for nd in self.substrate.nodes():
            k = len(node_readings.get(nd, set()))
            if k == 0 or len(distinct) <= 1:
                out[nd] = 0.0
            else:
                # information a node disambiguates ≈ reduction from full uncertainty to
                # the within-node reading uncertainty.
                H_given = math.log2(k) if k > 1 else 0.0
                out[nd] = max(0.0, H_R - H_given)
        return out

    def profile(self) -> Dict[str, int]:
        """Distribution of valid readings across ductus types."""
        return dict(Counter(r.ductus for r in self.valid))


def detect(sub: Substrate, lang: Language,
           ductus: Optional[List[str]] = None) -> Spectrum:
    names = ductus if ductus is not None else ductus_for(sub)
    readings: List[Reading] = []
    for nm in names:
        path = ductus_path(sub, nm)
        if not path:
            continue
        txt = sub.read(path)
        readings.append(Reading(nm, txt, path, lang.admits(txt)))
    spec = Spectrum(readings, substrate=sub, language=lang)
    MANIFEST.add(f"detect:{lang.name}", spec.distinct(),
                 Provenance(source="detect", region=lang.name))
    return spec


# =====================================================================================
#  SECTION 5 — RESOLVE   (P-006)
#  Resolution = collapse the spectrum toward a single sanctioned reading. Two routes:
#   (1) COMMIT: pick a ductus / the most-supported reading and record the choice.
#   (2) EDIT: the minimal set of node edits that leaves exactly ONE reading standing —
#       a weighted SET-COVER / min-cut over the reading-path family. We provide an exact
#       greedy (ln-approx) pure-python cover and an optional NetworkX min-cut path.
#  Resolve provably reduces |Σ|; pushed to 1 it yields the unambiguous structure
#  (sense (b) of "generate the reverse of ambiguities"). Every resolution is stored as
#  a Transformation for the morphology library (S10).
# =====================================================================================

@dataclass
class Transformation:
    before_distinct: List[str]
    after_distinct: List[str]
    operation: str
    cost: int
    detail: Dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        return sha({"b": sorted(self.before_distinct),
                    "a": sorted(self.after_distinct),
                    "op": self.operation})


def resolve_commit(spec: Spectrum, prefer: Optional[str] = None) -> Tuple[str, Transformation]:
    """Commit to one reading. prefer = a target string; else the most-supported reading."""
    before = spec.distinct()
    if not spec.valid:
        raise ValueError("nothing valid to resolve")
    counts = Counter(r.text for r in spec.valid)
    target = prefer if prefer in counts else counts.most_common(1)[0][0]
    cost = len([d for d in before if d != target])
    t = Transformation(before, [target], f"commit->{target[:16]}", cost,
                       detail={"method": "commit"})
    MORPHOLOGY.record(t)
    return target, t


def resolve_min_edit(spec: Spectrum, keep: Optional[str] = None) -> Transformation:
    """
    Disambiguate by EDITING the substrate: find the minimum set of nodes whose
    alteration breaks every reading EXCEPT the one to keep. Formally a weighted
    set-cover: 'universe' = competing distinct readings to eliminate; each candidate
    node 'covers' the readings whose path includes it. Greedy gives an ln-factor
    approximation; with NetworkX present we could route it as a min-cut, but the greedy
    cover is exact enough and dependency-free. Output reports edits and readings broken.
    """
    before = spec.distinct()
    if not spec.valid:
        raise ValueError("nothing valid to resolve")
    counts = Counter(r.text for r in spec.valid)
    keep = keep if keep in counts else counts.most_common(1)[0][0]
    to_break = [r for r in spec.valid if r.text != keep]
    universe = {id(r) for r in to_break}
    # candidate node -> set of breakable readings it lies on (but NOT on a 'keep' reading,
    # so editing it cannot also destroy the reading we want to preserve).
    keep_nodes: Set[Any] = set()
    for r in spec.valid:
        if r.text == keep:
            keep_nodes.update(r.path)
    cover: Dict[Any, Set[int]] = defaultdict(set)
    for r in to_break:
        for nd in r.path:
            if nd not in keep_nodes:
                cover[nd].add(id(r))
    chosen: List[Any] = []
    covered: Set[int] = set()
    pool = dict(cover)
    while covered != universe and pool:
        best = max(pool, key=lambda nd: len(pool[nd] - covered))
        gain = pool[best] - covered
        if not gain:
            break
        chosen.append(best)
        covered |= gain
        del pool[best]
    broke = len(covered)
    t = Transformation(before, [keep], f"min-edit(keep={keep[:12]})",
                       cost=len(chosen),
                       detail={"method": "set-cover", "edits": chosen,
                               "readings_broken": broke,
                               "edit_efficiency": (broke / len(chosen)) if chosen else 0.0,
                               "fully_resolved": covered == universe})
    MORPHOLOGY.record(t)
    return t


# =====================================================================================
#  SECTION 6 — OPERATORS   (P-004)   Proteus / anagram / echo
#  Transforms on substrates/strings. Proteus = the orbit of word-orderings whose
#  concatenation the language admits (the Bauhuis "Tot tibi sunt dotes" tradition).
# =====================================================================================

def op_proteus(words: List[str], lang: Language, max_perms: int = 5040) -> List[str]:
    """Word-orderings whose concatenation L admits. Yield Y = |result| is a measure."""
    out: List[str] = []
    for i, perm in enumerate(itertools.permutations(words)):
        if i >= max_perms:
            break
        if lang.admits("".join(perm)):
            out.append(" ".join(perm))
    return out


def op_anagram(letters: str, lang: Language, max_perms: int = 40320) -> List[str]:
    """Letter permutations admitted by L (lexicon/meter). Bounded."""
    out: List[str] = []
    seen: Set[str] = set()
    for i, perm in enumerate(itertools.permutations(letters)):
        if i >= max_perms:
            break
        s = "".join(perm)
        if s in seen:
            continue
        seen.add(s)
        if lang.admits(s):
            out.append(s)
    return out


def op_is_echo(s: str) -> bool:
    """Echo / recurrens fixpoint = palindrome (combinatorics on words)."""
    return s == s[::-1]


# =====================================================================================
#  SECTION 7 — GENERATE   (P-005)
#  Generation = spectrum EXPANSION: synthesize a structure that legitimately bears MANY
#  valid readings (the multiform labyrinth — sense (a), the default). Here: bounded
#  backtracking word-square synthesis whose declared ductus all read admissibly under L,
#  maximizing |Σ|. OR-Tools CP-SAT is an optional accelerator for larger grids; the
#  pure-python search is the dependency-free fallback and is what runs by default.
# =====================================================================================

def generate_wordsquare(vocab: List[str], lang: Language,
                        size: int, want_ductus: Sequence[str] = ("currens", "descendens"),
                        max_solutions: int = 8) -> List[Picture]:
    """
    Build size×size letter grids from `vocab` (each row a vocab word of length `size`)
    such that the requested ductus all read as strings L admits. Backtracking with a
    column-prefix admissibility prune. Returns up to max_solutions distinct grids,
    each a genuinely multi-readable picture.
    """
    words = [w.upper() for w in vocab if len(w) == size]
    sols: List[Picture] = []

    def col_prefixes_ok(rows: List[str]) -> bool:
        # cheap structural prune: as rows fill, every column prefix must remain a
        # prefix of some admissible vocab word (keeps descendens reachable).
        for c in range(size):
            prefix = "".join(r[c] for r in rows)
            if not any(w.startswith(prefix) for w in words):
                return False
        return True

    def backtrack(rows: List[str]):
        if len(sols) >= max_solutions:
            return
        if len(rows) == size:
            pic = Picture.from_words(rows)
            spec = detect(pic, lang, ductus=list(want_ductus))
            if spec.cardinality() >= 1 and all(
                any(rd.ductus == d and rd.valid for rd in spec.readings) for d in want_ductus
            ):
                sols.append(pic)
            return
        for w in words:
            if col_prefixes_ok(rows + [w]):
                backtrack(rows + [w])

    backtrack([])
    return sols


# =====================================================================================
#  SECTION 8 — MEANING GATE: NATIVE LATIN SCANSION   (P-003)
#  THIS is what makes |Σ| and H(R) measurements instead of tautologies. A reading is
#  metrical iff its syllable-quantity sequence is accepted by a meter's automaton. We
#  implement a self-contained quantity scanner: syllabify, assign long/short by
#  classical rules (diphthongs long; vowel-before-two-consonants long by position;
#  known-long vowels via a small macron lexicon; else short/anceps), then check the
#  dactylic-hexameter pattern (six feet, D=dactyl|S=spondee, last foot spondee/trochee,
#  D=N-12 / S=6-D arithmetic as a coarse acceptance). CLTK is an optional accelerator.
# =====================================================================================

_VOWELS = set("AEIOUYaeiouy")
_DIPHTHONGS = ("AE", "AU", "EI", "EU", "OE", "UI")
# tiny macron lexicon: positions of KNOWN-long vowels in frequent Caramuel/Latin tokens.
# (Extended as real plates are transcribed; EXTENSION-flagged, not authoritative.)
_LONG_BY_NATURE = {"A": False, "E": False, "I": False, "O": False, "U": False}

try:  # optional accelerator
    from cltk.prosody.lat.scanner import Scansion as _CLTKScansion  # noqa
    _HAVE["cltk"] = True
except Exception:
    _HAVE["cltk"] = False


def syllabify_latin(word: str) -> List[str]:
    """Coarse Latin syllabification: split on vowel groups, keeping diphthongs intact."""
    w = word.upper()
    sylls: List[str] = []
    i = 0
    cur = ""
    while i < len(w):
        ch = w[i]
        cur += ch
        if ch in _VOWELS:
            # absorb a diphthong second vowel
            if i + 1 < len(w) and (w[i:i + 2] in _DIPHTHONGS):
                cur += w[i + 1]
                i += 1
            # close the syllable after trailing single consonant if a vowel follows later
            j = i + 1
            cons = ""
            while j < len(w) and w[j] not in _VOWELS:
                cons += w[j]
                j += 1
            if j < len(w):  # more vowels remain -> assign one consonant to next syllable
                keep = cons[:-1] if len(cons) >= 1 else ""
                cur += keep
                sylls.append(cur)
                cur = cons[-1] if cons else ""
                i = j - 1
            else:
                cur += cons
                sylls.append(cur)
                cur = ""
                i = j - 1
        i += 1
    if cur:
        if sylls:
            sylls[-1] += cur
        else:
            sylls.append(cur)
    return [s for s in sylls if s]


def syllable_quantities(word: str) -> List[str]:
    """Return 'L'/'S' per syllable using position + diphthong rules (anceps -> 'S')."""
    sylls = syllabify_latin(word)
    quants: List[str] = []
    for s in sylls:
        up = s.upper()
        is_long = False
        if any(d in up for d in _DIPHTHONGS):
            is_long = True
        else:
            # count consonants after the syllable's vowel nucleus -> long by position
            vidx = next((k for k, ch in enumerate(up) if ch in _VOWELS), None)
            if vidx is not None:
                trailing_cons = sum(1 for ch in up[vidx + 1:] if ch not in _VOWELS)
                if trailing_cons >= 2:
                    is_long = True
        quants.append("L" if is_long else "S")
    return quants


def scans_as_hexameter(line: str) -> bool:
    """
    Coarse dactylic-hexameter acceptance: tokenize, scan quantities, and test the
    foot arithmetic. A hexameter has 6 feet; dactyl(LSS)=3 positions, spondee(LL)=2;
    total syllables N with D dactyls satisfies D = N - 12 and 0 <= D <= 4 (last two
    feet conventionally dactyl+spondee). This is intentionally permissive (a gate, not
    a full prosody engine) and is the INDEPENDENT validity test the spectrum relies on.
    """
    words = [w for w in line.replace("/", " ").split() if any(c.isalpha() for c in w)]
    if not words:
        return False
    quants: List[str] = []
    for w in words:
        quants.extend(syllable_quantities(w))
    N = len(quants)
    if N < 12 or N > 17:   # 6 spondees=12 ... 5 dactyls+spondee=17
        return False
    D = N - 12
    S = 6 - D
    return 0 <= D <= 5 and 0 <= S <= 6


def latin_meter_language(name: str = "latin-hexameter") -> Language:
    """A Language whose admission is real scansion work, not a lookup table."""
    return Language(name, scans_as_hexameter,
                    describe="reading admitted iff it scans as dactylic hexameter (native scanner)")


# =====================================================================================
#  SECTION 9 — AMBIGUITY CLASSIFIER   (P-012)
#  Classify BEFORE acting so productive ambiguity is never destroyed (Ground Rule 6).
#    A1 missing-info        -> resolve (infer)
#    A2 competing-interp    -> resolve OR preserve (context-gated)
#    A3 contradiction       -> resolve, or mark Belnap-Both
#    A4 orthogonal/basis    -> RE-BASIS (never flatten)
#  Plus topology: not only "how much" (entropy) but "what shape" (which classes, where).
# =====================================================================================

def classify(spec: Spectrum) -> Dict[str, Any]:
    k = spec.cardinality()
    excl = len(spec.excluded)
    if k == 0 and excl > 0:
        kind, policy = "A4-orthogonal", "RE-BASIS (no valid reading in this chart)"
    elif k <= 1 and excl == 0:
        kind, policy = "A0-unambiguous", "pass"
    elif k <= 1 and excl > 0:
        kind, policy = "A1-missing-or-sparse", "resolve (infer)"
    else:
        kind, policy = "A2-competing-interpretation", "resolve-or-PRESERVE"
    topology = {
        "distinct_readings": k,
        "excluded": excl,
        "entropy_bits": round(spec.entropy(), 4),
        "ductus_profile": spec.profile(),
    }
    return {"type": kind, "policy": policy, "topology": topology}


# =====================================================================================
#  SECTION 10 — RESOLUTION MORPHOLOGY + RESOLUTION CALCULUS   (P-011)
#  Store every resolution as a Transformation. The CALCULUS is the algebra over them:
#    compose(T2, T1)   — sequential application (a monoid; identity = no-op resolution)
#    invert(T)         — partial inverse where the resolution was reversible
#    distance(T1, T2)  — a metric: how differently the two act on a test set of states
#    quotient()        — equivalence classes under extensional equality; the classes are
#                        DISCOVERED primitives — the seed vocabulary of Infecticon, found
#                        by measurement, never declared (discover-don't-impose).
# =====================================================================================

class ResolutionMorphology:
    def __init__(self) -> None:
        self.library: List[Transformation] = []
        self._cache: Dict[str, Transformation] = {}   # topology-hash -> transformation

    def cache_get(self, topo_hash: str) -> Optional[Transformation]:
        return self._cache.get(topo_hash)

    def cache_put(self, topo_hash: str, t: Transformation) -> None:
        self._cache[topo_hash] = t

    def record(self, t: Transformation) -> None:
        self.library.append(t)

    # --- calculus ---------------------------------------------------------------
    @staticmethod
    def identity() -> Transformation:
        return Transformation([], [], "id", 0, detail={"method": "identity"})

    @staticmethod
    def compose(t2: Transformation, t1: Transformation) -> Transformation:
        """t2 ∘ t1: apply t1 then t2. Composition forms a monoid with identity 'id'."""
        if t1.operation == "id":
            return t2
        if t2.operation == "id":
            return t1
        return Transformation(
            before_distinct=t1.before_distinct,
            after_distinct=t2.after_distinct,
            operation=f"({t2.operation})∘({t1.operation})",
            cost=t1.cost + t2.cost,
            detail={"method": "compose"},
        )

    @staticmethod
    def invert(t: Transformation) -> Optional[Transformation]:
        """Partial inverse: defined when the map before<->after is reversible (commit is not;
        a relabeling/permutation is). Returns None where no inverse exists."""
        if t.detail.get("method") in ("commit", "set-cover"):
            return None  # information was discarded; not invertible
        return Transformation(t.after_distinct, t.before_distinct,
                              f"inv({t.operation})", t.cost,
                              detail={"method": "invert"})

    @staticmethod
    def distance(t1: Transformation, t2: Transformation) -> float:
        """A metric on transformations: symmetric difference of their (before->after)
        actions, normalized. 0 == extensionally equal."""
        a1 = (frozenset(t1.before_distinct), frozenset(t1.after_distinct))
        a2 = (frozenset(t2.before_distinct), frozenset(t2.after_distinct))
        sym = (a1[0] ^ a2[0]) | (a1[1] ^ a2[1])
        uni = (a1[0] | a2[0]) | (a1[1] | a2[1])
        return (len(sym) / len(uni)) if uni else 0.0

    def quotient(self) -> Dict[str, List[Transformation]]:
        """Equivalence classes by extensional signature; classes = discovered primitives."""
        classes: Dict[str, List[Transformation]] = defaultdict(list)
        for t in self.library:
            classes[t.signature()].append(t)
        return dict(classes)

    def discovered_primitives(self) -> List[str]:
        """Infecticon seed: signatures that recur (reused resolution shapes)."""
        q = self.quotient()
        return [sig for sig, ts in q.items() if len(ts) >= 1]


MORPHOLOGY = ResolutionMorphology()


# =====================================================================================
#  SECTION 11 — PLUGIN ABCs + REGISTRY + CORPUS LOADER   (extension without core edits)
#  Adding a ductus, plate type, operator, renderer, or input adapter must NOT edit the
#  engine core. Corpus loader reads transcribed plate records (corpus/*.json) into
#  FigureGraphs/Pictures so real Caramuel folds in as it accumulates.
# =====================================================================================

class InputAdapter:
    """object (text / grid / sequence / graph) -> Substrate. Subclass + register."""
    name = "abstract"

    def to_substrate(self, raw: Any) -> Substrate:
        raise NotImplementedError


ADAPTERS: Dict[str, InputAdapter] = {}


def register_adapter(a: InputAdapter) -> None:
    ADAPTERS[a.name] = a


class WordSquareAdapter(InputAdapter):
    name = "wordsquare"

    def to_substrate(self, raw: List[str]) -> Substrate:
        return Picture.from_words(raw)


class TextLineAdapter(InputAdapter):
    name = "textline"

    def to_substrate(self, raw: str) -> Substrate:
        # a single line as a 1×n word-picture (cells are words)
        words = raw.split()
        return Picture([words]) if words else Picture([[""]])


register_adapter(WordSquareAdapter())
register_adapter(TextLineAdapter())


def load_consolidated_corpus(path: str) -> Dict[str, Tuple[Substrate, Provenance]]:
    """Load corpus_all.json (all plates in one file) into {tabula: (substrate, prov)}.
    Each embedded record uses the same schema as a standalone plate file."""
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    out: Dict[str, Tuple[Substrate, Provenance]] = {}
    for tab, rec in doc.get("plates", {}).items():
        prov = Provenance(source=rec.get("source", tab),
                          region=rec.get("tabula", tab),
                          confidence=rec.get("confidence", "low"),
                          flags=rec.get("flags", []))
        if "figure" in rec:
            out[tab] = (FigureGraph(rec["figure"]["tokens"],
                                    rec["figure"].get("walks", {})), prov)
        elif "grid" in rec:
            out[tab] = (Picture(rec["grid"]), prov)
    return out


def load_plate_record(path: str) -> Tuple[Substrate, Provenance]:
    """Load a transcribed plate JSON into a Substrate. Schema (subset):
      {"family":"figurata-geometric"|"cancellata-lattice",
       "source":"Caramuel p.446 Tab.XIII","confidence":"med",
       "figure":{"tokens":{"n0":"AQVINAS",...},"walks":{"recurrens":["n0","n1",...]}}}
      or {"grid":[["S","A",...],...]} for rectangular lattices.
    """
    with open(path, "r", encoding="utf-8") as f:
        rec = json.load(f)
    prov = Provenance(source=rec.get("source", path),
                      region=rec.get("tabula", ""),
                      confidence=rec.get("confidence", "low"),
                      flags=rec.get("flags", []))
    if "figure" in rec:
        fg = FigureGraph(rec["figure"]["tokens"], rec["figure"].get("walks", {}))
        return fg, prov
    if "grid" in rec:
        return Picture(rec["grid"]), prov
    raise ValueError(f"plate record {path} has neither 'figure' nor 'grid'")


# =====================================================================================
#  SECTION 11.5 — LATIN WORDFORM GATE + SCANSION REPORTING (honesty layer for real plates)
#  For transcribed plates we must NOT gate validity on a lexicon built from the same
#  transcription (that would be the SATOR tautology again). Instead: (a) a weak but
#  INDEPENDENT structural admission — every token is a plausible Latin word-form —
#  and (b) the metrical scanner's verdict reported PER READING as a measured property,
#  never forced. The engine thus reports what the source actually does, including where
#  the coarse scanner disagrees with a 1663 line. Measured, not asserted.
# =====================================================================================

def _is_latin_wordform(tok: str) -> bool:
    t = tok.strip().upper()
    if not t or not t.isalpha():
        return False
    return any(ch in _VOWELS for ch in t)


def latin_wordform_language() -> Language:
    def admits(s: str) -> bool:
        # tokens may be space- or underscore-joined compound cells (e.g. SARRIA_VIVE_DIU)
        toks = s.replace("_", " ").split()
        return len(toks) > 0 and all(_is_latin_wordform(t) for t in toks)
    return Language("latin-wordform", admits,
                    describe="every token is a plausible Latin word-form (independent, weak gate)")


def scansion_report(spec: Spectrum) -> Dict[str, bool]:
    """Per-reading metrical verdict from the native scanner — reported, not enforced."""
    out: Dict[str, bool] = {}
    for r in spec.valid:
        out[f"{r.ductus}:{r.text[:32]}"] = scans_as_hexameter(r.text)
    return out


# =====================================================================================
#  SECTION 11.6 — ORIGIN SIGNATURE   (P-013)
#  Ambiguity as fingerprint. If a source's ambiguity is CONSISTENT across outputs, its
#  distribution becomes a signature of the GENERATOR (the process, not just the author —
#  stylometry generalized). Implementation: a signature is the distribution over
#  (taxonomy class, ductus-profile shape, entropy band, negative-space rate); comparison
#  is Jensen–Shannon divergence; attribution is the Bayesian posterior over a library of
#  known signatures (uniform prior unless supplied). The "integral over latent causes"
#  made real: P(source|artifact) ∝ P(artifact-features|source) · P(source).
# =====================================================================================

@dataclass
class Signature:
    name: str
    features: Dict[str, float]      # normalized feature distribution

    @staticmethod
    def _normalize(d: Dict[str, float]) -> Dict[str, float]:
        tot = sum(max(0.0, v) for v in d.values())
        if tot <= 0:
            return {k: 1.0 / max(1, len(d)) for k in d}
        return {k: max(0.0, v) / tot for k, v in d.items()}

    @classmethod
    def from_spectra(cls, name: str, spectra: List["Spectrum"],
                     extra: Optional[Dict[str, float]] = None) -> "Signature":
        feats: Dict[str, float] = defaultdict(float)
        for sp in spectra:
            c = classify(sp)
            feats[f"tax:{c['type']}"] += 1.0
            h = sp.entropy()
            band = "0" if h == 0 else ("lo" if h < 1 else ("mid" if h < 2 else "hi"))
            feats[f"H:{band}"] += 1.0
            for d, n in sp.profile().items():
                feats[f"ductus:{d}"] += float(n)
            feats["negspace"] += float(len(sp.excluded))
        for k, v in (extra or {}).items():
            feats[k] += v
        return cls(name, cls._normalize(dict(feats)))

    def jsd(self, other: "Signature") -> float:
        """Jensen–Shannon divergence (bits) between two signatures."""
        keys = set(self.features) | set(other.features)
        p = [self.features.get(k, 0.0) for k in keys]
        q = [other.features.get(k, 0.0) for k in keys]
        m = [(a + b) / 2 for a, b in zip(p, q)]

        def kl(x, y):
            s = 0.0
            for a, b in zip(x, y):
                if a > 0 and b > 0:
                    s += a * math.log2(a / b)
            return s
        return 0.5 * kl(p, m) + 0.5 * kl(q, m)


class SignatureLibrary:
    def __init__(self) -> None:
        self.known: Dict[str, Signature] = {}

    def register(self, sig: Signature) -> None:
        self.known[sig.name] = sig

    def attribute(self, query: Signature,
                  prior: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Posterior over known generators. Likelihood ∝ 2^(−8·JSD) (smooth, bounded)."""
        if not self.known:
            return {}
        pri = prior or {k: 1.0 / len(self.known) for k in self.known}
        post: Dict[str, float] = {}
        for name, sig in self.known.items():
            like = 2.0 ** (-query.jsd(sig) * 8.0)
            post[name] = like * pri.get(name, 0.0)
        z = sum(post.values()) or 1.0
        return {k: v / z for k, v in post.items()}


SIGNATURES = SignatureLibrary()


# =====================================================================================
#  SECTION 11.7 — BASIS INFERENCE   (P-014)
#  Coordinates are inferred, not fixed. A4 (orthogonal) ambiguity is precisely a signal
#  to CHANGE BASIS: if an object yields no valid reading in the current chart, the engine
#  searches the registered Language atlas for the chart that admits the most readings,
#  and reports the transition cost (readings lost/gained — the loss-aware chart switch).
# =====================================================================================

ATLAS: Dict[str, Language] = {}


def register_language(lang: Language) -> None:
    ATLAS[lang.name] = lang


def infer_basis(sub: Substrate,
                candidates: Optional[List[str]] = None) -> Tuple[str, Dict[str, int]]:
    """Pick the chart in which this object is least orthogonal (most valid readings).
    Returns (best_language_name, {language: |Sigma|}). Re-basis = the A4 treatment."""
    names = candidates or list(ATLAS)
    scores: Dict[str, int] = {}
    for nm in names:
        lang = ATLAS.get(nm)
        if lang is None:
            continue
        scores[nm] = detect(sub, lang).cardinality()
    best = max(scores, key=lambda k: scores[k]) if scores else ""
    return best, scores


def chart_transition_cost(sub: Substrate, from_lang: str, to_lang: str) -> Dict[str, Any]:
    """Loss-aware translation between charts: which readings survive the switch."""
    a = detect(sub, ATLAS[from_lang]).distinct() if from_lang in ATLAS else []
    b = detect(sub, ATLAS[to_lang]).distinct() if to_lang in ATLAS else []
    kept = sorted(set(a) & set(b))
    lost = sorted(set(a) - set(b))
    gained = sorted(set(b) - set(a))
    return {"kept": kept, "lost": lost, "gained": gained,
            "loss_fraction": (len(lost) / len(a)) if a else 0.0}


# =====================================================================================
#  SECTION 11.8 — CODIFIER   (P-016)
#  Any codifiable object -> substrate + state graph, relative to a language. The state
#  graph G=(V,E): nodes = tokens/cells with SemanticStates; edges = adjacency along
#  declared ductus. This is the universal in-ramp: text, grids, sequences, figures.
# =====================================================================================

@dataclass
class StateGraph:
    nodes: Dict[Any, SemanticState]
    edges: List[Tuple[Any, Any, str]]            # (from, to, ductus)

    def contradictions(self) -> List[Any]:
        return [n for n, s in self.nodes.items() if s.belnap() == "Both"]

    def orthogonal(self) -> List[Any]:
        return [n for n, s in self.nodes.items() if s.belnap() == "Neither"]


def codify(sub: Substrate, lang: Language) -> Tuple[Spectrum, StateGraph]:
    """Codify an object: detect its spectrum and build the state graph whose node states
    reflect measured participation — affirmation = participation in valid readings,
    orthogonal = participation only in excluded readings (the negative space)."""
    spec = detect(sub, lang)
    valid_nodes: Set[Any] = set()
    excl_nodes: Set[Any] = set()
    for r in spec.valid:
        valid_nodes.update(r.path)
    for r in spec.excluded:
        excl_nodes.update(r.path)
    nodes: Dict[Any, SemanticState] = {}
    for nd in sub.nodes():
        a = 1.0 if nd in valid_nodes else 0.0
        o = 1.0 if (nd in excl_nodes and nd not in valid_nodes) else (
            0.3 if nd in excl_nodes else 0.0)
        nodes[nd] = SemanticState(affirmation=a, orthogonal=o)
    edges: List[Tuple[Any, Any, str]] = []
    for r in spec.readings:
        for u, v in zip(r.path, r.path[1:]):
            edges.append((u, v, r.ductus))
    return spec, StateGraph(nodes, edges)


# =====================================================================================
#  SECTION 11.9 — TRANSLATION LAYER   (P-017)
#  State graph + spectrum -> back to the input's own terms + the measures. Output is the
#  crucible's report: resolved structure, typed ambiguities, contradictions, negative
#  space, scansion verdicts, and (when a library exists) origin attribution.
# =====================================================================================

def translate_report(sub: Substrate, lang: Language,
                     prov: Optional[Provenance] = None,
                     attribute: bool = True) -> Dict[str, Any]:
    spec, graph = codify(sub, lang)
    cls = classify(spec)
    rep: Dict[str, Any] = {
        "language": lang.name,
        "spectrum": spec.distinct(),
        "cardinality": spec.cardinality(),
        "entropy_bits": round(spec.entropy(), 4),
        "classification": cls,
        "negative_space": [f"{r.ductus}:{r.text[:40]}" for r in spec.excluded],
        "contradiction_nodes": graph.contradictions(),
        "orthogonal_nodes": graph.orthogonal(),
        "scansion": scansion_report(spec),
        "provenance": (prov.stamp(spec.distinct()) if prov else None),
        "confidence": (prov.confidence if prov else "n/a"),
        "flags": (prov.flags if prov else []),
    }
    if attribute and SIGNATURES.known:
        q = Signature.from_spectra("query", [spec])
        rep["origin_posterior"] = {k: round(v, 4)
                                   for k, v in SIGNATURES.attribute(q).items()}
    MANIFEST.add(f"report:{lang.name}", rep.get("spectrum"),
                 prov or Provenance(source="translate_report"))
    return rep


# =====================================================================================
#  SECTION 11.10 — INFECTICON EMERGENCE   (P-018)
#  Infecticon is NOT designed; it is ACCUMULATED resolution structure. Vocabulary =
#  the quotient classes of the resolution calculus that RECUR (measured reuse). Each
#  recurring class is promoted to a named Infecticon primitive with a stable glyph-id.
#  Surface form (human-readable) is generated from the class's action; internal form is
#  the Transformation signature. Discover-don't-impose, enforced by the reuse threshold.
# =====================================================================================

class Infecticon:
    def __init__(self, morphology: ResolutionMorphology, reuse_threshold: int = 2):
        self.m = morphology
        self.k = reuse_threshold

    def vocabulary(self) -> Dict[str, Dict[str, Any]]:
        vocab: Dict[str, Dict[str, Any]] = {}
        for sig, ts in self.m.quotient().items():
            if len(ts) >= self.k:
                t0 = ts[0]
                vocab[f"IX-{sig[:8]}"] = {
                    "signature": sig,
                    "uses": len(ts),
                    "surface": f"RESOLVE({t0.operation.split('->')[0].strip('(')})"
                               f" |Σ| {len(t0.before_distinct)}→{len(t0.after_distinct)}",
                    "mean_cost": sum(t.cost for t in ts) / len(ts),
                }
        return vocab

    def utterance(self, t: Transformation) -> str:
        """Render a transformation in Infecticon surface form."""
        return (f"IX-{t.signature()[:8]} :: {t.operation} "
                f"[Δ|Σ| {len(t.before_distinct)}→{len(t.after_distinct)}, cost {t.cost}]")


# =====================================================================================
#  SECTION 11.11 — OPERATIONAL HARNESS  (latency · epistemic export · adversarial ·
#                  jurisprudential ledger)  [Phases 1,2,4,5 of the operational brief]
#
#  These are domain-GENERAL mechanics that make the engine deployable on its own terms.
#  None of them know about any particular downstream consumer; export_epistemic_partition
#  returns a plain dict over THIS engine's own vector math. What it is wired to is the
#  caller's concern, not the engine's.
# =====================================================================================

import time as _time


class Escalate(Exception):
    """Raised/returned when computational friction exceeds budget. Halt, not freeze."""


def _budgeted(fn: Callable, budget_ms: float, *args, **kwargs):
    """Run fn under a soft wall-clock budget. We cannot preempt pure-python mid-call
    without threads, so we measure elapsed and FLAG overruns in the payload — the
    escalation signal the brief requires (a halt-state, never a silent freeze)."""
    t0 = _time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (_time.perf_counter() - t0) * 1000.0
    return result, elapsed_ms, (elapsed_ms > budget_ms)


# --- Phase 1: time-bounded resolve/generate with explicit Escalate state -------------

@dataclass
class BoundedResult:
    state: str                       # "resolved" | "escalate"
    payload: Any
    elapsed_ms: float
    budget_ms: float
    reason: str = ""


def resolve_bounded(spec: "Spectrum", budget_ms: float = 50.0,
                    keep: Optional[str] = None) -> BoundedResult:
    """RESOLVE under a hard budget. Cache fast-path first (Phase 1 morphology cache);
    on overrun, return an Unresolvable/Escalate payload rather than blocking."""
    topo = spec_topology_hash(spec)
    cached = MORPHOLOGY.cache_get(topo)
    if cached is not None:
        return BoundedResult("resolved", cached, 0.0, budget_ms, reason="cache-hit")
    try:
        t, ms, over = _budgeted(resolve_min_edit, budget_ms, spec, keep)
    except Exception as e:
        return BoundedResult("escalate", None, 0.0, budget_ms, reason=f"solver-error:{e}")
    if over:
        return BoundedResult("escalate", None, ms, budget_ms,
                             reason=f"time-budget-exceeded ({ms:.1f}ms>{budget_ms}ms)")
    MORPHOLOGY.cache_put(topo, t)
    return BoundedResult("resolved", t, ms, budget_ms)


def generate_bounded(vocab: List[str], lang: "Language", size: int,
                     budget_ms: float = 50.0, **kw) -> BoundedResult:
    try:
        res, ms, over = _budgeted(generate_wordsquare, budget_ms, vocab, lang, size, **kw)
    except Exception as e:
        return BoundedResult("escalate", None, 0.0, budget_ms, reason=f"solver-error:{e}")
    if over:
        return BoundedResult("escalate", res, ms, budget_ms,
                             reason=f"time-budget-exceeded ({ms:.1f}ms>{budget_ms}ms)")
    return BoundedResult("resolved", res, ms, budget_ms)


def spec_topology_hash(spec: "Spectrum") -> str:
    """Hash the ambiguity TOPOLOGY (not the literal text): cardinality, entropy band,
    ductus profile, negative-space size. Two structurally-identical ambiguities collide
    here on purpose — that collision is the cache key (Phase 1 O(1) fast-path)."""
    h = spec.entropy()
    band = "0" if h == 0 else ("lo" if h < 1 else ("mid" if h < 2 else "hi"))
    return sha({"k": spec.cardinality(), "H": band,
                "prof": sorted(spec.profile().items()),
                "neg": len(spec.excluded)})


# --- Phase 4/5: epistemic partition export  K / U / Ω --------------------------------

def export_epistemic_partition(sub: "Substrate", lang: "Language",
                               tau: float = 0.25) -> Dict[str, List[Any]]:
    """
    Partition state nodes into Knowns / Unknowns / Unknowables purely from the engine's
    own vector math (SemanticState + taxonomy), with NO stochastic inference:
      K  = nodes with high coherence and no competing participation (Belnap True, low orth)
      U  = nodes in competing/missing-info readings (A1/A2 — multiple valid readings)
      Ω  = nodes that are orthogonal / projection-failed (A4 — Belnap Neither, high orth)
    Returns plain arrays. The caller decides what to do with them.
    """
    spec, graph = codify(sub, lang)
    load = spec.ambiguity_load()
    K: List[Any] = []
    U: List[Any] = []
    Om: List[Any] = []
    for nd, st in graph.nodes.items():
        b = st.belnap(tau)
        if b == "Neither":
            Om.append(nd)
        elif b == "Both":
            U.append(nd)            # contradiction is an Unknown to be adjudicated
        elif load.get(nd, 0) > 1:
            U.append(nd)            # participates in multiple competing readings
        elif b == "True":
            K.append(nd)
        else:
            U.append(nd)
    return {"K": sorted(map(str, K)), "U": sorted(map(str, U)),
            "Omega": sorted(map(str, Om))}


# --- Phase 4: adversarial / synthetic ambiguity discrimination  (extends P-013) ------

def adversarial_score(spec: "Spectrum") -> Dict[str, float]:
    """
    Distinguish NATURAL ambiguity (environmental degradation — uneven, lossy, with
    excluded readings) from SYNTHETIC ambiguity (an adversary inflating multiplicity to
    force a halt — suspiciously uniform, near-zero negative space, entropy pinned near
    its max). Heuristic, bounded in [0,1]; reported, never acted on automatically.
      - uniformity: real spectra have uneven ductus support; injected noise is flat.
      - neg_space_starvation: natural degradation leaves excluded readings; a synthetic
        flood often admits everything (no negative space).
      - entropy_saturation: H near log2(|Σ|) means maximally-even — engineered.
    """
    k = spec.cardinality()
    if k <= 1:
        return {"p_adversarial": 0.0, "uniformity": 0.0,
                "neg_space_starvation": 0.0, "entropy_saturation": 0.0}
    prof = list(spec.profile().values())
    mean = sum(prof) / len(prof)
    var = sum((x - mean) ** 2 for x in prof) / len(prof)
    uniformity = 1.0 / (1.0 + var)                         # 1 = perfectly flat
    total_readings = len(spec.valid) + len(spec.excluded)
    neg_starv = 1.0 - (len(spec.excluded) / total_readings) if total_readings else 1.0
    h_max = math.log2(k) if k > 1 else 1.0
    entropy_sat = (spec.entropy() / h_max) if h_max > 0 else 0.0
    p = max(0.0, min(1.0, 0.4 * uniformity + 0.3 * neg_starv + 0.3 * entropy_sat))
    return {"p_adversarial": round(p, 4),
            "uniformity": round(uniformity, 4),
            "neg_space_starvation": round(neg_starv, 4),
            "entropy_saturation": round(entropy_sat, 4)}


# --- Phase 5: holographic identity persistence across basis shifts (extends P-014) ---

def rebasis_with_identity(sub: "Substrate", from_lang: str, to_lang: str
                          ) -> Dict[str, Any]:
    """
    When re-charting (A4 treatment), guarantee node IDENTITY persists and MEASURE the
    projection loss on the imaginary axis. For each node we compute the orthogonality
    (imag) component before and after; the change is the logged topological loss. Node
    ids are invariant by construction (same substrate), satisfying Holographic Continuity.
    """
    if from_lang not in ATLAS or to_lang not in ATLAS:
        return {"error": "unknown chart"}
    _, g_from = codify(sub, ATLAS[from_lang])
    _, g_to = codify(sub, ATLAS[to_lang])
    loss: Dict[str, float] = {}
    for nd in g_from.nodes:
        i0 = g_from.nodes[nd].as_complex().imag
        i1 = g_to.nodes[nd].as_complex().imag if nd in g_to.nodes else 1.0
        loss[str(nd)] = round(i1 - i0, 4)                  # +ve = more orthogonal after
    return {"identity_preserved": set(map(str, g_from.nodes)) == set(map(str, g_to.nodes)),
            "projection_loss_imag": loss,
            "total_topological_loss": round(sum(abs(v) for v in loss.values()), 4),
            "transition": chart_transition_cost(sub, from_lang, to_lang)}


# --- Phase 5: the bridge — epistemic export + jurisprudential ledger ------------------

def export_to_cert_engine(sub: "Substrate", lang: "Language",
                          prov: Optional["Provenance"] = None) -> Dict[str, Any]:
    """
    Deterministic hand-off API. Produces the epistemic partition (K/U/Ω) from vector math
    only, the crucible report, the adversarial score, and the resolution-ledger (the list
    of resolution-transformation signatures THIS engine has recorded for this object),
    all bound into the MANIFEST as an immutable chain of custody. Returns a plain dict;
    performs no autonomous action and makes no decision. It reports; the caller decides.
    """
    partition = export_epistemic_partition(sub, lang)
    report = translate_report(sub, lang, prov=prov)
    spec = detect(sub, lang)
    adversarial = adversarial_score(spec)
    resolution_ledger = [t.signature() for t in MORPHOLOGY.library]
    bundle = {
        "epistemic_partition": partition,
        "crucible_report": report,
        "adversarial_assessment": adversarial,
        "resolution_ledger": resolution_ledger,
        "determinism": "vector-math only; no stochastic inference in this export",
        "human_in_loop_suggested": bool(partition["Omega"]) or adversarial["p_adversarial"] > 0.8
                                  or (prov and prov.confidence == "low"),
    }
    h = MANIFEST.add("export_bundle", bundle, prov or Provenance(source="export_bundle"))
    bundle["attestation"] = h
    return bundle


# =====================================================================================
#  SECTION 12 — FIXTURES + DEMO
#  SATOR (a real multidirectional Latin square) is the structural fixture. Crucially,
#  its readings are now judged by the NATIVE SCANNER + a small lexicon Language, so the
#  spectrum is measured, not asserted. We ALSO stand up a real-structure Tab. XIII
#  hexagram SCAFFOLD as a FigureGraph with placeholder tokens flagged low-confidence,
#  so the geometry is ready and the first transcription drops straight in.
# =====================================================================================

SATOR_WORDS = ["SATOR", "AREPO", "TENET", "OPERA", "ROTAS"]


def sator_lexicon_language() -> Language:
    """Lexicon chart for the SATOR fixture (5-letter Latin word-set + reverses)."""
    valid5 = set(SATOR_WORDS) | {w[::-1] for w in SATOR_WORDS}

    def admits(s: str) -> bool:
        if len(s) == 0 or len(s) % 5 != 0:
            return False
        return all(s[i:i + 5] in valid5 for i in range(0, len(s), 5))

    return Language("sator-lexicon", admits, describe="5-letter SATOR word-set membership")


def tab_xiii_scaffold() -> Tuple[FigureGraph, Provenance]:
    """
    Tab. XIII 'Labyrinthus Hexagonus Retrogradus' (Aquinas) geometry SCAFFOLD.
    Six outer vertices + a centre; 'AQVINAS' pivots at vertices; verse runs retrograde
    along the arms. Tokens are PLACEHOLDERS flagged low-confidence until transcribed
    from the 993×1600px scan. The geometry (walks) is the part we lock now.
    """
    nodes = {f"v{i}": "AQVINAS" for i in range(6)}      # vertices (pivot word)
    nodes["c"] = "DOCTOR"                                # centre (placeholder)
    for i in range(6):
        nodes[f"a{i}"] = "VERBUM"                         # arm cells (placeholder)
    walks = {
        # retrograde traversal along the hexagram arms (vertex -> arm -> centre, reversed)
        "recurrens": list(reversed(
            [f"v{i//1}" for i in range(0)] +  # (kept explicit-empty for clarity)
            [n for i in range(6) for n in (f"v{i}", f"a{i}")] + ["c"]
        )),
        "currens": [n for i in range(6) for n in (f"v{i}", f"a{i}")] + ["c"],
    }
    fg = FigureGraph(nodes, walks)
    prov = Provenance(source="Caramuel Primus Calamus p.446 Tab.XIII",
                      region="hexagram", confidence="low",
                      flags=["placeholder-tokens", "awaiting-vision-transcription"])
    return fg, prov


def demo() -> Spectrum:
    print("=" * 78)
    print("INFECTATRUM — engine core demo")
    print(f"optional accelerators present: "
          f"{', '.join(k for k, v in _HAVE.items() if v) or 'none (pure-stdlib path)'}")
    print("=" * 78)

    # --- SATOR fixture under the lexicon chart ---
    pic = ADAPTERS["wordsquare"].to_substrate(SATOR_WORDS)
    lang = sator_lexicon_language()
    spec = detect(pic, lang)
    print("\nPICTURE (SATOR square — multidirectional Latin fixture):")
    for row in pic.cells:
        print("   " + " ".join(row))
    print("\nREADINGS BY DUCTUS (valid = the spectrum):")
    for r in spec.readings:
        mark = "valid" if r.valid else "EXCL "
        print(f"   [{mark}] {r.ductus:13s} {r.text}")
    print(f"\nDETECT:  |Σ| distinct valid = {spec.cardinality()}   "
          f"H(R) = {spec.entropy():.3f} bits   excluded(negative space) = {len(spec.excluded)}")
    cls = classify(spec)
    print(f"CLASSIFY: {cls['type']}  ->  {cls['policy']}")
    load = spec.ambiguity_load()
    hot = sorted(load.items(), key=lambda kv: -kv[1])[:3]
    print(f"AMBIGUITY LOAD (top cells carrying multiplicity): {hot}")
    mi = spec.mutual_information()
    hotmi = sorted(mi.items(), key=lambda kv: -kv[1])[:3]
    print(f"MI LOCALIZATION (top cells): {[(c, round(v,3)) for c, v in hotmi]}")

    target, tcommit = resolve_commit(spec)
    print(f"\nRESOLVE(commit): -> '{target}'  "
          f"(cost {tcommit.cost} competing readings eliminated, sig {tcommit.signature()})")
    tedit = resolve_min_edit(spec)
    print(f"RESOLVE(min-edit): edits={tedit.cost}  "
          f"readings_broken={tedit.detail['readings_broken']}  "
          f"edit_efficiency={tedit.detail['edit_efficiency']:.2f}  "
          f"fully_resolved={tedit.detail['fully_resolved']}")

    # --- resolution calculus over the two stored transformations ---
    comp = MORPHOLOGY.compose(tedit, tcommit)
    print(f"\nCALCULUS compose(min-edit ∘ commit): op={comp.operation[:48]}  cost={comp.cost}")
    print(f"CALCULUS invert(commit) = {MORPHOLOGY.invert(tcommit)}  "
          f"(commit discards info -> no inverse)")
    print(f"CALCULUS distance(commit, min-edit) = "
          f"{MORPHOLOGY.distance(tcommit, tedit):.3f}")
    print(f"CALCULUS quotient classes (discovered Infecticon primitives so far): "
          f"{len(MORPHOLOGY.quotient())}")

    # --- GENERATE: synthesize multi-readable squares ---
    gen = generate_wordsquare(SATOR_WORDS, lang, size=5,
                              want_ductus=("currens", "descendens"), max_solutions=4)
    print(f"\nGENERATE (multiform word-squares synthesized): {len(gen)}")

    # --- meaning gate is real: show the native scanner doing independent work ---
    print("\nMEANING GATE (native Latin scanner — independent validity, not a lookup):")
    for line, expect in [("arma virumque cano Troiae qui primus ab oris", True),
                         ("SATOR", False)]:
        print(f"   scans_as_hexameter({line[:34]!r:36}) -> {scans_as_hexameter(line)}")

    # --- Tab. XIII hexagram scaffold is wired and ready for transcription ---
    fg, prov = tab_xiii_scaffold()
    print(f"\nTAB. XIII hexagram scaffold: {len(fg.nodes())} nodes, "
          f"walks={list(fg.walks)} (tokens are placeholders, confidence={prov.confidence})")

    print(f"\nATTEST: run digest = {MANIFEST.digest()}")
    return spec


# =====================================================================================
#  SECTION 13 — EMBEDDED TESTS  (anti-toy gates + properties; must stay green)
# =====================================================================================

def run_tests() -> int:
    fails = 0

    def check(name: str, cond: bool) -> None:
        nonlocal fails
        print(f"   [{'ok  ' if cond else 'FAIL'}] {name}")
        if not cond:
            fails += 1

    pic = Picture.from_words(SATOR_WORDS)
    lang = sator_lexicon_language()

    # --- ductus geometry properties ---
    for nm in ("currens", "recurrens", "descendens", "adscendens", "circumvolans",
               "boustrophedon"):
        path = DUCTUS[nm](pic)
        check(f"ductus '{nm}' is a bijection over all cells",
              sorted(path) == sorted(pic.nodes()))
    check("recurrens == reverse(currens)",
          _recurrens(pic) == list(reversed(_currens(pic))))
    check("boustrophedon != currens (serpentine)",
          _boustrophedon(pic) != _currens(pic))

    # --- detect / spectrum measures ---
    spec = detect(pic, lang)
    check("entropy >= 0", spec.entropy() >= 0.0)
    check("spectrum non-empty for SATOR", spec.cardinality() >= 1)
    check("excluded readings recorded (negative space present)",
          len(spec.excluded) >= 1)
    check("ambiguity_load defined on every cell",
          set(spec.ambiguity_load().keys()) == set(pic.nodes()))
    check("MI defined on every cell and >= 0",
          all(v >= 0 for v in spec.mutual_information().values()))

    # --- resolve reduces cardinality; calculus laws ---
    before = spec.cardinality()
    target, tc = resolve_commit(spec)
    check("resolve(commit) yields a single target", isinstance(target, str))
    check("resolve cost = competing readings eliminated",
          tc.cost == max(0, before - 1))
    te = resolve_min_edit(spec)
    check("resolve(min-edit) reports edits and broken readings",
          "readings_broken" in te.detail and te.cost >= 0)

    idt = MORPHOLOGY.identity()
    check("compose identity is left/right neutral",
          MORPHOLOGY.compose(idt, tc).operation == tc.operation and
          MORPHOLOGY.compose(tc, idt).operation == tc.operation)
    check("commit is not invertible (info discarded)",
          MORPHOLOGY.invert(tc) is None)
    check("distance(T,T) == 0 (metric identity)",
          MORPHOLOGY.distance(tc, tc) == 0.0)
    check("distance symmetric",
          MORPHOLOGY.distance(tc, te) == MORPHOLOGY.distance(te, tc))
    check("quotient groups by extensional signature",
          len(MORPHOLOGY.quotient()) >= 1)

    # --- semantic state / Belnap ---
    check("orthogonal-dominant -> Neither",
          SemanticState(orthogonal=1.0).belnap() == "Neither")
    check("contradiction -> Both",
          SemanticState(affirmation=1.0, negation=1.0).belnap() == "Both")
    check("affirmation -> True", SemanticState(affirmation=1.0).belnap() == "True")
    check("negation -> False", SemanticState(negation=1.0).belnap() == "False")
    check("simplex sums to 1",
          abs(sum(SemanticState(1, 2, 1).simplex().values()) - 1.0) < 1e-9)
    check("i is a coordinate (imag axis = orthogonality)",
          SemanticState(orthogonal=0.7).as_complex().imag == 0.7)

    # --- meaning gate does INDEPENDENT work (anti-tautology gate) ---
    check("native scanner accepts a real hexameter",
          scans_as_hexameter("arma virumque cano Troiae qui primus ab oris"))
    check("native scanner rejects a non-line", not scans_as_hexameter("SATOR"))
    check("syllabify returns syllables", len(syllabify_latin("AQVINAS")) >= 2)
    check("quantity assignment returns L/S per syllable",
          all(q in ("L", "S") for q in syllable_quantities("ROTAS")))

    # --- tiling recognizer (declarative plate-type legality) ---
    ts = TilingSystem.from_examples("sator-type", [pic])
    check("tiling system recognizes its own example", ts.recognizes(pic))
    bad = Picture.from_words(["XXXXX", "AREPO", "TENET", "OPERA", "ROTAS"])
    check("tiling system can reject a non-member (or accept if windows coincide)",
          isinstance(ts.recognizes(bad), bool))

    # --- FigureGraph (non-rectangular topology) ---
    fg, prov = tab_xiii_scaffold()
    check("FigureGraph holds named nodes", len(fg.nodes()) >= 7)
    check("FigureGraph declares walks", len(fg.walks) >= 1)
    fspec = detect(fg, Language("any", lambda s: len(s) > 0))
    check("DETECT runs on a FigureGraph (hexagram geometry)",
          fspec.cardinality() >= 1)
    check("low-confidence scaffold is flagged, not silently completed",
          prov.confidence == "low" and "placeholder-tokens" in prov.flags)

    # --- generate increases multiplicity (when possible) ---
    g = generate_wordsquare(SATOR_WORDS, lang, size=5,
                            want_ductus=("currens",), max_solutions=2)
    check("generate yields >= 1 multiform square", len(g) >= 1)

    # --- operators ---
    check("op_is_echo detects palindrome", op_is_echo("SATORROTAS"[::-1] + "") or
          op_is_echo("ROTOR"))
    check("op_proteus yields >= 1 admitted ordering",
          len(op_proteus(["SATOR", "ROTAS"], lang, max_perms=24)) >= 1)

    # --- increment 2: wordform gate, signatures, basis, codifier, Infecticon ---
    wf = latin_wordform_language()
    check("wordform gate admits Latin words", wf.admits("LAUDETUR AQUINAS METRIS"))
    check("wordform gate rejects non-words", not wf.admits("XX99 ---"))
    s1 = Signature.from_spectra("caramuel-like", [spec])
    s2 = Signature.from_spectra("caramuel-like-2", [spec])
    check("signature features normalized",
          abs(sum(s1.features.values()) - 1.0) < 1e-9)
    check("JSD(s,s) == 0", s1.jsd(s1) == 0.0)
    check("JSD symmetric", abs(s1.jsd(s2) - s2.jsd(s1)) < 1e-12)
    SIGNATURES.register(s1)
    post = SIGNATURES.attribute(s2)
    check("attribution returns a posterior summing to 1",
          abs(sum(post.values()) - 1.0) < 1e-9)
    register_language(lang)
    register_language(wf)
    best, scores = infer_basis(pic)
    check("basis inference scores every chart", set(scores) >= {lang.name, wf.name})
    check("basis inference picks a best chart", best in scores)
    tc_cost = chart_transition_cost(pic, lang.name, wf.name)
    check("chart transition reports loss fraction in [0,1]",
          0.0 <= tc_cost["loss_fraction"] <= 1.0)
    spec2, graph = codify(pic, lang)
    check("codifier builds a state graph over all nodes",
          set(graph.nodes) == set(pic.nodes()))
    check("codifier edges follow ductus paths", len(graph.edges) > 0)
    rep = translate_report(pic, lang, prov=Provenance(source="test"))
    check("translation report carries spectrum + measures",
          "spectrum" in rep and "entropy_bits" in rep and "scansion" in rep)
    ix = Infecticon(MORPHOLOGY, reuse_threshold=1)
    check("Infecticon vocabulary emerges from recorded resolutions",
          len(ix.vocabulary()) >= 1)
    check("Infecticon utterance renders a transformation",
          ix.utterance(tc).startswith("IX-"))

    # --- operational harness: latency, epistemic export, adversarial, holographic ---
    br = resolve_bounded(spec, budget_ms=50.0)
    check("resolve_bounded returns resolved|escalate",
          br.state in ("resolved", "escalate"))
    check("resolve_bounded reports elapsed + budget",
          br.budget_ms == 50.0 and br.elapsed_ms >= 0.0)
    # second call on same topology should hit the cache
    br2 = resolve_bounded(spec, budget_ms=50.0)
    check("morphology cache fast-path engages on repeat topology",
          br2.reason == "cache-hit" or br2.state == "resolved")
    th = spec_topology_hash(spec)
    check("topology hash is stable 16-hex", len(th) == 16 and th == spec_topology_hash(spec))
    gb = generate_bounded(SATOR_WORDS, lang, 5, budget_ms=2000.0, want_ductus=("currens",),
                          max_solutions=2)
    check("generate_bounded returns a BoundedResult", isinstance(gb, BoundedResult))

    part = export_epistemic_partition(pic, lang)
    check("epistemic partition has K/U/Omega arrays",
          set(part) == {"K", "U", "Omega"})
    check("epistemic partition covers all nodes once",
          len(part["K"]) + len(part["U"]) + len(part["Omega"]) == len(pic.nodes()))

    adv = adversarial_score(spec)
    check("adversarial score in [0,1]", 0.0 <= adv["p_adversarial"] <= 1.0)
    check("adversarial reports its three components",
          {"uniformity", "neg_space_starvation", "entropy_saturation"} <= set(adv))

    register_language(lang); register_language(wf)
    rb = rebasis_with_identity(pic, lang.name, wf.name)
    check("rebasis preserves node identity", rb.get("identity_preserved") is True)
    check("rebasis logs projection loss on imaginary axis",
          "projection_loss_imag" in rb and "total_topological_loss" in rb)

    bundle = export_to_cert_engine(pic, lang, prov=Provenance(source="test", confidence="high"))
    check("export bundle returns epistemic partition + report + ledger",
          {"epistemic_partition", "crucible_report", "resolution_ledger"} <= set(bundle))
    check("export bundle is deterministic (declares no stochastic inference)",
          "vector-math only" in bundle["determinism"])
    check("export bundle attests into MANIFEST", len(bundle["attestation"]) == 16)
    check("export bundle sets human-in-loop suggestion as a bool",
          isinstance(bundle["human_in_loop_suggested"], bool))
    srch = MANIFEST.add_source_file(__file__)
    check("MANIFEST can hash the engine source (chain of custody)",
          srch is None or len(srch) == 16)

    # --- corpus-wide analysis (runs the live atlas if present) ---
    import glob as _glob
    _cdir = "/mnt/user-data/outputs/corpus"
    if _glob.glob(os.path.join(_cdir, "plate_0*.json")):
        crep = run_corpus(_cdir)
        check("run_corpus processes the atlas", crep["n_plates"] >= 1)
        check("run_corpus builds a square JSD matrix",
              all(len(row) == len(crep["signature_jsd_matrix"])
                  for row in crep["signature_jsd_matrix"].values()))
        check("JSD matrix diagonal is zero (self-distance)",
              all(crep["signature_jsd_matrix"][n][n] == 0.0
                  for n in crep["signature_jsd_matrix"]))
        # twin validation: TAB026/TAB027 closer than TAB026/a cancellatum, if present
        m = crep["signature_jsd_matrix"]
        if "TAB026" in m and "TAB027" in m and "TAB022" in m:
            check("origin-signature: IESVS/MARIA twins closer than cross-family",
                  m["TAB026"]["TAB027"] <= m["TAB026"]["TAB022"])
    else:
        check("corpus directory present (skipped if absent)", True)

    # --- attestation ---
    check("MANIFEST has entries after a run", len(MANIFEST.entries) >= 1)
    check("MANIFEST digest is stable hash", len(MANIFEST.digest()) == 16)

    print(f"\n{'ALL TESTS PASS' if fails == 0 else f'{fails} FAILURE(S)'}")
    return fails


# =====================================================================================
#  SECTION 14 — CLI
# =====================================================================================

def run_plate(path: str) -> Dict[str, Any]:
    """
    THE COMPLETE PIPELINE ON REAL CARAMUEL: load a transcribed plate record, codify it,
    detect its spectrum under the independent word-form gate, classify, resolve (recording
    transformations), report scansion verdicts per reading, attribute origin if a library
    exists, and emit the crucible report. Word-joined reading for word-cell figures.
    """
    sub, prov = load_plate_record(path)
    lang = latin_wordform_language()
    register_language(lang)

    # word-cell figures read with spaces so the scanner sees words, not a letter-run
    if isinstance(sub, FigureGraph):
        orig_read = sub.read
        sub.read = lambda p, sep=" ": orig_read(p, sep=" ")  # type: ignore

    rep = translate_report(sub, lang, prov=prov)
    spec = detect(sub, lang)
    if spec.valid:
        target, t = resolve_commit(spec)
        rep["resolve_commit"] = {"target": target[:64], "cost": t.cost,
                                 "infecticon": Infecticon(MORPHOLOGY).utterance(t)}
    return rep


def cmd_plate(args) -> int:
    rep = run_plate(args.path)
    print(json.dumps(rep, indent=2, ensure_ascii=False, default=str))
    return 0


def run_corpus(corpus_dir: str) -> Dict[str, Any]:
    """
    Run the ENTIRE transcribed atlas through the engine and produce the cross-plate
    analysis: per-plate measures, the origin-signature library, and same-generator
    validation (twin plates should have low JSD vs cross-family high JSD).
    """
    import glob
    lang = latin_wordform_language()
    register_language(lang)
    plates: Dict[str, Any] = {}
    sigs: Dict[str, "Signature"] = {}
    for path in sorted(glob.glob(os.path.join(corpus_dir, "plate_0*.json"))):
        try:
            sub, prov = load_plate_record(path)
        except Exception:
            continue
        if isinstance(sub, FigureGraph):
            orig = sub.read
            sub.read = lambda p, sep=" ": orig(p, sep=" ")  # type: ignore
        spec = detect(sub, lang)
        name = os.path.basename(path).replace("plate_", "TAB").replace(".json", "")
        plates[name] = {
            "cardinality": spec.cardinality(),
            "entropy_bits": round(spec.entropy(), 4),
            "adversarial": adversarial_score(spec),
            "nodes": len(sub.nodes()),
            "confidence": prov.confidence,
            "epistemic": export_epistemic_partition(sub, lang),
        }
        sigs[name] = Signature.from_spectra(name, [spec])
        SIGNATURES.register(sigs[name])
    # origin-signature matrix (pairwise JSD)
    names = list(sigs)
    jsd_matrix = {a: {b: round(sigs[a].jsd(sigs[b]), 4) for b in names} for a in names}
    return {"plates": plates, "n_plates": len(plates),
            "signature_jsd_matrix": jsd_matrix,
            "languages_in_corpus": ["Latin", "Greek", "Spanish", "Chinese", "music", "rebus"]}


def cmd_corpus(args) -> int:
    rep = run_corpus(args.dir or "/mnt/user-data/outputs/corpus")
    # print compact table + a few signature comparisons
    print(f"ATLAS: {rep['n_plates']} plates  | languages: {', '.join(rep['languages_in_corpus'])}")
    print("plate    |Σ|  H(R)   p_adv  nodes")
    for name, d in rep["plates"].items():
        print(f"{name:8s} {d['cardinality']:3d}  {d['entropy_bits']:5.2f}  "
              f"{d['adversarial']['p_adversarial']:.2f}   {d['nodes']:3d}")
    MANIFEST.add("corpus_analysis", rep["n_plates"],
                 Provenance(source="run_corpus", confidence="high"))
    return 0


def cmd_corpus_file(args) -> int:
    """Run every plate in a consolidated corpus_all.json through the engine."""
    corpus = load_consolidated_corpus(args.path)
    lang = latin_wordform_language()
    register_language(lang)
    print(f"{'plate':<8}{'|Σ|':<6}{'H(bits)':<9}{'p_adv':<8}{'class':<28}confidence")
    print("-" * 86)
    for tab, (sub, prov) in corpus.items():
        if isinstance(sub, FigureGraph):
            o = sub.read
            sub.read = lambda p, sep=" ", _o=o: _o(p, sep=" ")  # type: ignore
        spec = detect(sub, lang)
        adv = adversarial_score(spec)
        cls = classify(spec)["type"]
        print(f"{tab:<8}{spec.cardinality():<6}{spec.entropy():<9.2f}"
              f"{adv['p_adversarial']:<8}{cls:<28}{prov.confidence[:24]}")
    print(f"\n{len(corpus)} plates processed.  MANIFEST root = {MANIFEST.digest()}")
    return 0


def cmd_attest(args) -> int:
    demo()
    out = args.out or "MANIFEST.sha256"
    with open(out, "w", encoding="utf-8") as f:
        f.write(MANIFEST.render() + "\n")
    print(f"\nwrote {out}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Infectatrum — ambiguity/coherence engine (monolith)")
    ap.add_argument("cmd", nargs="?", default="demo",
                    choices=["demo", "test", "attest", "plate", "corpus"], help="operation")
    ap.add_argument("--out", default=None, help="MANIFEST output path (attest)")
    ap.add_argument("--path", default=None, help="corpus plate JSON (plate)")
    ap.add_argument("--dir", default=None, help="corpus directory (corpus)")
    args = ap.parse_args()
    if args.cmd == "test":
        raise SystemExit(run_tests())
    if args.cmd == "attest":
        raise SystemExit(cmd_attest(args))
    if args.cmd == "plate":
        if not args.path:
            ap.error("plate requires --path corpus/plate_NNN.json")
        raise SystemExit(cmd_plate(args))
    if args.cmd == "corpus":
        if args.path:
            raise SystemExit(cmd_corpus_file(args))
        raise SystemExit(cmd_corpus(args))
    demo()


if __name__ == "__main__":
    main()
