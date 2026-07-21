"""Refresh CH peer CVRs + merge into money_baseline_benchmark.json (skip slow Metrika)."""
from __future__ import annotations

import json
from pathlib import Path

from zolla_money_benchmark import (
    FASHION_PEERS_CH,
    OUT,
    ZOLLA_SITE,
    decide_baseline,
    pull_ch_peers,
)

NAME = {
    203: "tsum.ru",
    1378: "zarina.ru",
    1458: "gloria-jeans",
    1967: "befree",
    2297: "ecco.ru",
    2580: "superstep.ru",
    2878: "shoppinglive.ru",
    3083: "rendez-vous.ru",
    3826: "zolla.com",
    7433: "elis.ru",
}


def main() -> None:
    rows = pull_ch_peers(sorted(set(FASHION_PEERS_CH)))
    for r in rows:
        sid = int(r["siteId"])
        r["name"] = NAME.get(sid, str(sid))
        print(
            sid,
            r["name"],
            "search_sess",
            r["search_sessions"],
            "orders",
            r["search_orders"],
            "cvr%",
            r["search_cvr_pct"],
            "aov",
            r["aov_search"],
        )

    path = OUT / "money_baseline_benchmark.json"
    report = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    report["peer_ch"] = rows
    report["airtable"] = {
        "ok": False,
        "error": "tokens 401/403 — CRM vertical list unavailable; used curated fashion peers",
        "curated_peers": [
            {"site_id": k, "name": v} for k, v in NAME.items() if k != ZOLLA_SITE
        ],
        "note": "Peers from Metrika skill fashion map + known apparel (Gloria Jeans, Befree, Zarina, Elis, RV, Ecco, Superstep, TSUM).",
    }
    ch_zolla = next((r for r in rows if int(r["siteId"]) == ZOLLA_SITE), None)
    decision = decide_baseline(
        ch_zolla,
        report.get("metrika_zolla") or {},
        report.get("peer_metrika") or [],
        rows,
    )
    report["decision"] = decision
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CHOSEN", json.dumps(decision["chosen"], ensure_ascii=False, indent=2))
    print("wrote", path)


if __name__ == "__main__":
    main()
