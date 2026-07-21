# -*- coding: utf-8 -*-
"""
Classify vision probe attrs like attributes_extraction negation_value_filter:
- find on pack → log
- do NOT keep for search upload if negation / collision / fluff
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "portfolio" / "221_azbuka"
RAW = ROOT / "vision_probe_results.json"

# Mirror extraction config + English pack claims (search token trap)
NEG_CONTAINS = [
    "не содержит",
    "не вход",
    "не входит",
    "не входят",
    "не включ",
    "не комплект",
    "без заменителя",
    "msg-free",
    "msg free",
    "no preservative",
    "no artificial",
    "non-gmo",
    "non gmo",
    "gmo-free",
    "gluten-free",
    "gluten free",
    "lactose-free",
    "lactose free",
    "sugar-free",
    "sugar free",
    "without ",
    "-free",
    " free",
]
NEG_NAME_STARTS = ("без ", "не ")
NEG_ATTR_NAMES = {
    "не содержит",
    "бзмж",
    "без глутамата натрия",
    "без консервантов",
    "без гмо",
    "без искусственных ароматизаторов",
    "без сахара",
    "без лактозы",
    "без глютена",
}

NUTRITION_NAME = ("белк", "углевод", "энергет", "кбжу", "жиры на", "жир на", "белки на")
OPS_EXACT = {
    "ту",
    "гост",
    "срок годности",
    "история бренда",
    "производитель",
    "бренд",
    "регион производства",
    "название линейки",
}
WEAK_PACK = {"бутылка", "пластиковый контейнер", "стекло"}  # стекло для специй ок — см. ниже


def _norm(s: str) -> str:
    return " ".join(str(s or "").lower().replace("ё", "е").split())


def _stem_hit(token: str, hay: str) -> bool:
    """Rough RU stem: ваниль↔ванили, гриб↔грибами."""
    t = token.lower()
    if len(t) < 4:
        return t in hay
    root = t[: max(4, len(t) - 2)]
    return root in hay


def is_negation(name: str, value: str) -> bool:
    n, v = _norm(name), _norm(value)
    blob = f"{n} {v}"
    if n in NEG_ATTR_NAMES or any(n.startswith(p) for p in NEG_NAME_STARTS):
        return True
    if any(p in blob for p in NEG_CONTAINS):
        return True
    if re.search(r"\b(no|non|without|free)\b", blob):
        if any(
            x in blob
            for x in (
                "preserv",
                "gmo",
                "msg",
                "artificial",
                "gluten",
                "lactose",
                "sugar",
                "color",
                "colour",
                "dye",
            )
        ):
            return True
    return False


def classify(name: str, value: str, product_name: str, gold_names: list[str], product_type: str) -> str | None:
    """Return reject reason or None if keep candidate."""
    n, v = _norm(name), _norm(value)
    pname = _norm(product_name)

    if is_negation(name, value):
        return "negation_value"
    if any(x in n for x in NUTRITION_NAME) or "ккал" in v:
        return "nutrition_ops"
    if n in OPS_EXACT or n.startswith("срок год"):
        return "low_search_ops"
    if v and len(v) >= 4 and v in pname:
        return "offer_name_token_overlap"
    toks = [t for t in re.findall(r"[a-zа-я]{4,}", v) if t]
    if toks and all(_stem_hit(t, pname) for t in toks):
        return "offer_name_token_overlap"
    # latin line name overlap (terre & laves)
    latin = re.sub(r"[^a-z0-9]+", " ", v)
    if latin.strip() and all(len(t) < 3 or t in re.sub(r"[^a-z0-9]+", " ", pname) for t in latin.split()):
        if any(len(t) >= 4 for t in latin.split()):
            return "offer_name_token_overlap"
    if n in {"апелласьон", "регион", "сорт винограда"}:
        return "feed_wine_duplicate_risk"
    if n == "тип упаковки":
        if "вино" in pname or "alcohol" in product_type or "wine" in product_type:
            return "low_search_packaging"
        if v in {"бутылка", "пластиковый контейнер"}:
            return "low_search_packaging"
    if n == "способ обработки" and "сублимир" in v:
        return "weak_visual_guess"
    return None


def main():
    data = json.loads(RAW.read_text(encoding="utf-8"))
    rejected_rows = []
    keep_rows = []
    empty_product_only = []

    for r in data["results"]:
        p = r["product"]
        v = r.get("vision") or {}
        new = v.get("new_attributes") or []
        gold_names = p.get("gold_attr_names") or []
        if not new:
            empty_product_only.append(
                {
                    "offer_id": p["id"],
                    "product_type": p["product_type"],
                    "path": p["feed_category_path"],
                    "image_kind": v.get("image_kind"),
                    "offer_name": p["name"],
                    "note": v.get("skip_reason") or "no new_attributes from model",
                }
            )
            continue
        for a in new:
            an = str(a.get("name") or "").strip()
            av = a.get("value")
            if isinstance(av, bool):
                av = "true" if av else "false"
            else:
                av = str(av or "").strip()
            reason = classify(an, av, p["name"], gold_names, p.get("product_type") or "")
            row = {
                "offer_id": p["id"],
                "product_type": p["product_type"],
                "path": p["feed_category_path"],
                "offer_name": p["name"],
                "image_kind": v.get("image_kind"),
                "attribute_name": an,
                "attribute_value": av,
                "evidence": a.get("evidence"),
                "model_relevance": a.get("search_relevance"),
            }
            if reason:
                row["reject_reason"] = reason
                row["reject_label"] = {
                    "negation_value": "Негация (без / не содержит / -free) — ломает поиск",
                    "nutrition_ops": "КБЖУ / nutrition (уже в фиде)",
                    "low_search_ops": "ТУ/бренд/срок/регион — низкая search relevance",
                    "offer_name_token_overlap": "Уже в названии",
                    "feed_wine_duplicate_risk": "Уже закрыто params вина",
                    "low_search_packaging": "Тип упаковки слабо ищут / дубль",
                    "weak_visual_guess": "Слабая visual-догадка без OCR",
                }.get(reason, reason)
                rejected_rows.append(row)
            else:
                row["status"] = "keep_candidate"
                keep_rows.append(row)

    summary = {
        "site_id": 221,
        "rule": "Same spirit as attributes_extraction negation_value_filter: log negation claims, do not upload for search",
        "probed": len(data["results"]),
        "raw_attrs_from_model": sum(
            len((r.get("vision") or {}).get("new_attributes") or []) for r in data["results"]
        ),
        "rejected_n": len(rejected_rows),
        "keep_candidates_n": len(keep_rows),
        "empty_or_product_only_n": len(empty_product_only),
        "reject_reason_counts": {},
        "keep_attr_name_counts": {},
    }
    for row in rejected_rows:
        k = row["reject_reason"]
        summary["reject_reason_counts"][k] = summary["reject_reason_counts"].get(k, 0) + 1
    for row in keep_rows:
        k = row["attribute_name"]
        summary["keep_attr_name_counts"][k] = summary["keep_attr_name_counts"].get(k, 0) + 1

    out = {
        "summary": summary,
        "keep_candidates": keep_rows,
        "rejected_found_but_filtered": rejected_rows,
        "no_attrs_products": empty_product_only,
    }
    (ROOT / "vision_attr_decision.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # CSV tables
    rej_csv = ROOT / "vision_rejected_attrs.csv"
    with rej_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "offer_id",
                "product_type",
                "attribute_name",
                "attribute_value",
                "reject_reason",
                "reject_label",
                "evidence",
                "offer_name",
                "path",
            ],
        )
        w.writeheader()
        for row in rejected_rows:
            w.writerow({k: row.get(k, "") for k in w.fieldnames})

    keep_csv = ROOT / "vision_keep_candidates.csv"
    with keep_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "offer_id",
                "product_type",
                "attribute_name",
                "attribute_value",
                "evidence",
                "model_relevance",
                "offer_name",
                "path",
            ],
        )
        w.writeheader()
        for row in keep_rows:
            w.writerow({k: row.get(k, "") for k in w.fieldnames})

    # Markdown tables for humans
    lines = [
        "# 221 vision — решение по атрибутам (probe)",
        "",
        f"Сырых от модели: **{summary['raw_attrs_from_model']}** · "
        f"отфильтровано: **{summary['rejected_n']}** · "
        f"кандидаты в заливку: **{summary['keep_candidates_n']}** · "
        f"SKU без новых attrs: **{summary['empty_or_product_only_n']}**",
        "",
        "## Правило негации (как в extraction)",
        "",
        "Нашли на этикетке «без X» / «не содержит» / `MSG-free` / `Non-GMO` — **записываем в rejected**, "
        "в поиск **не льём**: токен `краситель`/`сахар`/`консервант` иначе матчится позитивным запросом.",
        "",
        "## KEEP — перечень новых кандидатов (после фильтров)",
        "",
    ]
    if not keep_rows:
        lines.append("_Пусто: после негации и коллизий с name/gold upload-кандидатов почти не осталось._")
        lines.append("")
    else:
        lines += [
            "| offer_id | type | attr | value | evidence |",
            "|---|---|---|---|---|",
        ]
        for row in keep_rows:
            lines.append(
                f"| {row['offer_id']} | {row['product_type']} | {row['attribute_name']} | "
                f"{row['attribute_value']} | {row.get('evidence','')} |"
            )
        lines.append("")

    lines += [
        "## REJECTED — нашли на этикетке, специально не выделяем",
        "",
        "| offer_id | attr | value | reason |",
        "|---|---|---|---|",
    ]
    for row in rejected_rows:
        lines.append(
            f"| {row['offer_id']} | {row['attribute_name']} | {row['attribute_value']} | "
            f"{row['reject_label']} |"
        )
    lines += [
        "",
        f"CSV: `{rej_csv.name}`, `{keep_csv.name}` · JSON: `vision_attr_decision.json`",
    ]
    (ROOT / "VISION_ATTR_DECISION.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("KEEP:")
    for row in keep_rows:
        print(f"  + {row['attribute_name']}={row['attribute_value']}  [{row['product_type']}] {row['offer_id']}")
    print(f"rejected={len(rejected_rows)} -> {rej_csv}")


if __name__ == "__main__":
    main()
