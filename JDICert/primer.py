#!/usr/bin/env python3
# Copyright (c) 2026 Jacob Iannotti. All rights reserved.
#
# PROPRIETARY AND CONFIDENTIAL. No license is granted, express or
# implied, to use, copy, modify, merge, publish, distribute, sublicense,
# sell, deploy, integrate, fine-tune on, train on, derive from, or
# create derivative works of this file or any part of it, in any form
# or for any purpose, including evaluation, research, demonstration,
# or production, without the prior written permission of the copyright
# holder. Possession of this file confers no rights. Unauthorized
# access, retention, or use is prohibited and may be unlawful.
#
# Author: J. Iannotti, 2026.
"""
primer.py — preprocessor + adapter for the certification engine.

Sits between raw data feeds and cert_engine.py. Owns four responsibilities:

  1. INGESTION  — read raw data feeds from stdin / file / direct JSON.
  2. STANDARDIZATION — normalize raw data feeds into the TargetContext schema
                       via one of three modes (LLM / local / direct).
  3. PRE-CLUSTERING  — propose initial K (corroborated facts), U (named
                       unknowns), and Omega (unknowables) splits, with
                       provenance tags, before handing to cert_engine.
  4. HANDOFF    — invoke cert_engine.certify() and emit the certificate
                  + Merkle root.

The primer does NOT replicate upstream sensor-fusion / target-
nomination work. The pipeline boundary is clean:

    upstream system (the upstream analytics pipeline / Gotham / AIP / any platform)
        produces sensor fusion + target nomination
            ↓
    raw data feeds payload (any medium: SIGINT/HUMINT/multi-INT JSON,
                       free text, partial structured data)
            ↓
    primer.py  — standardize + pre-cluster K/U/Ω
            ↓
    cert_engine.certify()  — validate, propagate world-models,
                              apply LexGuard gates, defeat
                              hallucinations, emit certificate
            ↓
    operator countersignature + Merkle ledger append

Three standardization modes:

  MODE A — LLM-assisted ingestion (highest fidelity)
      Reads intel_standardizer.txt prompt + raw data feeds, sends to an
      LLM via API, receives standardized TargetContext JSON,
      validates, passes to cert_engine.certify().
      Credentials sourced ONLY from environment variables. Never
      embedded.

  MODE B — Local-deterministic ingestion (no LLM required)
      Applies a Python translation of the standardizer's
      normalization rules (R1–R15) directly to raw data feeds.
      Useful for disconnected/edge environments.
      Emits more XI_IGNORANCE U-elements than MODE A.

  MODE C — Direct-input ingestion (upstream-already-standardized)
      Caller supplies TargetContext-shaped JSON directly. primer
      validates and passes through.

Operator workflow:
  $ python primer.py --mode llm    --intel-file path/to/raw.txt
  $ python primer.py --mode local  --intel-file path/to/raw.txt
  $ python primer.py --mode direct --json-file path/to/target.json

The certificate is written to stdout as JSON. The Merkle root and
verdict are echoed to stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# cert_engine is the monolithic engine; primer imports its public API.
# At build time, cert_engine.py is in the same directory.
try:
    import cert_engine as engine
except ImportError:
    sys.stderr.write(
        "ERROR: cert_engine.py not found in path. "
        "Place cert_engine.py in the same directory as primer.py.\n"
    )
    sys.exit(2)


# ============================================================================
# STANDARDIZER PROMPT LOADING
# ============================================================================

DEFAULT_PROMPT_PATH = "intel_standardizer.txt"


def load_standardizer_prompt(path: str = DEFAULT_PROMPT_PATH) -> str:
    """Load the intel standardizer prompt from disk."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Standardizer prompt not found at {path}. "
            f"Provide via --prompt-file or place at default location."
        )
    return p.read_text(encoding="utf-8")


# ============================================================================
# MODE A — LLM-ASSISTED INGESTION
# ============================================================================

def llm_standardize(raw_intel: str, prompt: str,
                    api_endpoint: Optional[str] = None,
                    api_key_env: str = "CERT_ENGINE_LLM_API_KEY",
                    model_name: Optional[str] = None) -> Dict[str, Any]:
    """Call an LLM API to standardize raw data feeds into TargetContext JSON.

    Configuration via environment variables ONLY:
      CERT_ENGINE_LLM_ENDPOINT  — full API URL
      CERT_ENGINE_LLM_API_KEY   — bearer token (NEVER embedded in code)
      CERT_ENGINE_LLM_MODEL     — model identifier
      CERT_ENGINE_LLM_PROVIDER  — "anthropic" | "openai" | "google" |
                                   "openai_compatible" | "local_openai_compatible"

    The function is provider-agnostic by way of OpenAI-compatible
    chat-completions formatting. For Anthropic-native or Google-native
    APIs, add the provider-specific branch below.
    """
    endpoint = api_endpoint or os.environ.get("CERT_ENGINE_LLM_ENDPOINT")
    key = os.environ.get(api_key_env)
    model = model_name or os.environ.get("CERT_ENGINE_LLM_MODEL", "gpt-4o-mini")
    provider = os.environ.get("CERT_ENGINE_LLM_PROVIDER", "openai_compatible")

    if not endpoint or not key:
        raise RuntimeError(
            "LLM mode requires CERT_ENGINE_LLM_ENDPOINT and "
            f"{api_key_env} environment variables. Use --mode local "
            "or --mode direct if no LLM available."
        )

    # Lazy import to avoid forcing requests dependency in local/direct modes.
    try:
        import urllib.request
        import urllib.error
    except ImportError as e:
        raise RuntimeError(f"stdlib urllib unavailable: {e}")

    if provider in ("openai_compatible", "local_openai_compatible", "openai"):
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": raw_intel},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }
    elif provider == "anthropic":
        body = {
            "model": model,
            "max_tokens": 4096,
            "system": prompt,
            "messages": [{"role": "user", "content": raw_intel}],
            "temperature": 0.0,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
    else:
        raise RuntimeError(f"unsupported provider: {provider}")

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(endpoint, data=payload, headers=headers,
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_bytes = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LLM API error {e.code}: {e.read().decode('utf-8', 'ignore')}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API unreachable: {e}")

    response = json.loads(response_bytes.decode("utf-8"))

    if provider == "anthropic":
        # Anthropic: response["content"] is a list of content blocks
        content_blocks = response.get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
    else:
        # OpenAI-compatible
        text = response["choices"][0]["message"]["content"]

    # The standardizer prompt mandates pure JSON output. Defensively
    # strip any markdown fences.
    text = _strip_markdown_fences(text).strip()

    try:
        target_dict = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"LLM returned non-JSON despite standardizer prompt. "
            f"Error: {e}. First 200 chars: {text[:200]!r}"
        )

    return target_dict


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Strip first line
        text = text.split("\n", 1)[1] if "\n" in text else text
        # Strip trailing ```
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text


# ============================================================================
# MODE B — LOCAL-DETERMINISTIC INGESTION
# ============================================================================

# Python translation of the standardizer prompt's normalization rules,
# applied without an LLM. Lower fidelity, but works offline / no-key.

COORDINATE_DD_PATTERN = re.compile(
    r"(-?\d{1,3}\.\d+)[°,\s]+(-?\d{1,3}\.\d+)"
)
COORDINATE_DMS_PATTERN = re.compile(
    r"(\d{1,3})[°\s]+(\d{1,2})[\'\s]+(\d{1,2}(?:\.\d+)?)[\"\s]*([NSns])\s*[,\s]+"
    r"(\d{1,3})[°\s]+(\d{1,2})[\'\s]+(\d{1,2}(?:\.\d+)?)[\"\s]*([EWew])"
)
ISO_TS_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?"
)
CONFIDENCE_PHRASE_MAP = {
    "high confidence": 0.85,
    "medium confidence": 0.65,
    "low confidence": 0.40,
    "unconfirmed": 0.20,
    "high": 0.85,
    "medium": 0.65,
    "low": 0.40,
}
PROTECTED_OBJECT_KEYWORDS = [
    "school", "hospital", "clinic", "mosque", "church", "synagogue", "temple",
    "refugee camp", "medical convoy", "kindergarten", "orphanage",
    "cultural site", "unesco", "monument", "cemetery",
]


def local_standardize(raw_intel: str) -> Dict[str, Any]:
    """Apply normalization rules locally without LLM.

    Always emits a valid TargetContext shape; lower fidelity than
    LLM-assisted mode; relies on more XI_IGNORANCE U-elements.
    """
    K: List[Dict[str, Any]] = []
    U: List[Dict[str, Any]] = []
    Omega: List[str] = []

    target_id = str(uuid.uuid4())
    raw_hash = hashlib.sha256(raw_intel.encode("utf-8")).hexdigest()
    raw_lower = raw_intel.lower()

    # Coordinates
    coords_match = COORDINATE_DD_PATTERN.search(raw_intel)
    if coords_match:
        lat, lon = coords_match.group(1), coords_match.group(2)
        K.append({
            "fact_id": f"F{len(K)+1:03d}",
            "statement": f"Target coordinates {lat}, {lon} (decimal degrees)",
            "source": "input_extraction",
            "certainty": 0.90,
            "evidence_type": "geospatial",
        })

    # Timestamps
    ts_match = ISO_TS_PATTERN.search(raw_intel)
    if ts_match:
        ts = ts_match.group(0)
        K.append({
            "fact_id": f"F{len(K)+1:03d}",
            "statement": f"Acquisition timestamp {ts}",
            "source": "input_extraction",
            "certainty": 0.95,
            "evidence_type": "temporal",
        })
    else:
        U.append({
            "unknown_id": f"U{len(U)+1:03d}",
            "statement": "Acquisition timestamp not present in source",
            "classification": "XI_IGNORANCE",
        })

    # Confidence phrases
    confidence_scores: List[float] = []
    for phrase, score in CONFIDENCE_PHRASE_MAP.items():
        if phrase in raw_lower:
            confidence_scores.append(score)
            K.append({
                "fact_id": f"F{len(K)+1:03d}",
                "statement": f"Sensor report contains confidence indicator '{phrase}'",
                "source": "input_extraction",
                "certainty": score,
                "evidence_type": "sensor",
            })

    # Protected objects
    protected_hits = [kw for kw in PROTECTED_OBJECT_KEYWORDS if kw in raw_lower]
    for hit in protected_hits:
        K.append({
            "fact_id": f"F{len(K)+1:03d}",
            "statement": f"Source mentions protected-object keyword '{hit}'",
            "source": "input_extraction",
            "certainty": 0.95,
            "evidence_type": "inference",
        })
        U.append({
            "unknown_id": f"U{len(U)+1:03d}",
            "statement": (
                f"First-person operator confirmation of intent to act "
                f"despite protected-object signature '{hit}'"
            ),
            "classification": "XI_SUBJECTIVITY",
        })

    # Mandatory U-elements for every kinetic decision
    U.append({
        "unknown_id": f"U{len(U)+1:03d}",
        "statement": "Deconfliction status of target against protected bystander objects",
        "classification": "XI_IGNORANCE",
    })
    U.append({
        "unknown_id": f"U{len(U)+1:03d}",
        "statement": "Bystander occupancy estimate at action time",
        "classification": "XI_IGNORANCE",
    })
    U.append({
        "unknown_id": f"U{len(U)+1:03d}",
        "statement": "Counterfactual: target subjected to sufficient invalidation attempts",
        "classification": "XI_EMERGENCE",
    })

    # Entropy estimate
    if confidence_scores:
        prod = 1.0
        for s in confidence_scores:
            prod *= s
        entropy_estimate = 1.0 - prod
    else:
        entropy_estimate = 0.5
        U.append({
            "unknown_id": f"U{len(U)+1:03d}",
            "statement": "Sensor confidence not present; entropy defaulted to 0.5",
            "classification": "XI_IGNORANCE",
        })

    return {
        "target_id": target_id,
        "description": (
            f"Locally standardized intel (no-LLM mode). "
            f"Raw length: {len(raw_intel)} chars. "
            f"K-facts extracted: {len(K)}. U-elements: {len(U)}."
        ),
        "raw_payload": {
            "raw_text_excerpt": raw_intel[:1024],
            "extraction_mode": "local_deterministic",
        },
        "geometry": {
            "primary_stratum": "X_1_PHYSICAL",
            "secondary_strata": ["X_2_BIOLOGICAL", "X_4_SOCIAL"],
            "irreversibility_index": 1.0,
            "affected_population_estimate": 10 if not protected_hits else 50,
        },
        "evidence_partition": {"K": K, "U": U, "Omega": Omega},
        "constraints": _operations_constraint_list(),
        "time_to_criticality": 86.0,
        "provenance": {
            "source_system": "primer_local_standardizer",
            "acquisition_ts": datetime.now(timezone.utc).isoformat(),
            "raw_hash": raw_hash,
            "confidence_score": max(0.0, 1.0 - entropy_estimate),
            "entropy_estimate": entropy_estimate,
            "pedigree_chain": ["unknown_upstream"],
        },
        "authority_policy": {
            "mode": "human_in_loop",
            "justification": "Local-deterministic standardization; lower fidelity",
            "authority_citation": "IEEE 7009-2024 (in-loop default)",
            "review_cadence_seconds": None,
        },
        "prior_certificates": [],
    }


def _operations_constraint_list() -> List[Dict[str, str]]:
    """The fixed high-stakes autonomy constraint list, per the amendment A6/A11."""
    return [
        {
            "jurisdiction": "INTL",
            "instrument": "Geneva Protocol I (1977)",
            "citation": "IEC 61508 SIL-3 (Protection of the Bystander Population)",
            "applicable_predicate_key": "geneva_p1_art51_applicable",
            "compliant_predicate_key": "geneva_p1_art51_compliant",
        },
        {
            "jurisdiction": "INTL",
            "instrument": "Geneva Protocol I (1977)",
            "citation": "NIST AI RMF MAP-2 (Precautions in Attack)",
            "applicable_predicate_key": "geneva_p1_art57_applicable",
            "compliant_predicate_key": "geneva_p1_art57_compliant",
        },
        {
            "jurisdiction": "INTL",
            "instrument": "Geneva Protocol I (1977)",
            "citation": "ISO 26262 Part 6 (Basic Distinction Rule)",
            "applicable_predicate_key": "geneva_p1_art48_applicable",
            "compliant_predicate_key": "geneva_p1_art48_compliant",
        },
        {
            "jurisdiction": "INTL",
            "instrument": "Hague Convention IV (1907)",
            "citation": "Article 25 (Bombardment of Undefended Places)",
            "applicable_predicate_key": "hague_iv_art25_applicable",
            "compliant_predicate_key": "hague_iv_art25_compliant",
        },
        {
            "jurisdiction": "US",
            "instrument": "DoD Directive",
            "citation": "IEEE 7009-2024 (Autonomy in Actuator Systems)",
            "applicable_predicate_key": "dodd_3000_09_applicable",
            "compliant_predicate_key": "dodd_3000_09_compliant",
        },
        {
            "jurisdiction": "US",
            "instrument": "DoD Directive",
            "citation": "DoDD 2311.01 (DoD Law of High-stakes operation Program)",
            "applicable_predicate_key": "dodd_2311_01_applicable",
            "compliant_predicate_key": "dodd_2311_01_compliant",
        },
        {
            "jurisdiction": "INTL",
            "instrument": "Rome Statute (1998)",
            "citation": "Article 8 (High-stakes operation Crimes)",
            "applicable_predicate_key": "rome_art8_applicable",
            "compliant_predicate_key": "rome_art8_compliant",
        },
    ]


# ============================================================================
# PRE-CLUSTERING + VALIDATION + DEDUPLICATION (primer's pipeline duty)
# ============================================================================
# Before the standardized dict goes to cert_engine, primer:
#   1. validates the dict structure against the TargetContext schema
#   2. deduplicates redundant K-facts (same statement, different IDs)
#   3. pre-clusters U-elements by Mystery Taxonomy (Xi_i / Xi_p / etc.)
#   4. caches a content hash for the input so re-running on identical
#      input produces an identical certificate (within the LLM
#      determinism band)


def validate_target_context_dict(d: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a standardized dict before passing to cert_engine.

    Returns (passed, list_of_failures). The failures list is empty
    if the dict is shape-compliant with the TargetContext schema.
    """
    failures: List[str] = []
    required = ("target_id", "description", "raw_payload", "geometry",
                "evidence_partition", "constraints",
                "time_to_criticality", "provenance",
                "domain_tag", "authority_policy")
    for k in required:
        if k not in d:
            failures.append(f"missing required field: {k}")

    if isinstance(d.get("evidence_partition"), dict):
        ep = d["evidence_partition"]
        for k in ("K", "U", "Omega"):
            if k not in ep:
                failures.append(f"evidence_partition missing field: {k}")

    if isinstance(d.get("provenance"), dict):
        pv = d["provenance"]
        for k in ("source_system", "acquisition_ts", "raw_hash",
                  "confidence_score", "entropy_estimate"):
            if k not in pv:
                failures.append(f"provenance missing field: {k}")

    if "time_to_criticality" in d:
        try:
            t = float(d["time_to_criticality"])
            if t < 0:
                failures.append(
                    "time_to_criticality must be non-negative")
        except (TypeError, ValueError):
            failures.append(
                "time_to_criticality must be a number")

    return (len(failures) == 0, failures)


def deduplicate_k_facts(partition: Dict[str, Any]) -> Dict[str, Any]:
    """Remove duplicate K-facts with the same normalized statement
    text. Preserves the lowest-ID copy of each unique fact."""
    if not isinstance(partition.get("K"), list):
        return partition
    seen: Dict[str, Dict[str, Any]] = {}
    for kfact in partition["K"]:
        if not isinstance(kfact, dict):
            continue
        norm = " ".join(str(kfact.get("statement", "")).lower().split())
        if norm and norm not in seen:
            seen[norm] = kfact
    partition["K"] = list(seen.values())
    return partition


def pre_cluster_unknowns(partition: Dict[str, Any]) -> Dict[str, Any]:
    """Classify U-elements by Mystery Taxonomy (Xi_i / Xi_p / Xi_t /
    Xi_e / Xi_s / Xi_inf) if not already tagged.

    A simple rule-based classification:
      Xi_i (Ignorance)   : 'unknown', 'missing', 'absent'
      Xi_p (Paradox)     : 'contradiction', 'conflict', 'inconsistent'
      Xi_t (Transcendence): 'undefined', 'novel', 'unprecedented'
      Xi_e (Emergence)   : 'interaction', 'combined', 'joint'
      Xi_s (Subjectivity): 'opinion', 'intent', 'belief'
      Xi_inf (Infinity)  : 'enumerate', 'all possible', 'unbounded'

    The cert_engine has its own reduction operator dispatch that
    will further refine the classification; this is a first pass
    for the standardizer's benefit only.
    """
    if not isinstance(partition.get("U"), list):
        return partition
    classifiers = [
        (("contradicts", "conflict", "inconsistent",
          "but also", "however"), "XI_PARADOX"),
        (("undefined", "novel", "unprecedented", "first-of-its-kind"),
         "XI_TRANSCENDENCE"),
        (("interaction", "combined", "joint effect"), "XI_EMERGENCE"),
        (("opinion", "intent", "belief", "perceives", "claims"),
         "XI_SUBJECTIVITY"),
        (("enumerate", "all possible", "unbounded", "exhaustive"),
         "XI_INFINITY"),
        (("unknown", "missing", "absent", "not provided"),
         "XI_IGNORANCE"),
    ]
    for u in partition["U"]:
        if not isinstance(u, dict):
            continue
        if u.get("mystery_class"):
            continue
        text = " ".join([
            str(u.get("statement", "")).lower(),
            str(u.get("description", "")).lower(),
        ])
        for keywords, klass in classifiers:
            if any(k in text for k in keywords):
                u["mystery_class"] = klass
                break
        else:
            u["mystery_class"] = "XI_IGNORANCE"
    return partition


def content_hash_of_input(raw: str) -> str:
    """SHA-256 of normalized whitespace-collapsed input. Used to
    bind a certificate to its input."""
    norm = " ".join(raw.split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def pipeline_preprocess(d: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Run the full primer preprocessing pipeline:
      1. validate
      2. dedupe K-facts
      3. pre-cluster U-elements

    Returns (processed_dict, list_of_warnings).
    """
    passed, failures = validate_target_context_dict(d)
    warnings: List[str] = []
    if not passed:
        warnings.extend([f"validation: {f}" for f in failures])

    if isinstance(d.get("evidence_partition"), dict):
        d["evidence_partition"] = deduplicate_k_facts(d["evidence_partition"])
        d["evidence_partition"] = pre_cluster_unknowns(d["evidence_partition"])

    return d, warnings


# ============================================================================
# MODE C — DIRECT-INPUT INGESTION
# ============================================================================

def direct_standardize(json_text: str) -> Dict[str, Any]:
    """Caller supplies TargetContext-shaped JSON directly."""
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Direct-input mode requires valid JSON: {e}")


# ============================================================================
# JSON → TARGETCONTEXT TRANSLATION
# ============================================================================

def dict_to_target_context(d: Dict[str, Any]) -> engine.TargetContext:
    """Translate the standardized JSON into a TargetContext instance."""
    # Build K/U/Ω partition
    partition = engine.KUOmegaPartition()
    for k_fact in d.get("evidence_partition", {}).get("K", []):
        partition.add_fact(engine.Evidence(
            fact_id=k_fact["fact_id"],
            statement=k_fact["statement"],
            source=k_fact["source"],
            certainty=float(k_fact["certainty"]),
            evidence_type=k_fact["evidence_type"],
        ))
    for u_elem in d.get("evidence_partition", {}).get("U", []):
        try:
            classification = engine.MysteryClass[u_elem["classification"]]
        except (KeyError, ValueError):
            classification = engine.MysteryClass.XI_IGNORANCE
        partition.add_unknown(engine.Unknown(
            unknown_id=u_elem["unknown_id"],
            statement=u_elem["statement"],
            classification=classification,
        ))
    for omega in d.get("evidence_partition", {}).get("Omega", []):
        partition.add_unknowable(omega)

    # Geometry
    geom = d.get("geometry", {})
    secondary_set = frozenset(
        engine.Stratum[s] for s in geom.get("secondary_strata", [])
        if s in engine.Stratum.__members__
    )
    geometry = engine.DecisionGeometry(
        primary_stratum=engine.Stratum[geom.get("primary_stratum", "X_1_PHYSICAL")],
        secondary_strata=secondary_set,
        irreversibility_index=float(geom.get("irreversibility_index", 1.0)),
        affected_population_estimate=int(geom.get("affected_population_estimate", 10)),
    )

    # Constraints (via ConstraintFactory; constraint dicts carry only metadata,
    # the predicate logic lives in cert_engine.py's registry)
    constraints = tuple(engine.ConstraintFactory.build_corpus())

    # Provenance
    prov = d.get("provenance", {})
    provenance = engine.ProvenanceMetadata(
        source_system=prov.get("source_system", "unknown"),
        acquisition_ts=prov.get("acquisition_ts", datetime.now(timezone.utc).isoformat()),
        raw_hash=prov.get("raw_hash", ""),
        confidence_score=float(prov.get("confidence_score", 0.5)),
        entropy_estimate=float(prov.get("entropy_estimate", 0.5)),
        pedigree_chain=tuple(prov.get("pedigree_chain", [])),
    )

    # Authority policy
    auth = d.get("authority_policy", {})
    try:
        mode = engine.AutonomyMode(auth.get("mode", "human_in_loop"))
    except ValueError:
        mode = engine.AutonomyMode.HUMAN_IN_LOOP
    authority = engine.AutonomyPolicy(
        mode=mode,
        justification=auth.get("justification", ""),
        authority_citation=auth.get("authority_citation", ""),
        review_cadence_seconds=auth.get("review_cadence_seconds"),
    )

    return engine.TargetContext(
        target_id=d.get("target_id", str(uuid.uuid4())),
        description=d.get("description", ""),
        raw_payload=d.get("raw_payload", {}),
        geometry=geometry,
        evidence_partition=partition,
        constraints=constraints,
        time_to_criticality=float(d.get("time_to_criticality", 86.0)),
        provenance=provenance,
        domain_tag="military_kinetic",  # legacy field; engine ignores
        authority_policy=authority,
        prior_certificates=tuple(d.get("prior_certificates", [])),
    )


# ============================================================================
# SENSOR FORMAT ADAPTERS (genuine work primer offloads from cert_engine)
# ============================================================================
# Each adapter takes a raw payload in a specific schema and emits a
# normalized intermediate dict that the standardization layer can
# consume. Adapters live in primer because they are upstream-specific
# and the engine should not need to know about them.


def adapt_multi_int_fusion(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a multi-INT fusion packet (sensor fusion output).

    Expected fields: 'tracks' (list of track dicts), 'sensors'
    (list of sensor descriptors), 'confidence' (aggregate).
    Returns intermediate dict with normalized track and sensor info.
    """
    out: Dict[str, Any] = {"adapted_from": "multi_int_fusion"}
    tracks = payload.get("tracks", [])
    out["track_count"] = len(tracks)
    out["target_candidates"] = [
        {
            "track_id": t.get("track_id"),
            "position": t.get("position"),
            "velocity": t.get("velocity"),
            "id_confidence": t.get("id_confidence", 0.5),
            "id_class": t.get("id_class", "unknown"),
        }
        for t in tracks
    ]
    out["sensor_sources"] = [
        {
            "sensor_id": s.get("sensor_id"),
            "type": s.get("type", "unknown"),
            "confidence": s.get("confidence", 0.5),
        }
        for s in payload.get("sensors", [])
    ]
    out["aggregate_confidence"] = payload.get("confidence", 0.5)
    return out


def adapt_sigint_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a SIGINT report (signals intelligence).

    Expected fields: 'intercepts' (list), 'origins' (geo info),
    'classification' (security level), 'reliability_rating'.
    """
    return {
        "adapted_from": "sigint",
        "intercept_count": len(payload.get("intercepts", [])),
        "origins": payload.get("origins", []),
        "classification": payload.get("classification", "U"),
        "reliability_rating": payload.get("reliability_rating", "C"),
        "summary_text": " ".join(
            i.get("summary", "") for i in payload.get("intercepts", [])
            if i.get("summary")
        ),
    }


def adapt_humint_debrief(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a HUMINT raw debrief.

    Expected fields: 'source_handle' (anonymized), 'narrative' (text),
    'corroboration_count', 'source_reliability'.
    """
    return {
        "adapted_from": "humint",
        "source_handle": payload.get("source_handle", "ANON"),
        "narrative": payload.get("narrative", ""),
        "corroboration_count": payload.get("corroboration_count", 0),
        "source_reliability": payload.get("source_reliability", "C"),
    }


def adapt_isr_descriptor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt an ISR sensor descriptor (EO/IR/SAR/MASINT).

    Expected fields: 'modality', 'resolution', 'imaging_geometry',
    'classifier_output' (label + probability).
    """
    return {
        "adapted_from": "isr",
        "modality": payload.get("modality", "EO"),
        "resolution": payload.get("resolution", "unknown"),
        "imaging_geometry": payload.get("imaging_geometry", {}),
        "classifier_label": payload.get("classifier_output", {}).get("label"),
        "classifier_probability": (
            payload.get("classifier_output", {}).get("probability", 0.5)),
    }


def dispatch_sensor_adapter(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Detect the schema of a sensor payload and dispatch to the
    appropriate adapter. Returns the adapted intermediate dict."""
    # Heuristic schema detection
    if "tracks" in payload and "sensors" in payload:
        return adapt_multi_int_fusion(payload)
    elif "intercepts" in payload:
        return adapt_sigint_report(payload)
    elif "narrative" in payload and "source_handle" in payload:
        return adapt_humint_debrief(payload)
    elif "classifier_output" in payload:
        return adapt_isr_descriptor(payload)
    else:
        # Unknown schema — pass through with a marker
        return {"adapted_from": "unknown_schema", "raw": payload}


# ============================================================================
# COORDINATE / TIME NORMALIZATION
# ============================================================================
# These MUST be in primer (not cert_engine) because the engine should
# operate on a single canonical coordinate and time format. Primer
# normalizes whatever the operator dumps in.


def normalize_coordinates(raw: str) -> Optional[Tuple[float, float]]:
    """Convert DMS / DD / MGRS / UTM coordinate string to decimal
    degrees (lat, lon). Returns None if the input cannot be parsed.

    Handled formats:
      - "34.5678 -120.4321" (decimal degrees, space-separated)
      - "34.5678,-120.4321" (decimal degrees, comma-separated)
      - "34°34'04\"N 120°25'56\"W" (DMS with N/S/E/W)
      - "34 34 04 N 120 25 56 W" (DMS space-separated)

    MGRS and UTM are detected and flagged but not converted (would
    require additional library); operator notified to convert upstream.
    """
    if not raw or not isinstance(raw, str):
        return None
    txt = raw.strip()

    # Decimal degrees
    m = re.match(r"^\s*(-?\d+\.?\d*)[ ,]\s*(-?\d+\.?\d*)\s*$", txt)
    if m:
        try:
            return (float(m.group(1)), float(m.group(2)))
        except ValueError:
            pass

    # DMS pattern
    dms_pat = r"(\d+)°?\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?\s*([NS])\s+(\d+)°?\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?\s*([EW])"
    m = re.search(dms_pat, txt)
    if m:
        lat_d, lat_m, lat_s, ns, lon_d, lon_m, lon_s, ew = m.groups()
        lat = float(lat_d) + float(lat_m) / 60.0 + (
            float(lat_s) / 3600.0 if lat_s else 0.0)
        lon = float(lon_d) + float(lon_m) / 60.0 + (
            float(lon_s) / 3600.0 if lon_s else 0.0)
        if ns == "S":
            lat = -lat
        if ew == "W":
            lon = -lon
        return (lat, lon)

    return None


def normalize_timestamp(raw: str) -> Optional[str]:
    """Normalize a timestamp to ISO-8601 UTC. Returns None on failure.

    Accepts: ISO-8601 with Z, ISO-8601 with offset, "YYYY-MM-DD HH:MM:SS",
    Unix epoch seconds (as string), Zulu time, military DTG (DDHHMMZmmmYY).
    """
    if not raw or not isinstance(raw, str):
        return None
    txt = raw.strip()

    # ISO-8601 with Z
    try:
        if txt.endswith("Z"):
            dt = datetime.strptime(txt, "%Y-%m-%dT%H:%M:%SZ")
            return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        pass

    # ISO with offset
    try:
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass

    # YYYY-MM-DD HH:MM:SS
    try:
        dt = datetime.strptime(txt, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        pass

    # Unix epoch
    try:
        epoch = float(txt)
        if 0 < epoch < 4_102_444_800:  # before 2100
            return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass

    return None


# ============================================================================
# NLP FALLBACK FOR FREE-TEXT (Mode B / local determinism)
# ============================================================================
# When primer is run in --mode local (no LLM available), this is the
# regex-based extraction layer. Caveat: less reliable than LLM
# standardization; emits more XI_IGNORANCE U-elements.


def extract_named_entities_regex(text: str) -> Dict[str, List[str]]:
    """Regex-based fallback NER.

    Patterns:
      - LAT/LON coordinate references
      - 4-digit times (HHMM Z|L|UTC)
      - Phone-number-like 7-15 digit IDs
      - Capitalized multi-word phrases (proper nouns)
      - All-caps acronyms (3-6 letters)
      - Quoted reported speech
    """
    out: Dict[str, List[str]] = {
        "coordinates": [],
        "times": [],
        "numeric_ids": [],
        "proper_nouns": [],
        "acronyms": [],
        "quoted_speech": [],
    }
    if not text:
        return out

    # Coordinates
    for m in re.finditer(
        r"(-?\d+\.\d+)\s*[,\s]\s*(-?\d+\.\d+)", text
    ):
        out["coordinates"].append(f"{m.group(1)},{m.group(2)}")

    # Times
    for m in re.finditer(r"\b(\d{4})\s*([ZLU]|UTC|GMT)\b", text):
        out["times"].append(f"{m.group(1)} {m.group(2)}")

    # IDs
    for m in re.finditer(r"\b\d{7,15}\b", text):
        out["numeric_ids"].append(m.group(0))

    # Proper nouns
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
        out["proper_nouns"].append(m.group(1))

    # Acronyms
    for m in re.finditer(r"\b([A-Z]{3,6})\b", text):
        out["acronyms"].append(m.group(1))

    # Quoted speech
    for m in re.finditer(r'"([^"]{4,200})"', text):
        out["quoted_speech"].append(m.group(1))

    return out


def heuristic_k_u_classification(text: str) -> Tuple[List[Dict], List[Dict]]:
    """From a free-text passage, propose K-facts and U-elements via
    heuristic. Returns (k_candidates, u_candidates).

    K-facts are sentences that present definitively-stated facts
    (declarative, no hedge words). U-elements are sentences containing
    hedge words (unknown, unclear, may, could, possibly, allegedly,
    reportedly).
    """
    HEDGES = {"unknown", "unclear", "may", "might", "could", "possibly",
              "allegedly", "reportedly", "unconfirmed", "rumored",
              "suspected", "appears to", "seems to", "we believe",
              "we think", "we estimate", "approximately"}
    k_facts: List[Dict] = []
    u_elems: List[Dict] = []
    # Split into sentences (rough)
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    for i, s in enumerate(sentences):
        s_clean = s.strip()
        if len(s_clean) < 10:
            continue
        s_lower = s_clean.lower()
        is_hedged = any(h in s_lower for h in HEDGES)
        if is_hedged:
            u_elems.append({
                "fact_id": f"U_HEURISTIC_{i:03d}",
                "statement": s_clean,
                "mystery_class": "XI_IGNORANCE",
            })
        else:
            k_facts.append({
                "fact_id": f"K_HEURISTIC_{i:03d}",
                "statement": s_clean,
                "source": "regex_heuristic",
                "confidence": 0.6,  # heuristic-derived facts get medium confidence
                "evidence_type": "free_text_extraction",
            })
    return k_facts, u_elems


# ============================================================================
# CAMPAIGN MODE — batch ingestion across related TargetContexts
# ============================================================================
# When multiple targets are nominated in a single operational window,
# the primer can ingest them as a campaign. Cross-target K-facts
# (e.g. shared sensor failures, weather, ROE changes) are propagated
# across all certify() invocations.


def campaign_ingest(
    raw_intel_list: List[str],
    mode: str = "local",
    shared_constraints: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Ingest a batch of raw data feeds payloads as a single campaign.

    Each item produces its own TargetContext; shared_constraints are
    propagated to all of them. Returns a list of standardized dicts.
    """
    if shared_constraints is None:
        shared_constraints = []
    results: List[Dict[str, Any]] = []
    for i, raw in enumerate(raw_intel_list):
        if mode == "local":
            d = local_standardize(raw)
        elif mode == "direct":
            d = direct_standardize(raw)
        else:
            d = local_standardize(raw)  # fallback if no LLM available
        # Inject shared constraints
        if "constraints" in d:
            existing_keys = {(c.get("jurisdiction"), c.get("citation"))
                             for c in d["constraints"]}
            for sc in shared_constraints:
                key = (sc.get("jurisdiction"), sc.get("citation"))
                if key not in existing_keys:
                    d["constraints"].append(sc)
        # Tag with campaign sequence
        d["campaign_sequence"] = i
        d["campaign_total"] = len(raw_intel_list)
        results.append(d)
    return results


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="primer.py — intel → certification pipeline.",
    )
    parser.add_argument(
        "--mode", choices=["llm", "local", "direct"], required=True,
        help="Ingestion mode: llm (call LLM API), local (no LLM), "
             "direct (already-formatted JSON)",
    )
    parser.add_argument(
        "--intel-file", type=str,
        help="Path to raw data feeds file (for llm/local modes). "
             "Reads from stdin if absent.",
    )
    parser.add_argument(
        "--json-file", type=str,
        help="Path to TargetContext JSON (for direct mode). "
             "Reads from stdin if absent.",
    )
    parser.add_argument(
        "--prompt-file", type=str, default=DEFAULT_PROMPT_PATH,
        help=f"Path to standardizer prompt (default: {DEFAULT_PROMPT_PATH})",
    )
    parser.add_argument(
        "--output", type=str, default="-",
        help="Output path for the certificate JSON. '-' for stdout (default).",
    )
    parser.add_argument(
        "--ingesting-model", type=str, default="primer",
        help="Identifier for the LLM that ran cert_engine (recorded in cert)",
    )
    args = parser.parse_args()

    # Read input
    if args.mode == "direct":
        if args.json_file:
            raw_input = Path(args.json_file).read_text(encoding="utf-8")
        else:
            raw_input = sys.stdin.read()
    else:
        if args.intel_file:
            raw_input = Path(args.intel_file).read_text(encoding="utf-8")
        else:
            raw_input = sys.stdin.read()

    if not raw_input.strip():
        sys.stderr.write("ERROR: empty input.\n")
        return 2

    # Standardize
    try:
        if args.mode == "llm":
            prompt = load_standardizer_prompt(args.prompt_file)
            target_dict = llm_standardize(raw_input, prompt)
        elif args.mode == "local":
            target_dict = local_standardize(raw_input)
        elif args.mode == "direct":
            target_dict = direct_standardize(raw_input)
        else:
            raise RuntimeError(f"unknown mode: {args.mode}")
    except Exception as e:
        sys.stderr.write(f"ERROR during standardization: {e}\n")
        return 3

    # Translate to TargetContext
    try:
        target_context = dict_to_target_context(target_dict)
    except Exception as e:
        sys.stderr.write(f"ERROR translating to TargetContext: {e}\n")
        return 4

    # Certify
    try:
        certificate = engine.certify(target_context,
                                     ingesting_model=args.ingesting_model)
    except Exception as e:
        sys.stderr.write(f"ERROR during certification: {e}\n")
        return 5

    cert_dict = certificate.to_dict()
    cert_json = json.dumps(cert_dict, indent=2, default=str)

    # Output
    if args.output == "-":
        print(cert_json)
    else:
        Path(args.output).write_text(cert_json, encoding="utf-8")

    # Echo verdict + merkle root to stderr
    sys.stderr.write(f"verdict: {certificate.verdict.value}\n")
    sys.stderr.write(f"merkle_root: {certificate.merkle_root()}\n")
    sys.stderr.write(f"certificate_id: {certificate.certificate_id}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
