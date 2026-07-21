# -*- coding: utf-8 -*-
"""Fetch TSUM conversion from Yandex Metrika (counter 21801616)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
COUNTER = 21801616
TOKEN = "y0__xCYxaLvARjFxj0gjIDmqBaoEC1nVwTDxx9o6-px7bKRIxj4NQ"  # diginetica.office
BASE = "https://api-metrika.yandex.net"


def api(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + urlencode(params, safe=":'()==,")
    req = Request(url, headers={"Authorization": f"OAuth {TOKEN}"})
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def metrics_row(params: dict) -> dict:
    data = api("/stat/v1/data", params)
    if not data.get("data"):
        return {"raw": data, "metrics": []}
    return {
        "metrics": data["data"][0]["metrics"],
        "totals": data.get("totals"),
    }


def main() -> None:
    d2 = date.today() - timedelta(days=1)
    d1 = d2 - timedelta(days=89)
    date1, date2 = d1.isoformat(), d2.isoformat()

    goals = api(f"/management/v1/counter/{COUNTER}/goals").get("goals") or []
    goal_brief = [
        {
            "id": g.get("id"),
            "name": g.get("name"),
            "type": g.get("type"),
            "conditions": g.get("conditions"),
        }
        for g in goals
    ]
    search_goals = [
        g
        for g in goal_brief
        if any(
            x in (g.get("name") or "").lower()
            for x in ("поиск", "search", "старт поиска", "сайт поиск")
        )
    ]
    print("goals", len(goals), "search-like", len(search_goals))
    for g in search_goals[:20]:
        print(" ", g["id"], g["name"], g["type"])

    # Overall ecommerce
    overall = metrics_row(
        {
            "ids": COUNTER,
            "metrics": "ym:s:visits,ym:s:users,ym:s:ecommercePurchases,ym:s:ecommerceRevenue,ym:s:avgPurchaseRevenue",
            "date1": date1,
            "date2": date2,
            "accuracy": "1",
        }
    )
    print("OVERALL", overall)

    # Try paramsLevel1==search segment
    with_search_params = metrics_row(
        {
            "ids": COUNTER,
            "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue,ym:s:avgPurchaseRevenue",
            "date1": date1,
            "date2": date2,
            "filters": "EXISTS(ym:s:paramsLevel1=='search')",
            "accuracy": "1",
        }
    )
    print("WITH_SEARCH_PARAMS", with_search_params)

    without_search_params = metrics_row(
        {
            "ids": COUNTER,
            "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue,ym:s:avgPurchaseRevenue",
            "date1": date1,
            "date2": date2,
            "filters": "NOT EXISTS(ym:s:paramsLevel1=='search')",
            "accuracy": "1",
        }
    )
    print("WITHOUT_SEARCH_PARAMS", without_search_params)

    # Per search goal if found
    by_goal = {}
    for g in search_goals[:5]:
        gid = g["id"]
        yes = metrics_row(
            {
                "ids": COUNTER,
                "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue,ym:s:avgPurchaseRevenue",
                "date1": date1,
                "date2": date2,
                "filters": f"ym:s:goal{gid}IsReached=='Yes'",
                "accuracy": "1",
            }
        )
        no = metrics_row(
            {
                "ids": COUNTER,
                "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue,ym:s:avgPurchaseRevenue",
                "date1": date1,
                "date2": date2,
                "filters": f"ym:s:goal{gid}IsReached=='No'",
                "accuracy": "1",
            }
        )
        by_goal[str(gid)] = {"goal": g, "reached": yes, "not_reached": no}
        print("GOAL", gid, g["name"], "yes", yes.get("metrics"), "no", no.get("metrics"))

    def pack(m: list) -> dict:
        if not m or len(m) < 3:
            return {"visits": None, "purchases": None, "revenue": None, "aov": None, "cvr_pct": None}
        visits, purchases, revenue = float(m[0]), float(m[1]), float(m[2])
        aov = float(m[3]) if len(m) > 3 and m[3] is not None else (revenue / purchases if purchases else None)
        cvr = 100.0 * purchases / visits if visits else None
        return {
            "visits": visits,
            "purchases": purchases,
            "revenue": revenue,
            "aov": aov,
            "cvr_pct": round(cvr, 3) if cvr is not None else None,
        }

    # overall metrics order: visits, users, purchases, revenue, aov
    om = overall.get("metrics") or []
    overall_pack = {
        "visits": om[0] if len(om) > 0 else None,
        "users": om[1] if len(om) > 1 else None,
        "purchases": om[2] if len(om) > 2 else None,
        "revenue": om[3] if len(om) > 3 else None,
        "aov": om[4] if len(om) > 4 else None,
        "cvr_pct": round(100.0 * om[2] / om[0], 3) if len(om) > 2 and om[0] else None,
    }

    report = {
        "partner": "TSUM",
        "site_id": 203,
        "counter_id": COUNTER,
        "period": {"date1": date1, "date2": date2, "days": 90},
        "goals_search_like": search_goals,
        "goals_all_count": len(goals),
        "overall": overall_pack,
        "segment_params_search": {
            "with_search": pack(with_search_params.get("metrics") or []),
            "without_search": pack(without_search_params.get("metrics") or []),
        },
        "by_search_goal": by_goal,
        "source": "Yandex Metrika API · diginetica.office token",
    }
    (OUT / "metrika_cvr.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"overall": overall_pack, "with": report["segment_params_search"]["with_search"], "without": report["segment_params_search"]["without_search"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
