"""Typed filter attribute specs (closed-set ready for Diginetica facets)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ValueType = Literal["boolean", "enum", "multi_enum", "numeric_bins"]
FilterRole = Literal["filter", "search_only", "reject"]


@dataclass
class FilterAttributeSpec:
    attr_id: str
    label_ru: str
    value_type: ValueType
    allowed_values: list[str]
    multi: bool = False
    sources: list[str] = field(default_factory=lambda: ["vision", "text"])
    categories: list[str] = field(default_factory=list)
    why_filter: str = ""
    why_not: str = ""
    role: FilterRole = "filter"
    dashboard_attr: str = ""
    synonym_map: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d.get("dashboard_attr"):
            d["dashboard_attr"] = f"digi_filter_{self.attr_id}"
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FilterAttributeSpec":
        return cls(
            attr_id=str(raw.get("attr_id") or raw.get("id") or "").strip(),
            label_ru=str(raw.get("label_ru") or raw.get("label") or "").strip(),
            value_type=str(raw.get("value_type") or "enum"),  # type: ignore[arg-type]
            allowed_values=[str(x).strip() for x in (raw.get("allowed_values") or []) if str(x).strip()],
            multi=bool(raw.get("multi", False)),
            sources=list(raw.get("sources") or ["vision", "text"]),
            categories=list(raw.get("categories") or []),
            why_filter=str(raw.get("why_filter") or ""),
            why_not=str(raw.get("why_not") or ""),
            role=str(raw.get("role") or "filter"),  # type: ignore[arg-type]
            dashboard_attr=str(raw.get("dashboard_attr") or ""),
            synonym_map={str(k): str(v) for k, v in (raw.get("synonym_map") or {}).items()},
        )


# Seed fashion filter specs for Zolla pilot (schema-stage may refine).
FASHION_SEED_SPECS: list[FilterAttributeSpec] = [
    FilterAttributeSpec(
        attr_id="hood",
        label_ru="Капюшон",
        value_type="boolean",
        allowed_values=["да", "нет"],
        categories=["верхняя_одежда", "толстовки", "куртки", "пальто"],
        why_filter="Бинарный facet с низкой кардинальностью; часто нужен в UI верхней одежды.",
        synonym_map={
            "yes": "да",
            "no": "нет",
            "true": "да",
            "false": "нет",
            "есть": "да",
            "капюшон есть": "да",
            "с капюшоном": "да",
            "присутствует": "да",
            "наличие": "да",
            "нет капюшона": "нет",
            "без капюшона": "нет",
            "отсутствует": "нет",
            "отсутствие": "нет",
        },
    ),
    FilterAttributeSpec(
        attr_id="length",
        label_ru="Длина изделия",
        value_type="enum",
        allowed_values=["mini", "midi", "maxi", "до колена", "укороченный"],
        categories=["платья", "юбки", "пальто"],
        why_filter="Ограниченный набор длин — классический facet fashion; не свободный текст.",
        synonym_map={
            "мини": "mini",
            "миди": "midi",
            "макси": "maxi",
            "короткий": "mini",
            "короткая": "mini",
            "короткая (мини)": "mini",
            "длинный": "maxi",
            "длинная": "maxi",
            "средний": "midi",
            "средняя": "midi",
            "knee": "до колена",
            "до колен": "до колена",
            "cropped": "укороченный",
            "укороченная": "укороченный",
            "укороченная длина": "укороченный",
        },
    ),
    FilterAttributeSpec(
        attr_id="print_pattern",
        label_ru="Узор / принт",
        value_type="multi_enum",
        multi=True,
        allowed_values=[
            "однотонный",
            "полоска",
            "клетка",
            "горошек",
            "цветочный",
            "геометрия",
            "леопард",
            "зебра",
            "тигровый",
            "камуфляж",
            "абстракция",
            "гусиная лапка",
            "меланж",
            "люрекс",
            "графика",
        ],
        categories=["одежда"],
        why_filter="Facet по визуальному узору; кардинальность ограничена closed-set.",
        synonym_map={
            "полоски": "полоска",
            "Полоски": "полоска",
            "в полоску": "полоска",
            "stripes": "полоска",
            "клетчатый": "клетка",
            "клетчатый узор": "клетка",
            "узор в клетку": "клетка",
            "в клетку": "клетка",
            "клетчатым узором": "клетка",
            "цветы": "цветочный",
            "floral": "цветочный",
            "leopard": "леопард",
            "леопардовый": "леопард",
            "леопардовый принт": "леопард",
            "animal print": "леопард",
            "pied-de-poule": "гусиная лапка",
            "houndstooth": "гусиная лапка",
            "solid": "однотонный",
            "без узора": "однотонный",
            "plain": "однотонный",
            "lurex": "люрекс",
            "military": "камуфляж",
            "милитари": "камуфляж",
            "абстрактный принт": "абстракция",
            "геометрический узор": "геометрия",
            "геометрический": "геометрия",
        },
    ),
    FilterAttributeSpec(
        attr_id="sleeve_length",
        label_ru="Длина рукава",
        value_type="enum",
        allowed_values=["короткий", "длинный", "3/4", "без рукавов"],
        categories=["футболки_топы", "блузки", "платья", "верхняя_одежда"],
        why_filter="Классический facet; 4 значения, хорошо видно на фото.",
        synonym_map={
            "short": "короткий",
            "long": "длинный",
            "sleeveless": "без рукавов",
            "безрукавка": "без рукавов",
            "три четверти": "3/4",
            "3-4": "3/4",
        },
    ),
    FilterAttributeSpec(
        attr_id="pockets",
        label_ru="Карманы",
        value_type="boolean",
        allowed_values=["да", "нет"],
        categories=["брюки", "юбки", "верхняя_одежда", "джинсы"],
        why_filter="Бинарный facet; важен для брюк/верхней одежды.",
        synonym_map={
            "есть": "да",
            "с карманами": "да",
            "без карманов": "нет",
            "yes": "да",
            "no": "нет",
        },
    ),
    FilterAttributeSpec(
        attr_id="fastener",
        label_ru="Застёжка",
        value_type="enum",
        allowed_values=["молния", "пуговицы", "кнопки", "завязки", "нет"],
        categories=["верхняя_одежда", "платья", "джинсы"],
        why_filter="Ограниченный набор типов застёжки — удобный facet.",
        synonym_map={
            "zipper": "молния",
            "на молнии": "молния",
            "buttons": "пуговицы",
            "на пуговицах": "пуговицы",
            "snap": "кнопки",
            "без застёжки": "нет",
            "none": "нет",
        },
    ),
    FilterAttributeSpec(
        attr_id="collar",
        label_ru="Воротник / вырез",
        value_type="enum",
        allowed_values=["круглый", "V-образный", "стойка", "отложной", "капюшон", "без воротника"],
        categories=["футболки_топы", "блузки", "верхняя_одежда"],
        why_filter="Визуальный facet с разумной кардинальностью.",
        synonym_map={
            "crew": "круглый",
            "crew neck": "круглый",
            "круглый вырез": "круглый",
            "округлый": "круглый",
            "обычный вырез": "круглый",
            "под горло": "круглый",
            "v-neck": "V-образный",
            "v образный": "V-образный",
            "turtleneck": "стойка",
            "гольф": "стойка",
            "водолазка": "стойка",
            "polo": "отложной",
            "рубашечный": "отложной",
            "с отворотом": "отложной",
            "hood": "капюшон",
            "none": "без воротника",
        },
    ),
    FilterAttributeSpec(
        attr_id="gender_target",
        label_ru="Пол",
        value_type="enum",
        allowed_values=["женский", "мужской", "унисекс", "детский"],
        categories=["одежда"],
        why_filter="Базовый facet каталога; часто уже в фиде — candidacy может reject.",
        synonym_map={
            "women": "женский",
            "men": "мужской",
            "unisex": "унисекс",
            "kids": "детский",
            "female": "женский",
            "male": "мужской",
        },
    ),
]
