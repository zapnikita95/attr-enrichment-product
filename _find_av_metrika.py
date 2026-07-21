# -*- coding: utf-8 -*-
import json
import re
import ssl
import urllib.request
from pathlib import Path

ctx = ssl.create_default_context()
req = urllib.request.Request("https://av.ru/", headers={"User-Agent": "Mozilla/5.0"})
try:
    html = urllib.request.urlopen(req, timeout=30, context=ctx).read().decode("utf-8", "replace")
except Exception as e:
    print("fetch err", e)
    html = ""
ids = set(re.findall(r"ym\((\d{5,})", html))
ids |= set(re.findall(r"metrica\.yandex\.(?:ru|com)/watch/(\d+)", html))
ids |= set(re.findall(r"mc\.yandex\.ru/watch/(\d+)", html))
print("page counters", sorted(ids), "html_len", len(html))

tok = ""
for p in (
    Path(r"C:\Users\1\OneDrive\Desktop\skills-portable\skills\.env"),
    Path(r"C:\Users\1\OneDrive\Desktop\skills-portable\skills\metrika\.env"),
):
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("METRIKA_TOKEN=") or line.startswith("YANDEX_METRIKA_TOKEN="):
                tok = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
if not tok:
    tok = "y0__xCYxaLvARjFxj0gjIDmqBaoEC1nVwTDxx9o6-px7bKRIxj4NQ"
print("token_ok", bool(tok))

url = "https://api-metrika.yandex.net/management/v1/counters?per_page=1000"
req2 = urllib.request.Request(url, headers={"Authorization": f"OAuth {tok}"})
try:
    data = json.loads(urllib.request.urlopen(req2, timeout=60).read().decode())
    counters = data.get("counters") or []
    print("counters total", len(counters))
    hits = []
    for c in counters:
        site = c.get("site") or ""
        name = c.get("name") or ""
        blob = f"{c.get('id')} {name} {site}"
        if re.search(r"av\.ru|азбук|vkusa|azbuka", blob, re.I):
            hits.append((c.get("id"), name, site))
    print("hits", hits[:30])
except Exception as e:
    print("api err", type(e).__name__, e)

# try page ids against API
for cid in sorted(ids):
    try:
        u = f"https://api-metrika.yandex.net/management/v1/counter/{cid}"
        r = urllib.request.Request(u, headers={"Authorization": f"OAuth {tok}"})
        d = json.loads(urllib.request.urlopen(r, timeout=30).read().decode())
        c = d.get("counter") or {}
        print("access", cid, c.get("name"), c.get("site"), c.get("permission"))
    except Exception as e:
        print("no access", cid, type(e).__name__, str(e)[:120])
