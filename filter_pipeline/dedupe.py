"""Picture URL dedupe + propagate filter values to sibling offers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

IMG_DESC = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main")
if str(IMG_DESC) not in sys.path:
    sys.path.insert(0, str(IMG_DESC))

from picture_dedupe import normalize_picture_url  # noqa: E402


def picture_key(url: str, offer_id: str = "") -> str:
    n = normalize_picture_url(url or "")
    if n:
        return n
    return f"__nopicture__:{offer_id}"


def group_by_picture(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Collapse to unique pictures. Each group:
      representative (first), member_offer_ids, picture_key, group_size
    Never call vision twice for the same picture_key.
    """
    order: list[str] = []
    groups: dict[str, dict[str, Any]] = {}
    for s in samples:
        key = picture_key(s.get("picture_url") or "", str(s.get("offer_id") or ""))
        # control local-only images: key by local path
        local = s.get("local_image") or ""
        if not (s.get("picture_url") or "").strip() and local:
            key = f"__local__:{Path(local).resolve()}"
        if key not in groups:
            order.append(key)
            groups[key] = {
                "picture_key": key,
                "representative": dict(s),
                "member_offer_ids": [str(s.get("offer_id") or "")],
                "members": [dict(s)],
                "group_size": 1,
            }
        else:
            oid = str(s.get("offer_id") or "")
            if oid and oid not in groups[key]["member_offer_ids"]:
                groups[key]["member_offer_ids"].append(oid)
                groups[key]["members"].append(dict(s))
                groups[key]["group_size"] = len(groups[key]["member_offer_ids"])
    return [groups[k] for k in order]


def unique_representatives(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Samples to send to vision (1 per picture)."""
    out = []
    for g in group_by_picture(samples):
        rep = dict(g["representative"])
        rep["picture_key"] = g["picture_key"]
        rep["member_offer_ids"] = list(g["member_offer_ids"])
        rep["group_size"] = g["group_size"]
        out.append(rep)
    return out


def propagate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Expand each vision row to all member_offer_ids sharing the picture.
    Marks duplicates with propagated_from.
    """
    expanded: list[dict[str, Any]] = []
    for r in rows:
        members = r.get("member_offer_ids") or [r.get("offer_id")]
        primary = str(r.get("offer_id") or "")
        for oid in members:
            oid = str(oid or "")
            if not oid:
                continue
            clone = dict(r)
            clone["offer_id"] = oid
            clone["propagated"] = oid != primary
            clone["propagated_from"] = primary if oid != primary else None
            clone["picture_key"] = r.get("picture_key")
            clone["group_size"] = r.get("group_size") or len(members)
            expanded.append(clone)
    return expanded
