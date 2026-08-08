#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Bounded, local-only source registration for UTF-8 text files.

This module turns one *caller-authorized* local file into a small,
JSON-serializable provenance record.  It never traverses directories or
follows symlinks (and fails closed where ``O_NOFOLLOW`` is unavailable), makes
no network calls, and never writes source bytes to a log or persistent store.
Authorization is intentionally outside this primitive: a UI, CLI, or
security-scoped bookmark must decide that the caller may access ``path`` before
calling it.

The returned record is metadata only: a SHA-256 digest, bounded size metadata,
and end-exclusive byte/character spans for each physical line.  It is safe to
persist the record, but it is not a substitute for retaining source text when a
workflow explicitly needs a retrievable corpus.

Run ``python3 source_provenance.py selftest`` for the standalone safety gates.
"""
import argparse
import hashlib
import os
import stat
import tempfile


SOURCE_RECORD_SCHEMA = "chiron.source_record/1"
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
MAX_SOURCE_BYTES = DEFAULT_MAX_BYTES
_READ_CHUNK_BYTES = 64 * 1024
_MAX_SOURCE_ID_CHARACTERS = 256


class SourceRecordError(ValueError):
    """Base class for an input that cannot produce an honest source record."""


class SourcePathRefused(SourceRecordError):
    """The requested path is not a permitted regular local file."""


class SourceTooLarge(SourceRecordError):
    """The requested source exceeds the caller's bounded read limit."""


class SourceEncodingError(SourceRecordError):
    """The source is not strict UTF-8 text."""


class SourceChangedDuringRead(SourceRecordError):
    """The source changed while its bounded snapshot was being collected."""


def _normalise_path(path):
    """Return an absolute path without resolving symlinks or reading a tree."""
    try:
        value = os.fspath(path)
    except TypeError as error:
        raise SourcePathRefused("a local path string is required") from error
    if not isinstance(value, str) or not value or "\x00" in value:
        raise SourcePathRefused("a non-empty local path string is required")
    return os.path.abspath(value)


def _validate_max_bytes(max_bytes):
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise SourceRecordError("max_bytes must be an integer")
    if max_bytes < 0:
        raise SourceRecordError("max_bytes must be non-negative")
    if max_bytes > MAX_SOURCE_BYTES:
        raise SourceRecordError(
            "max_bytes exceeds the source-record hard limit of %d bytes" % MAX_SOURCE_BYTES
        )
    return max_bytes


def _source_id_for(path, source_id):
    """Use a caller identifier, or an opaque stable identifier for the path."""
    if source_id is None:
        # Do not place a raw filesystem path in a record that may later be stored
        # or shared.  The identifier is stable for the same OS path but one-way.
        return "local-file:" + hashlib.sha256(os.fsencode(path)).hexdigest()
    if not isinstance(source_id, str) or not source_id.strip():
        raise SourceRecordError("source_id must be a non-empty string when supplied")
    if len(source_id) > _MAX_SOURCE_ID_CHARACTERS:
        raise SourceRecordError("source_id is longer than %d characters" % _MAX_SOURCE_ID_CHARACTERS)
    if any(character in source_id for character in ("\x00", "\r", "\n")):
        raise SourceRecordError("source_id must not contain control-line separators")
    return source_id


def _timestamp_ns(metadata, field):
    """Read an ns timestamp without eagerly evaluating a missing fallback."""
    value = getattr(metadata, field + "_ns", None)
    if value is not None:
        return value
    return int(getattr(metadata, field) * 1000000000)


def _stat_signature(metadata):
    """Fields that must remain stable while a regular file is being read."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        _timestamp_ns(metadata, "st_mtime"),
        _timestamp_ns(metadata, "st_ctime"),
    )


def _open_regular_file(path):
    """Open exactly one regular file without directory traversal or symlink use."""
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        # Do not weaken this safety boundary into a path-islink precheck: that
        # would be vulnerable to a link swap between check and open.
        raise SourcePathRefused("platform lacks required no-follow file support")
    flags |= nofollow
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise SourcePathRefused("unable to open the requested local source") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SourcePathRefused("only regular local files may be registered")
        return descriptor, metadata
    except Exception:
        os.close(descriptor)
        raise


def _read_bounded_snapshot(path, max_bytes):
    """Read one descriptor up to its declared limit, refusing concurrent changes."""
    descriptor, before = _open_regular_file(path)
    try:
        if before.st_size > max_bytes:
            raise SourceTooLarge("local source exceeds the configured byte limit")

        # Read no more than the declared limit.  The before/after descriptor
        # signature check catches a regular file that grows while this bounded
        # snapshot is in progress.
        remaining = max_bytes
        pieces = []
        while remaining:
            piece = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not piece:
                break
            pieces.append(piece)
            remaining -= len(piece)
        payload = b"".join(pieces)
        if len(payload) > max_bytes:
            raise SourceTooLarge("local source exceeds the configured byte limit")

        after = os.fstat(descriptor)
        if _stat_signature(before) != _stat_signature(after):
            raise SourceChangedDuringRead("local source changed while it was being registered")
        return payload, after
    finally:
        os.close(descriptor)


def _line_spans(text):
    """Return end-exclusive physical-line spans without retaining line content."""
    spans = []
    byte_start = 0
    character_start = 0
    # keepends=True makes each span reproduce exactly the source byte partition;
    # a final newline does not synthesize a contentless additional line.
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        byte_end = byte_start + len(line.encode("utf-8"))
        character_end = character_start + len(line)
        spans.append({
            "line": line_number,
            "byte_start": byte_start,
            "byte_end": byte_end,
            "character_start": character_start,
            "character_end": character_end,
        })
        byte_start = byte_end
        character_start = character_end
    return spans


def register_local_text_file(path, *, source_id=None, max_bytes=DEFAULT_MAX_BYTES):
    """Return a versioned provenance record for one caller-authorized UTF-8 file.

    ``path`` is only opened as one regular file.  It must have been authorized by
    the caller's enclosing interface; this function never expands a directory,
    uploads the source, follows file links, or persists its bytes.
    ``max_bytes`` is bounded globally and can be lowered per call.

    Line offsets are zero-based and end-exclusive.  A line's terminating newline
    belongs to that line, so byte spans partition the exact source payload.
    """
    local_path = _normalise_path(path)
    limit = _validate_max_bytes(max_bytes)
    identifier = _source_id_for(local_path, source_id)
    payload, metadata = _read_bounded_snapshot(local_path, limit)
    try:
        text = payload.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise SourceEncodingError("local source is not valid UTF-8") from error

    return {
        "schema": SOURCE_RECORD_SCHEMA,
        "source_id": identifier,
        "source_kind": "local_text_file",
        "encoding": "utf-8",
        "content_sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
        "character_count": len(text),
        "line_spans": _line_spans(text),
        # This is observation metadata, not an assertion that the file remains
        # unchanged after registration.  Re-indexers can compare it with a new
        # record and its content digest.
        "observed_mtime_ns": _timestamp_ns(metadata, "st_mtime"),
    }


def _selftest():
    """Exercise the safety and determinism contract without persisting content."""
    checks = []

    def check(name, condition):
        checks.append((name, bool(condition)))

    def refuses(error_type, operation):
        try:
            operation()
        except error_type:
            return True
        return False

    with tempfile.TemporaryDirectory(prefix="chiron-source-record-") as directory:
        valid = os.path.join(directory, "valid.txt")
        invalid = os.path.join(directory, "invalid.bin")
        oversized = os.path.join(directory, "oversized.txt")
        linked = os.path.join(directory, "linked.txt")
        with open(valid, "wb") as handle:
            handle.write("aé\nz".encode("utf-8"))
        with open(invalid, "wb") as handle:
            handle.write(b"\xff\xfe")
        with open(oversized, "wb") as handle:
            handle.write(b"12345")
        os.symlink(valid, linked)

        first = register_local_text_file(valid, source_id="selftest", max_bytes=64)
        second = register_local_text_file(valid, source_id="selftest", max_bytes=64)
        check("normal UTF-8 file records metadata", first["byte_count"] == 5 and first["character_count"] == 4)
        check("UTF-8 spans preserve byte and character offsets", first["line_spans"] == [
            {"line": 1, "byte_start": 0, "byte_end": 4, "character_start": 0, "character_end": 3},
            {"line": 2, "byte_start": 4, "byte_end": 5, "character_start": 3, "character_end": 4},
        ])
        check("invalid UTF-8 is refused", refuses(SourceEncodingError,
                                                    lambda: register_local_text_file(invalid)))
        check("oversized input is refused", refuses(SourceTooLarge,
                                                     lambda: register_local_text_file(oversized, max_bytes=4)))
        check("directory paths are refused", refuses(SourcePathRefused,
                                                       lambda: register_local_text_file(directory)))
        check("symlink paths are refused", refuses(SourcePathRefused,
                                                     lambda: register_local_text_file(linked)))
        check("hashes and spans are deterministic", first["content_sha256"] == second["content_sha256"]
              and first["line_spans"] == second["line_spans"])

    passed = sum(1 for _, result in checks if result)
    for name, result in checks:
        if not result:
            print("  FAIL:", name)
    print("  source_provenance.py self-test: %d/%d passed" % (passed, len(checks)))
    return passed == len(checks)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded local UTF-8 source provenance.")
    parser.add_argument("command", choices=("selftest",), help="run the standalone safety gates")
    args = parser.parse_args(argv)
    return 0 if args.command == "selftest" and _selftest() else 1


if __name__ == "__main__":
    raise SystemExit(main())
