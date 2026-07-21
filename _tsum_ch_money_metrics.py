# -*- coding: utf-8 -*-
"""TSUM site 203: session conversion, AOV, breakdown by isZeroQuery."""
from __future__ import annotations

import json
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

CH = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
AUTH = ("digi-admin", "Fl2bSowt")
SITE = 203
OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"


def ch_query(sql: str, timeout: int = 300) -> dict:
    r = requests.post(
        CH,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if r.status_code != 200:
        print("FAIL", r.status_code, r.text[:2000])
        r.raise_for_status()
    return r.json()


def main() -> None:
    # 1) Overall search-session conversion + AOV (dashboard method)
    overall = ch_query(
        f"""
        WITH deduped AS (
            SELECT
                sessionId,
                max(searches) AS searches,
                max(autocompleteClicks) AS ac,
                max(withOrder) AS withOrder,
                max(revenue) AS revenue
            FROM sessions.agg_sessions
            WHERE siteId = {SITE}
              AND toDate(timeBegin) >= today() - 90
              AND toDate(timeBegin) <= today() - 1
            GROUP BY sessionId
        )
        SELECT
            count() AS total_sessions,
            countIf(searches > 0 OR ac > 0) AS search_sessions,
            countIf((searches > 0 OR ac > 0) AND withOrder > 0) AS search_order_sessions,
            round(
                countIf((searches > 0 OR ac > 0) AND withOrder > 0)
                / nullIf(countIf(searches > 0 OR ac > 0), 0) * 100,
                3
            ) AS search_session_cvr_pct,
            round(
                sumIf(revenue, (searches > 0 OR ac > 0) AND withOrder > 0)
                / nullIf(countIf((searches > 0 OR ac > 0) AND withOrder > 0), 0),
                2
            ) AS avg_check_search_rub,
            round(sumIf(revenue, (searches > 0 OR ac > 0) AND withOrder > 0), 2) AS search_revenue_90d
        FROM deduped
        """
    )
    print("OVERALL", json.dumps(overall.get("data"), ensure_ascii=False, indent=2))

    # 2) Describe zero_query columns
    try:
        zq_desc = ch_query("DESCRIBE TABLE sessions.zero_query")
        cols = [r["name"] for r in zq_desc.get("data") or []]
        print("zero_query cols", cols[:40])
    except Exception as e:
        print("zq desc", e)
        cols = []

    # 3) Conversion by isZeroQuery flag on the search event
    # Session that had at least one zero-marked search vs only non-zero
    by_flag = ch_query(
        f"""
        WITH search_flags AS (
            SELECT
                sessionId,
                max(isZeroQuery = 'true') AS had_zero_flag,
                max(isZeroQuery = 'false') AS had_nonzero_flag
            FROM sessions.searches
            WHERE siteId = {SITE}
              AND timestamp >= now() - INTERVAL 90 DAY
              AND searchTerm IS NOT NULL
              AND trim(searchTerm) != ''
            GROUP BY sessionId
        ),
        sess AS (
            SELECT
                sessionId,
                max(withOrder) AS withOrder,
                max(revenue) AS revenue
            FROM sessions.agg_sessions
            WHERE siteId = {SITE}
              AND toDate(timeBegin) >= today() - 90
              AND toDate(timeBegin) <= today() - 1
            GROUP BY sessionId
        )
        SELECT
            multiIf(
                had_zero_flag = 1 AND had_nonzero_flag = 0, 'only_zero_flag',
                had_zero_flag = 1 AND had_nonzero_flag = 1, 'mixed',
                'only_normal_flag'
            ) AS bucket,
            count() AS sessions,
            countIf(withOrder > 0) AS orders,
            round(countIf(withOrder > 0) / count() * 100, 3) AS cvr_pct,
            round(sumIf(revenue, withOrder > 0) / nullIf(countIf(withOrder > 0), 0), 2) AS aov
        FROM search_flags sf
        INNER JOIN sess s ON sf.sessionId = s.sessionId
        GROUP BY bucket
        ORDER BY sessions DESC
        """
    )
    print("BY_FLAG", json.dumps(by_flag.get("data"), ensure_ascii=False, indent=2))

    # 4) Search-level: frequency of isZeroQuery
    zrate = ch_query(
        f"""
        SELECT
            count() AS searches,
            countIf(isZeroQuery = 'true') AS zero_flag_searches,
            countIf(isZeroQuery = 'false') AS normal_flag_searches,
            countIf(isZeroQuery IS NULL OR isZeroQuery = '') AS null_flag,
            round(countIf(isZeroQuery = 'true') / count() * 100, 2) AS zero_flag_pct
        FROM sessions.searches
        WHERE siteId = {SITE}
          AND timestamp >= now() - INTERVAL 90 DAY
          AND searchTerm IS NOT NULL
          AND trim(searchTerm) != ''
        """
    )
    print("ZRATE", json.dumps(zrate.get("data"), ensure_ascii=False, indent=2))

    # 5) Top zero-flag queries
    top_zero = ch_query(
        f"""
        SELECT
          lowerUTF8(trim(searchTerm)) AS q,
          count() AS cnt
        FROM sessions.searches
        WHERE siteId = {SITE}
          AND timestamp >= now() - INTERVAL 90 DAY
          AND isZeroQuery = 'true'
          AND searchTerm IS NOT NULL
        GROUP BY q
        ORDER BY cnt DESC
        LIMIT 100
        """
    )
    print("TOP_ZERO sample", (top_zero.get("data") or [])[:15])

    out = {
        "site_id": SITE,
        "period_days": 90,
        "overall": (overall.get("data") or [None])[0],
        "by_session_zero_flag": by_flag.get("data") or [],
        "search_zero_flag_rate": (zrate.get("data") or [None])[0],
        "top_zero_flag_queries": top_zero.get("data") or [],
    }
    (OUT / "ch_money_metrics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote", OUT / "ch_money_metrics.json")


if __name__ == "__main__":
    main()
