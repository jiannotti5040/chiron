#!/usr/bin/env python3
"""Build and verify the frozen, bounded A063880 research capsule.

This target-specific tool is not a theorem prover.  It checks only the finite
interval [1, 10,000,000] by two separately implemented exact-integer scans and
records frozen inputs plus output hashes for an offline replay.

Usage from the vault root:
    python3 studies/a063880_capsule.py selftest
    python3 studies/a063880_capsule.py build
    python3 studies/a063880_capsule.py verify
"""

from __future__ import annotations

import argparse
from array import array
from datetime import datetime, timezone
import gc
import hashlib
import json
from math import gcd, isqrt
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
DEFAULT_CAPSULE = HERE / "capsules" / "a063880-n10000000"
C_SOURCE = HERE / "a063880_capsule.c"
BOUND = 10_000_000
BLOCK_SIZE = 100_000
SCHEMA = "chiron.research-capsule/1"


class CapsuleRefused(RuntimeError):
    """The frozen evidence or an independently repeated computation disagreed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, value: Any) -> None:
    """Write generated evidence atomically so an interrupted build keeps old data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _git(args: list[str]) -> str | None:
    try:
        run = subprocess.run(["git", *args], cwd=VAULT, text=True, capture_output=True, check=False)
    except OSError:
        return None
    return run.stdout.strip() if run.returncode == 0 else None


def _paths(capsule: Path) -> dict[str, Path]:
    return {
        "formal": capsule / "inputs" / "formal-63880.lean",
        "oeis": capsule / "inputs" / "oeis-A063880.json",
        "members": capsule / "outputs" / "members.txt",
        "blocks": capsule / "outputs" / "block-digests.json",
        "result": capsule / "outputs" / "result.json",
        "manifest": capsule / "manifest.json",
    }


def _oeis_terms(path: Path) -> list[int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("number") != 63880:
        raise CapsuleRefused("frozen OEIS input is not A063880")
    terms = [int(x) for x in str(raw.get("data", "")).split(",") if x.strip()]
    if not terms:
        raise CapsuleRefused("frozen OEIS input has no published terms")
    return terms


# Primary scan: conventional smallest-prime-factor sieve plus a multiplicative
# divisor-sum formula. It is intentionally self-contained and reads no live
# source or ignored cache.
def _primary_spf(limit: int) -> array:
    spf = array("I", range(limit + 1))
    for p in range(2, isqrt(limit) + 1):
        if spf[p] != p:
            continue
        for multiple in range(p * p, limit + 1, p):
            if spf[multiple] == multiple:
                spf[multiple] = p
    return spf


def _primary_member(n: int, spf: array) -> bool:
    sigma = usigma = 1
    value = n
    while value > 1:
        p = int(spf[value])
        power = 1
        while value % p == 0:
            value //= p
            power *= p
        sigma *= (power * p - 1) // (p - 1)
        usigma *= 1 + power
    return sigma == 2 * usigma


def primary_scan(limit: int) -> list[int]:
    spf = _primary_spf(limit)
    try:
        return [n for n in range(1, limit + 1) if _primary_member(n, spf)]
    finally:
        del spf
        gc.collect()


# Independent scan: Euler's linear sieve and a separately written factor loop.
# It intentionally imports no helper from the campaign or from the primary path.
def _linear_spf(limit: int) -> array:
    spf = array("I", [0]) * (limit + 1)
    primes: list[int] = []
    for n in range(2, limit + 1):
        if spf[n] == 0:
            spf[n] = n
            primes.append(n)
        least = int(spf[n])
        for p in primes:
            composite = p * n
            if composite > limit:
                break
            spf[composite] = p
            if p == least:
                break
    return spf


def _independent_member(n: int, spf: array) -> bool:
    all_divisors = unitary_divisors = 1
    remaining = n
    while remaining != 1:
        prime = int(spf[remaining])
        prime_power = 1
        while remaining % prime == 0:
            remaining //= prime
            prime_power *= prime
        all_divisors *= (prime_power * prime - 1) // (prime - 1)
        unitary_divisors *= prime_power + 1
    return all_divisors == 2 * unitary_divisors


def independent_scan(limit: int) -> list[int]:
    spf = _linear_spf(limit)
    try:
        return [n for n in range(1, limit + 1) if _independent_member(n, spf)]
    finally:
        del spf
        gc.collect()


# Definition-level audit. It visits divisors directly, applies the unitary
# definition from the pinned Lean source, and checks every reported member.
def _direct_member_audit(n: int, member_set: set[int]) -> tuple[int, int, bool]:
    sigma = usigma = 0
    has_proper_member_divisor = False
    for divisor in range(1, isqrt(n) + 1):
        if n % divisor:
            continue
        mate = n // divisor
        candidates = (divisor,) if divisor == mate else (divisor, mate)
        for d in candidates:
            sigma += d
            if gcd(d, n // d) == 1:
                usigma += d
            if d != n and d in member_set:
                has_proper_member_divisor = True
    return sigma, usigma, has_proper_member_divisor


def direct_audit(members: list[int], published: list[int]) -> dict[str, Any]:
    member_set = set(members)
    if len(member_set) != len(members):
        raise CapsuleRefused("membership output is not a strictly increasing set")
    transcript: list[str] = []
    primitive: list[int] = []
    for n in members:
        sigma, usigma, has_proper = _direct_member_audit(n, member_set)
        if sigma != 2 * usigma:
            raise CapsuleRefused(f"direct divisor audit rejects reported member n={n}")
        if not has_proper:
            primitive.append(n)
        transcript.append(f"{n}:{sigma}:{usigma}:{int(has_proper)}")
    if members[:len(published)] != published:
        raise CapsuleRefused("computed members do not reproduce the frozen OEIS prefix")
    if primitive != [108]:
        raise CapsuleRefused(f"direct primitive audit found {primitive!r}, expected [108]")
    return {
        "definition_level_members_checked": len(members),
        "published_oeis_terms_checked": len(published),
        "primitive_terms": primitive,
        "direct_transcript_sha256": _sha256_bytes("\n".join(transcript).encode("ascii")),
    }


def _members_text(members: Iterable[int]) -> str:
    return "".join(f"{n}\n" for n in members)


def _block_digests(members: list[int], limit: int) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    cursor = 0
    for start in range(1, limit + 1, BLOCK_SIZE):
        end = min(limit, start + BLOCK_SIZE - 1)
        first = cursor
        while cursor < len(members) and members[cursor] <= end:
            cursor += 1
        subset = members[first:cursor]
        payload = f"{start}:{end}\n" + _members_text(subset)
        blocks.append({
            "start": start,
            "end": end,
            "member_count": len(subset),
            "members_sha256": _sha256_bytes(payload.encode("ascii")),
        })
    return {"bound": limit, "block_size": BLOCK_SIZE, "blocks": blocks}


def _compile_and_run(limit: int) -> tuple[list[int], list[tuple[int, int, int, int]], float, str]:
    """Run the tracked C99 scanner from a disposable directory, never a repo binary."""
    if not C_SOURCE.is_file():
        raise CapsuleRefused(f"missing native scanner source: {C_SOURCE}")
    compiler = os.environ.get("CC", "cc")
    with tempfile.TemporaryDirectory(prefix="chiron-a063880-") as td:
        executable = Path(td) / "a063880-scan"
        compilation = subprocess.run(
            [compiler, "-O3", "-std=c99", "-Wall", "-Wextra", str(C_SOURCE), "-o", str(executable)],
            text=True,
            capture_output=True,
            check=False,
        )
        if compilation.returncode:
            detail = (compilation.stderr or compilation.stdout).strip()[:500]
            raise CapsuleRefused(f"could not compile the pinned C99 scanner: {detail}")
        started = time.monotonic()
        run = subprocess.run([str(executable), str(limit)], text=True, capture_output=True, check=False)
        elapsed = round(time.monotonic() - started, 3)
    if run.returncode:
        detail = (run.stderr or run.stdout).strip()[:500]
        raise CapsuleRefused(f"native scanner refused or failed: {detail}")
    lines = run.stdout.splitlines()
    if len(lines) < 3 or lines[0] != "A063880-CAPSULE/1" or not lines[1].startswith("COUNT ") or lines[-1] != "END":
        raise CapsuleRefused("native scanner emitted an invalid transcript")
    try:
        declared_count = int(lines[1].split()[1])
        records = []
        for line in lines[2:-1]:
            tag, n, sigma, usigma, has_proper = line.split()
            if tag != "M":
                raise ValueError("non-member record")
            records.append((int(n), int(sigma), int(usigma), int(has_proper)))
    except (ValueError, IndexError) as exc:
        raise CapsuleRefused(f"native scanner transcript cannot be parsed: {exc}") from exc
    if len(records) != declared_count:
        raise CapsuleRefused("native scanner count does not match its member records")
    members = [record[0] for record in records]
    if members != sorted(set(members)):
        raise CapsuleRefused("native scanner member records are not strictly sorted and unique")
    return members, records, elapsed, compiler


def _native_audit(members: list[int], records: list[tuple[int, int, int, int]], published: list[int]) -> dict[str, Any]:
    if members[:len(published)] != published:
        raise CapsuleRefused("computed members do not reproduce the frozen OEIS prefix")
    primitive: list[int] = []
    transcript: list[str] = []
    for n, sigma, usigma, has_proper in records:
        if sigma != 2 * usigma:
            raise CapsuleRefused(f"native direct divisor audit rejects reported member n={n}")
        if has_proper not in (0, 1):
            raise CapsuleRefused(f"native primitive flag is invalid at n={n}")
        if not has_proper:
            primitive.append(n)
        transcript.append(f"{n}:{sigma}:{usigma}:{has_proper}")
    if primitive != [108]:
        raise CapsuleRefused(f"native direct primitive audit found {primitive!r}, expected [108]")
    return {
        "definition_level_members_checked": len(members),
        "published_oeis_terms_checked": len(published),
        "primitive_terms": primitive,
        "direct_transcript_sha256": _sha256_bytes("\n".join(transcript).encode("ascii")),
    }


def _run(limit: int, published: list[int]) -> tuple[list[int], dict[str, Any], dict[str, float], str]:
    print(f"  [phase] C99 primary scan, independent linear-sieve scan, and direct audit through {limit:,}", flush=True)
    members, records, elapsed, compiler = _compile_and_run(limit)
    audit = _native_audit(members, records, published)
    return members, audit, {"native_full_replay_seconds": elapsed, "total_seconds": elapsed}, compiler


def _manifest(capsule: Path, result: dict[str, Any], timings: dict[str, float], compiler: str) -> dict[str, Any]:
    paths = _paths(capsule)
    selected_status = _git([
        "status", "--porcelain=v1", "--",
        "studies/a063880_capsule.py", "studies/a063880_capsule.c",
    ])
    return {
        "schema": SCHEMA,
        "status": "bounded-computation",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "claim": {
            "source_label": "DeepMind FormalConjectures A063880",
            "scope": {"lower": 1, "upper": BOUND},
            "member_predicate": "n > 0 and sigma(n) == 2 * usigma(n), with unitary d defined by gcd(d, n / d) == 1",
            "residue_obligation": "every enumerated member has n % 216 == 108",
            "primitive_obligation": "a primitive member has no proper divisor that is also an enumerated member",
        },
        "sources": {
            "formal_conjectures": {
                "repository": "https://github.com/google-deepmind/formal-conjectures",
                "commit": "f776d2f2039351b00737ffcafb9d7d7666e1d9af",
                "path": "FormalConjectures/OEIS/63880.lean",
                "frozen_path": "inputs/formal-63880.lean",
                "sha256": _sha256_file(paths["formal"]),
                "declarations": ["OeisA63880.A", "OeisA63880.mod_216_of_a", "OeisA63880.unique_primitive_108"],
                "notice": "Frozen Apache-2.0 source retains its upstream notice.",
            },
            "oeis": {
                "url": "https://oeis.org/search?q=id:A063880&fmt=json",
                "frozen_path": "inputs/oeis-A063880.json",
                "sha256": _sha256_file(paths["oeis"]),
                "local_cache_mtime_utc": "2026-07-26T16:17:18Z",
                "notice": "Verification reads this frozen response, not the network or ignored cache.",
            },
        },
        "implementation": {
            "capsule_script": "studies/a063880_capsule.py",
            "capsule_script_sha256": _sha256_file(Path(__file__).resolve()),
            "native_scanner": "studies/a063880_capsule.c",
            "native_scanner_sha256": _sha256_file(C_SOURCE),
            "compiler": compiler,
            "vault_git_head": _git(["rev-parse", "HEAD"]),
            "selected_git_status": selected_status.splitlines() if selected_status else [],
            "python": {"implementation": platform.python_implementation(), "version": sys.version, "platform": platform.platform()},
            "replay_command": "python3 studies/a063880_capsule.py verify",
            "methods": {
                "primary": "C99 smallest-prime-factor sieve plus multiplicative sigma/usigma formula",
                "independent": "C99 Euler linear sieve plus separately written factor loop",
                "definition_level_audit": "C99 direct divisor enumeration for every reported member",
            },
        },
        "outputs": result,
        "timings_seconds": timings,
        "nonclaims": [
            "This is not a proof of either unbounded theorem.",
            "This makes no novelty or priority claim.",
            "Agreement of two programs is corroboration, not formal verification of their algorithms.",
            "The formal source snapshot contains statements; this capsule does not prove them in Lean.",
        ],
    }


def build(capsule: Path) -> None:
    paths = _paths(capsule)
    for key in ("formal", "oeis"):
        if not paths[key].is_file():
            raise CapsuleRefused(f"missing frozen input: {paths[key]}")
    published = _oeis_terms(paths["oeis"])
    members, audit, timings, compiler = _run(BOUND, published)
    bad_residues = [n for n in members if n % 216 != 108]
    if bad_residues:
        raise CapsuleRefused(f"residue obligation fails at n={bad_residues[0]}")
    members_text = _members_text(members)
    blocks = _block_digests(members, BOUND)
    _write_text(paths["members"], members_text)
    _write_json(paths["blocks"], blocks)
    result = {
        "schema": "chiron.a063880-result/1",
        "bound": BOUND,
        "verdict": "VERIFIED-TO-N",
        "member_count": len(members),
        "members_sha256": _sha256_bytes(members_text.encode("ascii")),
        "block_digests_path": "outputs/block-digests.json",
        "block_digests_sha256": _sha256_file(paths["blocks"]),
        "residue_counterexamples": [],
        "direct_audit": audit,
        "scope_statement": "Every member found in [1, 10,000,000] is 108 modulo 216; 108 is the only primitive member in that interval. This is bounded evidence, not a proof.",
    }
    _write_json(paths["result"], result)
    result["result_sha256"] = _sha256_file(paths["result"])
    _write_json(paths["manifest"], _manifest(capsule, result, timings, compiler))
    print(f"built {capsule}")
    print(f"  members: {len(members):,}")
    print(f"  members SHA-256: {result['members_sha256']}")
    print(f"  total seconds: {timings['total_seconds']:.3f}")
    print("  verdict: VERIFIED-TO-N (bounded computation; not a proof)")


def _load_members(path: Path) -> list[int]:
    try:
        members = [int(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except ValueError as exc:
        raise CapsuleRefused(f"members output is not one integer per line: {exc}") from exc
    if members != sorted(set(members)):
        raise CapsuleRefused("members output is not strictly sorted and unique")
    return members


def _verify_inputs(manifest: dict[str, Any], capsule: Path) -> None:
    if manifest.get("schema") != SCHEMA:
        raise CapsuleRefused("unexpected capsule schema")
    if manifest.get("claim", {}).get("scope", {}).get("upper") != BOUND:
        raise CapsuleRefused("capsule does not describe the fixed 10,000,000 bound")
    paths = _paths(capsule)
    if _sha256_file(paths["formal"]) != manifest["sources"]["formal_conjectures"]["sha256"]:
        raise CapsuleRefused("pinned formal source hash does not match manifest")
    if _sha256_file(paths["oeis"]) != manifest["sources"]["oeis"]["sha256"]:
        raise CapsuleRefused("frozen OEIS response hash does not match manifest")
    impl = manifest["implementation"]
    if _sha256_file(Path(__file__).resolve()) != impl["capsule_script_sha256"]:
        raise CapsuleRefused("capsule verifier source changed since this evidence was built")
    if _sha256_file(C_SOURCE) != impl["native_scanner_sha256"]:
        raise CapsuleRefused("native scanner source changed since this evidence was built")


def verify(capsule: Path) -> None:
    paths = _paths(capsule)
    required = ("formal", "oeis", "members", "blocks", "result", "manifest")
    missing = [str(paths[key]) for key in required if not paths[key].is_file()]
    if missing:
        raise CapsuleRefused("missing capsule artifact(s): " + ", ".join(missing))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    result = json.loads(paths["result"].read_text(encoding="utf-8"))
    _verify_inputs(manifest, capsule)
    if result.get("schema") != "chiron.a063880-result/1":
        raise CapsuleRefused("unexpected result schema")
    if result.get("bound") != BOUND or result.get("verdict") != "VERIFIED-TO-N":
        raise CapsuleRefused("result record does not describe the fixed bounded verdict")
    manifest_outputs = manifest.get("outputs")
    if not isinstance(manifest_outputs, dict) or any(manifest_outputs.get(key) != value for key, value in result.items()):
        raise CapsuleRefused("manifest output record does not exactly describe result.json")
    expected = _load_members(paths["members"])
    expected_text = _members_text(expected)
    if result.get("member_count") != len(expected):
        raise CapsuleRefused("result member count does not match members output")
    if _sha256_bytes(expected_text.encode("ascii")) != result["members_sha256"]:
        raise CapsuleRefused("members output hash does not match result record")
    if _sha256_file(paths["blocks"]) != result["block_digests_sha256"]:
        raise CapsuleRefused("block digest file hash does not match result record")
    if _sha256_file(paths["result"]) != manifest["outputs"]["result_sha256"]:
        raise CapsuleRefused("result file hash does not match manifest")
    frozen_blocks = json.loads(paths["blocks"].read_text(encoding="utf-8"))
    recomputed, audit, timings, _compiler = _run(BOUND, _oeis_terms(paths["oeis"]))
    if recomputed != expected:
        raise CapsuleRefused("fresh two-path computation does not match frozen membership output")
    bad_residues = [n for n in recomputed if n % 216 != 108]
    if bad_residues or result.get("residue_counterexamples") != []:
        detail = f" at n={bad_residues[0]}" if bad_residues else ""
        raise CapsuleRefused("fresh computation does not support the residue obligation" + detail)
    if _block_digests(recomputed, BOUND) != frozen_blocks:
        raise CapsuleRefused("fresh block digests do not match frozen block digests")
    if audit != result["direct_audit"]:
        raise CapsuleRefused("fresh definition-level audit does not match frozen result")
    print(f"verified {capsule}")
    print(f"  two full exact scans agree on {len(recomputed):,} members through {BOUND:,}")
    print("  direct divisor audit agrees for every reported member; primitive terms: [108]")
    print("  verdict: VERIFIED-TO-N (corroborated bounded computation; not a proof)")
    print(f"  replay seconds: {timings['total_seconds']:.3f}")


def selftest() -> None:
    """Small, no-write gate for both encoders and the direct-definition audit."""
    expected = [108, 540, 756, 1188, 1404, 1836]
    primary = primary_scan(2_000)
    independent = independent_scan(2_000)
    if primary != expected or independent != expected:
        raise CapsuleRefused(f"small-range scan mismatch: primary={primary!r}, independent={independent!r}")
    if direct_audit(primary, expected)["primitive_terms"] != [108]:
        raise CapsuleRefused("small-range primitive audit did not isolate 108")
    native_members, native_records, _elapsed, _compiler = _compile_and_run(2_000)
    if native_members != expected:
        raise CapsuleRefused(f"native small-range scan mismatch: {native_members!r}")
    if _native_audit(native_members, native_records, expected)["primitive_terms"] != [108]:
        raise CapsuleRefused("native small-range primitive audit did not isolate 108")
    print("a063880 capsule self-test: PASS")
    print("  primary and independent scans agree through 2,000")
    print("  Python and C99 encoders agree; definition-level audits isolate primitive 108")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("selftest", "build", "verify"), nargs="?", default="verify")
    parser.add_argument("--capsule", type=Path, default=DEFAULT_CAPSULE)
    args = parser.parse_args(argv)
    try:
        if args.command == "selftest":
            selftest()
        elif args.command == "build":
            build(args.capsule.resolve())
        else:
            verify(args.capsule.resolve())
    except CapsuleRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
