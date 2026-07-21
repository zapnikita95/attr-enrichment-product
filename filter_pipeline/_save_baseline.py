import json
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ch_config import CH_PASS, CH_URL, CH_USER

AUTH = (CH_USER, CH_PASS)
OUT = Path(__file__).resolve().parents[1] / "portfolio" / "zolla_filters"


def ch(sql, t=180):
    r = requests.post(
        CH_URL,
        auth=AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=t,
        verify=False,
    )
    r.raise_for_status()
    return r.json()


r = ch(
    """
WITH deduped AS (
  SELECT sessionId, max(searches) searches, max(autocompleteClicks) ac, max(withOrder) wo, max(revenue) rev
  FROM sessions.agg_sessions
  WHERE siteId=3826 AND toDate(timeBegin)>=today()-90 AND toDate(timeBegin)<=today()-1
  GROUP BY sessionId
)
SELECT
  count() total_sessions,
  countIf(searches>0 OR ac>0) search_sessions,
  countIf(wo>0 AND (searches>0 OR ac>0)) search_orders,
  round(countIf(wo>0 AND (searches>0 OR ac>0)) / nullIf(countIf(searches>0 OR ac>0),0) * 100, 3) search_cvr_pct,
  round(sumIf(rev, wo>0 AND (searches>0 OR ac>0)) / nullIf(countIf(wo>0 AND (searches>0 OR ac>0)),0), 2) aov_search,
  round(sumIf(rev, wo>0 AND (searches>0 OR ac>0)), 2) search_revenue_90d
FROM deduped
"""
)
r2 = ch(
    """
SELECT count() searches_90d, uniqExact(lowerUTF8(searchTerm)) uniq_queries_90d
FROM sessions.searches
WHERE siteId=3826 AND toDate(timestamp)>=today()-90 AND toDate(timestamp)<=today()-1
"""
)
base = {**r["data"][0], **r2["data"][0]}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ch_baseline_3826.json").write_text(
    json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(base)
