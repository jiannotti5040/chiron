# Primus as the reference implementation

`invariant_engine.py` (~1,200 lines) is the **clean, readable reference** for the
core operation that grew into Chiron's 30k-line monolith: `collapse` a codified
surface to its minimal generator, with held-out proof and honest residuals.

Where the monolith is exhaustive, this is auditable in one sitting — the same exact
arithmetic, the same hypothesis-class search, the same abstain-or-prove discipline,
without the certification, growth, governance, and physics layers around it. Read it
to understand *what the engine actually does* before reading how Chiron wraps it.

```bash
python3 -c "from invariant_engine import collapse; print(collapse([1,1,2,3,5,8,13,21]).explanation)"
python3 test_invariant_engine.py     # the stress tests
python3 benchmark.py                 # the proving run
```

The production engine is `../Chiron/chiron.py`; this folder is where it began and the
clearest place to read the idea in isolation.
