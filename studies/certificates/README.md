# Legacy, non-evidentiary artifacts

The JSON and text files in this directory were produced by a retired workflow
that serialized hand-authored prose into a general-purpose governance engine.
It did not replay the mathematical computations or bind them to frozen source,
code, and input revisions.

They are retained for audit history only. They must not be cited as proof,
counterexample certificates, or independent validation of a mathematical
claim. `studies/certify_conjectures.py` and
`studies/witness_certificate.py` now refuse to create new artifacts.

New work must use target-specific executable replay checkers with independently
implemented validation paths. A refutation of a Formal Conjectures statement
also needs a minimal Lean witness against the pinned upstream revision before
it is suitable for public review.
