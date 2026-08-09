#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Emit a software bill of materials from observed evidence, not assertion.

The security model used to say the Python core "relies on the standard
library". It does not: Primus declares numpy and imports it at module level.
That paragraph was the dependency-surface claim an SBOM would rest on, so the
honest fix is to stop asserting the surface and start reading it.

Everything here is derived from files in the tree:

    Primus/pyproject.toml      declared runtime and optional dependencies
    Chiron/manifest.json       per-module stdlib_only, written by build_manifest
    App/Package.swift          Swift package dependencies

Nothing is queried from a network and no version is resolved beyond what is
written down, so this runs offline and in CI. A declared range is reported as
a range: pinning it here would invent precision the repository does not have.

    python3 ci/sbom.py              human summary
    python3 ci/sbom.py --json       CycloneDX-style document
    python3 ci/sbom.py --check      non-zero if an undeclared import appears
"""
import json
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = "chiron.sbom/1"


def _read(path):
    with open(os.path.join(VAULT, path), "r", encoding="utf-8") as fh:
        return fh.read()


def python_dependencies():
    """Declared Python dependencies, runtime and optional, from pyproject."""
    text = _read("Primus/pyproject.toml")
    out = []

    runtime = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text,
                        re.S | re.M)
    for spec in re.findall(r'"([^"]+)"', runtime.group(1) if runtime else ""):
        out.append({"name": re.split(r"[<>=!~]", spec)[0].strip(),
                    "version_constraint": spec,
                    "scope": "required",
                    "ecosystem": "pypi",
                    "declared_in": "Primus/pyproject.toml"})

    optional = re.search(r"^\[project\.optional-dependencies\](.*?)(?=^\[)",
                         text, re.S | re.M)
    if optional:
        for extra, body in re.findall(r"^(\w+)\s*=\s*\[(.*?)\]",
                                      optional.group(1), re.S | re.M):
            for spec in re.findall(r'"([^"]+)"', body):
                out.append({"name": re.split(r"[<>=!~]", spec)[0].strip(),
                            "version_constraint": spec,
                            "scope": f"optional:{extra}",
                            "ecosystem": "pypi",
                            "declared_in": "Primus/pyproject.toml"})
    return out


def swift_dependencies():
    """External Swift packages. Expected to be empty; verified, not assumed."""
    text = _read("App/Package.swift")
    return [{"name": url.rsplit("/", 1)[-1].removesuffix(".git"),
             "version_constraint": "see Package.swift",
             "scope": "required",
             "ecosystem": "swiftpm",
             "declared_in": "App/Package.swift"}
            for url in re.findall(r'\.package\(url:\s*"([^"]+)"', text)]


def non_stdlib_modules():
    """Vault modules that build_manifest observed importing beyond stdlib."""
    manifest = json.loads(_read("Chiron/manifest.json"))
    return sorted(s["script"] for s in manifest["scripts"]
                  if not s.get("stdlib_only", True))


def document():
    py = python_dependencies()
    swift = swift_dependencies()
    modules = non_stdlib_modules()
    return {
        "schema": SCHEMA,
        "note": ("Derived from declarations in the tree. No network lookup, no "
                 "resolved lockfile — a declared range is reported as a range "
                 "rather than pinned to a version this repository does not "
                 "record."),
        "components": py + swift,
        "observations": {
            "swift_third_party_count": len(swift),
            "python_required_count": len([c for c in py if c["scope"] == "required"]),
            "python_optional_count": len([c for c in py if c["scope"] != "required"]),
            "vault_modules_importing_beyond_stdlib": modules,
        },
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    doc = document()

    if "--json" in argv:
        print(json.dumps(doc, indent=2))
        return 0

    if "--check" in argv:
        # A dependency that appears in the manifest's non-stdlib set but in no
        # declaration is the case worth failing on: it means something is
        # imported that nothing promises to install.
        declared = {c["name"].lower() for c in doc["components"]}
        # Known-optional third-party imports guarded at their call site.
        guarded = {"numpy", "gplearn", "scikit-learn", "sklearn", "scipy"}
        unknown = []
        manifest = json.loads(_read("Chiron/manifest.json"))
        for script in manifest["scripts"]:
            if script.get("stdlib_only", True):
                continue
            for name in script.get("imports", []):
                base = name.split(".")[0].lower()
                if base in declared or base in guarded:
                    continue
                # Intra-vault imports are not dependencies.
                if any(base == s["script"].lower() for s in manifest["scripts"]):
                    continue
                unknown.append((script["script"], name))
        if unknown:
            print("sbom: undeclared third-party imports:")
            for script, name in sorted(set(unknown)):
                print(f"  {script} imports {name}")
            return 1
        print("sbom: every third-party import is declared or guarded")
        return 0

    obs = doc["observations"]
    print(f"[sbom] {SCHEMA}")
    print(f"  Swift third-party packages : {obs['swift_third_party_count']}")
    print(f"  Python required            : {obs['python_required_count']}")
    print(f"  Python optional            : {obs['python_optional_count']}")
    for component in doc["components"]:
        print(f"    {component['ecosystem']:8} {component['version_constraint']:24} "
              f"[{component['scope']}]")
    modules = obs["vault_modules_importing_beyond_stdlib"]
    print(f"  Vault modules beyond stdlib: {len(modules)}")
    print("    " + ", ".join(modules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
