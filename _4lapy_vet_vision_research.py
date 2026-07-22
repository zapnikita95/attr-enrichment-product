# -*- coding: utf-8 -*-
"""
4lapy (8267) — ветаптека / препараты: vision deep-dive + partner HTML.
Фокус SKU: 1008050, 1029780, 1043477 + расширенная выборка.
Не опирается слепо на старые gap-отчёты — свежий разбор картинок.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import iterparse

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "4lapy_vet"
OUT.mkdir(parents=True, exist_ok=True)
DESKTOP_OUT = Path(r"C:\Users\1\OneDrive\Desktop\Output\4lapy_8267_vet_pharmacy")
FEED = Path(r"C:\Users\1\Downloads\yml-feed.8267.global.xml")
if not FEED.exists():
    FEED = ROOT / "portfolio" / "yml-feed.xml"

FOCUS_IDS = ["1008050", "1029780", "1043477"]
SITE_ID = 8267
MODEL = os.environ.get("OR_VISION_MODEL", "google/gemini-2.5-flash")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_VISION = int(os.environ.get("OR_VISION_N", "24"))

CH_URL = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
CH_AUTH = ("digi-admin", "Fl2bSowt")

# Feed fields already structured — do not sell as "new from image" if filled
FEED_STRUCTURED = {
    "Для кого",
    "Форма выпуска",
    "Фармакологическая группа",
    "Возраст питомца",
    "Размер питомца",
    "Страна-производитель",
    "Артикул",
    "Объем",
    "Вес / фасовка, кг",
    "Бренд",
    "Вкус корма",
    "Тип корма",
}

VET_CAT_NEEDLES = (
    "аптек",
    "препарат",
    "ветеринар",
    "паразит",
    "антигельминт",
    "блох",
    "клещ",
    "капли",
    "таблетк",
    "суспенз",
    "шампунь",
    "лечение",
    "вакцин",
    "витамин",
    "мазь",
    "спрей",
    "ошейник",
    "инсекто",
)

PHARM_GROUP_BUCKETS = {
    "anthelmintic": ("антигельминт", "гельминт", "глист"),
    "ecto_parasite": ("блох", "клещ", "паразит", "инсекто", "акариц"),
    "dermatology": ("кож", "дермат", "мазь", "шампунь лечеб"),
    "vitamins": ("витамин", "добавк", "нутрицевт"),
    "antibiotics": ("антибиот", "противомикроб"),
    "other_vet": (),
}


def local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def load_api_key() -> str:
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    for env in (
        Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\.env"),
        Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\.env"),
    ):
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY not found")


def ch_query(sql: str, timeout: int = 300) -> dict:
    r = requests.post(
        CH_URL,
        auth=CH_AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if r.status_code != 200:
        raise RuntimeError(f"CH {r.status_code}: {r.text[:800]}")
    return r.json()


def load_feed() -> tuple[dict, list[dict], dict]:
    cats: dict[str, dict] = {}
    offers: list[dict] = []
    param_fill: Counter = Counter()
    offers_total = 0

    for _ev, el in iterparse(str(FEED), events=("end",)):
        tag = local(el.tag)
        if tag == "category":
            cid = el.get("id") or ""
            cats[cid] = {
                "id": cid,
                "parentId": el.get("parentId") or "",
                "name": (el.text or "").strip(),
            }
            el.clear()
        elif tag == "offer":
            offers_total += 1
            oid = el.get("id") or ""
            name = url = price = cat = vendor = ""
            params: dict[str, str] = {}
            pics: list[str] = []
            for ch in el:
                ct = local(ch.tag)
                if ct == "name":
                    name = (ch.text or "").strip()
                elif ct == "url":
                    url = (ch.text or "").strip()
                elif ct == "price":
                    price = (ch.text or "").strip()
                elif ct == "categoryId":
                    cat = (ch.text or "").strip()
                elif ct == "vendor":
                    vendor = (ch.text or "").strip()
                elif ct == "picture" and ch.text:
                    pics.append(ch.text.strip())
                elif ct == "param":
                    pn = ch.get("name") or ""
                    params[pn] = (ch.text or "").strip()
                    if params[pn]:
                        param_fill[pn] += 1
            cname = cats.get(cat, {}).get("name", "")
            # walk parents for path
            path = []
            cur = cat
            seen = set()
            while cur and cur not in seen and cur in cats:
                seen.add(cur)
                path.append(cats[cur]["name"])
                cur = cats[cur].get("parentId") or ""
            path_s = " / ".join(reversed(path))
            blob = f"{name} {vendor} {cname} {path_s} {' '.join(params.values())}".lower()
            is_vet = any(n in blob for n in VET_CAT_NEEDLES) or any(
                n in (params.get("Фармакологическая группа") or "").lower()
                for n in ("антигельминт", "паразит", "блох", "клещ", "витамин", "антибиот")
            )
            if is_vet or oid in FOCUS_IDS:
                offers.append(
                    {
                        "id": oid,
                        "name": name,
                        "vendor": vendor,
                        "brand": vendor or (name.split()[0] if name else ""),
                        "url": url,
                        "price": price,
                        "categoryId": cat,
                        "category": cname,
                        "category_path": path_s,
                        "params": params,
                        "pictures": pics,
                        "pharm_group": params.get("Фармакологическая группа") or "",
                        "form": params.get("Форма выпуска") or "",
                        "for_whom": params.get("Для кого") or "",
                    }
                )
            el.clear()

    inv = {
        "offers_total": offers_total,
        "vet_offers": len(offers),
        "param_fill_pct": {
            k: round(v / max(offers_total, 1) * 100, 2)
            for k, v in param_fill.most_common()
        },
        "pharm_groups": Counter(
            (o.get("pharm_group") or "—") for o in offers
        ).most_common(30),
        "forms": Counter((o.get("form") or "—") for o in offers).most_common(20),
        "categories": Counter((o.get("category") or "—") for o in offers).most_common(25),
    }
    return cats, offers, inv


def pick_vision_sample(offers: list[dict]) -> list[dict]:
    by_id = {o["id"]: o for o in offers}
    picked: list[dict] = []
    for fid in FOCUS_IDS:
        if fid in by_id and by_id[fid].get("pictures"):
            o = dict(by_id[fid])
            o["focus"] = True
            picked.append(o)

    # diversify by pharm group + form
    buckets: dict[str, list] = defaultdict(list)
    for o in offers:
        if o["id"] in FOCUS_IDS:
            continue
        if not o.get("pictures"):
            continue
        g = (o.get("pharm_group") or "other").lower()
        key = "other"
        for bk, needles in PHARM_GROUP_BUCKETS.items():
            if any(n in g or n in o["name"].lower() for n in needles):
                key = bk
                break
        buckets[key].append(o)

    order = [
        "anthelmintic",
        "ecto_parasite",
        "dermatology",
        "vitamins",
        "antibiotics",
        "other_vet",
    ]
    per = max(2, (MAX_VISION - len(picked)) // max(len(order), 1))
    for bk in order:
        for o in buckets.get(bk, [])[:per]:
            o = dict(o)
            o["focus"] = False
            o["bucket"] = bk
            picked.append(o)
            if len(picked) >= MAX_VISION:
                return picked
    return picked[:MAX_VISION]


def build_prompt(p: dict) -> str:
    skip = {"Артикул", "sku_id", "rating", "reviews", "is_stm", "Длина", "Ширина", "Высота", "Объем"}
    param_lines = [
        f"- {k}: {v}" for k, v in (p.get("params") or {}).items() if k not in skip and v
    ][:35]
    return f"""Ты анализируешь фото упаковки товара ветаптеки зоомагазина «Четыре Лапы».

ЗАДАЧА: найти атрибуты, которые РЕАЛЬНО видны на фото (визуал упаковки или OCR этикетки),
и которых НЕТ в названии товара и параметрах фида ниже.

НЕ ИЗВЛЕКАЙ как «новые», если значение уже есть в названии / бренде(vendor) /
категории (path) / params — даже если видно на OCR упаковки:
- бренд, производитель, vendor, торговое имя из name;
- Форма выпуска и синонимы: Spot-on = капли на холку = спот-он;
- Для кого, Фармакологическая группа, Возраст/Размер, Страна, артикул, вес/объём из name;
- цену, штрихкод, маркетинговые слоганы без search-value.
Если МНН/действующее вещество ЕСТЬ в name или params — не дублируй.
Если МНН только на упаковке и НЕТ в фиде — это валидный new_attribute.

НЕ ВКЛЮЧАЙ негации («без X») как отдельные атрибуты — только если пользователь явно ищет «без …»
и это OCR с упаковки как claim (редко; помечай low).

ИЩИ В ПРИОРИТЕТЕ (только если явно на фото и НЕТ в name/params):
1. Действующее вещество / МНН (OCR) — praziquantel, imidacloprid, moxidectin…
2. Спектр действия детальнее фида: блохи / клещи / глисты / комары / власоеды / личинки
3. Длительность защиты (4 недели, 1 месяц, 3 месяца) — OCR
4. Возрастной порог / вес точнее («от 8 недель», «от 4 кг») если нет в params
5. Способ применения (на холку / внутрь / с кормом / наружно) если не покрыто формой
6. Количество доз в упаковке (1/3/4 пипетки) если не в name
7. Вкусовая маскировка / вкус суспензии (если на упаковке)
8. Показания/симптомы на этикетке (для поиска «от блох», «от глистов» уточнение)
9. Серия/линейка (Spot-on, Plus, Max…) если не в name
10. Иконки животных на упаковке vs заявленный «Для кого» (только если расхождение)

НАЗВАНИЕ: {p.get('name')}
КАТЕГОРИЯ: {p.get('category')} | path={p.get('category_path')}
ФАРМГРУППА: {p.get('pharm_group')} | ФОРМА: {p.get('form')} | ДЛЯ: {p.get('for_whom')}

УЖЕ В ФИДЕ:
{chr(10).join(param_lines) if param_lines else '(пусто)'}

Верни ТОЛЬКО JSON:
{{
  "image_kind": "packshot|label_closeup|multipack|lifestyle|unclear",
  "ocr_labels": ["короткие надписи с упаковки"],
  "skip_reason": null,
  "new_attributes": [
    {{"name": "...", "value": "...", "evidence": "ocr|visual", "search_relevance": "high|medium|low", "filter_candidate": true, "why_helps_search": "1 фраза"}}
  ],
  "already_in_feed_visible": ["видно на фото но уже в фиде/названии"],
  "not_useful_from_image": ["видно но бесполезно для поиска"]
}}
Не выдумывай. Пустой new_attributes — нормально."""


def call_openrouter(api_key: str, prompt: str, image_url: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/attr-enrichment-product",
        "X-Title": "4lapy vet vision research",
    }
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 1600,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=180)
    data = r.json()
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}", "raw": str(data)[:1500]}
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {"error": "bad shape", "raw": str(data)[:1500]}
    return {"raw_text": text, "usage": data.get("usage")}


def parse_json_content(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m2 = re.search(r"\{[\s\S]*\}", text)
        if m2:
            try:
                return json.loads(m2.group(0))
            except json.JSONDecodeError:
                pass
    return {"parse_error": True, "raw_text": text[:2000]}


def _norm_coll(s: str) -> str:
    s = str(s or "").strip().casefold().replace("ё", "е")
    s = s.replace("«", "").replace("»", "").replace('"', "")
    return re.sub(r"\s+", " ", s)


# Синонимы формы выпуска / упаковки — не выдавать как «новый» атрибут
_FORM_SYNONYM_GROUPS = (
    {"spot-on", "spot on", "спот-он", "спот он", "spoton", "капли на холку", "капли"},
    {"таблетки", "таблетка", "табл"},
    {"суспензия", "суспензии"},
    {"спрей", "аэрозоль"},
    {"ошейник", "ошейники"},
)

_BAN_ATTR_NAMES = {
    "для кого",
    "форма выпуска",
    "фармакологическая группа",
    "возраст питомца",
    "размер питомца",
    "страна-производитель",
    "тип препарата",
    "бренд",
    "brand",
    "vendor",
    "производитель",
    "торговая марка",
    "артикул",
    "категория",
}


def build_feed_corpus(product: dict) -> list[str]:
    """Корпус коллизий: название, бренд/vendor, категория/path, params (не description)."""
    pieces: list[str] = []

    def add(raw: str | None) -> None:
        t = _norm_coll(raw or "")
        if t:
            pieces.append(t)

    add(product.get("name"))
    add(product.get("vendor"))
    add(product.get("brand"))
    add(product.get("category"))
    path = product.get("category_path") or ""
    add(path)
    for seg in re.split(r"[/|>→]+", path):
        add(seg.strip())
    params = product.get("params") or {}
    if isinstance(params, dict):
        for k, v in params.items():
            add(str(k))
            add(str(v))
            # ключ+значение как в карточке
            add(f"{k} {v}")
    # бренд = первое слово названия, если vendor пуст
    name = product.get("name") or ""
    if name and not (product.get("vendor") or product.get("brand")):
        add(name.split()[0])
    return pieces


def _value_redundant_with_piece(value_norm: str, piece: str, *, min_len: int = 4) -> bool:
    """True если value целиком в piece / piece целиком покрывает value без новых токенов."""
    if not value_norm or not piece:
        return False
    if value_norm == piece:
        return True
    if len(value_norm) >= min_len and value_norm in piece:
        return True
    if len(piece) >= min_len and piece in value_norm:
        rem = value_norm.replace(piece, " ", 1)
        extra = [t for t in re.findall(r"[\w%-]+", rem, flags=re.UNICODE) if len(t) >= min_len and not t.isdigit()]
        return len(extra) == 0
    return False


def _form_synonym_collision(value_norm: str, corpus: list[str]) -> bool:
    """Spot-on ↔ капли на холку и др. — одна сущность формы выпуска."""
    blob = " ".join(corpus)
    vn = value_norm.replace("-", " ")
    for group in _FORM_SYNONYM_GROUPS:
        value_in_group = False
        for g in group:
            gn = g.replace("-", " ")
            if vn == gn or (len(gn) >= 5 and gn in vn) or (len(vn) >= 5 and vn in gn):
                value_in_group = True
                break
        if not value_in_group:
            continue
        if any(g.replace("-", " ") in blob for g in group if len(g) >= 4):
            return True
    return False


def feed_collision(product: dict, attr_name: str, attr_value: str) -> tuple[bool, str]:
    """True if value already in name / category / brand / params (или синоним формы)."""
    an = _norm_coll(attr_name)
    val = _norm_coll(attr_value)
    if not val:
        return True, "empty_value"
    if an in _BAN_ATTR_NAMES or an.startswith("для кого"):
        return True, "structured_feed_field"
    corpus = build_feed_corpus(product)
    blob = " ".join(corpus)
    # бренд/vendor как значение
    for brand_key in ("vendor", "brand"):
        b = _norm_coll(product.get(brand_key) or "")
        if b and (val == b or b in val or val in b):
            return True, "brand_collision"
    name0 = _norm_coll((product.get("name") or "").split()[0] if product.get("name") else "")
    if name0 and len(name0) >= 3 and val == name0:
        return True, "brand_collision"
    if _form_synonym_collision(val, corpus):
        return True, "form_synonym_collision"
    # целое значение / избыточность по кускам корпуса
    for piece in corpus:
        if _value_redundant_with_piece(val, piece):
            return True, "feed_or_name_collision"
    # все содержательные токены значения уже в корпусе (короткие МНН и т.п.)
    tokens = [t for t in re.findall(r"[a-zа-яё0-9%]{3,}", val) if not t.isdigit()]
    if tokens and all(t in blob for t in tokens):
        return True, "feed_or_name_collision"
    return False, ""


def decide_attrs(product: dict, vision: dict) -> dict:
    keep, reject = [], []
    for a in vision.get("new_attributes") or []:
        if not isinstance(a, dict):
            continue
        an, av = (a.get("name") or "").strip(), (a.get("value") or "").strip()
        if not an or not av:
            continue
        hit, reason = feed_collision(product, an, av)
        if hit:
            reject.append({**a, "decision": "REJECT", "reason": reason or "feed_or_name_collision"})
            continue
        if a.get("search_relevance") == "low" and not a.get("filter_candidate"):
            reject.append({**a, "decision": "REJECT", "reason": "low_search_relevance"})
            continue
        keep.append({**a, "decision": "KEEP"})
    return {"keep": keep, "reject": reject}


def pull_queries() -> dict:
    # vet / parasite related from top searches
    top = ch_query(
        f"""
        SELECT
          lowerUTF8(trim(searchTerm)) AS q,
          count() AS cnt
        FROM sessions.searches
        WHERE siteId = {SITE_ID}
          AND timestamp >= now() - INTERVAL 90 DAY
          AND searchTerm IS NOT NULL
          AND trim(searchTerm) != ''
        GROUP BY q
        ORDER BY cnt DESC
        LIMIT 40000
        """,
        timeout=600,
    )
    rows = top.get("data") or []
    needles = [
        "блох",
        "клещ",
        "гельминт",
        "глист",
        "антигельминт",
        "празител",
        "адвант",
        "гельминтал",
        "капли на холку",
        "спот",
        "суспенз",
        "ошейник",
        "от блох",
        "от клещ",
        "от паразит",
        "бравекто",
        "фронтлайн",
        "инспектор",
        "стронгхолд",
        "миладем",
        "дронтал",
        "пирантел",
        "ветаптек",
        "витамин",
        "шампунь от",
        "спрей от",
    ]
    families = {
        "Блохи / клещи / эктопаразиты": ["блох", "клещ", "от паразит", "ошейник", "фронтлайн", "бравекто", "адвант", "стронгхолд", "инспектор"],
        "Глисты / антигельминтики": ["гельминт", "глист", "антигельминт", "празител", "дронтал", "гельминтал", "пирантел", "миладем"],
        "Форма: капли / спот-он": ["капли", "спот", "на холку"],
        "Форма: суспензия / таблетки": ["суспенз", "таблет"],
        "Витамины / уход": ["витамин", "шампунь от", "спрей от"],
    }
    matched = []
    fam_counts = {k: {"searches": 0, "queries": 0, "examples": []} for k in families}
    for row in rows:
        q = row["q"]
        cnt = int(row["cnt"])
        if not any(n in q for n in needles):
            continue
        matched.append({"q": q, "cnt": cnt})
        for fam, fn in families.items():
            if any(x in q for x in fn):
                fam_counts[fam]["searches"] += cnt
                fam_counts[fam]["queries"] += 1
                if len(fam_counts[fam]["examples"]) < 8:
                    fam_counts[fam]["examples"].append({"q": q, "cnt": cnt})

    # money baselines from CH (agg_sessions schema: searches, withOrder, timeBegin)
    sess = ch_query(
        f"""
        WITH deduped AS (
          SELECT sessionId,
                 max(searches) AS searches,
                 max(autocompleteClicks) AS ac
          FROM sessions.agg_sessions
          WHERE siteId = {SITE_ID}
            AND toDate(timeBegin) >= today() - 90
            AND toDate(timeBegin) <= today() - 1
          GROUP BY sessionId
        )
        SELECT
          countIf(searches > 0 OR ac > 0) AS search_sessions
        FROM deduped
        """,
        timeout=180,
    )
    ord_q = ch_query(
        f"""
        SELECT
          sumIf(withOrder, searches > 0 OR autocompleteClicks > 0) AS search_orders,
          round(sumIf(revenue, withOrder > 0 AND (searches > 0 OR autocompleteClicks > 0)), 2) AS search_revenue
        FROM sessions.agg_sessions
        WHERE siteId = {SITE_ID}
          AND toDate(timeBegin) >= today() - 90
          AND toDate(timeBegin) <= today() - 1
          AND withOrder > 0
        """,
        timeout=180,
    )
    ss = int((sess.get("data") or [{}])[0].get("search_sessions") or 0)
    so = int(float((ord_q.get("data") or [{}])[0].get("search_orders") or 0))
    sr = float((ord_q.get("data") or [{}])[0].get("search_revenue") or 0)
    cvr = (so / ss) if ss else 0
    aov = (sr / so) if so else 0

    totals = ch_query(
        f"""
        SELECT count() AS searches
        FROM sessions.searches
        WHERE siteId = {SITE_ID}
          AND timestamp >= now() - INTERVAL 90 DAY
        """,
        timeout=180,
    )
    total_searches = int((totals.get("data") or [{}])[0].get("searches") or 0)

    return {
        "period_days": 90,
        "total_searches": total_searches,
        "vet_related_queries": len(matched),
        "vet_related_searches": sum(x["cnt"] for x in matched),
        "families": fam_counts,
        "top_vet_queries": matched[:40],
        "money_baseline": {
            "search_sessions_90d": ss,
            "search_orders_90d": so,
            "search_cvr_pct": round(cvr * 100, 3),
            "aov": round(aov, 2),
            "search_revenue_90d": round(sr, 2),
        },
    }


def compute_money(qdata: dict, attr_ranking: list[dict]) -> dict:
    """Stream A (query precision) + Stream B (catalog visibility) — vet-focused."""
    base = qdata["money_baseline"]
    cvr = base["search_cvr_pct"] / 100.0
    aov = base["aov"] or 2100
    vet_s = qdata["vet_related_searches"]

    fam = qdata["families"]
    # Ядро: блохи/клещи + глисты (пересечение брендов частично — берём 85% суммы)
    core = (
        fam["Блохи / клещи / эктопаразиты"]["searches"]
        + fam["Глисты / антигельминтики"]["searches"]
    )
    attr_demand = int(min(vet_s, core * 0.85))

    scenarios = {}
    for name, fixable, lift, gated, p_extract, cov, serp, ctr, pclick in [
        ("conservative", 0.40, 0.15, 0.75, 0.45, 0.22, 0.24, 0.055, 0.065),
        ("base", 0.55, 0.22, 0.85, 0.60, 0.15, 0.32, 0.07, 0.075),
        ("optimistic", 0.70, 0.30, 0.95, 0.75, 0.10, 0.42, 0.09, 0.085),
    ]:
        # Stream A: better matching on attr-driven vet searches
        rev_a_90 = attr_demand * fixable * (cvr * lift) * aov
        # Stream B: SKUs newly enter SERP via substance/spectrum/duration
        newly = p_extract * (1 - cov)
        p_sess = min(0.55, newly * (serp / 0.30))
        demand_b = int(attr_demand * gated)
        impr = demand_b * p_sess
        rev_b_90 = impr * ctr * pclick * aov
        scenarios[name] = {
            "stream_a_month": round(rev_a_90 / 3),
            "stream_b_month": round(rev_b_90 / 3),
            "total_month": round((rev_a_90 + rev_b_90) / 3),
            "stream_a_year": round(rev_a_90 / 3 * 12),
            "stream_b_year_cons_opt_note": "see scenarios",
            "note": "Срез только ветаптека/паразиты. A+B — иллюстрация; партнёру B = доп. потенциал.",
            "params": {
                "attr_demand_90d": attr_demand,
                "fixable": fixable,
                "rel_lift": lift,
                "cvr": cvr,
                "aov": aov,
                "p_extract": p_extract,
                "gated": gated,
            },
        }

    return {
        "scope": "vet_pharmacy_parasite_slice_only",
        "vet_related_searches_90d": vet_s,
        "attr_demand_searches_90d": attr_demand,
        "baseline": base,
        "scenarios": scenarios,
        "top_attrs_for_money": attr_ranking[:12],
    }


def cleanup_keeps(results: list[dict]) -> list[dict]:
    """Повторный проход коллизий по name/category/brand/params (и из vision.new_attributes)."""
    out = []
    for r in results:
        vision = r.get("vision") if isinstance(r.get("vision"), dict) else {}
        # Полный пересчёт KEEP/REJECT из сырого vision — единый gate
        if vision.get("new_attributes"):
            dec = decide_attrs(r, vision)
            keep2, rej2 = dec["keep"], dec["reject"]
        else:
            keep2, rej2 = [], list(r.get("reject") or [])
            for a in r.get("keep") or []:
                hit, reason = feed_collision(r, a.get("name") or "", a.get("value") or "")
                if hit:
                    rej2.append({**a, "decision": "REJECT", "reason": reason or "feed_or_name_collision"})
                else:
                    keep2.append({**a, "decision": "KEEP"})
        rr = dict(r)
        rr["keep"] = keep2
        rr["reject"] = rej2
        out.append(rr)
    return out


def rank_attributes(results: list[dict]) -> list[dict]:
    scores = Counter()
    examples = defaultdict(list)
    for r in results:
        for a in r.get("keep") or []:
            key = (a.get("name") or "").strip()
            if not key:
                continue
            w = {"high": 3, "medium": 2, "low": 1}.get(a.get("search_relevance"), 1)
            scores[key] += w
            if len(examples[key]) < 4:
                examples[key].append(
                    {
                        "offer_id": r["id"],
                        "value": a.get("value"),
                        "name_product": r.get("name"),
                        "picture": (r.get("pictures") or [None])[0],
                    }
                )
    ranked = []
    for name, sc in scores.most_common():
        ranked.append(
            {
                "attr": name,
                "score": sc,
                "n_products": len(examples[name]),
                "examples": examples[name],
                "effectiveness": "high" if sc >= 8 else ("medium" if sc >= 4 else "support"),
            }
        )
    return ranked


def build_html(
    inv: dict,
    qdata: dict,
    money: dict,
    results: list[dict],
    ranking: list[dict],
    focus_cases: list[dict],
) -> str:
    base = money["scenarios"]["base"]
    cons = money["scenarios"]["conservative"]
    opt = money["scenarios"]["optimistic"]
    bl = money["baseline"]

    def esc(s):
        return (
            str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    fam_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{v['searches']:,}</td><td>{v['queries']}</td>"
        f"<td>{esc(', '.join(e['q'] for e in v['examples'][:3]))}</td></tr>"
        for k, v in qdata["families"].items()
    )
    rank_rows = "".join(
        "<tr><td><strong>{}</strong></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(r["attr"]),
            esc(r["effectiveness"]),
            r["n_products"],
            r["score"],
            esc("; ".join(str(e.get("value") or "") for e in r["examples"][:3])),
        )
        for r in ranking[:15]
    )

    def case_html(c: dict, num: int) -> str:
        keep = c.get("keep") or []
        reject_n = len(c.get("reject") or [])
        feed_rows = "".join(
            f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
            for k, v in (c.get("params") or {}).items()
            if k
            not in {
                "Артикул",
                "sku_id",
                "rating",
                "reviews",
                "is_stm",
                "Длина",
                "Ширина",
                "Высота",
                "Новинка",
                "Требуется лицензия",
            }
            and v
        )[:2000]
        # rebuild properly
        feed_parts = []
        for k, v in (c.get("params") or {}).items():
            if k in {
                "Артикул",
                "sku_id",
                "rating",
                "reviews",
                "is_stm",
                "Длина",
                "Ширина",
                "Высота",
                "Новинка",
                "Требуется лицензия",
            }:
                continue
            if v:
                feed_parts.append(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>")
        feed_rows = "".join(feed_parts)
        keep_rows = "".join(
            f"<tr><td><strong>{esc(a.get('name'))}</strong></td><td>{esc(a.get('value'))}</td>"
            f"<td>{esc(a.get('evidence'))}</td><td>{esc(a.get('search_relevance'))}</td>"
            f"<td>{esc(a.get('why_helps_search') or '')}</td></tr>"
            for a in keep
        ) or "<tr><td colspan=5>Новых KEEP после коллизии с фидом нет — картинка дублирует карточку</td></tr>"
        pic = (c.get("pictures") or [""])[0]
        badge = "FOCUS" if c.get("focus") else (c.get("bucket") or "sample")
        return f"""
<article class="case">
  <div class="case-num">{num}</div>
  <a class="case-img" href="{esc(c.get('url'))}" target="_blank" rel="noopener">
    <img src="{esc(pic)}" alt="{esc(c.get('name'))}" loading="lazy"/>
  </a>
  <div class="case-body">
    <div class="case-meta">{esc(badge)} · id {esc(c.get('id'))} · {esc(c.get('category'))} · {esc(c.get('price'))} ₽</div>
    <h3>{esc(c.get('name'))}</h3>
    <p class="case-line">{esc((c.get('vision') or {}).get('image_kind') or '')} · OCR: {esc(', '.join(((c.get('vision') or {}).get('ocr_labels') or [])[:6]))}</p>
    <div class="case-cols">
      <div>
        <h4>Уже в фиде / названии</h4>
        <table class="mini"><tbody>{feed_rows}</tbody></table>
      </div>
      <div>
        <h4>С картинки (KEEP) · reject={reject_n}</h4>
        <table class="mini">
          <thead><tr><th>Атрибут</th><th>Значение</th><th>Доказ.</th><th>Релев.</th><th>Зачем поиску</th></tr></thead>
          <tbody>{keep_rows}</tbody>
        </table>
      </div>
    </div>
  </div>
</article>"""

    # focus first, then best keep samples
    ordered = sorted(
        results,
        key=lambda r: (0 if r.get("focus") else 1, -len(r.get("keep") or [])),
    )
    cases = "".join(case_html(c, i + 1) for i, c in enumerate(ordered[:12]))

    pharm = "".join(
        f"<tr><td>{esc(g)}</td><td>{n}</td></tr>" for g, n in inv["pharm_groups"][:12]
    )
    forms = "".join(f"<tr><td>{esc(g)}</td><td>{n}</td></tr>" for g, n in inv["forms"][:10])

    topq = "".join(
        f"<tr><td>{esc(x['q'])}</td><td>{x['cnt']:,}</td></tr>"
        for x in qdata["top_vet_queries"][:20]
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Четыре Лапы — атрибуты с картинок: ветаптека</title>
<style>
:root {{
  --bg:#f4f7f5; --ink:#14201a; --muted:#5a6b62; --line:#d5e0d9;
  --card:#fff; --accent:#1b5e3b; --warn:#8a4b12; --plus:#0d6b4c;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.5 "Segoe UI", system-ui, sans-serif; color:var(--ink); background:var(--bg); }}
.wrap {{ max-width:1100px; margin:0 auto; padding:32px 20px 80px; }}
h1 {{ font-size:28px; font-weight:650; letter-spacing:-0.02em; margin:0 0 8px; }}
h2 {{ font-size:20px; margin:40px 0 12px; color:var(--accent); }}
h3 {{ font-size:16px; margin:20px 0 8px; }}
.lead {{ color:var(--muted); font-size:17px; max-width:760px; }}
.meta {{ margin:12px 0 24px; color:var(--muted); font-size:13px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:18px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); padding:14px; }}
.stat b {{ display:block; font-size:22px; font-weight:650; margin-bottom:4px; }}
.stat span {{ color:var(--muted); font-size:12px; }}
.callout {{ background:var(--card); border-left:3px solid var(--accent); padding:14px 16px; margin:16px 0; }}
.callout.warn {{ border-left-color:var(--warn); }}
.callout.plus {{ border-left-color:var(--plus); }}
table {{ width:100%; border-collapse:collapse; background:var(--card); font-size:14px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:#e7f0ea; font-weight:600; }}
.tag {{ display:inline-block; background:#e7f0ea; padding:2px 8px; font-size:12px; margin-right:6px; }}
.case {{ display:grid; grid-template-columns:48px 200px 1fr; gap:14px; background:var(--card); border:1px solid var(--line); padding:14px; margin:14px 0; }}
.case-num {{ font-size:22px; font-weight:700; color:var(--accent); }}
.case-img img {{ width:200px; height:200px; object-fit:contain; background:#f0f4f1; display:block; }}
.case-meta {{ font-size:12px; color:var(--muted); }}
.case-cols {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.case-cols h4 {{ margin:0 0 6px; font-size:12px; color:var(--muted); }}
table.mini {{ font-size:12px; }}
footer {{ margin-top:48px; color:var(--muted); font-size:12px; }}
@media (max-width:800px) {{
  .case {{ grid-template-columns:1fr; }}
  .case-cols {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="tag">Четыре Лапы · ветаптека</div>
  <div class="tag">атрибуты с картинок</div>
  <div class="tag">оценка ₽</div>
  <h1>Ветаптека: что видно на упаковке и чего нет в фиде</h1>
  <p class="lead">
    Исследование разрыва между поиском покупателя («от блох», «от глистов», действующее вещество, срок защиты)
    и тем, что сейчас в карточке YML. Фокус — <strong>препараты</strong>: антигельминтики и средства от эктопаразитов.
    Deep-dive по трём SKU + расширенная выборка упаковок.
  </p>
  <p class="meta">
    Каталог ~{inv['offers_total']:,} offer · ветаптека/препараты в выборке ~{inv['vet_offers']:,} ·
    ClickHouse поиск 90 дней · vision по фото упаковок · коллизии с name/params отфильтрованы.
  </p>

  <div class="grid">
    <div class="stat"><b>{inv['vet_offers']:,}</b><span>товаров ветаптеки/препаратов в разборе</span></div>
    <div class="stat"><b>{qdata['vet_related_searches']:,}</b><span>вет/паразит-поисков за 90д</span></div>
    <div class="stat"><b>{base['stream_a_month']:,} ₽</b><span>стрим A · база Δ/мес (запросы)</span></div>
    <div class="stat"><b>+{cons['stream_b_month']:,}…{opt['stream_b_month']:,} ₽</b><span>стрим B · доп. потенциал / мес</span></div>
    <div class="stat"><b>{bl['search_cvr_pct']}%</b><span>search CVR · AOV ~{bl['aov']:,.0f} ₽</span></div>
    <div class="stat"><b>{len(results)}</b><span>упаковок прогнано vision</span></div>
  </div>

  <div class="callout">
    <strong>Вывод для партнёра.</strong> В фиде уже сильные «карточные» поля:
    для кого, форма выпуска, фармгруппа, возраст/размер. Слабое место — то, что покупатель
    <em>читает с коробки</em> и вбивает в поиск: <strong>действующее вещество</strong>,
    <strong>спектр</strong> (блохи / клещи / глисты / комары), <strong>срок защиты</strong>,
    <strong>число пипеток</strong>, уточнения по возрасту/весу с этикетки.
    Это как раз зона атрибутов с картинок + OCR.
  </div>
  <div class="callout plus">
    <strong>Два денежных слоя.</strong>
    A — точнее матчим уже идущие вет-запросы (база ~<strong>{base['stream_a_month']:,} ₽/мес</strong>).
    B — доп. потенциал: товары появляются в выдаче по новым attr
    (+<strong>{cons['stream_b_month']:,}…{opt['stream_b_month']:,} ₽/мес</strong>).
    B не замена A; не складывать без оговорки о пересечении.
  </div>

  <h2>1. Что уже есть в фиде (ветаптека)</h2>
  <div class="grid">
    <div>
      <h3>Фармгруппы (выборка)</h3>
      <table><thead><tr><th>Группа</th><th>Offers</th></tr></thead><tbody>{pharm}</tbody></table>
    </div>
    <div>
      <h3>Формы выпуска</h3>
      <table><thead><tr><th>Форма</th><th>Offers</th></tr></thead><tbody>{forms}</tbody></table>
    </div>
  </div>
  <table>
    <thead><tr><th>Не достаём с картинки (уже в карточке / бесполезно)</th><th>Почему</th></tr></thead>
    <tbody>
      <tr><td>Для кого / возраст / размер питомца</td><td>структурные params</td></tr>
      <tr><td>Форма выпуска, фармгруппа</td><td>уже в фиде</td></tr>
      <tr><td>Бренд / артикул / страна</td><td>в name или params</td></tr>
      <tr><td>Цена, акция, габариты упаковки</td><td>не search-facet с фото</td></tr>
      <tr><td>Повтор названия («капли на холку» если уже в форме)</td><td>коллизия с фидом</td></tr>
    </tbody>
  </table>

  <h2>2. Что нужно доставать с картинок</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Эффект</th><th>Почему gap</th></tr></thead>
    <tbody>
      <tr><td><strong>Действующее вещество (МНН)</strong></td><td>высокий</td><td>часто только на упаковке; в params нет</td></tr>
      <tr><td><strong>Спектр: блохи / клещи / глисты / комары</strong></td><td>высокий</td><td>фармгруппа грубая; поиск формулирует конкретнее</td></tr>
      <tr><td><strong>Срок защиты</strong></td><td>высокий</td><td>OCR «4 недели / 1 месяц»; в фиде нет</td></tr>
      <tr><td><strong>Число доз / пипеток в упаковке</strong></td><td>средний–высокий</td><td>в name не всегда; на блистере видно</td></tr>
      <tr><td>Порог возраста/веса с этикетки</td><td>средний</td><td>уточняет params «все возрасты»</td></tr>
      <tr><td>Способ применения (деталь)</td><td>средний</td><td>если форма общая</td></tr>
      <tr><td>Вкус суспензии / маскировка</td><td>поддержка</td><td>реже ищут, но OCR лёгкий</td></tr>
    </tbody>
  </table>

  <h3>Ранжирование по факту vision-прогона</h3>
  <table>
    <thead><tr><th>Атрибут</th><th>Эффект</th><th>SKU с KEEP</th><th>score</th><th>Примеры значений</th></tr></thead>
    <tbody>{rank_rows}</tbody>
  </table>

  <h2>3. Поиск: вет/паразит спрос (90 дней)</h2>
  <p>Всего поисков: <strong>{qdata['total_searches']:,}</strong>.
  Вет/паразит-лексика: <strong>{qdata['vet_related_searches']:,}</strong> поисков
  ({qdata['vet_related_queries']} запросов).</p>
  <table>
    <thead><tr><th>Семейство</th><th>Поисков</th><th>Запросов</th><th>Примеры</th></tr></thead>
    <tbody>{fam_rows}</tbody>
  </table>
  <h3>Топ запросов</h3>
  <table>
    <thead><tr><th>Запрос</th><th>Поисков/90д</th></tr></thead>
    <tbody>{topq}</tbody>
  </table>

  <h2>4. Наглядные кейсы: фото → атрибуты</h2>
  <p class="lead" style="font-size:15px">
    Слева — что уже в YML. Справа — KEEP с картинки после фильтра коллизий с названием и params.
    Первые три — запрошенные focus SKU.
  </p>
  {cases}

  <h2>5. Деньги</h2>
  <p class="meta">База CH: search CVR {bl['search_cvr_pct']}% · AOV {bl['aov']:,.0f} ₽ ·
  search revenue 90д ~{bl['search_revenue_90d']:,.0f} ₽. Attr-спрос (оценка) {money['attr_demand_searches_90d']:,}/90д.</p>
  <table>
    <thead><tr><th>Сценарий</th><th>Стрим A ₽/мес</th><th>Стрим B доп. ₽/мес</th><th>Иллюстрация A+B*</th></tr></thead>
    <tbody>
      <tr><td>Консервативный</td><td>{cons['stream_a_month']:,}</td><td>+{cons['stream_b_month']:,}</td><td>{cons['total_month']:,}</td></tr>
      <tr><td><strong>Базовый (партнёру)</strong></td><td><strong>{base['stream_a_month']:,}</strong></td><td><strong>+{base['stream_b_month']:,}</strong></td><td><strong>{base['total_month']:,}</strong></td></tr>
      <tr><td>Оптимистичный</td><td>{opt['stream_a_month']:,}</td><td>+{opt['stream_b_month']:,}</td><td>{opt['total_month']:,}</td></tr>
    </tbody>
  </table>
  <div class="callout warn">
    *A+B — верхняя иллюстрация портфеля; партнёру: база = A, доп. потенциал = B.
    Формулы как в шаблоне двух стримов (запросы × lift CVR; каталог × P(новый attr) × выдача).
  </div>

  <h2>6. Рекомендация пилота</h2>
  <ol>
    <li>Старт: антигельминтики + капли от блох/клещей (макс. поиск + читаемые упаковки).</li>
    <li>Обязательный OCR-пакет: МНН, спектр, срок защиты, число доз.</li>
    <li>Не дублировать «Для кого / форма / фармгруппа» — только пробелы и уточнения.</li>
    <li>Заливка в feed attributes → фильтры и уточнение выдачи по стилевым вет-запросам.</li>
  </ol>

  <div class="callout">
    <strong>Что купить (продуктово):</strong> пакет vision+OCR атрибутов для ветаптеки —
    действующее вещество, спектр паразитов, срок защиты, фасовка доз, уточнения возраста/веса с этикетки —
    с исключением дублей фида.
  </div>
  <div class="callout warn">
    <strong>Скоуп денег.</strong> Цифры выше — только срез «ветаптека / паразиты»
    (~{qdata['vet_related_searches']:,} поисков / 90д из {qdata['total_searches']:,}).
    Корма, наполнители, игрушки — отдельный upside, здесь не смешиваем.
  </div>

  <footer>
    Артефакты: portfolio/4lapy_vet/ · Desktop Output\\4lapy_8267_vet_pharmacy\\
  </footer>
</div>
</body>
</html>
"""


def main() -> None:
    print("loading feed…")
    _cats, offers, inv = load_feed()
    (OUT / "feed_inventory_vet.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sample = pick_vision_sample(offers)
    (OUT / "vision_sample.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"vet offers={len(offers)} vision sample={len(sample)}")

    api_key = load_api_key()
    results = []
    for i, p in enumerate(sample):
        pic = (p.get("pictures") or [None])[0]
        print(f"[{i+1}/{len(sample)}] {p['id']} {p['name'][:60]}…")
        if not pic:
            results.append({**p, "vision": {"error": "no picture"}, "keep": [], "reject": []})
            continue
        raw = call_openrouter(api_key, build_prompt(p), pic)
        if raw.get("error"):
            vision = {"error": raw["error"]}
        else:
            vision = parse_json_content(raw.get("raw_text") or "")
            vision["_usage"] = raw.get("usage")
        dec = decide_attrs(p, vision if isinstance(vision, dict) else {})
        results.append({**p, "vision": vision, **dec})
        time.sleep(0.4)

    (OUT / "vision_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ranking = rank_attributes(results)
    (OUT / "attr_ranking.json").write_text(
        json.dumps(ranking, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("CH queries…")
    qdata = pull_queries()
    (OUT / "query_impact_vet.json").write_text(
        json.dumps(qdata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    money = compute_money(qdata, ranking)
    (OUT / "money_vet.json").write_text(
        json.dumps(money, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    focus_cases = [r for r in results if r.get("id") in FOCUS_IDS]
    html = build_html(inv, qdata, money, results, ranking, focus_cases)
    html_path = OUT / "4lapy-vet-pharmacy-image-attrs.html"
    html_path.write_text(html, encoding="utf-8")

    DESKTOP_OUT.mkdir(parents=True, exist_ok=True)
    (DESKTOP_OUT / "4lapy-vet-pharmacy-image-attrs.html").write_text(html, encoding="utf-8")
    # companion summary
    summary = {
        "focus_ids": FOCUS_IDS,
        "vision_n": len(results),
        "keep_total": sum(len(r.get("keep") or []) for r in results),
        "money_base_a_month": money["scenarios"]["base"]["stream_a_month"],
        "money_b_cons_opt_month": [
            money["scenarios"]["conservative"]["stream_b_month"],
            money["scenarios"]["optimistic"]["stream_b_month"],
        ],
        "top_attrs": ranking[:10],
        "html": str(html_path),
        "desktop": str(DESKTOP_OUT / "4lapy-vet-pharmacy-image-attrs.html"),
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DESKTOP_OUT / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# 4lapy ветаптека — summary\n\n",
        f"- Vision SKU: {len(results)}\n",
        f"- KEEP attrs total: {summary['keep_total']}\n",
        f"- Стрим A base: {summary['money_base_a_month']:,} ₽/мес\n",
        f"- Стрим B: +{summary['money_b_cons_opt_month'][0]:,}…+{summary['money_b_cons_opt_month'][1]:,} ₽/мес\n",
        f"- HTML: `{html_path.name}`\n\n",
        "## Топ атрибутов\n",
    ]
    for r in ranking[:10]:
        md.append(f"- **{r['attr']}** ({r['effectiveness']}) — {r['n_products']} SKU\n")
    (OUT / "SUMMARY.md").write_text("".join(md), encoding="utf-8")
    (DESKTOP_OUT / "SUMMARY.md").write_text("".join(md), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
