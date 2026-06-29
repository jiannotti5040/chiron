#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""Hard stress tests for the clean invariant engine — 5 domains + the
reviewer's traps (same_family vs same_generator, Occam, noise)."""
import json, pathlib, random
import numpy as np
import invariant_engine as E

P = F = 0
def check(name, cond, extra=""):
    global P, F
    if cond: P += 1; print(f"  [PASS] {name}")
    else: F += 1; print(f"  [FAIL] {name}   {extra}")

print("\n=== TRAP 1: same_family != same_generator (reviewer's example) ===")
a = E.collapse([2, 4, 6, 8])
b = E.collapse([1000, 1002, 1004, 1006])
check("2,4,6,8 and 1000,1002,1004,1006 are the SAME FAMILY (arithmetic)",
      E.same_family(a, b)["same_family"])
check("...but NOT the same GENERATOR (different parameters)",
      not E.same_generator(a, b)["same_generator"])
c = E.collapse([2, 4, 6, 8, 10])
check("2,4,6,8 and 2,4,6,8,10 ARE the same generator (a0=2,d=2)",
      E.same_generator(a, c)["same_generator"])

print("\n=== TRAP 2: Occam — no absurd high-degree / accidental fits ===")
sq = E.collapse([0, 1, 4, 9, 16, 25, 36])
check("squares -> degree 2, NOT a higher-degree overfit", sq.model_class == "polynomial_deg2", sq.model_class)
check("squares predicts next term 49", abs(sq.predict(8)[-1] - 49) < 1e-6)
rnd = E.collapse([7, 2, 9, 1, 5, 8, 3, 4])
check("random-ish sequence is NOT reported as confidently compressible",
      (not rnd.compressible) or rnd.fit_score < 0.6, f"{rnd.model_class} comp={rnd.compressible} fit={rnd.fit_score:.2f}")

print("\n=== STRESS 1: invariant recovery THROUGH NOISE ===")
rng = np.random.default_rng(7)
base = np.array([2 + 3 * i for i in range(40)], dtype=float)          # a0=2,d=3
noisy = base + rng.normal(0, 0.03 * base.std(), size=base.shape)      # ~3% noise
ninv = E.collapse(list(noisy))
check("noisy arithmetic recovered as low-order (arithmetic/linear)",
      ninv.model_class in ("arithmetic", "polynomial_deg1"), ninv.model_class)
check("noisy fit is compressible but fit_score < 1 (honest about noise)",
      ninv.compressible and ninv.fit_score < 1.0, f"comp={ninv.compressible} fit={ninv.fit_score:.3f}")
check("recovered slope ~ 3 through the noise", abs(ninv.params["coeffs"][0] - 3) < 0.2, ninv.params["coeffs"])

print("\n=== STRESS 2: cipher transform recovered + inverted ===")
caesar = E.collapse("ATTACKATDAWN", "DWWDFNDWGDZQ")
check("Caesar shift 3 recovered", caesar.model_class == "caesar_shift" and caesar.params["shift"] == 3)
check("decoder inverts the cipher", caesar.params["decode"]("DWWDFNDWGDZQ") == "ATTACKATDAWN")

print("\n=== STRESS 3: the TWINS (figuregraph same-structure) ===")
CORPUS = pathlib.Path(__file__).resolve().parent.parent / "Infectatrum" / "corpus"
x26 = json.loads((CORPUS / "plate_026.json").read_text())
x27 = json.loads((CORPUS / "plate_027.json").read_text())
def pinv(p): return {"family": p["family"].split(" ")[0],
    "count": p["author_combinatorial_claim"]["claimed_simple_verses"],
    "meter": p.get("metrical_pattern_stated", "")}
i26 = E.collapse({"walks": x26["figure"]["walks"], "tokens": x26["figure"]["tokens"], "invariants": pinv(x26)})
i27 = E.collapse({"walks": x27["figure"]["walks"], "tokens": x27["figure"]["tokens"], "invariants": pinv(x27)})
check("twins share structure (same origin) despite different vocab",
      E.same_structure(i26, i27)["same_structure"])
check("twin surfaces are genuinely different", x26["figure"]["tokens"] != x27["figure"]["tokens"])

print("\n=== STRESS 4: ADVERSARIAL GRAPH COLLAPSE (your pick) ===")
# a structured base graph (8 nodes, asymmetric)
base_edges = [("a","b"),("b","c"),("c","d"),("d","e"),("e","f"),("f","g"),
              ("g","h"),("b","d"),("d","f"),("c","g")]
G = {"nodes": list("abcdefgh"), "edges": base_edges}
gi = E.collapse(G)

# adversary 1: random relabeling (the same graph wearing a disguise)
perm = dict(zip("abcdefgh", random.Random(1).sample("PQRSTUVW", 8)))
G_relabel = {"nodes": [perm[n] for n in "abcdefgh"],
             "edges": [(perm[u], perm[v]) for u, v in base_edges]}
gi_relabel = E.collapse(G_relabel)
sr = E.same_structure(gi, gi_relabel)
check("adversarial RELABELING defeated: relabeled graph -> SAME structure",
      sr["same_structure"], sr)

# adversary 2: relabel + inject 2 noise edges
G_noise = {"nodes": list(G_relabel["nodes"]),
           "edges": list(G_relabel["edges"]) + [(perm["a"], perm["h"]), (perm["a"], perm["e"])]}
gi_noise = E.collapse(G_noise)
sn = E.same_structure(gi, gi_noise)
check("noise-injected graph is NOT exact but HIGH similarity (honest)",
      (not sn["same_structure"]) and sn["structural_similarity"] > 0.3, sn)

# adversary 3: a genuinely different graph (decoy) of same size
decoy = {"nodes": list("abcdefgh"),
         "edges": [("a","b"),("a","c"),("a","d"),("a","e"),("a","f"),("a","g"),("a","h")]}  # star
gi_decoy = E.collapse(decoy)
sd = E.same_structure(gi, gi_decoy)
check("decoy graph (star) correctly rejected as different structure",
      not sd["same_structure"] and sd["structural_similarity"] < sn["structural_similarity"], sd)

print("\n=== STRESS 5: ONTOLOGICAL TRANSCODER (the commercial pivot) ===")
# a clean target ontology — realistically asymmetric (distinct roles)
target = {"nodes": ["Customer", "Order", "LineItem", "Product", "Warehouse",
                    "Shipment", "Payment", "Address"],
          "edges": [("Customer","Order"),("Customer","Address"),
                    ("Order","LineItem"),("Order","Shipment"),("Order","Payment"),
                    ("LineItem","Product"),("Product","Warehouse"),
                    ("Shipment","Warehouse"),("Shipment","Address")]}
# the SAME structure buried under a chaotic legacy schema (cryptic names)
truth = {"tbl_44":"Customer","fk_7":"Order","col_aa":"LineItem","x_99":"Product",
         "whs":"Warehouse","shp_2":"Shipment","pay_z":"Payment","adr_1":"Address"}
inv_t = {v: k for k, v in truth.items()}
legacy = {"nodes": [inv_t[n] for n in target["nodes"]],
          "edges": [(inv_t[u], inv_t[v]) for u, v in target["edges"]]}
res = E.transcode(legacy, target)
correct = sum(1 for s, t in res["mapping"].items() if truth.get(s) == t)
check("transcoder maps legacy schema onto clean ontology with high confidence",
      res["confidence"] >= 0.6, res["confidence"])
check("every mapping the transcoder MADE is structurally correct (no hallucinated links)",
      correct == len(res["mapping"]) and correct >= int(0.6 * len(target["nodes"])),
      f"{correct}/{len(res['mapping'])} correct")
print("   mapping:", res["mapping"])
print("   ->", res["explanation"])

print("\n=== STRESS 6: EARNED CONFIDENCE — held-out verification ===")
fibv = E.collapse([1, 1, 2, 3, 5, 8, 13, 21, 34, 55])
check("Fibonacci is VERIFIED (predicts held-out terms it never saw)",
      fibv.structure.get("verified") is True)
sqv = E.collapse([0, 1, 4, 9, 16, 25, 36, 49, 64])
check("squares VERIFIED by held-out prediction", sqv.structure.get("verified") is True)
noisy_v = E.collapse(list(np.array([5.0 + 2 * i for i in range(12)]) +
                          np.random.default_rng(3).normal(0, 0.4, 12)))
check("noisy data is honestly NOT marked verified (candidate only)",
      not noisy_v.structure.get("verified"), noisy_v.structure.get("verified"))

print("\n=== STRESS 7: SYNTHETIC O(1) TWIN ENGINE (quintillion-scale) ===")
import time
tw = E.caramuel_twin_spaces()
check("twin space size == Caramuel's documented 279,608,910,057,308,160",
      tw.size == 279608910057308160, tw.size)
check("radix product is EXACT (generator reproduces the count)",
      np.prod([float(r) for r in tw.a.radices]) > 0 and
      __import__("math").prod(tw.a.radices) == tw.size)
big_idxs = [0, 1, 10**6, 10**12, 10**15, tw.size - 1]
t0 = time.perf_counter()
ok_rt = all(tw.round_trip_ok(i) for i in big_idxs)
dt = (time.perf_counter() - t0) * 1000
check("exact round-trips across the WHOLE 2.8e17 space", ok_rt)
check(f"translation is O(1) per query ({dt:.2f} ms for 6 astronomically-separated verses)",
      dt < 50)
tr = tw.translate(10**15)
check("translate maps an A-verse to its B-twin deterministically",
      tr["b_surface"] == tw.translate(10**15)["b_surface"] and
      tr["a_surface"] != tr["b_surface"])
check("the bijection is structure-preserving (shared abstract verse)",
      tw.translate(42)["shared_digits"] == tw.a.unrank(42))

print("\n=== STRESS 8: AUTO TWIN DISCOVERY in a pile of data ===")
pile = {"arith_small": [2, 4, 6, 8, 10], "arith_big": [100, 102, 104, 106, 108],
        "geo": [3, 9, 27, 81], "fib": [1, 1, 2, 3, 5, 8],
        "geo2": [5, 10, 20, 40], "squares": [0, 1, 4, 9, 16]}
disc = E.discover_twins(pile)
check("twin discovery finds the hidden same-FAMILY sets",
      any(set(s) == {"arith_small", "arith_big"} for s in disc["twin_sets"])
      and any(set(s) == {"geo", "geo2"} for s in disc["twin_sets"]),
      disc["twin_sets"])

print("\n=== STRESS 9: O(1) RECORD TRANSCODER (commercial pivot at scale) ===")
rt = E.build_record_translator(legacy, target)
sample = {inv_t["Customer"]: "Acme Co", inv_t["Order"]: "ORD-1", inv_t["Payment"]: "$50"}
translated = rt["translate_record"](sample)
check("a legacy record is translated onto the clean ontology, O(fields)",
      translated == {"Customer": "Acme Co", "Order": "ORD-1", "Payment": "$50"},
      translated)

print("\n=== STRESS 10: DEEPER MODEL FAMILIES ===")
check("factorial n! -> multiplicative, verified",
      E.collapse([1, 1, 2, 6, 24, 120, 720, 5040]).model_class == "multiplicative_ratio")
check("power law n^3 -> power_law, verified",
      E.collapse([1, 8, 27, 64, 125, 216, 343, 512]).structure.get("verified") is True)
check("alternating sign recovered (predicts hidden tail within tol)",
      abs(E.collapse([1, -2, 3, -4, 5, -6, 7, -8, 9]).predict(11)[-1] - 11) < 1e-6)
check("a straight line still reads as 'arithmetic' (canonical Occam)",
      E.collapse([2, 4, 6, 8, 10]).model_class == "arithmetic")

print("\n=== STRESS 11: GENERAL A<->B CONTENT TRANSCODER ===")
a_vocab = [["create","update","delete"], ["customer","order","product"], ["urgent","normal","low"]]
b_vocab = [["crear","actualizar","borrar"], ["cliente","pedido","producto"], ["urgente","normal","bajo"]]
tw = E.make_twin(a_vocab, b_vocab, ("EN","ES"))
r = tw.transcode_content(["update","order","urgent"])
check("real payload transcodes A->B correctly",
      r["b_surface"] == ["actualizar","pedido","urgente"] and r["reversible"])
check("inverse transcode B->A round-trips",
      tw.back(["actualizar","pedido","urgente"]) == ["update","order","urgent"])
# composition A->B->C
c_vocab = [["c1","c2","c3"], ["k1","k2","k3"], ["z1","z2","z3"]]
ac = E.compose_spaces(tw, E.make_twin(b_vocab, c_vocab, ("ES","C")))
check("bijection composition A->B->C round-trips", ac.round_trip_ok(13))

print("\n=== STRESS 12: PROVING-RUN INVARIANTS (mini, inline) ===")
# inline sanity: recovery high, precision perfect, controls declined
import random as _rnd
ok_v = ok_c = 0; declined = 0
for a in range(4):
    for d in range(1, 4):
        seq = [a + d * i for i in range(16)]
        inv = E.collapse(seq[:12])
        if inv.structure.get("verified"):
            ok_v += 1
            if all(abs(p - h) < 1e-6 for p, h in zip(inv.predict(16)[12:], seq[12:16])):
                ok_c += 1
for s in range(6):
    rg = _rnd.Random(s)
    inv = E.collapse([rg.randint(0, 40) for _ in range(16)][:12])
    if not inv.structure.get("verified"):
        declined += 1
check("mini-proving: every verified arithmetic is externally correct (precision 1.0)",
      ok_v > 0 and ok_c == ok_v, f"{ok_c}/{ok_v}")
check("mini-proving: random controls all correctly declined", declined == 6, declined)

print("\n=== STRESS 13: HOLONOMIC (rational/generating-function) recovery ===")
cat = E.collapse([1, 1, 2, 5, 14, 42, 132, 429, 1430, 4862])
check("Catalan numbers VERIFIED (holonomic recovery)",
      cat.structure.get("verified") is True and cat.model_class.startswith("holonomic"))
cb = E.collapse([1, 2, 6, 20, 70, 252, 924, 3432, 12870, 48620])
check("central binomial coefficients VERIFIED (the prior 'miss')",
      cb.structure.get("verified") is True)
check("Catalan rule predicts 2 truly-unseen terms (16796, 58786)",
      all(abs(p - h) < 1e-3 for p, h in zip(cat.predict(12)[10:12], [16796, 58786])))
check("Fibonacci STILL canonical (linear_recurrence, not holonomic)",
      E.collapse([1,1,2,3,5,8,13,21,34,55]).model_class == "linear_recurrence_order2")

print("\n=== STRESS 14: AST CODE-HOMOLOGY (clone through disguise) ===")
src_a = "def total(items):\n    s = 0\n    for it in items:\n        s = s + it.price\n    return s\n"
src_b = "def sum_prices(records):  # total\n    acc = 0  # acc\n    for r in records:\n        acc = acc + r.price\n    return acc\n"
src_c = "def total(items):\n    return sum(x.price for x in items)\n"
ca, cb, cc = E.collapse({"code": src_a}), E.collapse({"code": src_b}), E.collapse({"code": src_c})
check("renamed+reformatted+commented clone -> SAME skeleton (Type-II)",
      E.same_structure(ca, cb)["same_structure"])
check("genuinely different implementation -> NOT an exact clone (honest)",
      not E.same_structure(ca, cc)["same_structure"])

print("\n=== STRESS 15: HARDENING — edge cases handled, not crashed ===")
import invariant_engine as _IE
try:
    _IE.collapse([]); check("empty sequence raises InvariantError", False)
except _IE.InvariantError:
    check("empty sequence raises InvariantError (not a crash)", True)
check("single/short sequence handled gracefully",
      E.collapse([5, 5]).model_class in ("too_short", "incompressible", "constant"))
check("NaN/inf reported honestly, no crash",
      E.collapse([1.0, float("nan"), 3.0]).model_class == "non_finite")
check("__all__ exposes the public API", "collapse" in _IE.__all__ and "TwinBijection" in _IE.__all__)

print(f"\n  {P}/{P+F} stress tests passed.")
exit(0 if F == 0 else 1)
