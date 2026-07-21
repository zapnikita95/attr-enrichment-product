#!/usr/bin/env python3
"""Zolla money baseline: Metrika first; if broken CH → peer fashion benchmark (Airtable + CH)."""

from __future__ import annotations

import json
import os
import statistics
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parents[1] / "portfolio" / "zolla_filters"
SKILLS = Path(r"C:\Users\1\OneDrive\Desktop\skills-portable\skills")

ZOLLA_SITE = 3826
ZOLLA_COUNTER = 79438447
ZOLLA_SEARCH_GOAL = 294554663


def _metrika_token() -> str:
    tok = (os.environ.get("METRIKA_TOKEN") or os.environ.get("YANDEX_METRIKA_TOKEN") or "").strip()
    if tok:
        return tok
    # skills-portable benchmarks mapping (no token in this repo)
    for env_path in (
        SKILLS / ".env",
        SKILLS / "metrika" / ".env",
        Path(r"C:\Users\1\OneDrive\Desktop\skills-portable\skills") / ".env",
    ):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("METRIKA_TOKEN=") or line.startswith("YANDEX_METRIKA_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    # fallback: collect_data module constant if present
    try:
        import importlib.util

        p = SKILLS / "benchmarks" / "collect_data.py"
        if p.is_file():
            spec = importlib.util.spec_from_file_location("bench_collect", p)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            tokens = getattr(mod, "METRIKA_TOKENS", {}) or {}
            if tokens.get(1):
                return str(tokens[1])
    except Exception:
        pass
    raise RuntimeError("METRIKA_TOKEN missing (env or skills-portable benchmarks)")

# Fashion / apparel peers with Metrika mapping (from skills metrika + collect_data)
FASHION_PEERS_METRIKA = {
    1378: {"name": "zarina.ru", "counter": 22537834, "search_goal": 6271953},
    7433: {"name": "elis.ru", "counter": 27914622, "search_goal": None},  # may lack goal
    3083: {"name": "rendez-vous.ru", "counter": 11099911, "search_goal": None},
    2297: {"name": "ecco.ru", "counter": 21455827, "search_goal": 480745779},
    2580: {"name": "superstep.ru", "counter": 29297810, "search_goal": 304093607},
    7735: {"name": "peakstore.ru", "counter": 79456705, "search_goal": None},
    2878: {"name": "shoppinglive.ru", "counter": 9754324, "search_goal": 460055339},
    203: {"name": "tsum.ru", "counter": 21801616, "search_goal": 260498358},
}

# CH-only fashion-ish peers (Airtable vertical Одежда / known Digi sites)
FASHION_PEERS_CH = [1378, 7433, 3083, 2297, 2580, 2878, 203, 1967, 1458, 3826]

AIRTABLE_BASE = "appzZPXw4Oaz2z6HC"
AIRTABLE_TABLE = "tbl8bEtku6GhSrvEq"
AIRTABLE_VIEW = "viwp11mdWYzPPxCvz"


def _airtable_tokens() -> list[str]:
    out: list[str] = []
    env = (os.environ.get("AIRTABLE_TOKEN") or "").strip()
    if env:
        out.append(env)
    for env_path in (
        SKILLS / ".env",
        SKILLS / "roadmap-bulk-tasks" / ".env",
        Path(r"C:\Users\1\OneDrive\Desktop\skills-portable\skills\scripts") / ".env",
    ):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("AIRTABLE_TOKEN="):
                t = line.split("=", 1)[1].strip().strip('"').strip("'")
                if t and t not in out:
                    out.append(t)
    return out

# CH CVR below this → treat as broken / undercounted orders
CH_CVR_BROKEN_PCT = 0.05  # 0.05% absolute


def _period_90d() -> tuple[str, str]:
    end = date(2026, 7, 20)
    start = end - timedelta(days=89)
    return start.isoformat(), end.isoformat()


def metrika_get(path: str, params: dict | None = None) -> dict:
    url = "https://api-metrika.yandex.net" + path
    if params:
        url += "?" + urllib.parse.urlencode(params, safe=":'()==,")
    req = urllib.request.Request(url, headers={"Authorization": f"OAuth {_metrika_token()}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def metrika_ecom(counter: int, d1: str, d2: str, filt: str | None = None) -> dict[str, float]:
    p: dict[str, Any] = {
        "ids": counter,
        "metrics": "ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue",
        "date1": d1,
        "date2": d2,
        "accuracy": "1",
    }
    if filt:
        p["filters"] = filt
    data = metrika_get("/stat/v1/data", p)
    visits, purch, rev = data["data"][0]["metrics"]
    cvr = 100.0 * purch / visits if visits else 0.0
    aov = rev / purch if purch else 0.0
    return {
        "visits": float(visits),
        "purchases": float(purch),
        "revenue": float(rev),
        "cvr_pct": round(cvr, 3),
        "aov": round(aov, 1),
    }


def pull_zolla_metrika() -> dict:
    d1, d2 = _period_90d()
    overall = metrika_ecom(ZOLLA_COUNTER, d1, d2)
    yes = metrika_ecom(
        ZOLLA_COUNTER, d1, d2, f"ym:s:goal{ZOLLA_SEARCH_GOAL}IsReached=='Yes'"
    )
    no = metrika_ecom(
        ZOLLA_COUNTER, d1, d2, f"ym:s:goal{ZOLLA_SEARCH_GOAL}IsReached=='No'"
    )
    return {
        "source": "yandex_metrika",
        "counter_id": ZOLLA_COUNTER,
        "search_goal_id": ZOLLA_SEARCH_GOAL,
        "period": {"date1": d1, "date2": d2},
        "overall": overall,
        "with_search": yes,
        "without_search": no,
    }


def pull_peer_metrika() -> list[dict]:
    d1, d2 = _period_90d()
    out = []
    for sid, meta in FASHION_PEERS_METRIKA.items():
        gid = meta.get("search_goal")
        row: dict[str, Any] = {
            "site_id": sid,
            "name": meta["name"],
            "counter": meta["counter"],
            "search_goal": gid,
        }
        try:
            overall = metrika_ecom(meta["counter"], d1, d2)
            row["overall"] = overall
            if gid:
                yes = metrika_ecom(
                    meta["counter"], d1, d2, f"ym:s:goal{gid}IsReached=='Yes'"
                )
                row["with_search"] = yes
            else:
                row["with_search"] = None
                row["note"] = "no search_goal in mapping"
        except Exception as e:
            row["error"] = str(e)
        out.append(row)
        print("metrika peer", sid, meta["name"], row.get("with_search") or row.get("error") or row.get("note"))
    return out


def pull_ch_peers(site_ids: list[int]) -> list[dict]:
    """HTTP ClickHouse via project ch_config (same as zolla_query_demand)."""
    import sys

    import requests
    import urllib3

    urllib3.disable_warnings()
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from ch_config import CH_PASS, CH_URL, CH_USER  # type: ignore

    ids = ",".join(str(i) for i in site_ids)
    # Same method as filter_pipeline/_save_baseline.py (timeBegin, session dedupe)
    sql = f"""
    WITH deduped AS (
      SELECT
        siteId,
        sessionId,
        max(searches) AS searches,
        max(autocompleteClicks) AS ac,
        max(withOrder) AS wo,
        max(revenue) AS rev
      FROM sessions.agg_sessions
      WHERE siteId IN ({ids})
        AND toDate(timeBegin) >= today() - 90
        AND toDate(timeBegin) <= today() - 1
      GROUP BY siteId, sessionId
    )
    SELECT
      siteId,
      count() AS total_sessions,
      countIf(searches > 0 OR ac > 0) AS search_sessions,
      countIf(wo > 0 AND (searches > 0 OR ac > 0)) AS search_orders,
      round(
        countIf(wo > 0 AND (searches > 0 OR ac > 0))
        / nullIf(countIf(searches > 0 OR ac > 0), 0) * 100, 3
      ) AS search_cvr_pct,
      round(
        sumIf(rev, wo > 0 AND (searches > 0 OR ac > 0))
        / nullIf(countIf(wo > 0 AND (searches > 0 OR ac > 0)), 0), 2
      ) AS aov_search
    FROM deduped
    GROUP BY siteId
    ORDER BY search_sessions DESC
    """
    r = requests.post(
        CH_URL,
        auth=(CH_USER, CH_PASS),
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=180,
        verify=False,
    )
    if not r.ok:
        raise RuntimeError(f"CH {r.status_code}: {r.text[:500]}")
    data = r.json()
    return list(data.get("data") or [])


def airtable_fashion_partners() -> dict:
    last_err = None
    tokens = _airtable_tokens()
    if not tokens:
        return {
            "ok": False,
            "error": "AIRTABLE_TOKEN missing (env / skills .env)",
            "partners": [],
        }
    for token in tokens:
        try:
            return _airtable_fetch(token)
        except Exception as e:
            last_err = e
            print("airtable fail", type(e).__name__, e)
    return {"ok": False, "error": str(last_err), "partners": []}


def _airtable_fetch(token: str) -> dict:
    base = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{AIRTABLE_TABLE}"
    offset = None
    records = []
    while True:
        q = {"pageSize": 100, "view": AIRTABLE_VIEW}
        if offset:
            q["offset"] = offset
        req = urllib.request.Request(
            base + "?" + urllib.parse.urlencode(q),
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        records.extend(data.get("records") or [])
        offset = data.get("offset")
        if not offset:
            break

    fashion_keys = (
        "одежд",
        "fashion",
        "обув",
        "sport",
        "спорт",
        "apparel",
        "белье",
        "textile",
    )
    partners = []
    verticals: dict[str, int] = {}
    for rec in records:
        f = rec.get("fields") or {}
        vert = f.get("Вертикаль") or f.get("Vertical") or ""
        if isinstance(vert, list):
            vert = ", ".join(map(str, vert))
        verticals[str(vert)] = verticals.get(str(vert), 0) + 1
        blob = " ".join(str(v) for v in f.values()).lower()
        vert_l = str(vert).lower()
        if not any(k in blob or k in vert_l for k in fashion_keys):
            continue
        sid = f.get("Site ID") or f.get("site_id") or f.get("SiteId")
        if isinstance(sid, list):
            sid = sid[0] if sid else None
        try:
            sid_i = int(sid) if sid is not None else None
        except Exception:
            sid_i = None
        partners.append(
            {
                "site_id": sid_i,
                "account": f.get("Account"),
                "url": f.get("URL"),
                "vertical": vert,
                "stage": f.get("Customer Stage AQ"),
                "mrr": f.get("AQ MRR") or f.get("MRR"),
            }
        )
    return {
        "ok": True,
        "n_records": len(records),
        "vertical_counts_top": sorted(verticals.items(), key=lambda x: -x[1])[:30],
        "partners": partners,
    }


def median_or_none(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None and v > 0]
    if not vals:
        return None
    return float(statistics.median(vals))


def decide_baseline(
    ch_zolla: dict | None,
    metrika: dict,
    peer_metrika: list[dict],
    peer_ch: list[dict],
) -> dict:
    """Pick usable CVR/AOV for money sketch."""
    ch_cvr = float((ch_zolla or {}).get("search_cvr_pct") or 0)
    ch_broken = ch_cvr < CH_CVR_BROKEN_PCT

    m_search = metrika.get("with_search") or {}
    m_cvr = float(m_search.get("cvr_pct") or 0)
    m_aov = float(m_search.get("aov") or 0)
    metrika_ok = m_cvr >= CH_CVR_BROKEN_PCT and m_search.get("visits", 0) > 1000

    peer_m_cvrs = []
    peer_m_aovs = []
    for p in peer_metrika:
        ws = p.get("with_search") or {}
        if ws.get("cvr_pct") and ws["cvr_pct"] >= CH_CVR_BROKEN_PCT:
            peer_m_cvrs.append(float(ws["cvr_pct"]))
            if ws.get("aov"):
                peer_m_aovs.append(float(ws["aov"]))

    peer_ch_cvrs = []
    peer_ch_aovs = []
    for p in peer_ch:
        if int(p.get("siteId") or 0) == ZOLLA_SITE:
            continue
        cvr = float(p.get("search_cvr_pct") or 0)
        if cvr >= CH_CVR_BROKEN_PCT:
            peer_ch_cvrs.append(cvr)
            if p.get("aov_search"):
                peer_ch_aovs.append(float(p["aov_search"]))

    med_m_cvr = median_or_none(peer_m_cvrs)
    med_m_aov = median_or_none(peer_m_aovs)
    med_ch_cvr = median_or_none(peer_ch_cvrs)
    med_ch_aov = median_or_none(peer_ch_aovs)

    chosen: dict[str, Any]
    if metrika_ok:
        chosen = {
            "cvr_source": "zolla_metrika_search",
            "search_cvr_pct": m_cvr,
            "aov": m_aov,
            "visits_or_sessions": m_search.get("visits"),
            "purchases": m_search.get("purchases"),
            "why": "У Zolla есть Метрика (counter+search goal); ecommerce с сегментом поиска надёжнее CH withOrder.",
        }
    elif med_m_cvr is not None:
        chosen = {
            "cvr_source": "fashion_peer_metrika_median",
            "search_cvr_pct": round(med_m_cvr, 3),
            "aov": round(med_m_aov or m_aov or float((ch_zolla or {}).get("aov_search") or 0), 1),
            "why": (
                f"CH Zolla CVR={ch_cvr}% broken (<{CH_CVR_BROKEN_PCT}%); "
                f"Метрика Zolla недоступна/слабая → медиана search CVR fashion-peers Metrika."
            ),
            "peer_n": len(peer_m_cvrs),
        }
    elif med_ch_cvr is not None:
        chosen = {
            "cvr_source": "fashion_peer_ch_median",
            "search_cvr_pct": round(med_ch_cvr, 3),
            "aov": round(med_ch_aov or float((ch_zolla or {}).get("aov_search") or 0), 1),
            "why": (
                f"CH Zolla CVR={ch_cvr}% broken; Metrika peers empty → "
                f"медиана search CVR fashion-peers ClickHouse (excl. broken)."
            ),
            "peer_n": len(peer_ch_cvrs),
        }
    else:
        chosen = {
            "cvr_source": "fallback_assumed_fashion",
            "search_cvr_pct": 1.0,
            "aov": float((ch_zolla or {}).get("aov_search") or 3500),
            "why": "Нет ни Метрики, ни живых peer CVR — ASSUMED fashion search CVR 1%.",
        }

    return {
        "ch_zolla_broken": ch_broken,
        "ch_zolla_cvr_pct": ch_cvr,
        "metrika_zolla_ok": metrika_ok,
        "peer_metrika_median_cvr_pct": med_m_cvr,
        "peer_ch_median_cvr_pct": med_ch_cvr,
        "chosen": chosen,
        "rule": (
            "Если CH search_cvr < 0.05% (явный недоучёт заказов) — не использовать для денег. "
            "Порядок: (1) Метрика партнёра search segment, (2) медиана Метрики похожих fashion, "
            "(3) медиана CH похожих с CVR≥0.05%, (4) ASSUMED vertical floor."
        ),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d1, d2 = _period_90d()
    print("period", d1, d2)

    print("--- Metrika Zolla ---")
    metrika = pull_zolla_metrika()
    print(json.dumps(metrika, ensure_ascii=False, indent=2))

    print("--- Metrika peers ---")
    peer_m = pull_peer_metrika()

    print("--- Airtable fashion ---")
    at = airtable_fashion_partners()
    print("airtable ok", at.get("ok"), "partners", len(at.get("partners") or []))
    if at.get("vertical_counts_top"):
        print("top verts", at["vertical_counts_top"][:15])

    # extend CH list from airtable site ids
    at_ids = [p["site_id"] for p in (at.get("partners") or []) if p.get("site_id")]
    ch_ids = sorted(set(FASHION_PEERS_CH + at_ids))[:40]
    print("--- CH peers", ch_ids, "---")
    peer_ch: list[dict] = []
    ch_zolla = None
    try:
        peer_ch = pull_ch_peers(ch_ids)
        for r in peer_ch:
            print(
                "CH",
                r.get("siteId"),
                "search_sess",
                r.get("search_sessions"),
                "cvr%",
                r.get("search_cvr_pct"),
                "aov",
                r.get("aov_search"),
            )
            if int(r.get("siteId") or 0) == ZOLLA_SITE:
                ch_zolla = r
    except Exception as e:
        print("CH error", e)
        # fallback local file
        p = OUT / "ch_baseline_3826.json"
        if p.is_file():
            ch_zolla = json.loads(p.read_text(encoding="utf-8"))
            ch_zolla = {
                "siteId": ZOLLA_SITE,
                "search_cvr_pct": ch_zolla.get("search_cvr_pct"),
                "aov_search": ch_zolla.get("aov_search"),
                "search_sessions": ch_zolla.get("search_sessions"),
                "search_orders": ch_zolla.get("search_orders"),
            }

    decision = decide_baseline(ch_zolla, metrika, peer_m, peer_ch)
    report = {
        "generated_for": "Zolla 3826 money baseline repair",
        "period": {"date1": d1, "date2": d2},
        "metrika_zolla": metrika,
        "peer_metrika": peer_m,
        "airtable": {
            "ok": at.get("ok"),
            "error": at.get("error"),
            "n_fashion_partners": len(at.get("partners") or []),
            "partners_sample": (at.get("partners") or [])[:40],
            "vertical_counts_top": at.get("vertical_counts_top"),
        },
        "peer_ch": peer_ch,
        "decision": decision,
    }
    path = OUT / "money_baseline_benchmark.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path)
    print("CHOSEN", json.dumps(decision["chosen"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
