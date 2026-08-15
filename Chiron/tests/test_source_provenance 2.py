# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Safety gates for bounded local-file provenance.

Run: python3 Chiron/tests/test_source_provenance.py
"""
import hashlib
import json
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import source_provenance as provenance


def _write(directory, name, payload):
    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


def test_normal_utf8_record_contains_only_metadata_and_exact_spans():
    with tempfile.TemporaryDirectory(prefix="chiron-source-test-") as directory:
        payload = "aé\nz".encode("utf-8")
        path = _write(directory, "normal.txt", payload)
        record = provenance.register_local_text_file(path, source_id="normal-test", max_bytes=64)

    assert record["schema"] == provenance.SOURCE_RECORD_SCHEMA
    assert record["source_id"] == "normal-test"
    assert record["content_sha256"] == hashlib.sha256(payload).hexdigest()
    assert record["byte_count"] == 5
    assert record["character_count"] == 4
    assert record["line_spans"] == [
        {"line": 1, "byte_start": 0, "byte_end": 4, "character_start": 0, "character_end": 3},
        {"line": 2, "byte_start": 4, "byte_end": 5, "character_start": 3, "character_end": 4},
    ]
    serialized = json.dumps(record, sort_keys=True, ensure_ascii=False)
    assert "aé" not in serialized
    assert "content" not in record


def test_invalid_utf8_is_refused():
    with tempfile.TemporaryDirectory(prefix="chiron-source-test-") as directory:
        path = _write(directory, "invalid.bin", b"\xff\xfe")
        try:
            provenance.register_local_text_file(path)
        except provenance.SourceEncodingError:
            return
    raise AssertionError("invalid UTF-8 should have been refused")


def test_oversized_input_is_refused_before_unbounded_read():
    with tempfile.TemporaryDirectory(prefix="chiron-source-test-") as directory:
        path = _write(directory, "large.txt", b"12345")
        try:
            provenance.register_local_text_file(path, max_bytes=4)
        except provenance.SourceTooLarge:
            return
    raise AssertionError("oversized input should have been refused")


def test_directory_and_missing_paths_are_refused():
    with tempfile.TemporaryDirectory(prefix="chiron-source-test-") as directory:
        for path in (directory, os.path.join(directory, "missing.txt")):
            try:
                provenance.register_local_text_file(path)
            except provenance.SourcePathRefused:
                continue
            raise AssertionError("non-regular path should have been refused")


def test_symlink_path_is_refused():
    with tempfile.TemporaryDirectory(prefix="chiron-source-test-") as directory:
        target = _write(directory, "target.txt", b"safe")
        link = os.path.join(directory, "link.txt")
        os.symlink(target, link)
        try:
            provenance.register_local_text_file(link)
        except provenance.SourcePathRefused:
            return
    raise AssertionError("symlink path should have been refused")


def test_changed_after_read_signature_is_refused():
    """A changed descriptor stat cannot be mistaken for a stable source record."""
    before = SimpleNamespace(st_dev=1, st_ino=2, st_size=2,
                             st_mtime_ns=10, st_ctime_ns=10)
    after = SimpleNamespace(st_dev=1, st_ino=2, st_size=2,
                            st_mtime_ns=11, st_ctime_ns=11)
    with patch.object(provenance, "_open_regular_file", return_value=(91, before)), \
            patch.object(provenance.os, "read", return_value=b"ok"), \
            patch.object(provenance.os, "fstat", return_value=after), \
            patch.object(provenance.os, "close") as close:
        try:
            provenance._read_bounded_snapshot("unused", max_bytes=2)
        except provenance.SourceChangedDuringRead:
            close.assert_called_once_with(91)
            return
    raise AssertionError("a changed file signature should have been refused")


def test_hashes_and_spans_are_deterministic_for_same_snapshot():
    with tempfile.TemporaryDirectory(prefix="chiron-source-test-") as directory:
        path = _write(directory, "stable.txt", "uno\ndos\n".encode("utf-8"))
        first = provenance.register_local_text_file(path, source_id="stable")
        second = provenance.register_local_text_file(path, source_id="stable")

    assert first["content_sha256"] == second["content_sha256"]
    assert first["line_spans"] == second["line_spans"]
    assert first["byte_count"] == second["byte_count"]
    assert first["character_count"] == second["character_count"]


if __name__ == "__main__":
    functions = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for function in functions:
        function()
        print("ok -", function.__name__)
    print("ALL PASSED (%d)" % len(functions))
