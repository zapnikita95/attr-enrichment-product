# -*- coding: utf-8 -*-
"""Pull TSUM (site 203) search metrics + top queries from ClickHouse."""
from __future__ import annotations

import json
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

CH = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
AUTH = ("digi-admin", "Fl2bSowt")
SITE_ID = 203
OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
OUT.mkdir(parents=True, exist_ok=True)


def ch_query(sql: str, timeout: int = 300) -> dict:
    r = requests.post(
        CH,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if r.status_code != 200:
        print("FAIL", r.status_code, r.text[:1500])
        r.raise_for_status()
    return r.json()


def main() -> None:
    # confirm host
    host = ch_query(
        f"""
        SELECT remoteHost, count() AS cnt
        FROM sessions.searches
        WHERE siteId = {SITE_ID}
          AND timestamp >= now() - INTERVAL 1 DAY
        GROUP BY remoteHost
        ORDER BY cnt DESC
        LIMIT 10
        """
    )
    print("HOSTS", json.dumps(host.get("data"), ensure_ascii=False, indent=2)[:1500])

    # zero rate from zero_query if available
    try:
        zq = ch_query(
            f"""
            SELECT
              sum(total_searches) AS total_searches,
              sum(zero_searches) AS zero_searches,
              round(sum(zero_searches) / nullIf(sum(total_searches), 0) * 100, 2) AS zero_rate_pct
            FROM sessions.zero_query
            WHERE site_id = {SITE_ID}
            """
        )
        print("ZERO", zq.get("data"))
        (OUT / "ch_zero_rate.json").write_text(
            json.dumps(zq.get("data"), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print("zero_query err", e)

    # top queries 90d
    top = ch_query(
        f"""
        SELECT
          lowerUTF8(trim(searchTerm)) AS q,
          count() AS cnt,
          countIf(isZeroQuery = 'true') AS zero_cnt,
          round(countIf(isZeroQuery = 'true') / count() * 100, 2) AS zero_pct
        FROM sessions.searches
        WHERE siteId = {SITE_ID}
          AND timestamp >= now() - INTERVAL 90 DAY
          AND searchTerm IS NOT NULL
          AND trim(searchTerm) != ''
        GROUP BY q
        ORDER BY cnt DESC
        LIMIT 30000
        """,
        timeout=600,
    )
    rows = top.get("data") or []
    (OUT / "top-30k-queries-ch.json").write_text(
        json.dumps(
            {
                "site_id": SITE_ID,
                "period_days": 90,
                "rows": len(rows),
                "queries": rows,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"saved {len(rows)} queries")
    print("TOP20:")
    for r in rows[:20]:
        print(f"  {r['cnt']:>8}  z={r['zero_pct']:>5}%  {r['q']}")


if __name__ == "__main__":
    main()
