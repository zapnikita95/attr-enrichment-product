# -*- coding: utf-8 -*-
"""Stream-inventory TSUM YML: params, categories, sample offers with pictures."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import iterparse

FEED = Path(r"C:\Users\1\Downloads\tsum.xml")
OUT = Path(r"C:\Users\1\OneDrive\Desktop\attr-enrichment-product\portfolio\tsum")
OUT.mkdir(parents=True, exist_ok=True)

# Priority L1/L2 keywords (url slugs + names) for sampling
PRIORITY_SLUGS = [
    "odezhda",
    "obuv",
    "sumki",
    "aksessuary",
    "parfyumeriya",
    "parfumeriya",
    "kosmetika",
    "chasy",
    "ukrasheniya",
    "bizhuteriya",
    "yuvelirnye",
    "platya",
    "kurtki",
    "palto",
    "bryuki",
    "dzhinsy",
    "rubashki",
    "futbolki",
    "krossovki",
    "tufli",
]


def local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def main() -> None:
    cats: dict[str, dict] = {}
    param_names: Counter[str] = Counter()
    param_value_examples: dict[str, list[str]] = defaultdict(list)
    param_fill: Counter[str] = Counter()
    offers_total = 0
    offers_with_pic = 0
    offers_by_cat: Counter[str] = Counter()
    samples_by_bucket: dict[str, list[dict]] = defaultdict(list)
    vendor_c: Counter[str] = Counter()

    # First pass categories via streaming
    context = None
    for event, elem in iterparse(str(FEED), events=("end",)):
        tag = local(elem.tag)
        if tag == "category":
            cid = elem.get("id") or ""
            parent = elem.get("parentId") or ""
            url = elem.get("url") or ""
            name = (elem.text or "").strip()
            cats[cid] = {"id": cid, "parentId": parent, "name": name, "url": url}
            elem.clear()
        elif tag == "categories":
            # keep cats, clear container
            elem.clear()
        elif tag == "offer":
            offers_total += 1
            oid = elem.get("id") or ""
            available = elem.get("available")
            name = ""
            price = ""
            cat_id = ""
            url = ""
            vendor = ""
            pics: list[str] = []
            params: dict[str, str] = {}
            for child in elem:
                ct = local(child.tag)
                if ct == "name":
                    name = (child.text or "").strip()
                elif ct == "price":
                    price = (child.text or "").strip()
                elif ct == "categoryId":
                    cat_id = (child.text or "").strip()
                elif ct == "url":
                    url = (child.text or "").strip()
                elif ct == "vendor":
                    vendor = (child.text or "").strip()
                elif ct == "picture":
                    p = (child.text or "").strip()
                    if p:
                        pics.append(p)
                elif ct == "param":
                    pn = (child.get("name") or "").strip()
                    pv = (child.text or "").strip()
                    if pn and pv:
                        params[pn] = pv
                        param_names[pn] += 1
                        if len(param_value_examples[pn]) < 8 and pv not in param_value_examples[pn]:
                            param_value_examples[pn].append(pv)
            if pics:
                offers_with_pic += 1
            if cat_id:
                offers_by_cat[cat_id] += 1
            if vendor:
                vendor_c[vendor] += 1
            for pn in params:
                param_fill[pn] += 1

            # bucket by category url/name
            cinfo = cats.get(cat_id) or {}
            curl = (cinfo.get("url") or "").lower()
            cname = (cinfo.get("name") or "").lower()
            bucket = "other"
            for slug in PRIORITY_SLUGS:
                if slug in curl or slug in cname:
                    bucket = slug
                    break
            # walk parents for L1 bucket
            if bucket == "other":
                pid = cinfo.get("parentId") or ""
                hops = 0
                while pid and hops < 6:
                    pinfo = cats.get(pid) or {}
                    purl = (pinfo.get("url") or "").lower()
                    pname = (pinfo.get("name") or "").lower()
                    for slug in PRIORITY_SLUGS:
                        if slug in purl or slug in pname:
                            bucket = slug
                            break
                    if bucket != "other":
                        break
                    pid = pinfo.get("parentId") or ""
                    hops += 1

            if pics and len(samples_by_bucket[bucket]) < 12:
                samples_by_bucket[bucket].append(
                    {
                        "offer_id": oid,
                        "name": name,
                        "price": price,
                        "categoryId": cat_id,
                        "category_name": cinfo.get("name"),
                        "category_url": cinfo.get("url"),
                        "url": url,
                        "vendor": vendor,
                        "picture": pics[0],
                        "pictures": pics[:4],
                        "params": params,
                        "bucket": bucket,
                        "available": available,
                    }
                )

            if offers_total % 50000 == 0:
                print(f"... offers={offers_total} cats={len(cats)} params={len(param_names)}")

            elem.clear()

    # Build L1 roots
    roots = [c for c in cats.values() if not c.get("parentId")]
    # Top categories by offer count
    top_cats = []
    for cid, cnt in offers_by_cat.most_common(80):
        c = cats.get(cid) or {"id": cid, "name": "?", "url": "", "parentId": ""}
        top_cats.append({**c, "offers": cnt})

    param_stats = []
    for pn, cnt in param_names.most_common():
        fill_pct = round(100.0 * param_fill[pn] / max(offers_total, 1), 2)
        param_stats.append(
            {
                "name": pn,
                "offers_with_param": cnt,
                "fill_pct": fill_pct,
                "examples": param_value_examples.get(pn, []),
            }
        )

    summary = {
        "feed": str(FEED),
        "offers_total": offers_total,
        "offers_with_picture": offers_with_pic,
        "categories_total": len(cats),
        "root_categories": roots[:40],
        "unique_param_names": len(param_names),
        "param_stats": param_stats,
        "top_categories_by_offers": top_cats,
        "top_vendors": vendor_c.most_common(40),
        "samples_by_bucket_counts": {k: len(v) for k, v in samples_by_bucket.items()},
    }

    (OUT / "feed_inventory.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "vision_candidates.json").write_text(
        json.dumps(samples_by_bucket, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "categories.json").write_text(
        json.dumps(cats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "offers_total": offers_total,
        "offers_with_picture": offers_with_pic,
        "categories_total": len(cats),
        "unique_param_names": len(param_names),
        "top_params": [p["name"] for p in param_stats[:25]],
        "sample_buckets": summary["samples_by_bucket_counts"],
        "out": str(OUT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
