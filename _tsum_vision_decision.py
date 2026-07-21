# -*- coding: utf-8 -*-
"""Decide KEEP vs REJECT for TSUM vision attrs (feed collision + search rules)."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
PROBE = OUT / "vision_probe_results.json"
GAP = OUT / "gap_analysis.json"
INV = OUT / "feed_inventory.json"

# Canonical attr groups for partner messaging
CANON = {
    "принт": "принт_узор",
    "принт/узор": "принт_узор",
    "узор": "принт_узор",
    "силуэт": "силуэт_посадка",
    "посадка": "силуэт_посадка",
    "силуэт сумки": "силуэт_сумки",
    "тип застежки": "застежка",
    "застежка": "застежка",
    "тип воротника": "воротник_вырез",
    "воротник": "воротник_вырез",
    "вырез": "воротник_вырез",
    "капюшон": "капюшон",
    "детали": "детали_декор",
    "фактура": "фактура",
    "эффект": "фактура",
    "форма носка": "обувь_форма",
    "концентрация": "парфюм_концентрация",
    "функции часов": "часы_функции",
    "тип циферблата": "часы_циферблат",
    "форма корпуса": "часы_корпус",
    "материал ремешка": "часы_ремешок",
    "цвет ремешка": "часы_ремешок",
    "тип индикации": "часы_функции",
    "тип браслета": "украшения",
    "форма подвески": "украшения",
    "тип цепочки": "украшения",
    "материал браслета": "украшения",
    "тип плетения": "украшения",
    "форма оправы": "очки",
    "тип линз": "очки",
    "карманы": "детали_декор",
    "количество ручек": "силуэт_сумки",
}


def norm(s: str) -> str:
    return (s or "").strip().casefold().replace("ё", "е")


def decide(attr_name: str, value: str, product: dict, vision: dict) -> tuple[str, str]:
    """Return (KEEP|REJECT, reason)."""
    an = norm(attr_name)
    val = norm(value)
    params = {norm(k): norm(str(v)) for k, v in (product.get("params") or {}).items()}
    # product in results is stripped — reload keys only; use vision already_in_feed
    name = norm(product.get("name") or "")

    if not val or val in {"true", "false", "да", "нет"} and an not in {"капюшон"}:
        if an not in {"капюшон"} and val in {"true", "false"}:
            return "REJECT", "булев без search value"

    # Negations
    if val.startswith("без ") or "не содержит" in val or val.endswith("-free"):
        return "REJECT", "негация ломает поиск"

    # Length — often already in attribute_length
    if an in {"длина"} or val in {"мини", "миди", "макси"}:
        return "REJECT", "уже есть attribute_length / слабо новое"

    # Color / material duplicates
    if an in {"цвет", "оттенок", "материал", "состав"}:
        return "REJECT", "уже в фиде (Цвет/Материал)"

    # Brand / volume often in name
    if an in {"бренд", "объем", "объём", "линия"}:
        if val and val in name:
            return "REJECT", "уже в названии"
        if an in {"бренд", "линия"}:
            return "REJECT", "бренд/линия — не vision-ценность"

    # Low search relevance
    if an in {"стойкость", "тип волос", "особенность"}:
        return "REJECT", "слабая search relevance / маркетинг"

    # Watch OCR noise if attribute already exists sparsely — still KEEP functions/dial as new search lex
    if an in {"детали", "детали декора"} and val in {"без декора", "декор"}:
        return "REJECT", "слишком общее значение"

    # If model itself said already in feed
    already = [norm(x) for x in (vision.get("already_in_feed_visible") or [])]
    blob = " ".join(already)
    if val and val in blob:
        return "REJECT", "модель отметила: уже в фиде"

    # Default KEEP for visual fashion facets
    return "KEEP", "новый визуальный/OCR атрибут"


def main() -> None:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    gap = json.loads(GAP.read_text(encoding="utf-8"))
    inv = json.loads(INV.read_text(encoding="utf-8"))

    # Reload full params from candidates for collision
    cands = json.loads((OUT / "vision_candidates.json").read_text(encoding="utf-8"))
    by_id = {}
    for bucket, items in cands.items():
        for it in items:
            by_id[str(it.get("offer_id"))] = it

    keep, reject = [], []
    canon_keep = Counter()
    by_bucket_keep = defaultdict(list)

    for r in probe.get("results") or []:
        if "error" in r:
            continue
        meta = r.get("product") or {}
        oid = str(meta.get("offer_id") or "")
        full = by_id.get(oid) or meta
        vision = r.get("vision") or {}
        for a in vision.get("new_attributes") or []:
            name = (a.get("name") or "").strip()
            value = (a.get("value") or "").strip()
            decision, reason = decide(name, value, full, vision)
            row = {
                "offer_id": oid,
                "bucket": meta.get("bucket") or full.get("bucket"),
                "product_name": meta.get("name") or full.get("name"),
                "picture": meta.get("picture") or full.get("picture"),
                "attr": name,
                "value": value,
                "evidence": a.get("evidence"),
                "search_relevance": a.get("search_relevance"),
                "filter_candidate": a.get("filter_candidate"),
                "decision": decision,
                "reason": reason,
                "canon": CANON.get(norm(name), norm(name)),
            }
            if decision == "KEEP":
                keep.append(row)
                canon_keep[row["canon"]] += 1
                by_bucket_keep[row["bucket"]].append(row)
            else:
                reject.append(row)

    # Cleaner vision impact: families with stricter needles (no short substring traps)
    STRICT = {
        "принт_узор": ["принт", "клетка", "полоск", "леопард", "цветочн", "горошек", "логомания", "animal print"],
        "силуэт_посадка": ["оверсайз", "oversize", "slim fit", "wide leg", "клёш", "клеш", "притален", "а-силуэт"],
        "капюшон": ["капюшон", "с капюшоном", "hoodie"],
        "застежка": ["на молнии", "на пуговиц", "шнуровк", "на кнопк"],
        "обувь_каблук": ["на каблуке", "каблук", "шпилька", "танкетк", "платформ"],
        "сумка_тип": ["кроссбоди", "crossbody", "тоут ", " tote", "клатч", "шоппер", "багет"],
        "парфюм": ["туалетная вода", "парфюмерная вода", "eau de", " edp", " edt", "ноты "],
        "фактура_декор": ["стёжк", "стежк", "плиссе", "кружев", "пайетк", "стразы", "вышивк", "бахром"],
    }
    queries = json.loads((OUT / "top-30k-queries-ch.json").read_text(encoding="utf-8"))["queries"]
    strict_impact = {}
    seen_all = set()
    total_strict_searches = 0
    for fam, needles in STRICT.items():
        matched = []
        for qrow in queries:
            q = qrow["q"]
            if any(n in q for n in needles):
                matched.append(qrow)
                seen_all.add(q)
        s = sum(int(x["cnt"]) for x in matched)
        strict_impact[fam] = {
            "unique_queries": len(matched),
            "searches_90d": s,
            "examples": [
                {"q": x["q"], "cnt": int(x["cnt"])}
                for x in sorted(matched, key=lambda z: -int(z["cnt"]))[:8]
            ],
        }
        total_strict_searches = None  # compute below
    # unique across families
    uniq = []
    seen = set()
    for fam, needles in STRICT.items():
        for qrow in queries:
            q = qrow["q"]
            if q in seen:
                continue
            if any(n in q for n in needles):
                seen.add(q)
                uniq.append(qrow)
    total_strict_searches = sum(int(x["cnt"]) for x in uniq)

    # Feed params summary for partner
    param_stats = inv.get("param_stats") or []
    searchable_params = []
    technical = {
        "brand_id",
        "model_id",
        "product_id",
        "color_concrete_id",
        "color_base_id",
        "size_id",
        "date_create",
        "Лого",
        "Штрихкод",
        "Артикул",
    }
    for p in param_stats:
        name = p["name"]
        fill = round(100.0 * p["offers_with_param"] / max(inv["offers_total"], 1), 1)
        role = "technical" if name in technical else "searchable"
        searchable_params.append(
            {
                "name": name,
                "fill_pct": fill,
                "offers": p["offers_with_param"],
                "role": role,
                "examples": p.get("examples", [])[:5],
            }
        )

    decision = {
        "partner": "TSUM",
        "site_id": 203,
        "model": probe.get("summary", {}).get("model"),
        "n_probed": probe.get("summary", {}).get("n_probed"),
        "keep_count": len(keep),
        "reject_count": len(reject),
        "canon_keep_counts": canon_keep.most_common(),
        "keep": keep,
        "reject": reject,
        "do_not_extract_from_images": [
            {"attr": "Цвет / Оттенок", "why": "fill ~100% в фиде"},
            {"attr": "Материал (состав %)", "why": "fill ~91% в фиде"},
            {"attr": "Пол", "why": "всегда в фиде"},
            {"attr": "Размер", "why": "в фиде (SKU-level)"},
            {"attr": "Бренд / vendor", "why": "в name; топ запросов — брендовые"},
            {"attr": "Артикул / id / штрихкод", "why": "технические поля"},
            {"attr": "Страна дизайна", "why": "уже в фиде (~77%)"},
            {"attr": "Сезон SS/FW", "why": "уже в фиде; слабо ищут как фильтр"},
            {"attr": "attribute_length (мини/миди/макси)", "why": "частично заполнен (~35%); не дублировать"},
            {"attr": "attribute_sleeve", "why": "частично заполнен (~33%); дополнять только пробелы"},
            {"attr": "Негации (без X)", "why": "ломают поиск"},
        ],
        "extract_from_images": [
            {
                "attr": "Принт / узор",
                "why": "в фиде нет отдельного паттерна; attribute_details ~8% и почти без клеток/полосок",
                "query_family": "принт_узор",
            },
            {
                "attr": "Силуэт / посадка",
                "why": "нет structured fit; запросы оверсайз/slim/клёш",
                "query_family": "силуэт_посадка",
            },
            {
                "attr": "Капюшон",
                "why": "нет boolean hood в фиде",
                "query_family": "капюшон",
            },
            {
                "attr": "Воротник / вырез",
                "why": "нет отдельного атрибута",
                "query_family": "воротник_вырез",
            },
            {
                "attr": "Застёжка (визуальная)",
                "why": "attribute_clasp только ~2%",
                "query_family": "застежка",
            },
            {
                "attr": "Детали / декор / фактура",
                "why": "attribute_details sparse; стёжка, плиссе, пайетки видны на фото",
                "query_family": "фактура_декор",
            },
            {
                "attr": "Тип сумки (тоут/кроссбоди/багет)",
                "why": "custom categories частично; визуальный силуэт стабильнее",
                "query_family": "сумка_тип",
            },
            {
                "attr": "Обувь: каблук / форма носка",
                "why": "attribute_base есть, но каблук/шпилька в запросах без покрытия",
                "query_family": "обувь_каблук",
            },
            {
                "attr": "Парфюм: концентрация + ноты (OCR)",
                "why": "в params нет нот; на флаконе часто EDP/EDT и ноты",
                "query_family": "парфюм",
            },
            {
                "attr": "Часы: функции / циферблат / ремешок",
                "why": "watch attrs sparse (<0.2%); OCR с циферблата сильный",
                "query_family": "часы",
            },
        ],
        "strict_query_impact": {
            "unique_queries": len(uniq),
            "searches_90d": total_strict_searches,
            "share_of_top30k_searches_pct": round(
                100.0 * total_strict_searches / max(gap["total_searches_in_top30k"], 1), 2
            ),
            "by_family": strict_impact,
        },
        "feed_params": searchable_params,
        "catalog": {
            "offers_total": inv["offers_total"],
            "categories_total": inv["categories_total"],
            "unique_param_names": inv["unique_param_names"],
            "offers_with_picture": inv["offers_with_picture"],
        },
        "gap_headline": {
            "residual_rate_searches_pct": gap["residual_rate_searches_pct"],
            "searches_with_residual": gap["searches_with_residual"],
            "total_searches_top30k": gap["total_searches_in_top30k"],
        },
    }

    (OUT / "vision_attr_decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = []
    md.append("# TSUM — решение по атрибутам с картинок\n")
    md.append(f"Модель: `{decision['model']}` · probe: **{decision['n_probed']}** SKU · KEEP **{len(keep)}** · REJECT **{len(reject)}**\n")
    md.append("## Не извлекать с картинок (уже в фиде / вредно)\n")
    for x in decision["do_not_extract_from_images"]:
        md.append(f"- **{x['attr']}** — {x['why']}")
    md.append("\n## Извлекать с картинок (нужно партнёру)\n")
    for x in decision["extract_from_images"]:
        fam = x["query_family"]
        imp = strict_impact.get(fam) or {}
        md.append(
            f"- **{x['attr']}** — {x['why']} · запросы≈{imp.get('searches_90d', 'n/a')} / 90д"
        )
    md.append("\n## Impact (строгие семейства запросов, 90д, top-30k)\n")
    md.append(
        f"- Уникальных запросов: **{len(uniq)}**\n- Поисков: **{total_strict_searches:,}** "
        f"({decision['strict_query_impact']['share_of_top30k_searches_pct']}% top-30k)\n"
    )
    md.append("\n## KEEP canon counts (probe)\n")
    for c, n in canon_keep.most_common():
        md.append(f"- {c}: {n}")
    md.append("\n## Примеры KEEP\n")
    md.append("| bucket | товар | attr | value | evidence |")
    md.append("|---|---|---|---|---|")
    for row in keep[:40]:
        md.append(
            f"| {row['bucket']} | {(row['product_name'] or '')[:40]} | {row['attr']} | {row['value']} | {row['evidence']} |"
        )
    (OUT / "VISION_ATTR_DECISION.md").write_text("\n".join(md), encoding="utf-8")
    print(
        json.dumps(
            {
                "keep": len(keep),
                "reject": len(reject),
                "canon": canon_keep.most_common(15),
                "strict_searches": total_strict_searches,
                "strict_queries": len(uniq),
                "share_pct": decision["strict_query_impact"]["share_of_top30k_searches_pct"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
