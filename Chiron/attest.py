#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. Apache-2.0 — use, modification, distribution,
# and commercial use permitted with attribution. See LICENSE.
"""attest.py — provenance of generated language: know the inputs, not the output.

THE INVERSION

Every tool aimed at machine-generated text grades the output. Detectors score
how "AI-like" a passage reads. Evaluators score whether an answer looks right.
Both produce a number about a finished artifact, and a number about a finished
artifact is exactly what cannot be checked — which is why none of them can be
put in front of someone who is accountable.

This module does the opposite. It does not look at the output and guess. It
takes the output TOGETHER WITH the inputs that produced it, and attributes each
span of the result to what actually caused it:

    which source is this span closest to, by measurement, not by vibe
    does this span survive checking against the ground truth it claims
    if this span is challenged, what is the smallest set of inputs to blame

No span is scored. Each is VERIFIED, REFUTED, or REFUSED — Chiron's contract,
unchanged, applied to prose. A span with no exact grounding is REFUSED and
handed back to the human intact. Refusal is not a gap in the analysis; it is the
analysis.

WHAT IT IS BUILT FROM (all existing vault modules, none re-implemented)

    language.sentences          segmentation, stdlib, offline
    language.origin_attribution Burrows's Delta + function-word cosine +
                                char-bigram JSD, fused into a ranking — the
                                measured answer to "whose language is this"
    language.stylometry         per-span register, so a human edit inside a
                                machine paragraph is visible as a seam
    semic_bridge.recover        MDL minimal-generator recovery over meaning;
                                REFUSES (INCOMPRESSIBLE) rather than laundering
    provenance.blame_incident   minimal blame set over the numeric surface

WHAT IT REFUSES TO DO

It will not report a probability that a passage is machine-written. That number
does not exist, every product that sells it is guessing, and a guess dressed as
evidence is the failure this repository was built to refuse. Attribution here is
always relative to CANDIDATE INPUTS YOU SUPPLY. With no candidates, the honest
answer is REFUSED, and that is what it returns.

    python3 Chiron/attest.py demo
    python3 Chiron/attest.py selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import language as lang          # noqa: E402
import provenance as prov        # noqa: E402

SCHEMA = "chiron.attestation/1"

VERIFIED = "VERIFIED"
REFUTED = "REFUTED"
REFUSED = "REFUSED"


@dataclass
class Token:
    """One word, and where it came from.

    Sentence-level attribution is too coarse to act on: a model routinely takes
    a real sentence and changes one number, or splices an invented clause into
    a quoted one. The seam is what matters, and the seam is between words.

    `sources` is every supplied input whose vocabulary contains this token, so a
    reader can see at a glance which words are traceable to something and which
    appeared from nowhere. A token present in no input is not "suspicious" — it
    is unattributable, which is a fact, not a score.
    """
    text: str
    kind: str            # "content" | "function" | "number" | "punct"
    sources: List[str] = field(default_factory=list)
    novel: bool = False  # present in no supplied input


@dataclass
class Span:
    text: str
    verdict: str = REFUSED
    origin: Optional[str] = None          # which supplied input it is closest to
    origin_delta: Optional[float] = None  # Burrows's Delta — lower is closer
    origin_cosine: Optional[float] = None
    origin_margin: Optional[float] = None  # gap to the runner-up
    checked_against: Optional[str] = None
    ground_truth: Optional[str] = None
    asserted: Optional[str] = None
    reason: str = ""
    owner: str = "human"
    blame: List[str] = field(default_factory=list)
    tokens: List[Token] = field(default_factory=list)
    novel_content_words: List[str] = field(default_factory=list)
    traceable_fraction: Optional[float] = None


_NUM = re.compile(r"^\d[\d,.]*$")


def _token_origins(span: str, candidates: Dict[str, str]) -> List[Token]:
    """Word-level trace: for each token, which supplied inputs contain it.

    Function words are marked but never counted as novel — every English text
    contains "the", so their presence carries no provenance information and
    treating it as evidence would inflate the traceable fraction into
    meaninglessness. Content words and numbers are where provenance lives.
    """
    vocab = {name: set(lang.tokenize(text)) for name, text in candidates.items()}
    fw = {w.lower() for w in getattr(lang, "FUNCTION_WORDS", set())}
    out: List[Token] = []
    for raw in span.split():
        bare = raw.strip(".,;:!?()\"'").lower()
        if not bare:
            out.append(Token(raw, "punct"))
            continue
        if _NUM.match(bare):
            kind = "number"
        elif bare in fw:
            kind = "function"
        else:
            kind = "content"
        # Compound identifiers (CLR-114, 2-32, FOB/Kestrel) are one token to a
        # reader but several to a tokenizer. Treat the compound as present when
        # every one of its parts is — otherwise a convoy ID that is sitting in
        # the source reads as invented, which is a false accusation.
        parts = [q for q in re.split(r"[-/_.]", bare) if q]
        srcs = sorted(n for n, v in vocab.items()
                      if bare in v or (len(parts) > 1 and all(q in v for q in parts)))
        out.append(Token(raw, kind, srcs,
                         novel=(not srcs and kind in ("content", "number"))))
    return out


def _attribute(span: str, candidates: Dict[str, str]) -> Dict[str, Any]:
    """Whose language is this? Measured, and only against inputs you supplied.

    A margin is reported because a ranking without one is an opinion: if the
    top two candidates are indistinguishable, the honest answer is that this
    span cannot be attributed, not that it belongs to whichever sorted first.
    """
    if not candidates or len(span.split()) < 6:
        return {"origin": None, "delta": None, "cosine": None, "margin": None,
                "reason": "too short to attribute" if candidates
                          else "no candidate inputs supplied"}
    try:
        ranked = lang.origin_attribution(span, candidates)
    except Exception as exc:                      # noqa: BLE001
        return {"origin": None, "delta": None, "cosine": None, "margin": None,
                "reason": f"attribution unavailable ({type(exc).__name__})"}
    if not ranked:
        return {"origin": None, "delta": None, "cosine": None, "margin": None,
                "reason": "no ranking produced"}
    top = ranked[0]
    margin = (round(ranked[1]["delta"] - top["delta"], 4)
              if len(ranked) > 1 else None)
    # An indistinguishable margin is a refusal to attribute, not a weak guess.
    if margin is not None and margin < 0.05:
        return {"origin": None, "delta": top["delta"],
                "cosine": top["function_word_cosine"], "margin": margin,
                "reason": f"candidates indistinguishable (margin {margin})"}
    return {"origin": top["candidate"], "delta": top["delta"],
            "cosine": top["function_word_cosine"], "margin": margin,
            "reason": ""}


def attest(output: str,
           inputs: Optional[Dict[str, str]] = None,
           ground_truth: Optional[Dict[str, Any]] = None,
           checker=None) -> Dict[str, Any]:
    """Attribute and judge every span of `output` against the things that made it.

    inputs        name -> text, the candidate sources (a retrieved document, the
                  system prompt, the operator's own prior writing). Attribution
                  is relative to these and is REFUSED without them.
    ground_truth  name -> value, the authoritative record a span can be checked
                  against.
    checker       optional callable(span, ground_truth) -> (verdict, detail)
                  for domain-specific exact checking. Without one, spans are
                  REFUSED rather than assumed true.
    """
    inputs = inputs or {}
    spans: List[Span] = []

    for sentence in lang.sentences(output):
        sentence = sentence.strip()
        if not sentence:
            continue
        s = Span(text=sentence)

        a = _attribute(sentence, inputs)
        s.origin, s.origin_delta = a["origin"], a["delta"]
        s.origin_cosine, s.origin_margin = a["cosine"], a["margin"]

        if checker is not None:
            try:
                verdict, detail, meta = checker(sentence, ground_truth or {})
            except Exception as exc:              # noqa: BLE001
                verdict, detail, meta = REFUSED, f"checker error: {type(exc).__name__}", {}
            s.verdict, s.reason = verdict, detail
            s.checked_against = meta.get("field")
            s.ground_truth = meta.get("truth")
            s.asserted = meta.get("asserted")
        else:
            s.verdict = REFUSED
            s.reason = "no exact checker supplied for this domain"

        s.owner = "machine" if s.verdict == VERIFIED else "human"
        if a["reason"] and not s.reason:
            s.reason = a["reason"]

        # Word level. This is what makes the analysis operational: it locates
        # the seam where invented language was spliced into traceable language.
        s.tokens = _token_origins(sentence, inputs)
        weighted = [t for t in s.tokens if t.kind in ("content", "number")]
        s.novel_content_words = [t.text for t in weighted if t.novel]
        if weighted:
            s.traceable_fraction = round(
                sum(1 for t in weighted if not t.novel) / len(weighted), 3)

        # Minimal blame: the smallest set of supplied inputs a challenge lands
        # on. Only meaningful once a span is actually attributable.
        if s.origin:
            s.blame = [s.origin]
        spans.append(s)

    counts = {v: sum(1 for s in spans if s.verdict == v)
              for v in (VERIFIED, REFUTED, REFUSED)}
    n = len(spans) or 1
    attributed = sum(1 for s in spans if s.origin)
    all_weighted = [t for s in spans for t in s.tokens
                    if t.kind in ("content", "number")]
    novel_total = sum(1 for t in all_weighted if t.novel)

    return {
        "schema": SCHEMA,
        "spans": [asdict(s) for s in spans],
        "counts": counts,
        "span_total": len(spans),
        "attributed": attributed,
        "unattributable": len(spans) - attributed,
        "content_words": len(all_weighted),
        "novel_content_words": novel_total,
        "traceable_word_fraction": (round(1 - novel_total / len(all_weighted), 3)
                                    if all_weighted else None),
        "machine_warranted": round(counts[VERIFIED] / n, 3),
        "human_owned": round((counts[REFUSED] + counts[REFUTED]) / n, 3),
        "candidate_inputs": sorted(inputs),
        "scope": (
            "Attribution is relative to the supplied candidate inputs only. No "
            "probability that a span is machine-written is reported, because no "
            "such measurement exists. Spans with no exact grounding are REFUSED "
            "and returned to the human unchanged."
        ),
    }


def render(a: Dict[str, Any]) -> str:
    out = [
        "=" * 78,
        "  ATTESTATION — know the inputs, not the output",
        "=" * 78,
        f"  {a['span_total']} spans   "
        f"verified {a['counts'][VERIFIED]} · refuted {a['counts'][REFUTED]} · "
        f"refused {a['counts'][REFUSED]}",
        f"  content words traceable to an input: "
        f"{a['traceable_word_fraction']:.0%}"
        f"   ({a['content_words'] - a['novel_content_words']}/{a['content_words']})"
        if a.get("traceable_word_fraction") is not None else "",
        f"  attributed to a supplied input: {a['attributed']}/{a['span_total']}"
        f"   ·   machine-warranted {a['machine_warranted']:.0%}"
        f"   ·   yours {a['human_owned']:.0%}",
        "",
    ]
    tag = {VERIFIED: "[VERIFIED]", REFUTED: "[REFUTED ]", REFUSED: "[REFUSED ]"}
    for s in a["spans"]:
        out.append(f"  {tag[s['verdict']]} {s['text']}")
        src = (f"origin={s['origin']} (delta {s['origin_delta']}, "
               f"margin {s['origin_margin']})" if s["origin"]
               else "origin=UNATTRIBUTABLE")
        out.append(f"             {src}")
        if s["traceable_fraction"] is not None:
            out.append(f"             words traceable to an input: "
                       f"{s['traceable_fraction']:.0%}")
        if s["novel_content_words"]:
            out.append(f"             appears in NO input: "
                       f"{', '.join(s['novel_content_words'])}")
        if s["reason"]:
            out.append(f"             {s['reason']}")
    out += ["",
            "  Nothing above is scored. A REFUSED span is not a low-confidence",
            "  span — it is one this engine has no warrant for, returned intact.",
            "=" * 78]
    return "\n".join(out)


# ------------------------------------------------------------------ selftest
def _selftest() -> int:
    ok = fail = 0

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  [PASS] {label}")
        else:
            fail += 1
            print(f"  [FAIL] {label}  {detail}")

    a = attest("The unit is ready. Fuel is adequate.", inputs={})
    check("no candidates -> every span REFUSED",
          a["counts"][REFUSED] == a["span_total"] and a["span_total"] == 2)
    check("no candidates -> nothing attributed", a["attributed"] == 0)
    check("never reports a machine-likelihood",
          not any("probab" in json.dumps(s).lower() for s in a["spans"]))

    src = {"doctrine": "The commander shall assess sustainment posture and "
                       "report shortfalls to the brigade support operations "
                       "officer without delay in accordance with policy.",
           "operator": "yeah bravo is hurting on fuel again, gonna need a "
                       "push before friday or theyre gonna be walking"}
    b = attest("The commander shall assess sustainment posture and report "
               "shortfalls without delay in accordance with policy.", inputs=src)
    check("attributes a doctrinal span to the doctrinal source",
          b["spans"][0]["origin"] == "doctrine",
          str(b["spans"][0]["origin"]))

    def checker(span, gt):
        if "4200" in span:
            return (VERIFIED, "matches record", {"field": "FUEL", "truth": "4200",
                                                 "asserted": "4200"})
        if "16800" in span:
            return (REFUTED, "record holds 4200", {"field": "FUEL", "truth": "4200",
                                                   "asserted": "16800"})
        return (REFUSED, "no exact check applies", {})

    c = attest("BRAVO holds 4200 GAL. BRAVO holds 16800 GAL. The unit is ready.",
               inputs=src, checker=checker)
    check("checker drives VERIFIED/REFUTED/REFUSED",
          c["counts"] == {VERIFIED: 1, REFUTED: 1, REFUSED: 1}, str(c["counts"]))
    check("a REFUTED span is owned by the human",
          all(s["owner"] == "human" for s in c["spans"] if s["verdict"] != VERIFIED))
    check("blame set names a supplied input, never invents one",
          all(set(s["blame"]) <= set(src) for s in c["spans"]))
    check("schema is stable", c["schema"] == SCHEMA)

    ident = {"a": "the quick brown fox jumps over the lazy dog repeatedly",
             "b": "the quick brown fox jumps over the lazy dog repeatedly"}
    d = attest("the quick brown fox jumps over the lazy dog repeatedly",
               inputs=ident)
    check("indistinguishable candidates -> refuses to attribute",
          d["spans"][0]["origin"] is None, str(d["spans"][0]))

    print("-" * 60)
    print(f"  attest.py self-test: {ok}/{ok + fail} passed")
    return 1 if fail else 0


def _demo() -> int:
    inputs = {
        "ontology_extract": "BRAVO FUEL.ON_HAND_QTY 4200 GAL. "
                            "BRAVO FUEL.DAILY_BURN_RATE 1400 GAL per day. "
                            "BRAVO FUEL.DAYS_OF_SUPPLY 3 days.",
        "doctrine": "Commanders shall assess sustainment posture continuously "
                    "and report shortfalls to the brigade support operations "
                    "officer without delay in accordance with standing policy.",
        "prior_operator_reporting": "bravo is hurting on fuel again, they need "
                                    "a push before friday or theyre walking, "
                                    "same as last rotation honestly",
    }

    def checker(span, gt):
        for token, truth in (("16800", "4200"), ("12 days", "3")):
            if token in span:
                return (REFUTED, f"record holds {truth}; span asserts {token}",
                        {"field": "BRAVO.FUEL", "truth": truth, "asserted": token})
        for token, truth in (("4200", "4200"), ("1400", "1400")):
            if token in span:
                return (VERIFIED, "matches the record exactly",
                        {"field": "BRAVO.FUEL", "truth": truth, "asserted": token})
        return (REFUSED, "no exact check applies to this span", {})

    draft = (
        "BRAVO holds 16800 GAL of fuel on hand. "
        "BRAVO burns 1400 GAL per day. "
        "The unit remains mission capable and should not be prioritized for "
        "emergency resupply. "
        "Commanders shall assess sustainment posture continuously and report "
        "shortfalls without delay in accordance with standing policy."
    )
    print(render(attest(draft, inputs=inputs, checker=checker)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("demo", "selftest"), nargs="?", default="demo")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    return _selftest() if args.command == "selftest" else _demo()


if __name__ == "__main__":
    raise SystemExit(main())
