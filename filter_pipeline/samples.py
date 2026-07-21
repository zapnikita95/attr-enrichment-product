"""Pick Zolla pilot SKUs from results.db + control images."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

ZOLLA_RESULTS = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\results.db")
ZOLLA_CACHE = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\image_cache")
CONTROL_DIR = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\_audit_samples\zolla_pattern")


def resolve_local_image(offer_id: str, picture_url: str) -> Path | None:
    """Match image_description attribute_detector._image_cache_path: sha256(url)[:24].jpg"""
    if picture_url:
        key = hashlib.sha256(picture_url.encode("utf-8")).hexdigest()[:24]
        p = ZOLLA_CACHE / f"{key}.jpg"
        if p.is_file():
            return p
        for ext in (".jpeg", ".webp", ".png"):
            alt = ZOLLA_CACHE / f"{key}{ext}"
            if alt.is_file():
                return alt
    if offer_id and ZOLLA_CACHE.is_dir():
        hits = list(ZOLLA_CACHE.glob(f"*{offer_id}*"))
        if hits:
            return hits[0]
    return None


def _fetch_by_name_like(pattern: str, limit: int = 8) -> list[dict[str, Any]]:
    if not ZOLLA_RESULTS.is_file():
        return []
    con = sqlite3.connect(str(ZOLLA_RESULTS))
    rows = con.execute(
        """
        SELECT offer_id, name, category, picture_url, attributes_json
        FROM results
        WHERE name LIKE ?
        LIMIT ?
        """,
        (pattern, limit * 3),
    ).fetchall()
    con.close()
    out: list[dict[str, Any]] = []
    seen_pic: set[str] = set()
    for oid, name, cat, pic, aj in rows:
        pic = pic or ""
        if pic in seen_pic:
            continue
        seen_pic.add(pic)
        local = resolve_local_image(str(oid), pic)
        out.append(
            {
                "offer_id": str(oid),
                "name": name or "",
                "category": cat or "",
                "picture_url": pic,
                "local_image": str(local) if local else None,
                "attributes_json": aj,
                "expect_hint": pattern,
            }
        )
        if len(out) >= limit:
            break
    return out


def samples_for_hood(n_yes: int = 6, n_no: int = 6) -> list[dict[str, Any]]:
    yes = _fetch_by_name_like("%капюшон%", n_yes)
    for s in yes:
        s["expected"] = "да"
        s["attr_id"] = "hood"
    no: list[dict[str, Any]] = []
    for pat in ("%Футболка%", "%Блузка%", "%Юбка%"):
        for s in _fetch_by_name_like(pat, max(2, n_no // 2)):
            if "капюшон" in (s["name"] or "").lower():
                continue
            s["expected"] = "нет"
            s["attr_id"] = "hood"
            no.append(s)
            if len(no) >= n_no:
                break
        if len(no) >= n_no:
            break
    return yes + no[:n_no]


def samples_for_length(n: int = 10) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pat, expect in (
        ("%платье%мини%", "mini"),
        ("%мини%плать%", "mini"),
        ("%платье%макси%", "maxi"),
        ("%макси%плать%", "maxi"),
        ("%платье%", None),
        ("%юбк%", None),
    ):
        for s in _fetch_by_name_like(pat, 4):
            s["attr_id"] = "length"
            s["expected"] = expect
            out.append(s)
            if len(out) >= n:
                return out
    return out[:n]


def samples_for_print_pattern() -> list[dict[str, Any]]:
    """Control set from _audit_samples + a few DB patterns."""
    control = [
        ("96863", "lurex_jumper_96863.jpg", "меланж", "title may say lurex — expect melange/not false lurex"),
        ("96705", "cardigan_96705.jpg", "меланж", "melange cardigan"),
        ("94603", "socks_94603.jpg", "графика", "christmas socks — not houndstooth"),
        ("100889", "maybe_lurex_100889.jpg", "люрекс", "real lurex"),
        ("101742", "maybe_lurex_101742.jpg", "однотонный", "no lurex"),
    ]
    out: list[dict[str, Any]] = []
    for oid, fname, expect, note in control:
        p = CONTROL_DIR / fname
        out.append(
            {
                "offer_id": oid,
                "name": f"control {fname}",
                "category": "control",
                "picture_url": "",
                "local_image": str(p) if p.is_file() else None,
                "attr_id": "print_pattern",
                "expected": expect,
                "note": note,
            }
        )
    # DB stripes etc.
    if ZOLLA_RESULTS.is_file():
        con = sqlite3.connect(str(ZOLLA_RESULTS))
        rows = con.execute(
            """
            SELECT offer_id, name, category, picture_url, attributes_json
            FROM results
            WHERE attributes_json LIKE '%полоск%'
            LIMIT 40
            """
        ).fetchall()
        con.close()
        seen = 0
        for oid, name, cat, pic, aj in rows:
            local = resolve_local_image(str(oid), pic or "")
            if not local and not pic:
                continue
            out.append(
                {
                    "offer_id": str(oid),
                    "name": name or "",
                    "category": cat or "",
                    "picture_url": pic or "",
                    "local_image": str(local) if local else None,
                    "attr_id": "print_pattern",
                    "expected": "полоска",
                    "note": "db prior stripe",
                }
            )
            seen += 1
            if seen >= 4:
                break
    return out


def dump_samples(path: Path) -> dict[str, Any]:
    data = {
        "hood": samples_for_hood(),
        "length": samples_for_length(),
        "print_pattern": samples_for_print_pattern(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
