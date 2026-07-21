# -*- coding: utf-8 -*-
"""
Site 221 vision batch: focus categories × closed-set positive attrs via OpenRouter.
Negation → rejected log (not upload). Resume via checkpoint.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "221_azbuka"
OUT.mkdir(parents=True, exist_ok=True)
AE = Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\data\projects\221")
FEED_DB = AE / "feed.db"
GOLD_CSV = Path(r"C:\Users\1\OneDrive\Desktop\221_azbuka_vkusa_gold_final_20260721_0958.csv")
ENV = Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\.env")

MODEL = os.environ.get("OR_VISION_MODEL", "google/gemini-2.5-flash-lite")
WORKERS = int(os.environ.get("OR_VISION_WORKERS", "10"))
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# per-type caps (None = all)
LIMITS: dict[str, int | None] = {
    "snacks_and_chips": None,
    "condiments_oils_spices_sauces": None,
    "grains_and_legumes": None,
    "pet_food_wet_dry": None,
    "milk_products": 600,
    "bakery_dairy": 500,
    "food_beverages_non_alcohol": 500,
    "bakery_and_sweets": 500,
}

CLOSED_SET = [
    "Форма выпуска",
    "Нарезка",
    "Вкус, Добавки",
    "Технология приготовления",
    "Способ обработки",
    "Тип упаковки",
    "Тип соуса",
    "Текстура корма",
]

NAME_MAP = {
    "форма выпуска": "Форма выпуска",
    "нарезка": "Нарезка",
    "вкус": "Вкус, Добавки",
    "вкус/наполнитель": "Вкус, Добавки",
    "вкус, добавки": "Вкус, Добавки",
    "технология приготовления": "Технология приготовления",
    "способ обработки": "Способ обработки",
    "тип упаковки": "Тип упаковки",
    "тип соуса": "Тип соуса",
    "текстура корма": "Текстура корма",
}

NEG_CONTAINS = [
    "не содержит",
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
]
NEG_NAME_STARTS = ("без ", "не ")
NEG_ATTR = {
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

SKIP_PARAM = {
    "currencyId",
    "dimension22",
    "id",
    "name",
    "nonprice_promo",
    "only_for_eighteen_plus",
    "picture",
    "price",
    "price_promo",
    "promo_id",
    "promo_name",
    "sales_notes",
    "store",
    "typePrefix",
    "usp",
    "url",
    "categoryId",
    "market_category",
    "margin",
    "Белки",
    "Жиры",
    "Углеводы",
    "Пищевая ценность",
    "Энергетическая ценность",
    "Сайт производителя",
    "Нормативные документы",
}

_lock = threading.Lock()
_key_cache: str | None = None


def api_key() -> str:
    global _key_cache
    if _key_cache:
        return _key_cache
    k = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not k and ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not k:
        raise SystemExit("OPENROUTER_API_KEY missing")
    _key_cache = k
    return k


def _norm(s: str) -> str:
    return " ".join(str(s or "").lower().replace("ё", "е").split())


def load_gold_text_blobs() -> dict[str, str]:
    """offer_id -> lower blob of gold attr names+values for collision."""
    out: dict[str, str] = {}
    if not GOLD_CSV.exists():
        return out
    with GOLD_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            oid = (row.get("offer_id") or "").strip()
            raw = (row.get("attributes") or "").strip()
            if oid and raw:
                out[oid] = _norm(raw)
    return out


def load_offers() -> list[dict]:
    con = sqlite3.connect(str(FEED_DB))
    con.row_factory = sqlite3.Row
    by_type: dict[str, list] = {k: [] for k in LIMITS}
    for row in con.execute(
        "SELECT id, name, params_json, product_type, feed_category_path FROM offers"
    ):
        pt = row["product_type"] or ""
        if pt not in LIMITS:
            continue
        try:
            params = json.loads(row["params_json"] or "{}")
        except json.JSONDecodeError:
            params = {}
        pic = (params.get("picture") or "").strip()
        if not pic:
            continue
        clean = {k: v for k, v in params.items() if k not in SKIP_PARAM and v not in (None, "", "0")}
        by_type[pt].append(
            {
                "id": str(row["id"]),
                "name": row["name"] or "",
                "product_type": pt,
                "path": row["feed_category_path"] or "",
                "picture": pic,
                "params": clean,
            }
        )
    selected = []
    for pt, lim in LIMITS.items():
        lst = by_type[pt]
        # prefer diversified order: as in DB is fine; optional shuffle by id
        take = lst if lim is None else lst[:lim]
        selected.extend(take)
        print(f"  {pt}: {len(take)}/{len(lst)}")
    return selected


def is_negation(name: str, value: str) -> bool:
    n, v = _norm(name), _norm(value)
    blob = f"{n} {v}"
    if n in NEG_ATTR or any(n.startswith(p) for p in NEG_NAME_STARTS):
        return True
    if any(p in blob for p in NEG_CONTAINS):
        return True
    if re.search(r"\b(no|non|without|free)\b", blob) and any(
        x in blob for x in ("preserv", "gmo", "msg", "artificial", "gluten", "lactose", "sugar", "color", "dye")
    ):
        return True
    return False


def map_name(raw: str) -> str | None:
    n = _norm(raw)
    if n in NAME_MAP:
        return NAME_MAP[n]
    for k, canon in NAME_MAP.items():
        if k in n or n in k:
            return canon
    # exact closed
    for c in CLOSED_SET:
        if _norm(c) == n:
            return c
    return None


def stem_in(token: str, hay: str) -> bool:
    t = token.lower()
    if len(t) < 4:
        return t in hay
    return t[: max(4, len(t) - 2)] in hay


def build_prompt(p: dict) -> str:
    params = p.get("params") or {}
    plines = [f"- {k}: {v}" for k, v in list(params.items())[:20]]
    return f"""Проанализируй фото товара продуктового ритейлера. Извлеки ТОЛЬКО атрибуты из списка ниже,
которые РЕАЛЬНО видны (OCR/иконка/форма), и которых НЕТ в названии и params.

РАЗРЕШЁННЫЕ ИМЕНА (строго одно из):
{json.dumps(CLOSED_SET, ensure_ascii=False)}

ЗАПРЕЩЕНО включать в attributes (даже если видно):
- без X / не содержит / MSG-free / Non-GMO / No Preservatives / sugar-free / БЗМЖ
- бренд, вес, страна, КБЖУ, срок годности, ТУ
- вкусовые «ноты» и маркетинг без явной надписи-лейбла
- тип упаковки «бутылка/стекло» для вина

НАЗВАНИЕ: {p['name']}
КАТЕГОРИЯ: {p['path']}
PARAMS:
{chr(10).join(plines) if plines else '(нет)'}

JSON only:
{{"image_kind":"packshot|product_only|unclear","attributes":[{{"name":"...","value":"...","evidence":"ocr|visual"}}],"rejected_seen":[{{"raw":"...","why":"negation|already_in_name|not_in_closed_set"}}]}}
Если на фото только продукт без этикетки — attributes:[]."""


def call_vision(p: dict) -> dict:
    prompt = build_prompt(p)
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/attr-enrichment-product",
        "X-Title": "221 azbuka vision batch",
    }
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 700,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": p["picture"]}},
                ],
            }
        ],
    }
    t0 = time.time()
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        data = r.json()
        if r.status_code != 200:
            return {"id": p["id"], "error": f"HTTP {r.status_code}", "raw": data, "elapsed": time.time() - t0}
        text = data["choices"][0]["message"]["content"]
    except Exception as e:
        return {"id": p["id"], "error": str(e), "elapsed": time.time() - t0}
    parsed = {}
    try:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        blob = (m.group(1) if m else text).strip()
        m2 = re.search(r"\{[\s\S]*\}", blob)
        parsed = json.loads(m2.group(0) if m2 else blob)
    except Exception:
        parsed = {"parse_error": True, "raw_text": (text or "")[:1500]}
    return {
        "id": p["id"],
        "name": p["name"],
        "product_type": p["product_type"],
        "path": p["path"],
        "picture": p["picture"],
        "vision": parsed,
        "usage": data.get("usage") if r.status_code == 200 else None,
        "elapsed": round(time.time() - t0, 2),
        "model": MODEL,
    }


def decide_attrs(result: dict, gold_blob: str) -> tuple[list[dict], list[dict]]:
    keep, rejected = [], []
    vision = result.get("vision") or {}
    attrs = vision.get("attributes") or vision.get("new_attributes") or []
    pname = _norm(result.get("name") or "")
    for a in attrs:
        raw_name = str(a.get("name") or "").strip()
        val = a.get("value")
        if isinstance(val, bool):
            val = "true" if val else "false"
        else:
            val = str(val or "").strip()
        if not raw_name or not val:
            continue
        if is_negation(raw_name, val):
            rejected.append(
                {
                    "offer_id": result["id"],
                    "attribute_name": raw_name,
                    "attribute_value": val,
                    "reject_reason": "negation_value",
                    "reject_label": "Негация — ломает поиск",
                }
            )
            continue
        canon = map_name(raw_name)
        if not canon:
            rejected.append(
                {
                    "offer_id": result["id"],
                    "attribute_name": raw_name,
                    "attribute_value": val,
                    "reject_reason": "not_in_closed_set",
                    "reject_label": "Вне closed-set",
                }
            )
            continue
        vn = _norm(val)
        toks = [t for t in re.findall(r"[a-zа-я]{4,}", vn) if t]
        if vn and (vn in pname or (toks and all(stem_in(t, pname) for t in toks))):
            rejected.append(
                {
                    "offer_id": result["id"],
                    "attribute_name": canon,
                    "attribute_value": val,
                    "reject_reason": "offer_name_token_overlap",
                    "reject_label": "Уже в названии",
                }
            )
            continue
        if gold_blob and vn and len(vn) >= 4 and vn in gold_blob:
            rejected.append(
                {
                    "offer_id": result["id"],
                    "attribute_name": canon,
                    "attribute_value": val,
                    "reject_reason": "already_in_gold_text",
                    "reject_label": "Уже в text gold",
                }
            )
            continue
        if canon == "Тип упаковки" and vn in {"бутылка", "пластиковый контейнер"}:
            rejected.append(
                {
                    "offer_id": result["id"],
                    "attribute_name": canon,
                    "attribute_value": val,
                    "reject_reason": "low_search_packaging",
                    "reject_label": "Слабо для поиска",
                }
            )
            continue
        keep.append(
            {
                "offer_id": result["id"],
                "attribute_name": canon,
                "attribute_value": val,
                "product_type": result.get("product_type"),
                "offer_name": result.get("name"),
                "path": result.get("path"),
                "evidence": a.get("evidence"),
                "picture": result.get("picture"),
            }
        )
    # model-reported rejected_seen
    for r in vision.get("rejected_seen") or []:
        rejected.append(
            {
                "offer_id": result["id"],
                "attribute_name": str(r.get("raw") or "")[:80],
                "attribute_value": "",
                "reject_reason": str(r.get("why") or "model_rejected_seen"),
                "reject_label": "Модель увидела, не взяла",
            }
        )
    return keep, rejected


def main():
    ckpt_path = OUT / "vision_batch_checkpoint.jsonl"
    done_ids: set[str] = set()
    if ckpt_path.exists():
        for line in ckpt_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                done_ids.add(json.loads(line)["id"])
            except Exception:
                pass
        print(f"resume: {len(done_ids)} already done")

    print("Loading offers…")
    offers = load_offers()
    print(f"selected={len(offers)}")
    gold = load_gold_text_blobs()
    todo = [o for o in offers if o["id"] not in done_ids]
    print(f"todo={len(todo)} model={MODEL} workers={WORKERS}")

    keep_all: list[dict] = []
    rej_all: list[dict] = []
    # reload previous keeps if resuming
    prev_keep = OUT / "vision_batch_keep.json"
    prev_rej = OUT / "vision_batch_rejected.json"
    if prev_keep.exists():
        keep_all = json.loads(prev_keep.read_text(encoding="utf-8"))
    if prev_rej.exists():
        rej_all = json.loads(prev_rej.read_text(encoding="utf-8"))

    t_start = time.time()
    n_ok = n_err = 0

    def _one(p: dict) -> dict:
        return call_vision(p)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex, ckpt_path.open("a", encoding="utf-8") as ckpt:
        futs = {ex.submit(_one, p): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            with _lock:
                ckpt.write(json.dumps(res, ensure_ascii=False) + "\n")
                ckpt.flush()
                if res.get("error"):
                    n_err += 1
                else:
                    n_ok += 1
                    k, r = decide_attrs(res, gold.get(res["id"], ""))
                    keep_all.extend(k)
                    rej_all.extend(r)
                if i % 25 == 0 or i == len(todo):
                    elapsed = time.time() - t_start
                    rate = i / elapsed if elapsed else 0
                    eta = (len(todo) - i) / rate if rate else 0
                    print(
                        f"[{i}/{len(todo)}] ok={n_ok} err={n_err} keep={len(keep_all)} "
                        f"rej={len(rej_all)} {rate:.2f}/s eta={eta/60:.1f}m"
                    )
                    prev_keep.write_text(json.dumps(keep_all, ensure_ascii=False, indent=2), encoding="utf-8")
                    prev_rej.write_text(json.dumps(rej_all, ensure_ascii=False, indent=2), encoding="utf-8")

    # dedupe keep
    seen = set()
    keep_dedup = []
    for row in keep_all:
        key = (row["offer_id"], row["attribute_name"], _norm(row["attribute_value"]))
        if key in seen:
            continue
        seen.add(key)
        keep_dedup.append(row)

    # final CSV for dashboard
    dash_csv = OUT / "221_vision_dashboard_upload.csv"
    with dash_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["external_id", "attribute_name", "attribute_value"])
        w.writeheader()
        for row in keep_dedup:
            w.writerow(
                {
                    "external_id": row["offer_id"],
                    "attribute_name": row["attribute_name"],
                    "attribute_value": row["attribute_value"],
                }
            )

    rej_csv = OUT / "221_vision_rejected.csv"
    with rej_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["offer_id", "attribute_name", "attribute_value", "reject_reason", "reject_label"],
        )
        w.writeheader()
        for row in rej_all:
            w.writerow({k: row.get(k, "") for k in w.fieldnames})

    # desktop copy
    desk = Path(r"C:\Users\1\OneDrive\Desktop")
    desk_csv = desk / "221_azbuka_vision_dashboard_upload.csv"
    desk_csv.write_bytes(dash_csv.read_bytes())
    (desk / "221_azbuka_vision_rejected.csv").write_bytes(rej_csv.read_bytes())

    summary = {
        "site_id": 221,
        "model": MODEL,
        "offers_selected": len(offers),
        "offers_done_ok": n_ok,
        "offers_errors": n_err,
        "keep_rows": len(keep_dedup),
        "rejected_rows": len(rej_all),
        "keep_by_attr": {},
        "dashboard_csv": str(dash_csv),
        "desktop_csv": str(desk_csv),
        "elapsed_min": round((time.time() - t_start) / 60, 2),
    }
    for row in keep_dedup:
        an = row["attribute_name"]
        summary["keep_by_attr"][an] = summary["keep_by_attr"].get(an, 0) + 1

    (OUT / "vision_batch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    prev_keep.write_text(json.dumps(keep_dedup, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
