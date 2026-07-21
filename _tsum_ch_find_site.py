# -*- coding: utf-8 -*-
"""Find TSUM siteId in ClickHouse."""
from __future__ import annotations

import json
import requests
import urllib3

urllib3.disable_warnings()

CH = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
AUTH = ("digi-admin", "Fl2bSowt")


def ch_query(sql: str, timeout: int = 180) -> dict:
    r = requests.post(
        CH,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    print("STATUS", r.status_code)
    if r.status_code != 200:
        print(r.text[:2000])
        r.raise_for_status()
    return r.json()


def main() -> None:
    sqls = [
        """
        SELECT siteId, count() AS cnt
        FROM sessions.searches
        WHERE timestamp >= now() - INTERVAL 3 DAY
          AND (
            remoteHost ILIKE '%tsum%'
            OR referer ILIKE '%tsum%'
            OR location ILIKE '%tsum%'
          )
        GROUP BY siteId
        ORDER BY cnt DESC
        LIMIT 20
        """,
        """
        SELECT siteId, count() AS cnt
        FROM sessions.agg_sessions
        WHERE date >= today() - 7
          AND (
            domain ILIKE '%tsum%'
            OR host ILIKE '%tsum%'
            OR siteName ILIKE '%tsum%'
          )
        GROUP BY siteId
        ORDER BY cnt DESC
        LIMIT 20
        """,
    ]
    for sql in sqls:
        print("=" * 60)
        print(sql.strip()[:120])
        try:
            data = ch_query(sql)
            print(json.dumps(data.get("data", []), ensure_ascii=False, indent=2)[:3000])
        except Exception as e:
            print("ERR", e)


if __name__ == "__main__":
    main()
