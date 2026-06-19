# Knowledge graph export

Recovered generators as nodes; edges join surfaces that share one structural skeleton (cross-domain twins). Regenerate with `python3 export_graph.py`.

## Nodes

| id | domain | model class | skeleton | verified |
|---|---|---|---|---|
| evens | numeric | `arithmetic` | `polynomial:1` | True |
| tens | numeric | `arithmetic` | `polynomial:1` | True |
| powers2 | numeric | `geometric` | `geometric` | True |
| powers3 | numeric | `geometric` | `geometric` | True |
| squares | numeric | `polynomial_deg2` | `polynomial:2` | True |
| fibonacci | numeric | `linear_recurrence_order2` | `linear_recurrence:2` | True |
| toggle | numeric | `periodic_2` | `periodic:2` | True |

## Edges (shared structure)

| from | to | skeleton |
|---|---|---|
| evens | tens | `polynomial:1` |
| powers2 | powers3 | `geometric` |

Formats: [`graph.jsonld`](graph.jsonld) (JSON-LD), [`edges.tsv`](edges.tsv) (edge list).
