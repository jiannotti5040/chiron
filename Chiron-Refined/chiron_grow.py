#!/usr/bin/env python3
# ============================================================================
#  chiron_grow.py — the operator-directed grower for CHIRON
#  Architect & sole owner: Jacob Iannotti. Proprietary — all rights reserved.
#
#  Runs LOCALLY. This is the network-capable companion, deliberately SEPARATE
#  from the offline monolith: chiron.py stays deterministic and offline; only
#  this runner reaches out, and only when you run it.
#
#  Each cycle it (optionally) pulls the current Congress from GitHub, fetches
#  public articles topic-by-topic, feeds each through Chiron — which analyzes how
#  it fits, spawns or extends a domain, classifies it integral vs general, and
#  grows — then pushes the grown Congress back to GitHub when it fills. Run it
#  whenever you like; it resumes where it left off, so it grows continuously.
#
#  Wikipedia needs NO API key — only a descriptive User-Agent (set in
#  parameters.json). For any other source, fill in source.api_url / api_key.
#
#  Usage:
#     python3 chiron_grow.py                  # use parameters.json beside this file
#     python3 chiron_grow.py --params my.json
#     python3 chiron_grow.py --dry-run        # offline demo on a built-in sample
# ============================================================================
import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# SSL on macOS: the stock python.org build ships without a CA bundle, so HTTPS
# verification fails ("CERTIFICATE_VERIFY_FAILED"). Use certifi if present; if
# verification is impossible, auto-fall back to unverified TLS — acceptable for
# read-only fetches of public articles — so the grower just runs anywhere.
_SSL = {"ctx": None, "verify": True, "fell_back": False}


def _ssl_ctx():
    if _SSL["ctx"] is not None:
        return _SSL["ctx"]
    if not _SSL["verify"]:
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
    else:
        try:
            import certifi
            c = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            c = ssl.create_default_context()
    _SSL["ctx"] = c
    return c

DEFAULT_PARAMS = {
    "congress_path": "chiron_memory.json",
    "topics": ["law", "programming", "computation", "physics", "electronics",
               "mathematics", "statistics", "linguistics", "language",
               "communication", "semantics", "heuristics", "psychology",
               "artificial intelligence", "chemistry", "biology", "technology",
               "government", "medicine", "philosophy", "debate", "rhetoric",
               "art", "music", "economics", "humanities", "poetry", "literature"],
    "articles_per_topic": 100,
    "max_chars_per_item": 8000,
    "links_per_article": 20,
    "frontier_per_pass": 400,
    "frontier_max": 20000,
    "random_when_idle": 10,
    "push_when_mb": 5.0,
    "max_congress_mb": 25.0,
    "rate_limit_seconds": 0.5,
    "author": "Wikipedia contributors",
    "resume_state": "chiron_grow_state.json",
    "source": {"name": "wikipedia",
               "api_url": "https://en.wikipedia.org/w/api.php",
               "user_agent": "Chiron-Grow/1.0 (operator-directed; contact: you@example.com)",
               "verify_ssl": True,
               "api_key": ""},
    "git": {"push": True, "pull_first": True, "branch": "main"},
}

# A tiny built-in corpus so `--dry-run` proves the whole loop offline (no net/git).
_SAMPLE = {
    "mathematics": [("Fibonacci number", "The Fibonacci sequence: 1 1 2 3 5 8 13 21 34 55 89 144."),
                    ("Triangular number", "Triangular numbers: 1 3 6 10 15 21 28 36 45 55.")],
    "physics":     [("Powers of two", "Common powers of two in computing: 2 4 8 16 32 64 128 256 512.")],
    "philosophy":  [("Epistemology", "Epistemology studies knowledge, justification, and the rationality of belief.")],
    "law":         [("Rule of law", "The rule of law is the principle that all persons and institutions are accountable to law.")],
}


def load_params(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            p = json.load(f)
        for k, v in DEFAULT_PARAMS.items():
            p.setdefault(k, v)
        return p
    return dict(DEFAULT_PARAMS)


_THROTTLE = {"last": 0.0, "min": 0.0}    # min seconds between ANY two requests (anti-429)


def _fetch(url, ua, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    for attempt in range(6):
        gap = _THROTTLE["min"] - (time.perf_counter() - _THROTTLE["last"])
        if gap > 0:
            time.sleep(gap)
        _THROTTLE["last"] = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            # 429 = rate-limited. Wait what the server asks (Retry-After), else an
            # escalating backoff, then retry the SAME request — don't abort the batch.
            if e.code == 429 and attempt < 5:
                ra = e.headers.get("Retry-After") if getattr(e, "headers", None) else None
                wait = float(ra) if (ra and str(ra).isdigit()) else min(20 * (2 ** attempt), 300)
                print("  [429 rate-limited by source — waiting %ds]" % int(wait))
                time.sleep(wait); continue
            raise
        except urllib.error.URLError as e:
            # macOS Python without a CA bundle raises CERTIFICATE_VERIFY_FAILED on
            # read-only public fetches; fall back to unverified TLS once, then retry.
            reason = str(getattr(e, "reason", e))
            if (not _SSL["fell_back"]) and ("CERTIFICATE_VERIFY" in reason or "SSL" in reason):
                _SSL["fell_back"] = True; _SSL["verify"] = False; _SSL["ctx"] = None
                print("  [ssl] CA verification unavailable; continuing with unverified TLS")
                continue
            raise
    raise urllib.error.URLError("max retries exceeded (rate limit)")


def _get(url, ua, timeout=25):
    return json.loads(_fetch(url, ua, timeout).decode("utf-8", "replace"))


def _get_text(url, ua, timeout=25):
    return _fetch(url, ua, timeout).decode("utf-8", "replace")


# --- generic web source: any website / web connection -----------------------
_RE_SCRIPT = re.compile(r"(?is)<(script|style|noscript|head|nav|footer|header|aside)[^>]*>.*?</\1>")
_RE_TAG = re.compile(r"<[^>]+>")
_RE_HREF = re.compile(r'(?i)href\s*=\s*["\']([^"\']+)')


def html_to_text(html_doc):
    import html as _html
    h = _RE_SCRIPT.sub(" ", html_doc)
    t = _RE_TAG.sub(" ", h)
    t = _html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def extract_links(html_doc, base_url, same_domain_only=False):
    base_host = urllib.parse.urlparse(base_url).netloc
    out, seen = [], set()
    for m in _RE_HREF.finditer(html_doc):
        u = urllib.parse.urljoin(base_url, m.group(1)).split("#")[0]
        p = urllib.parse.urlparse(u)
        if p.scheme not in ("http", "https"):
            continue
        if same_domain_only and p.netloc != base_host:
            continue
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def web_text(url, ua):
    return html_to_text(_get_text(url, ua))


def web_links(url, ua, limit=20, same_domain_only=False):
    return extract_links(_get_text(url, ua), url, same_domain_only)[:max(0, limit)]


def api_items(list_url, ua, items_path="", id_field="id"):
    # Pull a list of item keys from any JSON API. items_path walks nested dicts
    # (dot-separated) to the array; each item yields id_field (or the item itself).
    node = _get(list_url, ua)
    for key in [k for k in items_path.split(".") if k]:
        node = node.get(key) if isinstance(node, dict) else None
    out = []
    for it in (node or []):
        if isinstance(it, dict):
            if id_field in it:
                out.append(str(it[id_field]))
        elif isinstance(it, str):
            out.append(it)
    return out


def wiki_titles(api_url, topic, limit, offset, ua):
    q = {"action": "query", "list": "search", "srsearch": topic,
         "srlimit": max(1, min(50, limit)), "sroffset": offset, "format": "json"}
    d = _get(api_url + "?" + urllib.parse.urlencode(q), ua)
    return [it["title"] for it in d.get("query", {}).get("search", [])]


_WIKI_LINKS_CACHE = {}     # title -> links, captured alongside the extract in ONE request
_WIKI_TEXT_CACHE = {}      # title -> extract, captured by a BATCH prefetch (anti-429)

# Low-value pages the crawl should not waste requests on (disambiguation, lists, etc.)
_SKIP_TITLE = re.compile(r"\((disambiguation)\)\s*$|^(List of|Index of|Outline of|Glossary of)\b", re.I)


def is_relevant_title(title):
    return bool(title) and not _SKIP_TITLE.search(title)


def wiki_prefetch(api_url, titles, ua, links_limit=500):
    # Pull text + links for up to ~20 titles in ONE request and cache them, so the
    # per-article consider() calls hit cache instead of the network (~20x fewer calls).
    titles = [t for t in dict.fromkeys(titles) if t][:20]
    if not titles:
        return
    q = {"action": "query", "prop": "extracts|links", "explaintext": 1, "redirects": 1,
         "plnamespace": 0, "pllimit": links_limit, "titles": "|".join(titles), "format": "json"}
    try:
        d = _get(api_url + "?" + urllib.parse.urlencode(q), ua)
    except Exception:
        return
    for _, pg in d.get("query", {}).get("pages", {}).items():
        t = pg.get("title")
        if not t:
            continue
        _WIKI_TEXT_CACHE[t] = pg.get("extract", "") or ""
        _WIKI_LINKS_CACHE[t] = [l["title"] for l in pg.get("links", []) if l.get("title")]


def wiki_text(api_url, title, ua):
    cached = _WIKI_TEXT_CACHE.pop(title, None)     # served by a batch prefetch?
    if cached is not None:
        return cached
    q = {"action": "query", "prop": "extracts|links", "explaintext": 1, "redirects": 1,
         "plnamespace": 0, "pllimit": 200, "titles": title, "format": "json"}
    d = _get(api_url + "?" + urllib.parse.urlencode(q), ua)
    for _, pg in d.get("query", {}).get("pages", {}).items():
        _WIKI_LINKS_CACHE[title] = [l["title"] for l in pg.get("links", []) if l.get("title")]
        return pg.get("extract", "") or ""
    return ""


def oeis_page(search_url, query, offset, ua):
    # OEIS search API -> structured integer sequences (the engine's ideal food).
    # Each result's 'data' is a comma-separated sequence; 'keyword' gives the subject.
    q = {"q": query, "fmt": "json", "start": int(offset)}
    d = _get(search_url + "?" + urllib.parse.urlencode(q), ua)
    out = []
    for r in (d.get("results") or []):
        num, data = r.get("number"), (r.get("data") or "")
        kw = [k for k in (r.get("keyword") or "").split(",") if k]
        if num is not None and data:
            out.append(("A%06d" % num, data, kw))
    return out


def wiki_links(api_url, title, ua, limit=20):
    # Reuse the links captured with the extract (no extra request). Only if the text
    # wasn't fetched first do we make a dedicated links call.
    cached = _WIKI_LINKS_CACHE.pop(title, None)
    if cached is not None:
        return cached[:max(0, limit)]
    q = {"action": "query", "prop": "links", "plnamespace": 0,
         "pllimit": max(1, min(500, limit)), "titles": title, "format": "json"}
    d = _get(api_url + "?" + urllib.parse.urlencode(q), ua)
    out = []
    for _, pg in d.get("query", {}).get("pages", {}).items():
        for l in pg.get("links", []):
            t = l.get("title")
            if t:
                out.append(t)
    return out


def wiki_random(api_url, ua, n=5):
    # Fallback discovery: pull random real articles so the grower keeps finding
    # genuinely new material even once the seed topics are exhausted.
    q = {"action": "query", "list": "random", "rnnamespace": 0,
         "rnlimit": max(1, min(20, n)), "format": "json"}
    d = _get(api_url + "?" + urllib.parse.urlencode(q), ua)
    return [it["title"] for it in d.get("query", {}).get("random", [])]


_SRC_PREFIXES = ("wikipedia:", "web:", "api:", "oeis:")


def seen_from_congress(path):
    # The Congress carries an authoritative ledger of every source it has eaten
    # (Chiron.save_memory -> "ingested_sources"). Re-derive seen keys from it so a
    # fresh/cleared crawl state — or a different machine — never re-ingests anything.
    s = set()
    try:
        doc = json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        return s
    for src in doc.get("ingested_sources", []):
        if not isinstance(src, str):
            continue
        for pre in _SRC_PREFIXES:
            if src.startswith(pre):
                s.add(src[len(pre):]); break
    return s


def git(args, cwd=HERE):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def size_mb(path):
    return os.path.getsize(path) / 1e6 if os.path.exists(path) else 0.0


def main(argv=None):
    ap = argparse.ArgumentParser(description="CHIRON operator-directed grower")
    ap.add_argument("--params", default=os.path.join(HERE, "parameters.json"))
    ap.add_argument("--dry-run", action="store_true", help="offline demo: built-in sample, no network, no git")
    ap.add_argument("--reset", action="store_true", help="wipe to a clean seed Congress + clear resume state, then exit")
    ap.add_argument("--once", action="store_true", help="run a single pass through the topics, then exit")
    ap.add_argument("--serve", action="store_true", help="also open the live dashboard while crawling (one command)")
    ap.add_argument("--port", type=int, default=8765, help="dashboard port for --serve")
    args = ap.parse_args(argv)
    P = load_params(args.params)

    sys.path.insert(0, HERE)
    try:
        import chiron
    except Exception as e:
        print("ERROR: chiron.py must sit beside chiron_grow.py (", e, ")"); return 2

    # Paths resolve relative to the params file's folder, so ONE shared engine can
    # drive any subfolder (grow-public/, grow-private/, …) by pointing --params at it.
    base = os.path.dirname(os.path.abspath(args.params))
    def _abs(p):
        return p if os.path.isabs(p) else os.path.join(base, p)
    cong = _abs(P["congress_path"])
    state_path = _abs(P.get("resume_state", "chiron_grow_state.json"))
    gitcfg, src = P.get("git", {}), P.get("source", {})
    ua = src.get("user_agent", "Chiron-Grow/1.0")
    api_url = src.get("api_url")
    _SSL["verify"] = bool(src.get("verify_ssl", True))
    _SSL["ctx"] = None
    topics = P["topics"]; per = int(P.get("articles_per_topic", 25))
    thresh = float(P.get("push_when_mb", 5.0)); rl = float(P.get("rate_limit_seconds", 0.5))
    _THROTTLE["min"] = rl                 # pace EVERY request (search/text/links), not just per-article
    max_mb = float(P.get("max_congress_mb", 25.0)); author = P.get("author", "Wikipedia contributors")
    links_per_article = int(P.get("links_per_article", 20))
    frontier_per_pass = int(P.get("frontier_per_pass", 400))
    frontier_max = int(P.get("frontier_max", 20000))
    random_when_idle = int(P.get("random_when_idle", 10))
    max_chars = int(P.get("max_chars_per_item", 8000))   # bound per-item storage (slim Congress)

    if args.reset:
        chiron.Chiron().save_memory(cong)
        if os.path.exists(state_path):
            os.remove(state_path)
        print("[reset] clean seed Congress written to %s (%.4f MB); resume state cleared."
              % (cong, size_mb(cong)))
        return 0

    if not args.dry_run and gitcfg.get("pull_first"):
        print("[sync] pulling current Congress from GitHub…"); git(["pull", "--rebase"])

    org = chiron.Chiron.load_memory(cong) if os.path.exists(cong) else chiron.Chiron()
    if args.dry_run:
        state = {"offsets": {}, "seen": [], "passes": 0}      # dry-run never touches real resume state
    else:
        state = json.load(open(state_path)) if os.path.exists(state_path) else {"offsets": {}, "seen": [], "passes": 0}
    seen = set(state.get("seen", []))
    offsets = dict(state.get("offsets", {}))
    frontier = list(state.get("frontier", []))     # self-extending crawl queue (BFS over article links)
    frontier_set = set(frontier)
    item_domain = dict(state.get("item_domain", {}))  # subject carried from parent -> linked children
    if not args.dry_run:
        # The Congress travels via GitHub; the local resume state does not. Re-derive
        # what's already ingested from the Congress so a fresh/cleared state — or a
        # different machine — never re-ingests the same article.
        before = len(seen); seen |= seen_from_congress(cong)
        if len(seen) > before:
            print("[resume] recognized %d already-ingested articles from the Congress" % (len(seen) - before))

    if args.serve and not args.dry_run:                 # one command: crawl + live dashboard
        try:
            import chiron as _ch, threading as _th
            _th.Thread(target=_ch._serve_dashboard,
                       args=(["--congress", cong, "--port", str(args.port)],), daemon=True).start()
        except Exception as _e:
            print("[serve] could not start dashboard:", _e)

    push_marker = [size_mb(cong)]      # Congress size at last push; push again only after +push_when_mb growth

    def push(reason=""):
        if args.dry_run:                                # NEVER mutate the real Congress in a dry run
            tmp = cong + ".dryrun"
            org.save_memory(tmp); sz = size_mb(tmp)
            try:
                os.remove(tmp)
            except OSError:
                pass
            print("  [dry-run: would be %.2f MB; real Congress untouched]" % sz); return
        org.save_memory(cong)
        if size_mb(cong) > max_mb:                      # auto-compaction: grow forever, repo stays bounded
            info = org.compact(); org.save_memory(cong)
            print("  [compacted -> %.2f MB; trimmed %s; kept %d laws]"
                  % (size_mb(cong), info["trimmed"], info["integral_laws_kept"]))
        push_marker[0] = size_mb(cong)                  # reset the growth counter at every push
        if not gitcfg.get("push"):
            print("  [saved %.2f MB locally]" % size_mb(cong)); return
        git(["add", cong])
        git(["add", state_path])              # Congress + crawl cursor both travel
        git(["commit", "-m", "grow: Congress %.2f MB %s" % (size_mb(cong), reason)])
        r = git(["push", "origin", gitcfg.get("branch", "main")])
        print("  [pushed to GitHub + saved locally]" if r.returncode == 0
              else "  [saved locally; push failed: %s]" % r.stderr.strip()[:120])
        if gitcfg.get("pull_first"):
            git(["pull", "--rebase"])

    def save_state():
        if args.dry_run:
            return
        org.save_memory(cong)        # keep the Congress on disk in lock-step with the
                                     # cursor, so a hard kill never loses fetched work
                                     # and the dashboard reflects live progress
        json.dump({"offsets": offsets, "seen": list(seen), "frontier": frontier,
                   "item_domain": item_domain, "passes": state.get("passes", 0)},
                  open(state_path, "w"))

    def queue(title, domain=None):
        if smode == "wikipedia" and not is_relevant_title(title):
            return                                       # skip disambiguation/list/index pages
        if title not in seen and title not in frontier_set and len(frontier) < frontier_max:
            frontier.append(title); frontier_set.add(title)
            if domain:
                item_domain[title] = domain

    # --- source adapters: ONE engine, any input (wikipedia / web / api) ------
    smode = src.get("name", "wikipedia")
    src_prefix = {"wikipedia": "wikipedia:", "web": "web:", "api": "api:"}.get(smode, smode + ":")
    same_dom = bool(src.get("same_domain_only", False))

    def text_of(key):
        if smode == "web":
            return web_text(key, ua)
        if smode == "api":
            tmpl = src.get("item_url_template")
            return web_text(tmpl.format(id=key), ua) if tmpl else _get_text(key, ua)
        return wiki_text(api_url, key, ua)

    def links_of(key):
        if smode == "web":
            return web_links(key, ua, links_per_article, same_dom)
        if smode == "wikipedia":
            return wiki_links(api_url, key, ua, links_per_article)
        return []

    def random_keys(n):
        return wiki_random(api_url, ua, n) if smode == "wikipedia" else []

    def consider(key, text=None, domain=None):
        # Ingest one item: dedup, fetch, assimilate under its SUBJECT, then harvest
        # its links into the frontier (carrying the same subject) so the crawl keeps
        # extending itself and the Congress organizes by subject. Returns 1 if ingested.
        if key in seen:
            return 0
        if smode == "wikipedia" and not is_relevant_title(key):
            seen.add(key); return 0                    # disambiguation/list/index -> not worth a request
        if text is None and not args.dry_run:
            try:
                text = text_of(key)
            except Exception:
                return 0                               # transient fetch error -> retry later (not marked seen)
        seen.add(key)
        if not text or len(text) < 12:
            return 0
        if max_chars > 0 and len(text) > max_chars:    # bound per-item storage (slim Congress)
            text = text[:max_chars]
        try:
            res = org.assimilate(text, source=src_prefix + key, author=author, domain_hint=domain)
        except Exception as e:
            print("  [skip %s: %s]" % (key[:30], str(e)[:50])); return 0
        print("  + %-38s [%-12s %-8s] domains=%s laws=%s  %.2fMB"
              % (key[:38], (res.get("domain") or "")[:12], res.get("classification"),
                 res["congress"]["domains"], res["congress"]["integral"], size_mb(cong)))
        if not args.dry_run and links_per_article > 0:
            try:
                for lt in links_of(key):
                    queue(lt, domain)                  # children inherit the parent's subject
            except Exception:
                pass
        if size_mb(cong) - push_marker[0] >= thresh:   # push per +push_when_mb of GROWTH (not absolute size)
            push("(full)")
        return 1                          # request pacing is handled globally in _fetch

    control_path = os.path.join(os.path.dirname(cong), "chiron_control.json")
    applied_source = None

    mode = "single pass (--once)" if args.once else "dry-run (one demo pass)" if args.dry_run else "CONTINUOUS"
    print("[grow] %s — Ctrl-C to stop." % mode)
    try:
        while True:
            state["passes"] = state.get("passes", 0) + 1
            print("==== pass %d ====" % state["passes"]); new_this_pass = 0
            # operator redirect: pick up a new feed set from the dashboard, if any
            if not args.dry_run:
                try:
                    ns = (json.load(open(control_path)).get("source")
                          if os.path.exists(control_path) else None)
                except Exception:
                    ns = None
                if ns and ns != applied_source:
                    src = ns
                    smode = src.get("name", "wikipedia")
                    src_prefix = {"wikipedia": "wikipedia:", "web": "web:", "api": "api:",
                                  "oeis": "oeis:"}.get(smode, smode + ":")
                    same_dom = bool(src.get("same_domain_only", False))
                    api_url = src.get("api_url", api_url)
                    ua = src.get("user_agent", ua)
                    _SSL["verify"] = bool(src.get("verify_ssl", True)); _SSL["ctx"] = None
                    frontier.clear(); frontier_set.clear(); item_domain.clear()
                    applied_source = ns
                    print("  [redirect] now consuming: %s %s" % (smode,
                          str(src.get("seeds") or src.get("query") or src.get("list_url") or "")[:80]))
                    save_state()
            if not args.dry_run and gitcfg.get("pull_first"):
                git(["pull", "--rebase"])
            # 1) seed the pass. wikipedia: topic search (deepening each pass).
            #    web: the configured seed URLs.  api: a list endpoint. All three
            #    then feed the same self-extending frontier in step 2.
            if args.dry_run or smode == "wikipedia":
                # rotate the starting topic each pass so EVERY subject gets covered
                # even if a pass is interrupted (otherwise it always restarts at topic 0)
                _rot = ((state["passes"] - 1) % len(topics)) if topics else 0
                for topic in (topics[_rot:] + topics[:_rot]):
                    got = 0; off = int(offsets.get(topic, 0))
                    while got < per:
                        try:
                            batch = (list(_SAMPLE.get(topic, [])) if args.dry_run
                                     else [(t, None) for t in wiki_titles(api_url, topic, per - got, off, ua)])
                        except Exception as e:
                            print("  [fetch error: %s] backing off 30s" % str(e)[:90]); time.sleep(30); break
                        if not batch:
                            break
                        if not args.dry_run and smode == "wikipedia":
                            wiki_prefetch(api_url, [t for t, _ in batch], ua, links_per_article)
                        for item in batch:
                            n = consider(item[0], item[1], domain=topic)   # subject = the topic
                            got += n; new_this_pass += n
                            if got >= per:
                                break
                        off += len(batch)
                        if args.dry_run:
                            break
                    offsets[topic] = off
                    save_state()
            elif smode == "web":
                label = src.get("domain_label")        # e.g. "regulation"; else subject = the site
                for u in src.get("seeds", []):
                    queue(u, label or urllib.parse.urlparse(u).netloc)
            elif smode == "api":
                try:
                    label = src.get("domain_label", "api")
                    for k in api_items(src.get("list_url", ""), ua,
                                       src.get("items_path", ""), src.get("id_field", "id")):
                        queue(k, label)
                except Exception as e:
                    print("  [api list error: %s] backing off 30s" % str(e)[:80]); time.sleep(30)
            elif smode == "oeis":                       # STRUCTURED data — the engine's ideal food
                search_url = src.get("search_url", "https://oeis.org/search")
                query = src.get("query", "keyword:core")
                off = int(offsets.get("oeis", 0))
                try:
                    rows = oeis_page(search_url, query, off, ua)
                except Exception as e:
                    print("  [oeis error: %s] backing off 30s" % str(e)[:80]); rows = []; time.sleep(30)
                # OEIS keywords are PROPERTIES (nonn, easy, core…), not subjects, so
                # don't file by them (that collapses everything into one domain and
                # kills cross-domain transfer). File under a real subject instead.
                oeis_dom = src.get("domain_label", "mathematics")
                for sid, data, kw in rows:
                    new_this_pass += consider(sid, text=data, domain=oeis_dom)
                offsets["oeis"] = (off + len(rows)) if rows else 0   # loop back when exhausted
                save_state()
            # 2) drain the self-built frontier — this is the continuous expansion
            if not args.dry_run and frontier:
                print("  -- frontier: %d queued; ingesting up to %d --" % (len(frontier), frontier_per_pass))
                drained = 0
                while frontier and drained < frontier_per_pass:
                    chunk = []                            # pull a batch, prefetch it in ONE request, then ingest
                    while frontier and len(chunk) < 20 and drained + len(chunk) < frontier_per_pass:
                        chunk.append(frontier.pop(0))
                    for t in chunk:
                        frontier_set.discard(t)
                    if smode == "wikipedia":
                        wiki_prefetch(api_url, chunk, ua, links_per_article)
                    for title in chunk:
                        dom = item_domain.pop(title, None)
                        new_this_pass += consider(title, domain=dom); drained += 1
                    save_state()
            # 3) nothing left to ingest -> discover brand-new material at random
            if not args.dry_run and new_this_pass == 0:
                try:
                    rnd = random_keys(random_when_idle)
                except Exception:
                    rnd = []
                for t in rnd:
                    queue(t)
                if rnd:
                    print("  [idle] seed topics exhausted — queued %d random articles to keep discovering" % len(rnd))
                    save_state()
            # tier-1 self-growth: grow cross-domain concepts from what was verified
            try:
                gc = org.grow_concepts()
                if gc.get("newly_minted"):
                    print("  [concepts] +%d cross-domain concept(s) grown (total %d)"
                          % (gc["newly_minted"], gc["concepts_total"]))
            except Exception:
                pass
            push("(pass %d)" % state["passes"])
            print("==== pass %d done — %d new; Congress %.2f MB; frontier %d queued ===="
                  % (state["passes"], new_this_pass, size_mb(cong), len(frontier)))
            if args.once or args.dry_run:
                break
            time.sleep(2.0 if new_this_pass else 60.0)   # short breath; longer only if truly idle (e.g. offline)
        return 0
    except KeyboardInterrupt:
        print("\n[stop] saving + pushing…"); push("(interrupt)"); save_state(); return 0


if __name__ == "__main__":
    sys.exit(main())
