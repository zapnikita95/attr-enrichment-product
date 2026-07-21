"""Hard closed-set coerce + negation reject for filter values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import FilterAttributeSpec

_NEG = (
    "без ",
    "не содержит",
    "не имеет",
    "отсутств",
    "-free",
    " free",
)


def _norm(s: str) -> str:
    s = str(s or "").strip().lower().replace("ё", "е")
    s = s.replace("«", "").replace("»", "").replace('"', "")
    s = re.sub(r"\s+", " ", s)
    return s


@dataclass
class CoerceResult:
    ok: bool
    value: str | list[str] | None
    raw: str
    reason: str = ""
    mapped_from: str = ""


def coerce_value(spec: FilterAttributeSpec, raw: Any) -> CoerceResult:
    """Map model output into allowed_values only. Reject OOD / negation traps."""
    if raw is None:
        return CoerceResult(False, None, "", reason="empty")

    if isinstance(raw, bool):
        raw = "да" if raw else "нет"
    if isinstance(raw, (int, float)):
        raw = str(raw)

    if isinstance(raw, list):
        parts = [str(x) for x in raw if str(x).strip()]
        coerced: list[str] = []
        for p in parts:
            one = coerce_value(spec, p)
            if one.ok and one.value:
                v = one.value if isinstance(one.value, str) else one.value[0]
                if v not in coerced:
                    coerced.append(v)
        if not coerced:
            return CoerceResult(False, None, str(raw), reason="multi_all_ood")
        if not spec.multi:
            return CoerceResult(True, coerced[0], str(raw), reason="multi_collapsed")
        return CoerceResult(True, coerced, str(raw))

    text = str(raw).strip()
    n = _norm(text)
    if not n:
        return CoerceResult(False, None, text, reason="empty")

    allowed_norm = {_norm(a): a for a in spec.allowed_values}

    # Exact allowed FIRST (e.g. «без рукавов» contains «без» but is a valid enum)
    if n in allowed_norm:
        return CoerceResult(True, allowed_norm[n], text)

    # Synonym map (exact, then contains for noisy gold phrases)
    for syn, target in (spec.synonym_map or {}).items():
        sn = _norm(syn)
        if sn == n or (len(sn) >= 4 and sn in n):
            tn = _norm(target)
            if tn in allowed_norm:
                return CoerceResult(True, allowed_norm[tn], text, mapped_from=syn)
            if target in spec.allowed_values:
                return CoerceResult(True, target, text, mapped_from=syn)

    # Negation phrasing for freeform OOD (after allowed/synonym hits)
    if spec.value_type != "boolean" and any(p in n for p in _NEG):
        return CoerceResult(False, None, text, reason="negation")

    # Boolean soft parse
    if spec.value_type == "boolean":
        if n in {"1", "да", "yes", "true", "есть", "есть капюшон", "с капюшоном", "капюшон"}:
            if n == "капюшон":
                return CoerceResult(False, None, text, reason="ambiguous_label_as_value")
            if "да" in allowed_norm:
                return CoerceResult(True, allowed_norm["да"], text, mapped_from="bool_soft_yes")
        if n in {"0", "нет", "no", "false", "без капюшона", "нет капюшона"}:
            if "нет" in allowed_norm:
                return CoerceResult(True, allowed_norm["нет"], text, mapped_from="bool_soft_no")

    # multi_enum: comma / slash split
    if spec.multi or "," in text or "/" in text:
        chunks = re.split(r"[,;/|]+", text)
        if len(chunks) > 1:
            return coerce_value(spec, [c.strip() for c in chunks if c.strip()])

    # Substring hit on allowed (careful: prefer longest)
    hits = sorted(
        ((a, an) for an, a in allowed_norm.items() if an and an in n),
        key=lambda x: len(x[1]),
        reverse=True,
    )
    if hits:
        return CoerceResult(True, hits[0][0], text, mapped_from="substring")

    return CoerceResult(False, None, text, reason="out_of_vocabulary")


def feed_collision(value: str, feed_name: str, feed_params: str = "") -> bool:
    """True if value already present in title/params (do not ship as new filter fact)."""
    v = _norm(value)
    if len(v) < 3:
        return False
    blob = _norm(f"{feed_name} {feed_params}")
    return bool(v and v in blob)
