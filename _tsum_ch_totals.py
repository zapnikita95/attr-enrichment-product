# -*- coding: utf-8 -*-
"""TSUM site 203 totals from ClickHouse."""
from __future__ import annotations

import json
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
CH = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
AUTH = ("digi-admin", "Fl2bSowt")
OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"


def q(sql: str, timeout: int = 180) -> dict:
    r = requests.post(
        CH,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if r.status_code != 200:
        print(r.text[:1500])
        r.raise_for_status()
    return r.json()


def main() -> None:
    totals = q(
        """
        SELECT
          count() AS searches,
          uniqExact(searchTerm) AS unique_queries,
          countIf(isZeroQuery = 'true') AS zero_searches,
          round(countIf(isZeroQuery = 'true') / count() * 100, 2) AS zero_pct
        FROM sessions.searches
        WHERE siteId = 203
          AND timestamp >= now() - INTERVAL 90 DAY
          AND searchTerm IS NOT NULL
          AND trim(searchTerm) != ''
        """
    )
    # top category-ish product types via query keywords volume already in gap
    print(json.dumps(totals.get("data"), ensure_ascii=False, indent=2))
    (OUT / "ch_totals_90d.json").write_text(
        json.dumps(totals.get("data"), ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
