# -*- coding: utf-8 -*-
"""Sanity-check TSUM order tracking in CH."""
import json
import requests
import urllib3

urllib3.disable_warnings()
CH = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
AUTH = ("digi-admin", "Fl2bSowt")
SITE = 203


def q(sql, t=180):
    r = requests.post(
        CH,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=t,
        verify=False,
    )
    print(sql.strip()[:80], "->", r.status_code)
    if r.status_code != 200:
        print(r.text[:1500])
        return None
    print(json.dumps(r.json().get("data"), ensure_ascii=False, indent=2)[:2000])
    return r.json()


# all orders
q(
    f"""
SELECT
  count() AS rows_with_order,
  uniqExact(sessionId) AS order_sessions,
  round(sum(revenue),2) AS revenue
FROM sessions.agg_sessions
WHERE siteId = {SITE}
  AND toDate(timeBegin) >= today() - 90
  AND toDate(timeBegin) <= today() - 1
  AND withOrder > 0
"""
)

# order_successes if exists
q(
    f"""
SELECT count() AS cnt, uniqExact(sessionId) AS sessions, round(sum(revenue),2) AS rev
FROM sessions.order_successes
WHERE siteId = {SITE}
  AND timestamp >= now() - INTERVAL 90 DAY
"""
)

# sample withOrder distribution
q(
    f"""
SELECT
  countIf(withOrder > 0) AS with_order_rows,
  count() AS all_rows,
  round(avg(revenue),2) AS avg_rev_all,
  round(avgIf(revenue, withOrder>0),2) AS avg_rev_orders
FROM sessions.agg_sessions
WHERE siteId = {SITE}
  AND toDate(timeBegin) >= today() - 30
  AND toDate(timeBegin) <= today() - 1
"""
)
