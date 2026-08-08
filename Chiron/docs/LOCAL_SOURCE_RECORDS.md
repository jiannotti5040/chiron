# Bounded local source records

`source_provenance.py` registers one caller-authorized UTF-8 text file as a
metadata-only, versioned record. It is a local primitive for source identity
and precise citation spans; it is not a crawler, file indexer, or persistent
corpus.

```python
from source_provenance import register_local_text_file

record = register_local_text_file(
    selected_path,                 # authorized by the surrounding UI/CLI
    source_id="document:42",       # optional stable application identifier
    max_bytes=2 * 1024 * 1024,      # per-call limit; hard ceiling is 8 MiB
)
```

The result has schema `chiron.source_record/1` and contains only:

- a source identifier (an opaque path-derived identifier if none is supplied);
- `content_sha256`, byte and character counts, and the observed modification
  timestamp;
- zero-based, end-exclusive `line_spans` with byte and character offsets.

A terminating newline belongs to its preceding line; no empty line is invented
after a final newline. The module never puts original text or a raw filesystem
path in the record. `source_id` is caller-controlled and must likewise be an
identifier, never source text.

## Boundaries

The enclosing interface must authorize file selection before invoking this
function. The primitive opens exactly one regular file, rejects directories and
symlinks, caps reads at the supplied limit (never above 8 MiB), requires strict
UTF-8, refuses a file that changes during the read, makes no network request,
and writes no logs or other persistent data. Callers that need stored text,
PDF parsing, recursive indexing, deletion, or re-indexing must add those
capabilities behind their own explicit authorization and privacy policy.

Run its standalone gates with:

```bash
python3 Chiron/source_provenance.py selftest
python3 Chiron/tests/test_source_provenance.py
```
