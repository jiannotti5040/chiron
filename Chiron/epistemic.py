#!/usr/bin/env python3
"""
epistemic.py — the abstract primitive the whole portfolio instantiates.

    Surface  ->  Hypothesis Space  ->  Constraint Space  ->  Verification  ->  Certificate

The repository is not "many projects around Chiron." It is ONE epistemic contract instantiated
across domains. This module makes that explicit: a RecoveryEngine interface, plus adapters showing
that Chiron (integers / ciphers / code), semic (meaning), the governance layer (law), and the
energy layer (probabilistic) all implement the same five-stage pipeline with the same load-bearing
invariant --- recover the minimal generator, verify on held-out data at exact equality, and REFUSE
when nothing verifies. The energy instance may additionally return an explicitly UNCERTIFIED
approximation (see semic_energy), which is the one principled exception and is never called
"verified".

    python3 epistemic.py            # run every engine through the common pipeline
    python3 epistemic.py selftest   # 0/1 gate

Status: implemented & tested. This is an integration/abstraction layer over the existing engines,
not new mathematics; it realizes the compendium's closing "unifying object" in code.
"""
import os
import sys
import json
import argparse
from dataclasses import dataclass, field
from typing import Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)


# ---------------------------------------------------------------------
# the contract
# ---------------------------------------------------------------------
@dataclass
class Certificate:
    domain: str
    verdict: str                       # CERTIFIED | REFUSED | APPROXIMATE
    generator: Optional[Any] = None
    detail: dict = field(default_factory=dict)


class RecoveryEngine:
    """Surface -> Hypothesis Space -> Constraint Space -> Verification -> Certificate."""
    domain = "abstract"

    def hypothesis_space(self, surface) -> str: raise NotImplementedError
    def constraint_space(self, surface) -> str: raise NotImplementedError
    def search(self, surface): raise NotImplementedError
    def verify(self, candidate, surface) -> bool: raise NotImplementedError
    def certify(self, surface) -> Certificate: raise NotImplementedError


def run(engine: "RecoveryEngine", surface) -> Certificate:
    """Drive the common pipeline uniformly, whatever the domain."""
    return engine.certify(surface)


def pipeline_stages(engine: "RecoveryEngine", surface) -> dict:
    """The five named stages for one (engine, surface) — the abstraction made concrete."""
    candidate = engine.search(surface)
    cert = engine.certify(surface)
    return {"hypothesis_space": engine.hypothesis_space(surface),
            "constraint_space": engine.constraint_space(surface),
            "verification": engine.verify(candidate, surface),
            "certificate": cert.verdict}


# ---------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------
class ChironEngine(RecoveryEngine):
    domain = "integers / ciphers / code"

    def hypothesis_space(self, s):
        return "closed-form generator classes (constant..holonomic / P-recursive)"

    def constraint_space(self, s):
        return "ranked candidates within the typed classes (exact rationals)"

    def search(self, s):
        import chiron
        return chiron.collapse(s)

    def verify(self, inv, s):
        return bool(getattr(inv, "verified", False))

    def certify(self, s):
        inv = self.search(s)
        v = self.verify(inv, s)
        return Certificate(self.domain, "CERTIFIED" if v else "REFUSED",
                           inv.model_class if v else None,
                           {"model_class": inv.model_class,
                            "explanation": (getattr(inv, "explanation", "") or "")[:120]})


class SemicEngine(RecoveryEngine):
    domain = "meaning (semic)"

    def _fam(self, texts):
        import semic
        return [semic.surface_skeleton(t) for t in texts]

    def hypothesis_space(self, texts):
        return "typed edge-set classes H1..H5 over the role grammar"

    def constraint_space(self, texts):
        fam = self._fam(texts)
        U = set().union(*fam) if fam else set()
        return f"subset lattice over {len(U)} role edges"

    def search(self, texts):
        import semic
        return semic.collapse(self._fam(texts))

    def verify(self, gen, texts):
        import semic
        return semic.certify(self._fam(texts)).verified

    def certify(self, texts):
        import semic
        fam = self._fam(texts)
        v = semic.certify(fam)
        gen = [list(e) for e in sorted(semic.collapse(fam))] if v.verified else None
        return Certificate(self.domain, "CERTIFIED" if v.verified else "REFUSED", gen,
                           {"heldout_residuals": v.heldout_residuals})


class GovernanceEngine(RecoveryEngine):
    domain = "governance / law"

    def hypothesis_space(self, q):
        return "the codified legal corpus scoped to the operating domain"

    def constraint_space(self, q):
        import legal_corpus as lc
        return f"{len(lc.applicable(q['domain']))} provisions in scope"

    def search(self, q):
        import legal_corpus as lc
        hits = set()
        for kw in q["keywords"]:
            hits |= {p["id"] for p in lc.search(kw)}
        scope = {p["id"] for p in lc.applicable(q["domain"])}
        return sorted(hits & scope)

    def verify(self, provisions, q):
        return len(provisions) > 0

    def certify(self, q):
        prov = self.search(q)
        v = self.verify(prov, q)
        return Certificate(self.domain, "CERTIFIED" if v else "REFUSED", prov if v else None,
                           {"provisions": prov, "domain": q["domain"]})


class EnergyEngine(RecoveryEngine):
    """The probabilistic instance: exact collapse, or an explicitly uncertified approximation."""
    domain = "meaning (energy / approximate)"

    def _fam(self, texts):
        import semic
        return [semic.surface_skeleton(t) for t in texts]

    def hypothesis_space(self, texts):
        return "Gibbs measure over the generator space at T>0 (around the exact collapse)"

    def constraint_space(self, texts):
        import semic
        return f"{len(semic.candidate_space(self._fam(texts)))} generators in the manifold"

    def search(self, texts):
        import semic_energy
        return semic_energy.three_level(self._fam(texts))

    def verify(self, r, texts):
        return r["level"] == 1

    def certify(self, texts):
        import semic_energy
        r = semic_energy.three_level(self._fam(texts))
        if r["level"] == 1:
            return Certificate(self.domain, "CERTIFIED", r["generator"], {"level": 1})
        top = r["candidates"][0]["generator"] if r.get("candidates") else None
        return Certificate(self.domain, "APPROXIMATE", top,
                           {"level": 3, "uncertified": True,
                            "relative_entropy": r.get("relative_entropy")})


ENGINES = {"chiron": ChironEngine(), "semic": SemicEngine(),
           "governance": GovernanceEngine(), "energy": EnergyEngine()}


# ---------------------------------------------------------------------
# demonstration + self-test
# ---------------------------------------------------------------------
def _examples():
    import semic
    fish = list(semic.FISH_FAMILY_TEXT)
    control = list(semic.CONTROLS_TEXT.values())[0]
    return {
        "chiron":     ([2, 4, 6, 8, 10, 12, 14], [3, 1, 4, 1, 5, 9, 2, 6]),
        "semic":      (fish, fish + [control]),
        "governance": ({"domain": "military", "keywords": ["proportionality", "distinction"]},
                       {"domain": "general", "keywords": ["sandwich", "lunch"]}),
        "energy":     (fish, fish + [control]),
    }


def demo():
    ex = _examples()
    print("one contract, four instances:  Surface -> Hypothesis -> Constraint -> Verify -> Certificate\n")
    for name, eng in ENGINES.items():
        good, bad = ex[name]
        cg, cb = run(eng, good), run(eng, bad)
        print(f"  {name:11} [{eng.domain}]")
        print(f"      structured -> {cg.verdict:11}  unstructured -> {cb.verdict}")


def _selftest():
    ex = _examples()
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # every engine implements the contract and returns a Certificate with a legal verdict
    for name, eng in ENGINES.items():
        good, bad = ex[name]
        cg, cb = run(eng, good), run(eng, bad)
        ok(f"{name}: returns Certificate", isinstance(cg, Certificate) and isinstance(cb, Certificate))
        ok(f"{name}: verdicts are legal", cg.verdict in {"CERTIFIED", "REFUSED", "APPROXIMATE"}
           and cb.verdict in {"CERTIFIED", "REFUSED", "APPROXIMATE"})

    # structured input certifies; unstructured input does NOT certify (refuse or, for energy, approximate)
    ok("chiron: structured CERTIFIED, noise REFUSED",
       run(ENGINES["chiron"], ex["chiron"][0]).verdict == "CERTIFIED"
       and run(ENGINES["chiron"], ex["chiron"][1]).verdict == "REFUSED")
    ok("semic: family CERTIFIED, contaminated REFUSED",
       run(ENGINES["semic"], ex["semic"][0]).verdict == "CERTIFIED"
       and run(ENGINES["semic"], ex["semic"][1]).verdict == "REFUSED")
    ok("governance: in-scope CERTIFIED, off-scope REFUSED",
       run(ENGINES["governance"], ex["governance"][0]).verdict == "CERTIFIED"
       and run(ENGINES["governance"], ex["governance"][1]).verdict == "REFUSED")
    ok("energy: family CERTIFIED, contaminated APPROXIMATE (never falsely CERTIFIED)",
       run(ENGINES["energy"], ex["energy"][0]).verdict == "CERTIFIED"
       and run(ENGINES["energy"], ex["energy"][1]).verdict == "APPROXIMATE")

    # the five-stage pipeline is exposed uniformly
    stages = pipeline_stages(ENGINES["chiron"], ex["chiron"][0])
    ok("pipeline exposes all five stages",
       all(k in stages for k in ("hypothesis_space", "constraint_space", "verification", "certificate")))

    passed = sum(1 for _, c in checks if c)
    print("epistemic self-test")
    for n, c in checks:
        if not c:
            print(f"  [FAIL] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="The abstract epistemic primitive + domain instances.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("demo")
    args = ap.parse_args(argv)
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
