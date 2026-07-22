#!/usr/bin/env python3
"""
Zolla full-catalog filter extract on LOCAL Ollama vision.

- 1 vision call per unique picture_url (dedupe) → propagate to all offer_ids
- Plus free text/title + existing clothing.print_pattern coerce (no vision)
- Outputs:
  1) dashboard CSV: external_id,attribute_name,attribute_value
  2) partner analytics HTML (+ JSON coverage)

Usage:
  py -3.13 filter_pipeline/run_zolla_local_catalog.py --smoke 20
  py -3.13 filter_pipeline/run_zolla_local_catalog.py --run
  py -3.13 filter_pipeline/run_zolla_local_catalog.py --export-only
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import sqlite3
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from filter_pipeline.coerce import coerce_value
from filter_pipeline.dedupe import picture_key
from filter_pipeline.extract_multi import COLLAR_HINT, _specs, build_multi_prompt
from filter_pipeline.llm_client import parse_json_object
from filter_pipeline.models import FilterAttributeSpec
from filter_pipeline.samples import resolve_local_image

OUT = ROOT / "portfolio" / "zolla_filters" / "local_catalog"
ZOLLA_DB = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\results.db")
DESKTOP_OUT = Path(r"C:\Users\1\OneDrive\Desktop\Output\Zolla_3826")

OLLAMA_BASE = "http://127.0.0.1:11434"  # direct Ollama (avoid pool contention)
DEFAULT_MODEL = "gemma4:12b"  # multimodal; use think=False ~2s/pic
SCHEMA = ROOT / "portfolio" / "zolla_filters" / "filter_schema_clean.json"

# Skip noisy boolean-no / solid in dashboard? Partner wants filters — ship yes + enums + print.
DASHBOARD_SKIP = {
    ("digi_filter_hood", "нет"),
    ("digi_filter_pockets", "нет"),
    ("digi_filter_belt_drawstring", "нет"),
    ("digi_filter_quilted", "нет"),
    ("digi_filter_fastener", "нет"),
}


def _jpeg_b64(path: Path, max_side: int = 640, quality: int = 78) -> str:
    from PIL import Image

    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def ollama_vision(prompt: str, image_path: Path, *, model: str, system: str, max_tokens: int = 900) -> str:
    b64 = _jpeg_b64(image_path)
    payload = {
        "model": model,
        "stream": False,
        "think": False,  # gemma4 otherwise dumps into thinking, empty content
        "options": {"temperature": 0.0, "num_predict": max_tokens},
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": prompt,
                "images": [b64],
            },
        ],
    }
    req = urllib.request.Request(
        f"{OLLAMA_BASE.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    msg = data.get("message") or {}
    content = str(msg.get("content") or "").strip()
    if not content and msg.get("thinking"):
        content = str(msg.get("thinking") or "")
    return content


SYSTEM = (
    "Ты vision-экстрактор facet-фильтров fashion. "
    "С одного фото достаёшь атрибуты из схемы. Ответ — только JSON. "
    "Значения строго из allowed_values. " + COLLAR_HINT
)


def load_offers() -> list[dict[str, Any]]:
    con = sqlite3.connect(str(ZOLLA_DB))
    rows = con.execute(
        "SELECT offer_id, name, category, picture_url, attributes_json FROM results"
    ).fetchall()
    con.close()
    out = []
    for oid, name, cat, pic, aj in rows:
        old = {}
        try:
            a = json.loads(aj or "{}")
            cloth = a.get("clothing") or {}
            for k, v in cloth.items():
                if isinstance(v, dict) and v.get("value"):
                    old[k] = str(v["value"])
                elif isinstance(v, str) and v.strip():
                    old[k] = v.strip()
        except Exception:
            pass
        out.append(
            {
                "offer_id": str(oid),
                "name": name or "",
                "category": cat or "",
                "picture_url": pic or "",
                "old_extract": old,
            }
        )
    return out


def title_heuristics(name: str) -> dict[str, Any]:
    """Cheap closed-set hits from product name (no vision)."""
    n = (name or "").lower().replace("ё", "е")
    hits: dict[str, Any] = {}
    if "капюшон" in n:
        hits["hood"] = "да"
    if re.search(r"\bмини\b|\bmini\b", n):
        hits["length"] = "mini"
    elif re.search(r"\bмиди\b|\bmidi\b", n):
        hits["length"] = "midi"
    elif re.search(r"\bмакси\b|\bmaxi\b", n):
        hits["length"] = "maxi"
    if "без рукав" in n:
        hits["sleeve_length"] = "без рукавов"
    elif "коротким рукав" in n or "короткий рукав" in n:
        hits["sleeve_length"] = "короткий"
    elif "длинным рукав" in n or "длинный рукав" in n:
        hits["sleeve_length"] = "длинный"
    if "на молнии" in n or "молни" in n:
        hits["fastener"] = "молния"
    elif "на пуговиц" in n or "пуговиц" in n:
        hits["fastener"] = "пуговицы"
    elif "на кнопк" in n:
        hits["fastener"] = "кнопки"
    if "кулиск" in n or "с поясом" in n or "на поясе" in n:
        hits["belt_drawstring"] = "да"
    if "воротником-стойк" in n or "воротник-стойк" in n or "стойкой" in n:
        hits["collar"] = "стойка"
    elif "v-образ" in n or "v образ" in n:
        hits["collar"] = "V-образный"
    if "накладными карманами" in n or "с карманами" in n:
        hits["pockets"] = "да"
    if "стеган" in n or "стёган" in n:
        hits["quilted"] = "да"
    return hits


def coerce_old_print(specs_by: dict[str, FilterAttributeSpec], old: dict[str, str]) -> Any | None:
    raw = old.get("print_pattern")
    if not raw:
        return None
    spec = specs_by.get("print_pattern")
    if not spec:
        return None
    c = coerce_value(spec, raw)
    return c.value if c.ok else None


def group_unique(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for o in offers:
        key = picture_key(o.get("picture_url") or "", o["offer_id"])
        if key not in groups:
            order.append(key)
            local = resolve_local_image(o["offer_id"], o.get("picture_url") or "")
            groups[key] = {
                "picture_key": key,
                "picture_url": o.get("picture_url") or "",
                "local_image": str(local) if local else None,
                "representative": o,
                "member_offer_ids": [o["offer_id"]],
                "names": [o.get("name") or ""],
                "categories": [o.get("category") or ""],
            }
        else:
            g = groups[key]
            if o["offer_id"] not in g["member_offer_ids"]:
                g["member_offer_ids"].append(o["offer_id"])
                g["names"].append(o.get("name") or "")
                g["categories"].append(o.get("category") or "")
    return [groups[k] for k in order]


def merge_attr(dst: dict[str, dict], attr_id: str, value: Any, source: str, conf: int = 70) -> None:
    if value is None or value == "":
        return
    prev = dst.get(attr_id)
    # prefer vision over title over old
    rank = {"vision": 3, "title": 2, "old_extract": 1}
    if prev and rank.get(prev.get("source"), 0) > rank.get(source, 0):
        return
    dst[attr_id] = {"value": value, "source": source, "confidence": conf}


_NON_APPAREL_RE = re.compile(
    r"сумк|рюкзак|перчат|шапк|шарф|рем(е|ё)н|носк|колгот|трус|белье|бельё|"
    r"купальн|плавк|бикини|очк|украшен|серьг|браслет|кошель",
    re.I,
)
# clothing structure attrs that make no sense on bags/gloves/etc.
_APPAREL_ONLY = {
    "hood",
    "length",
    "sleeve_length",
    "collar",
    "belt_drawstring",
    "quilted",
    "pockets",
    "fastener",
}


def is_non_apparel(name: str, category: str = "") -> bool:
    blob = f"{name or ''} {category or ''}"
    return bool(_NON_APPAREL_RE.search(blob))


def compact_prompt(specs: list[FilterAttributeSpec], product_name: str) -> str:
    """Shorter prompt → faster gemma4 (~2–5s vs 14s with full schema dump)."""
    lines = []
    for s in specs:
        lines.append(f"{s.attr_id}: {', '.join(s.allowed_values)}")
    schema = "\n".join(lines)
    return (
        "Одежда на фото (только главное изделие из названия). "
        "Верни JSON: {\"attributes\":[{\"attr_id\":\"...\",\"value\":\"...\"}]}. "
        "value ТОЛЬКО из списка. круглый≠отложной. пояс≠застёжка.\n"
        "Верни ВСЕ атрибуты из схемы (каждый attr_id ровно один раз).\n"
        f"Схема:\n{schema}\n"
        f"Товар: {product_name or '—'}\n"
        "Только JSON."
    )


def _normalize_attrs(parsed: dict[str, Any], specs: list[FilterAttributeSpec]) -> list[dict[str, Any]]:
    if not parsed.get("attributes") and any(k in parsed for k in (s.attr_id for s in specs)):
        parsed = {
            "attributes": [
                {"attr_id": k, "value": v}
                for k, v in parsed.items()
                if k in {s.attr_id for s in specs}
            ]
        }
    attrs = parsed.get("attributes") or []
    return attrs if isinstance(attrs, list) else []


def extract_one(group: dict, specs: list[FilterAttributeSpec], model: str) -> dict[str, Any]:
    local = group.get("local_image")
    name = group["representative"].get("name") or ""
    t0 = time.time()
    err = None
    raw = ""
    attrs: list[dict[str, Any]] = []
    if local and Path(local).is_file():
        prompt = compact_prompt(specs, name)
        try:
            for attempt in range(2):
                raw = ollama_vision(
                    prompt,
                    Path(local),
                    model=model,
                    system=SYSTEM,
                    max_tokens=700 if attempt else 550,
                )
                attrs = _normalize_attrs(parse_json_object(raw), specs)
                if len(attrs) >= 6:
                    break
        except Exception as e:
            err = str(e)
    else:
        err = "no_local_image"
    return {
        "picture_key": group["picture_key"],
        "elapsed_s": round(time.time() - t0, 2),
        "error": err,
        "raw_text": (raw or "")[:4000],
        "attributes": attrs,
        "model": model,
    }


def build_offer_filters(
    offers: list[dict[str, Any]],
    vision_by_pic: dict[str, dict],
    specs: list[FilterAttributeSpec],
) -> dict[str, dict[str, dict]]:
    """offer_id -> {attr_id: {value, source, confidence}}"""
    by_id = {s.attr_id: s for s in specs}
    # map picture -> vision coerced
    pic_vals: dict[str, dict[str, Any]] = {}
    for pk, row in vision_by_pic.items():
        slot: dict[str, Any] = {}
        for item in row.get("attributes") or []:
            if not isinstance(item, dict):
                continue
            aid = str(item.get("attr_id") or "")
            if aid not in by_id:
                continue
            c = coerce_value(by_id[aid], item.get("value"))
            if c.ok:
                slot[aid] = c.value
        pic_vals[pk] = slot

    out: dict[str, dict[str, dict]] = {}
    for o in offers:
        oid = o["offer_id"]
        pk = picture_key(o.get("picture_url") or "", oid)
        slot: dict[str, dict] = {}
        name = o.get("name") or ""
        skip_struct = is_non_apparel(name, o.get("category") or "")
        # 1) old print
        pv = coerce_old_print(by_id, o.get("old_extract") or {})
        if pv is not None:
            merge_attr(slot, "print_pattern", pv, "old_extract", 85)
        # 2) title (explicit sleeve/hood in name beats bad vision later via higher conf path)
        title_hits = title_heuristics(name)
        for aid, val in title_hits.items():
            if skip_struct and aid in _APPAREL_ONLY:
                continue
            if aid in by_id:
                c = coerce_value(by_id[aid], val)
                if c.ok:
                    merge_attr(slot, aid, c.value, "title", 75)
        # 3) vision (wins) — but not apparel structure on accessories
        for aid, val in (pic_vals.get(pk) or {}).items():
            if skip_struct and aid in _APPAREL_ONLY:
                continue
            # title said long/short sleeve → don't let vision flip to sleeveless
            if (
                aid == "sleeve_length"
                and title_hits.get("sleeve_length") in {"длинный", "короткий", "3/4"}
                and val == "без рукавов"
            ):
                continue
            merge_attr(slot, aid, val, "vision", 90)
        out[oid] = slot
    return out


def export_dashboard_csv(offer_filters: dict[str, dict[str, dict]], specs: list[FilterAttributeSpec], path: Path) -> int:
    by_id = {s.attr_id: s for s in specs}
    n = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["external_id", "attribute_name", "attribute_value"])
        for oid, attrs in offer_filters.items():
            for aid, meta in attrs.items():
                spec = by_id.get(aid)
                if not spec:
                    continue
                dash = spec.dashboard_attr or f"digi_filter_{aid}"
                val = meta["value"]
                if isinstance(val, list):
                    # multi_enum → one row per value (dashboard convention)
                    for one in val:
                        if (dash, str(one)) in DASHBOARD_SKIP:
                            continue
                        w.writerow([oid, dash, one])
                        n += 1
                else:
                    if (dash, str(val)) in DASHBOARD_SKIP:
                        continue
                    w.writerow([oid, dash, val])
                    n += 1
    return n


def export_analytics(
    offers: list[dict[str, Any]],
    offer_filters: dict[str, dict[str, dict]],
    specs: list[FilterAttributeSpec],
    unique_n: int,
    vision_done: int,
    model: str,
) -> dict[str, Any]:
    by_id = {s.attr_id: s for s in specs}
    n_offers = len(offers)
    # L1 category
    def l1(cat: str) -> str:
        parts = [p.strip() for p in (cat or "").split("/") if p.strip()]
        return parts[0] if parts else "(без категории)"

    cov_attr = Counter()
    cov_src = Counter()
    by_cat_attr: dict[str, Counter] = defaultdict(Counter)
    by_cat_offers: Counter = Counter()
    value_dist: dict[str, Counter] = defaultdict(Counter)

    for o in offers:
        cat = l1(o.get("category") or "")
        by_cat_offers[cat] += 1
        attrs = offer_filters.get(o["offer_id"]) or {}
        for aid, meta in attrs.items():
            cov_attr[aid] += 1
            cov_src[meta.get("source") or "?"] += 1
            by_cat_attr[cat][aid] += 1
            val = meta["value"]
            if isinstance(val, list):
                for one in val:
                    value_dist[aid][str(one)] += 1
            else:
                value_dist[aid][str(val)] += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "partner": "Zolla",
        "site_id": 3826,
        "model": model,
        "offers_total": n_offers,
        "unique_pictures": unique_n,
        "vision_unique_done": vision_done,
        "dedupe_note": f"Vision 1× на unique picture; propagate на {n_offers} offer_id (экономия ~{max(0,n_offers-unique_n)} вызовов)",
        "coverage_by_attr": {
            aid: {
                "label": by_id[aid].label_ru if aid in by_id else aid,
                "offers_with_value": cov_attr[aid],
                "coverage_pct": round(100 * cov_attr[aid] / n_offers, 2) if n_offers else 0,
                "top_values": value_dist[aid].most_common(12),
            }
            for aid in [s.attr_id for s in specs]
            if cov_attr[aid]
        },
        "source_mix": dict(cov_src),
        "coverage_by_category_l1": {
            cat: {
                "offers": by_cat_offers[cat],
                "attrs": {
                    aid: {
                        "n": by_cat_attr[cat][aid],
                        "pct": round(100 * by_cat_attr[cat][aid] / by_cat_offers[cat], 1),
                    }
                    for aid in by_cat_attr[cat]
                },
            }
            for cat in sorted(by_cat_offers, key=lambda c: -by_cat_offers[c])[:40]
        },
    }
    return report


def write_analytics_html(report: dict, path: Path) -> None:
    def num(n: int | float) -> str:
        return f"{int(n):,}".replace(",", " ")

    rows = []
    for _aid, info in (report.get("coverage_by_attr") or {}).items():
        tops = ", ".join(f"{v} ({num(n)})" for v, n in (info.get("top_values") or [])[:6])
        rows.append(
            f"<tr><td>{info['label']}</td><td>{num(info['offers_with_value'])}</td>"
            f"<td>{info['coverage_pct']}%</td><td style='font-size:12px'>{tops}</td></tr>"
        )
    cat_rows = []
    for cat, info in (report.get("coverage_by_category_l1") or {}).items():
        attrs = ", ".join(
            f"{a}: {d['pct']}%"
            for a, d in sorted(info["attrs"].items(), key=lambda x: -x[1]["n"])[:8]
        )
        cat_rows.append(
            f"<tr><td>{cat}</td><td>{num(info['offers'])}</td>"
            f"<td style='font-size:12px'>{attrs}</td></tr>"
        )
    pct_vision = 0.0
    u = report.get("unique_pictures") or 0
    d = report.get("vision_unique_done") or 0
    if u:
        pct_vision = round(100 * d / u, 1)
    html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/>
<title>Zolla — покрытие фильтров</title>
<style>
body{{font:16px/1.5 Georgia,"Times New Roman",serif;margin:32px;background:#f7f5f2;color:#1a1a1a}}
h1{{font-size:28px;font-weight:600}} h2{{font-size:18px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:13px;font-family:system-ui,sans-serif}}
th,td{{border:1px solid #ddd6cc;padding:8px;text-align:left;vertical-align:top}} th{{background:#efeae3}}
.meta{{color:#5c5c5c;font-size:13px;max-width:720px}}
.stat{{display:inline-block;background:#fff;border:1px solid #ddd6cc;padding:12px 16px;margin:6px 6px 6px 0}}
.stat b{{font-size:22px;font-family:system-ui,sans-serif}}
</style></head><body>
<h1>Zolla: покрытие фильтров</h1>
<p class="meta">Значения собраны с фото карточек, из названий и уже заполненных полей.
Дубли одного и того же фото не обрабатывались повторно — значение разносится на все карточки с этой картинкой.</p>
<div>
  <div class="stat"><b>{num(report['offers_total'])}</b><br/>карточек</div>
  <div class="stat"><b>{num(report['unique_pictures'])}</b><br/>уникальных фото</div>
  <div class="stat"><b>{num(report['vision_unique_done'])}</b><br/>фото с разметкой с фото ({pct_vision}%)</div>
</div>
<h2>1. Покрытие по фильтрам</h2>
<table><thead><tr><th>Фильтр</th><th>Карточек</th><th>Coverage</th><th>Топ значений</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>2. Покрытие по категориям</h2>
<table><thead><tr><th>Категория</th><th>Карточек</th><th>Фильтры (coverage %)</th></tr></thead>
<tbody>{''.join(cat_rows)}</tbody></table>
<p class="meta">Файл для загрузки в Dashboard: zolla_filters_dashboard_upload.csv
(колонки external_id, attribute_name, attribute_value).</p>
</body></html>
"""
    path.write_text(html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--smoke", type=int, default=0, help="vision only N unique pics then export")
    ap.add_argument("--run", action="store_true", help="full unique-pic vision (checkpointed)")
    ap.add_argument("--export-only", action="store_true")
    ap.add_argument("--limit-unique", type=int, default=0)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    DESKTOP_OUT.mkdir(parents=True, exist_ok=True)
    specs = [s for s in _specs(SCHEMA if SCHEMA.is_file() else None) if s.attr_id != "gender_target"]
    ckpt_path = OUT / "vision_checkpoint.jsonl"
    state_path = OUT / "run_state.json"

    def log(msg: str) -> None:
        print(msg, flush=True)

    log("loading offers…")
    offers = load_offers()
    groups = group_unique(offers)
    log(f"offers={len(offers)} unique_pics={len(groups)} saved_calls≈{len(offers)-len(groups)}")

    # load checkpoint
    vision_by_pic: dict[str, dict] = {}
    if ckpt_path.is_file():
        with ckpt_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pk = row.get("picture_key")
                if pk:
                    vision_by_pic[pk] = row
        log(f"checkpoint loaded: {len(vision_by_pic)} unique")

    todo = [g for g in groups if g["picture_key"] not in vision_by_pic and g.get("local_image")]
    if args.limit_unique:
        todo = todo[: args.limit_unique]
    if args.smoke:
        todo = todo[: args.smoke]

    if args.run or args.smoke:
        log(f"vision queue={len(todo)} model={args.model} ollama={OLLAMA_BASE}")
        t_all = time.time()
        for i, g in enumerate(todo, 1):
            row = extract_one(g, specs, args.model)
            vision_by_pic[g["picture_key"]] = row
            with ckpt_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            ok = not row.get("error") and bool(row.get("attributes"))
            log(
                f"[{i}/{len(todo)}] {g['representative']['offer_id']} "
                f"{'OK' if ok else 'FAIL'} {row.get('elapsed_s')}s "
                f"attrs={len(row.get('attributes') or [])} err={row.get('error')}"
            )
            if i % 25 == 0:
                state_path.write_text(
                    json.dumps(
                        {
                            "done": len(vision_by_pic),
                            "queue_left": len(todo) - i,
                            "elapsed_min": round((time.time() - t_all) / 60, 1),
                            "model": args.model,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            if i % 200 == 0:
                # mid-run export so partner files stay fresh
                of_mid = build_offer_filters(offers, vision_by_pic, specs)
                export_dashboard_csv(of_mid, specs, OUT / "zolla_filters_dashboard_upload.csv")
                (DESKTOP_OUT / "zolla_filters_dashboard_upload.csv").write_bytes(
                    (OUT / "zolla_filters_dashboard_upload.csv").read_bytes()
                )
                rep_mid = export_analytics(
                    offers, of_mid, specs, len(groups), len(vision_by_pic), args.model
                )
                (OUT / "filter_coverage_analytics.json").write_text(
                    json.dumps(rep_mid, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                write_analytics_html(rep_mid, OUT / "zolla_filters_coverage.html")
                (DESKTOP_OUT / "zolla_filters_coverage.html").write_text(
                    (OUT / "zolla_filters_coverage.html").read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                log(f"  mid-export @ {i} unique")
        log(f"vision pass done in {round((time.time()-t_all)/60,1)} min")

    log("merging filters…")
    offer_filters = build_offer_filters(offers, vision_by_pic, specs)
    (OUT / "offer_filters.json").write_text(
        json.dumps(offer_filters, ensure_ascii=False), encoding="utf-8"
    )

    csv_path = OUT / "zolla_filters_dashboard_upload.csv"
    n_rows = export_dashboard_csv(offer_filters, specs, csv_path)
    # also desktop
    desk_csv = DESKTOP_OUT / "zolla_filters_dashboard_upload.csv"
    desk_csv.write_bytes(csv_path.read_bytes())

    report = export_analytics(
        offers, offer_filters, specs, len(groups), len(vision_by_pic), args.model
    )
    (OUT / "filter_coverage_analytics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_path = OUT / "zolla_filters_coverage.html"
    write_analytics_html(report, html_path)
    (DESKTOP_OUT / "zolla_filters_coverage.html").write_text(
        html_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (DESKTOP_OUT / "filter_coverage_analytics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log(f"dashboard rows={n_rows} → {csv_path}")
    log(f"desktop → {DESKTOP_OUT}")
    for aid, info in (report.get("coverage_by_attr") or {}).items():
        log(f"  {info['label']}: {info['coverage_pct']}% ({info['offers_with_value']})")


if __name__ == "__main__":
    main()
