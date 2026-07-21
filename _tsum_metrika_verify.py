# -*- coding: utf-8 -*-
"""Sanity: Metrika API works for TSUM counter 21801616."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN = "y0__xCYxaLvARjFxj0gjIDmqBaoEC1nVwTDxx9o6-px7bKRIxj4NQ"
COUNTER = 21801616
BASE = "https://api-metrika.yandex.net"
OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
GID = 260498358  # Автоцель: поиск по сайту


def get(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + urlencode(params, safe=":'()==,")
    req = Request(url, headers={"Authorization": f"OAuth {TOKEN}"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> None:
    c = get(f"/management/v1/counter/{COUNTER}").get("counter") or {}
    print(
        "COUNTER_OK",
        c.get("id"),
        c.get("name"),
        c.get("site"),
        "perm=",
        c.get("permission"),
    )

    d = get(
        "/stat/v1/data",
        {
            "ids": COUNTER,
            "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue",
            "date1": "2026-04-22",
            "date2": "2026-07-20",
            "accuracy": "1",
        },
    )
    visits, purch, rev = d["data"][0]["metrics"]
    print(
        "ECOM_OK",
        "visits",
        round(visits),
        "purchases",
        round(purch),
        "revenue",
        round(rev),
        "aov",
        round(rev / purch),
        "cvr_pct",
        round(100 * purch / visits, 3),
    )

    yes = get(
        "/stat/v1/data",
        {
            "ids": COUNTER,
            "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue",
            "date1": "2026-04-22",
            "date2": "2026-07-20",
            "filters": f"ym:s:goal{GID}IsReached=='Yes'",
            "accuracy": "1",
        },
    )["data"][0]["metrics"]
    no = get(
        "/stat/v1/data",
        {
            "ids": COUNTER,
            "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue",
            "date1": "2026-04-22",
            "date2": "2026-07-20",
            "filters": f"ym:s:goal{GID}IsReached=='No'",
            "accuracy": "1",
        },
    )["data"][0]["metrics"]

    cvr_yes = 100 * yes[1] / yes[0]
    cvr_no = 100 * no[1] / no[0]
    print(
        "SEARCH_YES",
        "visits",
        round(yes[0]),
        "purch",
        round(yes[1]),
        "rev",
        round(yes[2]),
        "aov",
        round(yes[2] / yes[1]),
        "cvr",
        round(cvr_yes, 3),
    )
    print(
        "SEARCH_NO",
        "visits",
        round(no[0]),
        "purch",
        round(no[1]),
        "rev",
        round(no[2]),
        "aov",
        round(no[2] / no[1]),
        "cvr",
        round(cvr_no, 3),
    )
    print("LIFT_x", round(cvr_yes / cvr_no, 2))

    cleaned = {
        "api_works": True,
        "counter_id": COUNTER,
        "counter_name": c.get("name"),
        "site": c.get("site"),
        "period": {"date1": "2026-04-22", "date2": "2026-07-20"},
        "search_goal_id": GID,
        "search_goal_name": "Автоцель: поиск по сайту",
        "overall": {
            "visits": visits,
            "purchases": purch,
            "revenue": rev,
            "aov": rev / purch,
            "cvr_pct": 100 * purch / visits,
        },
        "with_search": {
            "visits": yes[0],
            "purchases": yes[1],
            "revenue": yes[2],
            "aov": yes[2] / yes[1],
            "cvr_pct": cvr_yes,
        },
        "without_search": {
            "visits": no[0],
            "purchases": no[1],
            "revenue": no[2],
            "aov": no[2] / no[1],
            "cvr_pct": cvr_no,
        },
        "search_vs_no_lift_x": cvr_yes / cvr_no,
        "note": "AOV = ecommerceRevenue / ecommercePurchases (avgPurchaseRevenue на счётчике врёт).",
    }
    (OUT / "metrika_cvr_clean.json").write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # patch metrika_cvr.json for HTML builder
    old = {}
    p = OUT / "metrika_cvr.json"
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
    old["overall"] = {
        "visits": visits,
        "users": old.get("overall", {}).get("users"),
        "purchases": purch,
        "revenue": rev,
        "aov": rev / purch,
        "cvr_pct": round(100 * purch / visits, 3),
    }
    old["segment_params_search"] = {
        "with_search": {
            "visits": yes[0],
            "purchases": yes[1],
            "revenue": yes[2],
            "aov": yes[2] / yes[1],
            "cvr_pct": round(cvr_yes, 3),
            "source": f"goal {GID}",
        },
        "without_search": {
            "visits": no[0],
            "purchases": no[1],
            "revenue": no[2],
            "aov": no[2] / no[1],
            "cvr_pct": round(cvr_no, 3),
            "source": f"goal {GID} not reached",
        },
    }
    old["verified"] = True
    p.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote metrika_cvr_clean.json + patched metrika_cvr.json")


if __name__ == "__main__":
    main()
