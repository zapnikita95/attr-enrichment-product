# -*- coding: utf-8 -*-
"""Measure CH session CVR for API-classified RESERVE vs NORMAL impact queries."""
from __future__ import annotations

import json
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
CH = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
AUTH = ("digi-admin", "Fl2bSowt")
OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"


def ch(sql: str, t: int = 300) -> dict:
    r = requests.post(
        CH,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=t,
        verify=False,
    )
    if r.status_code != 200:
        print(r.text[:1500])
        r.raise_for_status()
    return r.json()


def cvr_for_queries(terms: list[str], label: str) -> dict:
    # limit to top terms by keeping list as-is (already sorted)
    terms = terms[:80]
    if not terms:
        return {"label": label, "empty": True}
    # escape
    lit = ", ".join("'" + t.replace("\\", "\\\\").replace("'", "\\'") + "'" for t in terms)
    sql = f"""
    WITH hit_sessions AS (
        SELECT DISTINCT sessionId
        FROM sessions.searches
        WHERE siteId = 203
          AND timestamp >= now() - INTERVAL 90 DAY
          AND lowerUTF8(trim(searchTerm)) IN ({lit})
    ),
    sess AS (
        SELECT sessionId, max(withOrder) AS w, max(revenue) AS r
        FROM sessions.agg_sessions
        WHERE siteId = 203
          AND toDate(timeBegin) >= today() - 90
          AND toDate(timeBegin) <= today() - 1
        GROUP BY sessionId
    )
    SELECT
        count() AS sessions,
        countIf(w > 0) AS orders,
        round(countIf(w > 0) / count() * 100, 4) AS cvr_pct,
        round(sumIf(r, w > 0) / nullIf(countIf(w > 0), 0), 2) AS aov
    FROM hit_sessions h
    INNER JOIN sess s ON h.sessionId = s.sessionId
    """
    data = (ch(sql).get("data") or [{}])[0]
    data["label"] = label
    data["n_terms"] = len(terms)
    print(label, data)
    return data


def main() -> None:
    api = json.loads((OUT / "api_classify_impact.json").read_text(encoding="utf-8"))
    by = {"RESERVE": [], "NORMAL": [], "ZERO": []}
    for e in api["queries"].values():
        k = e.get("kind")
        if k in by:
            by[k].append(e)
    for k in by:
        by[k].sort(key=lambda x: -int(x.get("cnt") or 0))
    out = {
        "reserve": cvr_for_queries([x["q"] for x in by["RESERVE"]], "RESERVE_top80"),
        "normal": cvr_for_queries([x["q"] for x in by["NORMAL"]], "NORMAL_top80"),
    }
    (OUT / "ch_cvr_by_api_kind.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
