"""Grower tests — HTML reduction, relevance filter, link extraction, native parity,
OEIS parsing. Run: python Chiron/tests/test_grow.py   (or: pytest Chiron/tests)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chiron_grow as g


def test_html_to_text_strips_scripts():
    t = g.html_to_text("<p>Hello <b>world</b></p><script>evil()</script>")
    assert "Hello world" in t and "evil" not in t


def test_relevance_filter():
    assert g.is_relevant_title("Quantum mechanics")
    assert not g.is_relevant_title("List of prime numbers")
    assert not g.is_relevant_title("Foo (disambiguation)")
    assert not g.is_relevant_title("Index of physics articles")


def test_extract_links_same_domain_only():
    html = '<a href="/b">b</a> <a href="https://other.com/c">c</a>'
    assert g.extract_links(html, "https://site.com/a", True) == ["https://site.com/b"]


def test_native_matches_python():
    import chiron
    seq = [i * i * i - 2 * i + 7 for i in range(24)]
    assert chiron.poly_degree(seq) == chiron._py_poly_degree(seq)


def test_oeis_parse():
    orig = g._get
    g._get = lambda u, ua, timeout=25: {"results": [
        {"number": 45, "data": "0,1,1,2,3,5", "keyword": "core,nonn"}]}
    try:
        rows = g.oeis_page("x", "keyword:core", 0, "ua")
    finally:
        g._get = orig
    assert rows == [("A000045", "0,1,1,2,3,5", ["core", "nonn"])]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print("ok -", fn.__name__)
    print("ALL PASSED (%d)" % len(fns))
