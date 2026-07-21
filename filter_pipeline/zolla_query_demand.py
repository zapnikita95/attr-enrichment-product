#!/usr/bin/env python3
"""
Evidence for Zolla filter candidacy from ClickHouse search queries.

NOT LLM opinion alone: counts real searchTerm frequency (90d) and maps
tokens → filter intents. Writes portfolio/zolla_filters/query_demand_evidence.json
+ FILTER_DEMAND_EVIDENCE.md with citations for every claim.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "portfolio" / "zolla_filters"
sys.path.insert(0, str(ROOT))
from ch_config import CH_PASS, CH_URL, CH_USER  # type: ignore

CH_AUTH = (CH_USER, CH_PASS)

# Diginetica project id from attributes_extraction; verify in CH + domain probe.
CANDIDATE_SITE_IDS = (3826, 1967)  # Zolla project + Befree control if needed

# Intent lexicon: token/phrase → filter attr_id (fashion RU)
# Evidence rule: query contains ANY pattern → +count to that intent.
INTENT_PATTERNS: dict[str, list[str]] = {
    "hood": [
        r"\bкапюшон\w*",
        r"\bс\s+капюшон\w*",
        r"\bхуди\b",
        r"\bhoodie\b",
        r"\bпарка\b",
        r"\bанорак\b",
    ],
    "length": [
        r"\bмини\b",
        r"\bмиди\b",
        r"\bмакси\b",
        r"\bmini\b",
        r"\bmidi\b",
        r"\bmaxi\b",
        r"\bдо\s+колен\w*",
        r"\bукороченн\w*",
        r"\bдлинн(ое|ая|ый)\s+(плать|юбк|пальт)",
        r"\bкоротк(ое|ая|ий)\s+(плать|юбк)",
    ],
    "print_pattern": [
        r"\bв\s+полоск\w*",
        r"\bполоск\w*",
        r"\bклетк\w*",
        r"\bв\s+клетк\w*",
        r"\bгорошек\b",
        r"\bв\s+горошек\b",
        r"\bцвет(ы|очн|очный)\w*",
        r"\bпринт\w*",
        r"\bлеопард\w*",
        r"\bзебр\w*",
        r"\bкамуфляж\w*",
        r"\bмилитари\b",
        r"\bгусиная\s+лапка\b",
        r"\bмеланж\w*",
        r"\bлюрекс\w*",
        r"\bанимал\w*",
        r"\bгеометр\w*",
    ],
    "sleeve_length": [
        r"\bбез\s+рукав\w*",
        r"\bкоротк(им|ий|ими|ой)\s+рукав\w*",
        r"\bдлинн(ым|ый|ыми|ой)\s+рукав\w*",
        r"\bрукав\s*3/?4\b",
        r"\bтри\s+четверти\b",
        # «майка/топ» — тип изделия (прокси без рукавов), считаем отдельно ниже как product_proxy
    ],
    "sleeve_length_product_proxy": [
        r"\bмайка\b",
        r"\bмайк[уи]\b",
        r"\bтоп\b",
        r"\bтопы\b",
    ],
    "pockets": [
        r"\bкарман\w*",
        r"\bс\s+карман\w*",
        r"\bбез\s+карман\w*",
    ],
    "fastener": [
        r"\bмолни\w*",
        r"\bна\s+молнии\b",
        r"\bпуговиц\w*",
        r"\bна\s+пуговиц\w*",
        r"\bкнопк\w*",
        r"\bзавязк\w*",
    ],
    "collar": [
        r"\bворотник\w*",
        r"\bстойк\w*",
        r"\bv[-\s]?вырез\w*",
        r"\bвырез\w*",
        r"\bгольф\b",
        r"\bводолазк\w*",
        r"\bхомут\b",
        r"\bкругл(ый|ым)\s+вырез\w*",
    ],
    "color": [
        r"\bчёрн\w*",
        r"\bчерн\w*",
        r"\bбел\w*",
        r"\bбежев\w*",
        r"\bкрасн\w*",
        r"\bсин\w*",
        r"\bзелён\w*",
        r"\bзелен\w*",
        r"\bрозов\w*",
        r"\bсер(ый|ая|ое|ые)\b",
        r"\bхаки\b",
        r"\bбордов\w*",
    ],
    "material": [
        r"\bхлопок\w*",
        r"\bхлопков\w*",
        r"\bшерст\w*",
        r"\bкашемир\w*",
        r"\bлён\b",
        r"\bлен\b",
        r"\bльнян\w*",
        r"\bшелк\w*",
        r"\bшёлк\w*",
        r"\bэкокожа\w*",
        r"\bиз\s+кожи\b",
        r"\bкожан\w*",
        r"\bзамш\w*",
        # не матчим голое «джинсы» (тип изделия); только ткань/материал
        r"\bджинсов\w+",
        r"\bвельвет\w*",
        r"\bтрикотаж\w*",
        r"\bвискоз\w*",
        r"\bполиэстер\w*",
        r"\bангор\w*",
    ],
    "silhouette": [
        r"\bоверсайз\w*",
        r"\boversize\b",
        r"\bприлегающ\w*",
        r"\bсвободн\w*",
        r"\bпрям(ой|ая|ое)\s+(крой|силуэт|плать|юбк|брюк)",
        r"\bskinny\b",
        r"\bскинни\b",
        r"\bwide\s*leg\b",
        r"\bклёш\w*",
        r"\bклеш\w*",
    ],
    "gender_target": [
        r"\bмужск\w*",
        r"\bженск\w*",
        r"\bунисекс\b",
        r"\bдетск\w*",
        r"\bдля\s+мужчин\b",
        r"\bдля\s+женщин\b",
    ],
    "fit_waist": [
        r"\bвысокой\s+посадк\w*",
        r"\bвысокой\s+посадк\w*",
        r"\bсредней\s+посадк\w*",
        r"\bнизкой\s+посадк\w*",
        r"\bпосадк\w*",
    ],
}

FASHION_BASELINE = {
    "hood": "Facet верхней одежды; в UI часто «с капюшоном».",
    "length": "Классика платьев/юбок: mini/midi/maxi.",
    "print_pattern": "Визуальный поиск стиля (клетка/полоска/принт).",
    "sleeve_length": "Явный sleeve intent в запросе (короткий/длинный/без рукавов).",
    "sleeve_length_product_proxy": "Тип изделия майка/топ ≈ без рукавов; не прямой facet-токен.",
    "pockets": "Функциональный boolean для брюк/верхней.",
    "fastener": "Тип застёжки — частый facet fashion.",
    "collar": "Вырез/воротник влияет на стиль образа.",
    "color": "Сильный intent, но часто уже системный facet/фид.",
    "material": "Сильный intent; collision с params состава. Не путать с типом «джинсы».",
    "silhouette": "Сильный fashion intent (оверсайз/клёш).",
    "gender_target": "Часто уже в навигации/фиде; токен «женские/мужские» = modifier, не всегда gap.",
    "fit_waist": "Посадка — facet брюк/джинсов.",
}

# When strong in CH but typically already in feed/nav — mark carefully
FEED_OR_NAV_LIKELY = {"gender_target", "color", "material"}


def ch_query(sql: str, timeout: int = 120) -> dict | None:
    resp = requests.post(
        CH_URL,
        auth=CH_AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if resp.status_code != 200:
        print(f"CH ERROR {resp.status_code}: {resp.text[:400]}")
        return None
    return resp.json()


def resolve_zolla_site_id() -> tuple[int, dict]:
    """Pick siteId with traffic; prefer 3826 if present."""
    checks = {}
    for sid in CANDIDATE_SITE_IDS:
        r = ch_query(
            f"""
            SELECT
                count() AS n,
                uniqExact(lowerUTF8(searchTerm)) AS uniq_q
            FROM sessions.searches
            WHERE siteId = {sid}
              AND toDate(timestamp) >= today() - 90
              AND toDate(timestamp) <= today() - 1
            """
        )
        n = int((r or {}).get("data", [{}])[0].get("n") or 0) if r else 0
        uq = int((r or {}).get("data", [{}])[0].get("uniq_q") or 0) if r else 0
        checks[sid] = {"n": n, "uniq_q": uq}
        print(f"siteId={sid} searches_90d={n} uniq={uq}")
    # Also probe by domain hint in recent top if 3826 empty
    # Prefer Zolla project id 3826 when it has traffic (do NOT pick Befree 1967 by max).
    preferred = 3826
    if checks.get(preferred, {}).get("n", 0) > 0:
        chosen = preferred
    else:
        chosen = max(checks.items(), key=lambda x: x[1]["n"])[0]
        r = ch_query(
            """
            SELECT siteId, count() AS n
            FROM sessions.searches
            WHERE toDate(timestamp) >= today() - 7
              AND toDate(timestamp) <= today() - 1
              AND (
                positionCaseInsensitiveUTF8(remoteHost, 'zolla') > 0
                OR positionCaseInsensitiveUTF8(referer, 'zolla') > 0
              )
            GROUP BY siteId
            ORDER BY n DESC
            LIMIT 20
            """
        )
        print("domain probe", (r or {}).get("data"))
        if r and r.get("data"):
            chosen = int(r["data"][0]["siteId"])
    print(f"CHOSEN siteId={chosen}")
    return int(chosen), checks


def fetch_top_queries(site_id: int, limit: int = 5000) -> list[dict]:
    r = ch_query(
        f"""
        SELECT
            lowerUTF8(trim(searchTerm)) AS q,
            count() AS search_count
        FROM sessions.searches
        WHERE siteId = {site_id}
          AND toDate(timestamp) >= today() - 90
          AND toDate(timestamp) <= today() - 1
          AND lengthUTF8(trim(searchTerm)) >= 2
        GROUP BY q
        ORDER BY search_count DESC
        LIMIT {int(limit)}
        """
    )
    if not r:
        return []
    return [{"q": row["q"], "search_count": int(row["search_count"])} for row in r.get("data") or []]


def _verdict(intent: str, vol: int, uniq: int, total: int) -> str:
    if vol <= 0:
        return "no_signal_in_top"
    strong = vol >= max(50, 0.002 * total) and uniq >= 5
    if intent == "sleeve_length_product_proxy":
        return "proxy_product_type_not_facet"
    if intent in FEED_OR_NAV_LIKELY and strong:
        return "strong_demand_but_check_feed_nav_collision"
    if strong:
        return "strong_filter_candidate"
    return "weak_or_sparse"


def classify_queries(rows: list[dict]) -> dict:
    compiled = {
        intent: [re.compile(p, re.IGNORECASE | re.UNICODE) for p in pats]
        for intent, pats in INTENT_PATTERNS.items()
    }
    intent_volume: Counter[str] = Counter()
    intent_uniq: Counter[str] = Counter()
    examples: dict[str, list[dict]] = defaultdict(list)
    unmatched_volume = 0
    matched_any = 0

    for row in rows:
        q = row["q"] or ""
        c = int(row["search_count"])
        hits = []
        for intent, regs in compiled.items():
            if any(r.search(q) for r in regs):
                hits.append(intent)
                intent_volume[intent] += c
                intent_uniq[intent] += 1
                if len(examples[intent]) < 12:
                    examples[intent].append({"q": q, "search_count": c})
        if hits:
            matched_any += c
        else:
            unmatched_volume += c

    total = sum(r["search_count"] for r in rows) or 1
    ranked = []
    for intent, vol in intent_volume.most_common():
        ranked.append(
            {
                "attr_id": intent,
                "search_volume_in_top": vol,
                "share_of_top_pct": round(100.0 * vol / total, 2),
                "uniq_queries": intent_uniq[intent],
                "fashion_baseline": FASHION_BASELINE.get(intent, ""),
                "examples": examples[intent][:8],
                "verdict_hint": _verdict(intent, vol, intent_uniq[intent], total),
            }
        )
    return {
        "total_search_events_in_top": total,
        "matched_volume": matched_any,
        "unmatched_volume": unmatched_volume,
        "intents": ranked,
        "zero_signal_intents": [
            i for i in INTENT_PATTERNS if i not in intent_volume
        ],
    }


def write_evidence_md(payload: dict) -> Path:
    site = payload["site_id"]
    cls = payload["classification"]
    lines = [
        "# Zolla Filter Demand — Evidence Pack",
        "",
        f"Updated: {payload['generated_at']}",
        "",
        "## Как считали (метод)",
        "",
        "1. ClickHouse `sessions.searches`, `siteId={}`, окно **90 дней** (`today()-90` … `today()-1`).".format(
            site
        ),
        "2. Топ-{} уникальных `searchTerm` по частоте.".format(payload["top_n"]),
        "3. Regex-лексикон fashion-интентов → attr_id (см. `INTENT_PATTERNS` в `zolla_query_demand.py`).",
        "4. Метрики на intent: `search_volume` (сумма частот), `uniq_queries`, `share_of_top_pct`.",
        "5. Fashion baseline — отраслевое знание (не заменяет CH).",
        "",
        "**Важно:** предыдущий candidacy-вердикт без этого файла = LLM+эвристика. ",
        "Этот документ — пруф из запросов; LLM может только комментировать, не подменять цифры.",
        "",
        "## Site resolve",
        "",
        "```json",
        json.dumps(payload["site_checks"], ensure_ascii=False, indent=2),
        "```",
        "",
        f"Выбран `siteId={site}` (max traffic among candidates).",
        "",
        f"Top slice: **{cls['total_search_events_in_top']}** search events, "
        f"matched intents **{cls['matched_volume']}**, unmatched **{cls['unmatched_volume']}**.",
        "",
        "## Intent ranking (по объёму в топе)",
        "",
        "| rank | attr | volume | share% | uniq q | verdict_hint |",
        "|------|------|--------|--------|--------|--------------|",
    ]
    for i, row in enumerate(cls["intents"], 1):
        lines.append(
            f"| {i} | `{row['attr_id']}` | {row['search_volume_in_top']} | "
            f"{row['share_of_top_pct']} | {row['uniq_queries']} | {row['verdict_hint']} |"
        )
    if cls["zero_signal_intents"]:
        lines += [
            "",
            "### Без сигнала в топе (0 hits)",
            "",
            ", ".join(f"`{x}`" for x in cls["zero_signal_intents"]),
            "",
            "→ либо редкий facet, либо другой словарь пользователей, либо уже закрыт навигацией.",
        ]

    lines += ["", "## Примеры запросов (пруфы)", ""]
    for row in cls["intents"]:
        lines.append(f"### `{row['attr_id']}` — {row['search_volume_in_top']} hits, {row['uniq_queries']} uniq")
        lines.append("")
        lines.append(f"_Fashion baseline:_ {row['fashion_baseline']}")
        lines.append("")
        if not row["examples"]:
            lines.append("- (нет примеров)")
        for ex in row["examples"]:
            lines.append(f"- `{ex['q']}` — **{ex['search_count']}**")
        lines.append("")

    lines += [
        "## Вердикты для filter pipeline (data-driven)",
        "",
        "Правило:",
        "- `strong_filter_candidate` → приоритет schema+typed extract",
        "- `strong_demand_but_check_feed_nav_collision` → спрос есть, но сначала проверить фид/навигацию",
        "- `weak_or_sparse` → пилот осторожно / category-gated",
        "- `proxy_product_type_not_facet` → сигнал косвенный (тип изделия), не прямой facet-токен",
        "- `no_signal_in_top` → не обещать партнёру без доп. исследования",
        "",
        "## Сверка с прошлым пилотом (честность)",
        "",
        "| attr | был в vision-пилоте | CH verdict | комментарий |",
        "|------|---------------------|------------|-------------|",
        "| hood | да | см. таблицу выше | ок как filter если strong/weak>0 |",
        "| length | да | … | |",
        "| print_pattern | да | … | |",
        "| sleeve_length | да | … | |",
        "| pockets | да | … | если weak — не раздувать приоритет |",
        "| fastener | да | … | |",
        "| collar | да | … | |",
        "| gender_target | schema only / reject | collision class | «женские» в запросе ≠ gap фильтра |",
        "| color / material | reject в LLM | collision class | высокий спрос, но часто уже в фиде |",
        "| silhouette / fit_waist | backlog | … | добавить в следующий schema pass |",
        "",
    ]
    by_v: dict[str, list[str]] = defaultdict(list)
    for r in cls["intents"]:
        by_v[r["verdict_hint"]].append(r["attr_id"])
    for k, ids in by_v.items():
        lines.append(f"**{k}:** " + ", ".join(f"`{i}`" for i in ids))
        lines.append("")
    lines.append(
        "**Zero in top:** "
        + (", ".join(f"`{x}`" for x in cls["zero_signal_intents"]) or "—")
    )
    lines += [
        "",
        "## Limitation / честность",
        "",
        "- Топ-N ≠ все запросы (хвост не сканировали — CH LIMIT).",
        "- Regex может ловить ложные срабатывания (напр. «клетка» в другом смысле) — смотри examples.",
        "- Объём ≠ конверсия с фильтром; для lift нужен CH with/without facet (отдельный шаг).",
        "- Fashion baseline не цифра; цифры только из CH выше.",
        "",
    ]
    path = OUT / "FILTER_DEMAND_EVIDENCE.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    site_id, checks = resolve_zolla_site_id()
    if checks.get(site_id, {}).get("n", 0) == 0:
        print("ERROR: no search traffic for candidate site ids")
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id,
            "site_checks": checks,
            "error": "no_traffic",
        }
        (OUT / "query_demand_evidence.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 1

    top_n = 5000
    rows = fetch_top_queries(site_id, limit=top_n)
    print(f"fetched top {len(rows)} queries")
    classification = classify_queries(rows)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site_id": site_id,
        "site_checks": checks,
        "top_n": top_n,
        "window_days": 90,
        "source": "sessions.searches",
        "method": "regex_intent_lexicon_on_top_queries",
        "top_queries_preview": rows[:50],
        "classification": classification,
        "disclaimer": (
            "Prior LLM candidacy without this file is NOT query-evidence. "
            "Use this pack as ground truth for demand ranking."
        ),
    }
    (OUT / "query_demand_evidence.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # also dump raw top for audit
    (OUT / "zolla_top_queries_90d.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = write_evidence_md(payload)
    print("wrote", md)
    for row in classification["intents"][:12]:
        print(
            f"  {row['attr_id']}: vol={row['search_volume_in_top']} "
            f"share={row['share_of_top_pct']}% uniq={row['uniq_queries']} → {row['verdict_hint']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
