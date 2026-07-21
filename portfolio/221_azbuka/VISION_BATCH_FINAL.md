# 221 Азбука — vision batch → Dashboard

**Модель:** `google/gemini-2.5-flash-lite`  
**Офферов в фокусе:** 5457 (P0 полный + сэмплы P1)  
**Успешно vision:** 5129 · ошибки API: 21 · время ~24 мин  

## Итоговые файлы

| Файл | Назначение |
|------|------------|
| `221_vision_dashboard_upload.csv` | **заливка** `external_id,attribute_name,attribute_value` |
| `C:\Users\1\OneDrive\Desktop\221_azbuka_vision_dashboard_upload.csv` | копия на рабочий стол |
| `221_vision_rejected.csv` | нашли, но **не** льём (негация / name / вне closed-set) |
| `C:\Users\1\OneDrive\Desktop\221_azbuka_vision_rejected.csv` | копия rejected |

## KEEP в upload (2464 строк / 1885 офферов)

| Атрибут | N |
|---------|---|
| Форма выпуска | 956 |
| Вкус, Добавки | 734 |
| Тип упаковки | 532 |
| Технология приготовления | 90 |
| Способ обработки | 81 |
| Нарезка | 58 |
| Тип соуса | 11 |
| Текстура корма | 2 |

Негации (`без` / `не содержит` / `-free`) в upload **не входят** — только в rejected.

## Dashboard UI

```powershell
py -3.13 _221_dashboard_upload_ui.py
```

→ http://127.0.0.1:8767/ — TOTP → «Загрузить в Dashboard» → ждать `ok=… failed=0`.
