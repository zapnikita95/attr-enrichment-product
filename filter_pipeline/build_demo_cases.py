#!/usr/bin/env python3
"""Assemble Zolla demo cases: MAX filters per photo + feed collision + demand tags."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from filter_pipeline.extract_multi import _specs, extract_all_filters
from filter_pipeline.samples import resolve_local_image

OUT = Path(__file__).resolve().parents[1] / "portfolio" / "zolla_filters"
ZOLLA_DB = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\results.db")
SCHEMA = OUT / "filter_schema_clean.json"
DEMAND = OUT / "query_demand_evidence.json"
CACHE = OUT / "demo_multi_extract.json"

# Diversified SKUs (boolean / enum / multi_enum stories)
WANTED = [
    ("31629", "Утеплённое пальто: капюшон + пояс + длина + стёжка, не один boolean."),
    ("177548", "Футболка: кулиска/рукав/вырез; полоска не gap если уже в extract."),
    ("42955", "Мини-платье: длина + рукав + застёжка/бант; материал шифон — из name/фида."),
    ("83302", "Макси-платье: длина + кулиска + вырез + рукав, не только maxi."),
    ("39070", "Мини-юбка: молния + длина + пояс; замша — material из name."),
    ("38537", "Тренчкот: стойка + застёжка + длина + карманы при видимости."),
    ("39614", "Куртка: карманы + капюшон/застёжка/длина — полный набор с фото."),
    ("15873", "Топ без рукавов: рукав + вырез + длина/принт если видно."),
]

# Boolean «нет» / однотонный — шум в демо, если не смысловой gap
SKIP_DISPLAY_VALUES = {
    ("hood", "нет"),
    ("pockets", "нет"),
    ("belt_drawstring", "нет"),
    ("quilted", "нет"),
    ("fastener", "нет"),
    ("print_pattern", "однотонный"),
}

# Не тащим атрибуты «чужого» слоя аутфита по типу изделия
def _name_kind(name: str) -> str:
    n = (name or "").lower().replace("ё", "е")
    if "юбк" in n:
        return "skirt"
    if "брюк" in n or "джинсы" in n or "шорт" in n:
        return "bottom"
    if "футболк" in n or "майк" in n or "топ " in n or n.startswith("топ"):
        return "tee"
    if "плать" in n or "сарафан" in n:
        return "dress"
    if "куртк" in n or "пальто" in n or "тренч" in n or "пухов" in n or "ветров" in n:
        return "outer"
    return "other"


KIND_DROP_ATTRS = {
    "skirt": {"sleeve_length", "collar", "hood", "quilted"},
    "bottom": {"sleeve_length", "collar", "hood", "quilted"},
    "tee": {"quilted", "hood"},  # hood=да всё ещё покажем через is_displayable if yes — но drop hood entirely for tee
}


def load_demand() -> dict[str, dict]:
    if not DEMAND.is_file():
        return {}
    data = json.loads(DEMAND.read_text(encoding="utf-8"))
    out = {}
    for row in (data.get("classification") or {}).get("intents") or []:
        aid = row.get("attr_id")
        if aid:
            out[aid] = row
    # aliases
    if "sleeve_length" not in out and "sleeve_length_product_proxy" in out:
        out["sleeve_length"] = out["sleeve_length_product_proxy"]
    return out


def demand_bucket(attr_id: str, demand: dict[str, dict]) -> dict:
    """searched_strong | searched_weak | extractable_no_facet_yet"""
    aliases = {
        "belt_drawstring": "fit_waist",
        "quilted": None,
    }
    key = aliases.get(attr_id, attr_id)
    row = demand.get(key) if key else None
    if not row:
        return {
            "bucket": "extractable_no_facet_yet",
            "note": "В top-5000 запросов Zolla явного intent мало; всё равно полезный facet с фото.",
            "volume": 0,
            "examples": [],
        }
    vol = int(row.get("search_volume_in_top") or 0)
    verdict = str(row.get("verdict_hint") or "")
    examples = [{"q": e["q"], "n": e["search_count"]} for e in (row.get("examples") or [])[:3]]
    if "strong_filter" in verdict or vol >= 1000:
        bucket = "searched_strong"
    elif "weak" in verdict or vol < 200:
        bucket = "searched_weak"
    else:
        bucket = "searched_strong"
    return {
        "bucket": bucket,
        "note": verdict,
        "volume": vol,
        "examples": examples,
    }


def old_extract_from_db(aj: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        a = json.loads(aj or "{}")
        clothing = a.get("clothing") or a
        for k in (
            "color",
            "color_shade",
            "print_pattern",
            "material",
            "length",
            "sleeve_length",
            "hood",
            "fastener",
            "collar",
        ):
            v = clothing.get(k)
            if isinstance(v, dict) and v.get("value"):
                out[k] = str(v["value"])
            elif isinstance(v, str) and v.strip():
                out[k] = v.strip()
    except Exception:
        pass
    return out


def feed_side(offer_id: str) -> tuple[dict, str, str, dict[str, str]]:
    if not ZOLLA_DB.is_file():
        return {}, "", "", {}
    con = sqlite3.connect(str(ZOLLA_DB))
    row = con.execute(
        "SELECT name, category, picture_url, attributes_json FROM results WHERE offer_id=?",
        (offer_id,),
    ).fetchone()
    con.close()
    if not row:
        return {}, "", "", {}
    name, cat, pic, aj = row
    old = old_extract_from_db(aj or "")
    feed = {"Категория": cat or "—"}
    for k, label in (
        ("color", "Цвет"),
        ("color_shade", "Оттенок"),
        ("print_pattern", "Принт (старый freeform)"),
        ("material", "Материал"),
    ):
        feed[label] = old.get(k) or "—"
    feed["Капюшон (param)"] = "нет в фиде"
    feed["Застёжка (param)"] = "нет в фиде"
    feed["Длина как facet"] = "нет в фиде"
    feed["Пояс/кулиска (param)"] = "нет в фиде"
    # Fabric adjectives often only in title (не vision-% состава)
    name_l = (name or "").lower().replace("ё", "е")
    for token, label in (
        ("шифон", "шифон (в name)"),
        ("замш", "замша (в name)"),
        ("хлопк", "хлопок (в name/extract)"),
        ("джинс", "джинс (в name)"),
    ):
        if token in name_l and "Материал (title)" not in feed:
            feed["Материал (title)"] = label
            break
    return feed, pic or "", name or "", old


def is_displayable(row: dict, *, product_name: str = "") -> bool:
    if not row.get("coerced_ok"):
        return False
    status = row.get("status") or ""
    if status not in {"keep", "mention_in_title"}:
        return False
    aid = row.get("attr_id")
    kind = _name_kind(product_name)
    if aid in KIND_DROP_ATTRS.get(kind, set()):
        return False
    # collar=капюшон дублирует hood=да — оставляем hood
    if aid == "collar":
        val = row.get("coerced_value")
        if str(val) == "капюшон":
            return False
    val = row.get("coerced_value")
    if isinstance(val, list):
        val_s = val[0] if val else ""
    else:
        val_s = val
    if (aid, str(val_s)) in SKIP_DISPLAY_VALUES:
        return False
    return True


def drop_belt_as_fastener(attrs: list[dict]) -> list[dict]:
    """Пояс/кулиска ≠ застёжка=завязки — убираем ложный fastener."""
    has_belt = any(
        a.get("attr_id") == "belt_drawstring"
        and a.get("coerced_ok")
        and str(a.get("coerced_value")) == "да"
        for a in attrs
    )
    if not has_belt:
        return attrs
    out = []
    for a in attrs:
        if a.get("attr_id") == "fastener" and str(a.get("coerced_value")) == "завязки":
            a = dict(a)
            a["status"] = "dropped_belt_not_fastener"
            a["coerced_ok"] = False
        out.append(a)
    return out


def sample_for(oid: str) -> dict | None:
    feed, pic, name, old = feed_side(oid)
    if not pic and not name:
        return None
    local = resolve_local_image(oid, pic or "")
    if not local and not pic:
        return None
    return {
        "offer_id": oid,
        "name": name,
        "picture_url": pic,
        "old_extract": old,
        "feed": feed,
        "local_image": str(local) if local else None,
    }


def build_case(n: int, oid: str, blurb: str, multi: dict, demand: dict[str, dict]) -> dict:
    attrs = drop_belt_as_fastener(list(multi.get("attributes") or []))
    shown = []
    pname = multi.get("name") or ""
    for r in attrs:
        if not is_displayable(r, product_name=pname):
            continue
        dem = demand_bucket(r["attr_id"], demand)
        shown.append(
            {
                "attr_id": r["attr_id"],
                "label": r.get("label"),
                "value": r.get("coerced_value"),
                "value_type": r.get("value_type"),
                "filter_ui": r.get("filter_ui"),
                "evidence": r.get("evidence") or "visual",
                "status": r.get("status"),
                "demand_bucket": dem["bucket"],
                "demand_volume_top5k": dem["volume"],
                "demand_examples": dem["examples"],
                "demand_note": dem["note"],
            }
        )
    # sort: searched_strong first, then title mentions, then weak/extractable
    rank = {"searched_strong": 0, "searched_weak": 1, "extractable_no_facet_yet": 2}
    shown.sort(key=lambda x: (rank.get(x["demand_bucket"], 9), x["attr_id"]))

    collisions = [
        {
            "attr_id": r["attr_id"],
            "label": r.get("label"),
            "value": r.get("coerced_value"),
            "why": "Уже было в старом extract — не gap, в фильтр как «новинку» не продаём.",
        }
        for r in attrs
        if r.get("status") == "collision_old_extract" and r.get("coerced_ok")
    ]

    searched = [x for x in shown if x["demand_bucket"] == "searched_strong"]
    extra = [x for x in shown if x["demand_bucket"] != "searched_strong"]

    return {
        "n": n,
        "offer_id": oid,
        "name": multi.get("name") or oid,
        "picture_url": multi.get("picture_url"),
        "product_url": f"https://zolla.com/catalog/?q={oid}",
        "blurb": blurb,
        "focus_attr": "multi",
        "feed": multi.get("feed") or {},
        "extracted_filters": shown,
        "searched_filters": searched,
        "extra_filters": extra,
        "collisions_not_gap": collisions,
        "keep_count": len(shown),
        "model": multi.get("model"),
        "elapsed_s": multi.get("elapsed_s"),
        "error": multi.get("error"),
    }


def main() -> None:
    demand = load_demand()
    specs = _specs(SCHEMA if SCHEMA.is_file() else None)
    # Prefer fashion filter attrs (+ extras); drop gender (nav collision)
    specs = [s for s in specs if s.attr_id not in {"gender_target"}]

    cache: dict[str, dict] = {}
    if CACHE.is_file():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8")).get("by_offer") or {}
        except Exception:
            cache = {}

    cases = []
    for i, (oid, blurb) in enumerate(WANTED, 1):
        sample = sample_for(oid)
        if not sample:
            print("MISS", oid)
            continue
        print(f"[{i}/{len(WANTED)}] multi-extract {oid} {sample['name'][:50]}…")
        multi = extract_all_filters(sample, specs)
        multi["feed"] = sample["feed"]
        multi["old_extract"] = sample["old_extract"]
        cache[oid] = {
            "attributes": multi.get("attributes"),
            "keep_count": multi.get("keep_count"),
            "model": multi.get("model"),
            "error": multi.get("error"),
            "elapsed_s": multi.get("elapsed_s"),
        }
        case = build_case(i, oid, blurb, multi, demand)
        cases.append(case)
        print(
            f"  keep_display={case['keep_count']} "
            f"searched={len(case['searched_filters'])} "
            f"extra={len(case['extra_filters'])} "
            f"collisions={len(case['collisions_not_gap'])} "
            f"err={case.get('error')}"
        )
        for f in case["extracted_filters"]:
            print(f"    + {f['label']}={f['value']} [{f['demand_bucket']}]")

    CACHE.write_text(
        json.dumps({"by_offer": cache}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    path = OUT / "demo_cases.json"
    path.write_text(
        json.dumps(
            {
                "partner": "Zolla",
                "site_id": 3826,
                "rule": (
                    "Per photo: MAX closed-set filters; skip old-extract collisions; "
                    "split searched vs extractable-no-facet; never one-attr demo cards."
                ),
                "principles": [
                    "Один кейс = все видимые filter-атрибуты с фото, не focus на один.",
                    "Если значение уже в старом extract (полоски→полоска) — не продаём как gap.",
                    "Title mention (капюшон в name) — ок как structured facet, помечаем mention_in_title.",
                    "Делим: ищут в CH (searched_strong) vs можем достать как facet без сильного intent.",
                    "Boolean «нет» / однотонный не засоряют карточку демо.",
                    "Воротник: круглый ≠ отложной (crew vs shirt collar).",
                ],
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"cases={len(cases)} → {path}")


if __name__ == "__main__":
    main()
