#!/usr/bin/env python3
"""
Knowledge-graph export — turn recovered generators into a portable graph that
other tools can read: JSON-LD, Markdown, and a plain edge list.

    python3 export_graph.py                         # from a built-in cross-domain corpus
    python3 export_graph.py --memory chiron_memory.json   # also include a Congress

Nodes are recovered generators (class, domain, fingerprint). Edges connect
surfaces that share the same structural skeleton — the cross-domain twins the
engine treats as one rule wearing two disguises.
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chiron import collapse, _structural_class  # noqa: E402

OUT = os.path.join(HERE, "export")

# surfaces chosen so some SHARE a skeleton across different inputs/domains
CORPUS = [
    ("evens", "numeric", "2 4 6 8 10 12"),
    ("tens", "numeric", "10 20 30 40 50 60"),          # same skeleton as evens (arithmetic)
    ("powers2", "numeric", "1 2 4 8 16 32"),
    ("powers3", "numeric", "1 3 9 27 81 243"),          # same skeleton as powers2 (geometric)
    ("squares", "numeric", "0 1 4 9 16 25 36"),
    ("fibonacci", "numeric", "0 1 1 2 3 5 8 13 21"),
    ("toggle", "numeric", "1 0 1 0 1 0 1 0"),           # periodic
]


def _nums(s):
    from fractions import Fraction
    return [int(x) if float(x).is_integer() else Fraction(x) for x in s.split()]


def build_nodes(memory_path=None):
    nodes = []
    for name, domain, raw in CORPUS:
        inv = collapse(_nums(raw))
        nodes.append({
            "id": name,
            "input": raw,
            "domain": inv.domain,
            "model_class": inv.model_class,
            "verified": bool(inv.verified),
            "skeleton": _structural_class(inv),
            "family_fingerprint": inv.family_fingerprint[:16],
        })
    if memory_path and os.path.exists(memory_path):
        try:
            with open(memory_path) as f:
                mem = json.load(f)
            laws = mem.get("laws") or mem.get("law_library") or []
            for i, law in enumerate(laws[:200]):
                nodes.append({"id": "law_%d" % i, "input": None,
                              "domain": law.get("domain", "?"),
                              "model_class": law.get("model_class", "?"),
                              "verified": True,
                              "skeleton": law.get("model_class", "?"),
                              "family_fingerprint": str(law.get("fingerprint", ""))[:16]})
        except Exception:
            pass
    return nodes


def build_edges(nodes):
    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            if a["verified"] and b["verified"] and a["skeleton"] == b["skeleton"]:
                edges.append({"from": a["id"], "rel": "shares_structure", "to": b["id"],
                              "skeleton": a["skeleton"]})
    return edges


def to_jsonld(nodes, edges):
    return {
        "@context": {
            "id": "@id", "type": "@type",
            "modelClass": "https://chiron.local/modelClass",
            "domain": "https://chiron.local/domain",
            "skeleton": "https://chiron.local/skeleton",
            "sharesStructure": {"@id": "https://chiron.local/sharesStructure", "@type": "@id"},
        },
        "@graph": (
            [{"id": n["id"], "type": "Generator", "modelClass": n["model_class"],
              "domain": n["domain"], "skeleton": n["skeleton"],
              "sharesStructure": [e["to"] for e in edges if e["from"] == n["id"]]}
             for n in nodes]
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory", default=None)
    args = ap.parse_args()
    nodes = build_nodes(args.memory)
    edges = build_edges(nodes)
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(OUT, "graph.jsonld"), "w") as f:
        json.dump(to_jsonld(nodes, edges), f, indent=2)
    with open(os.path.join(OUT, "edges.tsv"), "w") as f:
        f.write("from\trel\tto\tskeleton\n")
        for e in edges:
            f.write("%s\t%s\t%s\t%s\n" % (e["from"], e["rel"], e["to"], e["skeleton"]))
    md = ["# Knowledge graph export", "",
          "Recovered generators as nodes; edges join surfaces that share one structural "
          "skeleton (cross-domain twins). Regenerate with `python3 export_graph.py`.",
          "", "## Nodes", "", "| id | domain | model class | skeleton | verified |",
          "|---|---|---|---|---|"]
    for n in nodes:
        md.append("| %s | %s | `%s` | `%s` | %s |" % (
            n["id"], n["domain"], n["model_class"], n["skeleton"], n["verified"]))
    md += ["", "## Edges (shared structure)", "", "| from | to | skeleton |", "|---|---|---|"]
    for e in edges:
        md.append("| %s | %s | `%s` |" % (e["from"], e["to"], e["skeleton"]))
    md += ["", "Formats: [`graph.jsonld`](graph.jsonld) (JSON-LD), "
           "[`edges.tsv`](edges.tsv) (edge list)."]
    with open(os.path.join(OUT, "graph.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("wrote export/graph.jsonld, export/graph.md, export/edges.tsv  "
          "(%d nodes, %d shared-structure edges)" % (len(nodes), len(edges)))


if __name__ == "__main__":
    main()
