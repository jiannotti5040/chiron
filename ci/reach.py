#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""ci/reach.py — who is actually looking at this project.

Two sources, and both mislead in different ways, so both are labeled rather
than merged into one flattering number:

  GitHub traffic     Views and clones, **14 days only** — GitHub keeps no
                     more than that, so a number here is a fortnight's
                     worth and yesterday's fortnight is gone forever. Needs
                     push access on the repository. Clones are heavily
                     inflated by CI: every Actions run that checks out the
                     repo is a clone, so this repo's own workflows show up
                     as traffic.

  PyPI downloads     Served by pypistats.org, which reads the public BigQuery
                     download logs. **Not real-time — roughly a day behind**,
                     so a release published in the last few hours legitimately
                     reports nothing. That is a missing measurement, not a
                     zero, and this script says so rather than printing 0.
                     Mirrors are excluded where the API allows it; CI installs
                     are NOT excluded and cannot be.

Neither number is an audience. A download is a machine fetching a file, and a
clone is very often a runner. Read them as direction, not as people.

    python3 ci/reach.py                     # the defaults for this project
    python3 ci/reach.py --json              # machine-readable, same data
    python3 ci/reach.py --package foo --repo owner/name

Auth: GITHUB_TOKEN if set, otherwise `gh auth token`. Public-only fields
still work with no token; traffic does not.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_REPO = "jiannotti5040/chiron"
DEFAULT_PACKAGE = "primus-intelligence"

UA = "chiron-reach/1 (+https://github.com/jiannotti5040/chiron)"
BLOCKS = "▁▂▃▄▅▆▇█"


# ----------------------------------------------------------------- fetching

def _token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, timeout=15)
        return out.stdout.strip() or None
    except Exception:
        return None


def _get(url: str, token: str | None = None, timeout: int = 30):
    """Return (ok, payload). `payload` is parsed JSON, or an explanation."""
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if token and "api.github.com" in url:
        headers["Authorization"] = "Bearer " + token
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = {401: "not authenticated", 403: "forbidden — traffic needs "
                  "push access on the repo", 404: "not found (or no data yet)"}
        return False, "HTTP %s — %s" % (exc.code, detail.get(exc.code, exc.reason))
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, exc)


# ----------------------------------------------------------------- rendering

def _spark(values) -> str:
    values = list(values)
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return BLOCKS[3] * len(values)
    return "".join(BLOCKS[int((v - lo) / (hi - lo) * (len(BLOCKS) - 1))]
                   for v in values)


def _rule(title: str) -> None:
    print("\n\033[1m%s\033[0m" % title)
    print("─" * max(38, len(title)))


def _kv(label: str, value, note: str = "") -> None:
    print("  %-26s %s%s" % (label, value, ("   %s" % note) if note else ""))


def _unavailable(label: str, why: str) -> None:
    print("  %-26s \033[2m— unavailable (%s)\033[0m" % (label, why))


# ------------------------------------------------------------------- github

def github(repo: str, token: str | None, out: dict) -> None:
    owner_repo = repo
    ok, meta = _get("https://api.github.com/repos/%s" % owner_repo, token)
    _rule("GitHub — %s" % owner_repo)
    if not ok:
        _unavailable("repository", meta)
        out["github"] = {"error": meta}
        return

    g = out.setdefault("github", {})
    g["stars"] = meta.get("stargazers_count")
    g["forks"] = meta.get("forks_count")
    g["watchers"] = meta.get("subscribers_count")
    g["open_issues"] = meta.get("open_issues_count")
    g["visibility"] = meta.get("visibility")
    g["pushed_at"] = meta.get("pushed_at")

    _kv("stars", g["stars"])
    _kv("forks", g["forks"])
    _kv("watchers", g["watchers"], "(people subscribed, not stargazers)")
    _kv("open issues + PRs", g["open_issues"])
    _kv("visibility", g["visibility"])

    # ---- traffic (14-day window, push access required) ----
    ok_v, views = _get("https://api.github.com/repos/%s/traffic/views"
                       % owner_repo, token)
    ok_c, clones = _get("https://api.github.com/repos/%s/traffic/clones"
                        % owner_repo, token)

    if ok_v:
        daily = views.get("views", [])
        g["views_14d"] = views.get("count", 0)
        g["unique_views_14d"] = views.get("uniques", 0)
        g["views_daily"] = [d["count"] for d in daily]
        _kv("views (14d)", "%s  (%s unique)"
            % (g["views_14d"], g["unique_views_14d"]))
        if daily:
            _kv("  daily", _spark(g["views_daily"]),
                "%s → %s" % (daily[0]["timestamp"][:10],
                             daily[-1]["timestamp"][:10]))
    else:
        _unavailable("views (14d)", views)
        g["views_error"] = views

    if ok_c:
        daily = clones.get("clones", [])
        g["clones_14d"] = clones.get("count", 0)
        g["unique_clones_14d"] = clones.get("uniques", 0)
        g["clones_daily"] = [d["count"] for d in daily]
        _kv("clones (14d)", "%s  (%s unique)"
            % (g["clones_14d"], g["unique_clones_14d"]),
            "CI checkouts included")
        if daily:
            _kv("  daily", _spark(g["clones_daily"]))
    else:
        _unavailable("clones (14d)", clones)
        g["clones_error"] = clones

    for label, path, key in [
            ("referrers", "traffic/popular/referrers", "referrers"),
            ("popular paths", "traffic/popular/paths", "paths")]:
        ok_x, data = _get("https://api.github.com/repos/%s/%s"
                          % (owner_repo, path), token)
        if not ok_x:
            g[key + "_error"] = data
            continue
        if not data:
            print("  %-26s \033[2m(none in the last 14 days)\033[0m" % label)
            g[key] = []
            continue
        g[key] = data
        print("  %s:" % label)
        for row in data[:5]:
            name = row.get("referrer") or row.get("path", "")
            print("      %-42s %5s views  %4s uniq"
                  % (name[:42], row.get("count"), row.get("uniques")))

    # ---- release asset downloads ----
    ok_r, rels = _get("https://api.github.com/repos/%s/releases?per_page=100"
                      % owner_repo, token)
    if ok_r and isinstance(rels, list):
        total = 0
        rows = []
        for rel in rels:
            n = sum(a.get("download_count", 0) for a in rel.get("assets", []))
            total += n
            rows.append((rel.get("tag_name"), n, len(rel.get("assets", []))))
        g["releases"] = [{"tag": t, "asset_downloads": n, "assets": a}
                         for t, n, a in rows]
        g["release_asset_downloads_total"] = total
        _kv("releases", len(rows))
        if any(a for _, _, a in rows):
            for tag, n, a in rows[:5]:
                if a:
                    print("      %-20s %5s asset downloads" % (tag, n))
        else:
            print("      \033[2m(no attached binaries — the artifact for this "
                  "project is on PyPI)\033[0m")


# --------------------------------------------------------------------- pypi

def pypi(package: str, out: dict) -> None:
    _rule("PyPI — %s" % package)
    p = out.setdefault("pypi", {})

    ok, meta = _get("https://pypi.org/pypi/%s/json" % package)
    if ok:
        info = meta.get("info", {})
        rels = meta.get("releases", {})
        p["version"] = info.get("version")
        p["releases"] = sorted(rels)
        _kv("latest version", p["version"])
        _kv("versions published", "%d  (%s)"
            % (len(rels), ", ".join(sorted(rels))))
        files = rels.get(info.get("version"), [])
        if files:
            up = files[0].get("upload_time_iso_8601") or files[0].get("upload_time")
            p["latest_upload"] = up
            _kv("latest uploaded", up)
            try:
                when = datetime.fromisoformat(up.replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - when).total_seconds() / 3600
                p["latest_age_hours"] = round(age_h, 1)
                if age_h < 36:
                    print("      \033[2m(published %.1f h ago — download stats "
                          "lag ~1 day, so expect no data for it yet)\033[0m"
                          % age_h)
            except Exception:
                pass
    else:
        _unavailable("metadata", meta)
        p["error"] = meta

    # ---- pypistats: recent totals ----
    ok, recent = _get("https://pypistats.org/api/packages/%s/recent" % package)
    if ok:
        d = recent.get("data", {})
        p["downloads"] = d
        _kv("downloads last day", d.get("last_day"))
        _kv("downloads last week", d.get("last_week"))
        _kv("downloads last month", d.get("last_month"), "mirrors excluded")
    else:
        _unavailable("download totals", recent)
        p["downloads_error"] = recent
        print("      \033[2m(pypistats has no row for this package yet — "
              "normal for a package published in the last day or two)\033[0m")

    # ---- pypistats: daily series ----
    ok, overall = _get("https://pypistats.org/api/packages/%s/overall"
                       "?mirrors=false" % package)
    if ok:
        series = {}
        for row in overall.get("data", []):
            series[row["date"]] = series.get(row["date"], 0) + row["downloads"]
        days = sorted(series)[-30:]
        if days:
            p["daily"] = {d: series[d] for d in days}
            _kv("daily (last %d days)" % len(days),
                _spark(series[d] for d in days),
                "%s → %s" % (days[0], days[-1]))
            _kv("  peak day", "%s on %s"
                % (max(series[d] for d in days),
                   max(days, key=lambda d: series[d])))
    else:
        p["daily_error"] = overall

    # ---- pypistats: breakdowns ----
    for label, endpoint, field in [
            ("by Python version", "python_minor", "category"),
            ("by OS", "system", "category")]:
        ok, data = _get("https://pypistats.org/api/packages/%s/%s"
                        "?mirrors=false" % (package, endpoint))
        if not ok:
            continue
        agg = {}
        for row in data.get("data", []):
            key = row.get(field) or "unknown"
            agg[key] = agg.get(key, 0) + row.get("downloads", 0)
        agg.pop("null", None)
        if not agg:
            continue
        p[endpoint] = agg
        total = sum(agg.values()) or 1
        print("  %s:" % label)
        for key, n in sorted(agg.items(), key=lambda kv: -kv[1])[:6]:
            print("      %-12s %8s  %5.1f%%  %s"
                  % (key, n, 100 * n / total,
                     "▇" * max(1, round(28 * n / total))))


# --------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Traffic and download analytics for the GitHub repo and "
                    "the PyPI package.")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="owner/name")
    ap.add_argument("--package", default=DEFAULT_PACKAGE, help="PyPI name")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON only, no formatted report")
    args = ap.parse_args(argv)

    out = {
        "schema": "chiron.reach/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": args.repo,
        "package": args.package,
    }

    token = _token()
    if args.json:
        buf, sys.stdout = sys.stdout, open(os.devnull, "w")
        try:
            github(args.repo, token, out)
            pypi(args.package, out)
        finally:
            sys.stdout.close()
            sys.stdout = buf
        print(json.dumps(out, indent=2))
        return 0

    print("\033[1mreach\033[0m  %s" % out["generated_utc"])
    if not token:
        print("\033[2m  no GitHub token (set GITHUB_TOKEN or run `gh auth "
              "login`) — public fields only, traffic will be unavailable\033[0m")
    github(args.repo, token, out)
    pypi(args.package, out)

    print("\n\033[2mGitHub traffic is a rolling 14-day window and includes CI "
          "checkouts.\nPyPI downloads come from pypistats.org (BigQuery logs, "
          "~1 day behind) and\ninclude automated installs. Neither number is a "
          "count of people.\033[0m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
