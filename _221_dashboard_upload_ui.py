# -*- coding: utf-8 -*-
"""Browser TOTP UI: upload 221 vision CSV → Diginetica Dashboard site 221."""
from __future__ import annotations

import csv
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMG = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main")
sys.path.insert(0, str(IMG))

import dashboard_feed_attributes as dfa  # noqa: E402

PORT = int(os.environ.get("AZBUKA_DASHBOARD_UI_PORT", "8767"))
SITE_ID = 221
CSV_PATH = ROOT / "portfolio" / "221_azbuka" / "221_vision_dashboard_upload.csv"
SENT_PATH = ROOT / "portfolio" / "221_azbuka" / "dashboard_sent.json"

STATE: dict = {"phase": "idle", "log": [], "result": "", "progress": "", "rows": 0}


def _log(msg: str) -> None:
    STATE["log"].append(msg)
    if len(STATE["log"]) > 400:
        STATE["log"] = STATE["log"][-400:]
    if "Отправлено" in msg or "/" in msg:
        STATE["progress"] = msg


def _creds() -> tuple[str, str]:
    login = (os.environ.get("DASHBOARD_LOGIN") or "").strip()
    password = (os.environ.get("DASHBOARD_PASSWORD") or "").strip()
    if login and password:
        return login, password
    p = Path.home() / ".search-checkup-creds.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    dash = data.get("dashboard") or {}
    return str(dash.get("login") or "").strip(), str(dash.get("password") or "").strip()


def load_rows() -> list[tuple[str, str, str]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Нет CSV: {CSV_PATH}. Сначала дождись батча vision.")
    rows = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            eid = (r.get("external_id") or "").strip()
            an = (r.get("attribute_name") or "").strip()
            av = (r.get("attribute_value") or "").strip()
            if eid and an and av:
                rows.append((eid, an, av))
    return rows


def load_sent() -> set[str]:
    if not SENT_PATH.exists():
        return set()
    try:
        data = json.loads(SENT_PATH.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else data.get("keys") or [])
    except Exception:
        return set()


def mark_sent(eid: str, an: str, av: str) -> None:
    keys = load_sent()
    keys.add(f"{eid}|{an}|{av}")
    SENT_PATH.write_text(
        json.dumps({"keys": sorted(keys)}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


HTML = """<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>221 Азбука · vision → Dashboard</title>
<style>
:root{--bg:#eef3ef;--sur:#fff;--brd:#d0ddd4;--acc:#1f6f4a;--grn:#1a7a45;--red:#c0392b;--txt:#14201a;--txt2:#5a6b62}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--txt);padding:32px}
.card{max-width:480px;margin:0 auto;background:var(--sur);border:1px solid var(--brd);border-radius:12px;padding:28px}
h1{font-size:18px;margin-bottom:8px}
p{color:var(--txt2);font-size:13px;margin-bottom:16px;line-height:1.5}
label{font-size:12px;font-weight:600;display:block;margin-bottom:6px}
input{width:100%;font-size:28px;letter-spacing:.35em;text-align:center;padding:12px;border:2px solid var(--brd);border-radius:8px}
input:focus{outline:none;border-color:var(--acc)}
button{margin-top:16px;width:100%;padding:14px;font-size:15px;font-weight:700;background:var(--acc);color:#fff;border:none;border-radius:8px;cursor:pointer}
button:disabled{opacity:.55;cursor:wait}
#status{margin-top:16px;padding:12px;border-radius:8px;font-size:13px;display:none}
#status.show{display:block}
#status.run{background:#f0faf4;border:1px solid #b8e0c8;color:var(--txt)}
#status.ok{background:#edf7f0;border:1px solid #b8e0c8;color:var(--grn);font-weight:700}
#status.err{background:#fdf0ef;border:1px solid #f5c0bb;color:var(--red);font-weight:600}
#log{margin-top:12px;font-size:11px;color:var(--txt2);white-space:pre-wrap;max-height:220px;overflow:auto;background:#f7faf8;border:1px solid var(--brd);border-radius:8px;padding:10px;display:none}
#log.show{display:block}
.spin{display:inline-block;width:14px;height:14px;border:2px solid #b8e0c8;border-top-color:var(--acc);border-radius:50%;animation:sp .7s linear infinite;vertical-align:-2px;margin-right:6px}
@keyframes sp{to{transform:rotate(360deg)}}
</style></head><body>
<div class="card">
  <h1>221 Азбука Вкуса · vision attrs</h1>
  <p>Заливка CSV с картинок в Diginetica Dashboard (siteId=221). Введи свежий TOTP (6 цифр) и жми «Загрузить».</p>
  <p id="meta">Строк в файле: …</p>
  <form id="f">
    <label for="totp">Код TOTP</label>
    <input id="totp" name="totp" inputmode="numeric" autocomplete="one-time-code" required autofocus placeholder="000000">
    <button type="submit" id="btn">Загрузить в Dashboard</button>
  </form>
  <div id="status"></div>
  <div id="log"></div>
</div>
<script>
const f=document.getElementById('f'), logEl=document.getElementById('log'), btn=document.getElementById('btn'), st=document.getElementById('status'), inp=document.getElementById('totp');
inp.addEventListener('input',()=>{ inp.value=inp.value.replace(/\\D/g,'').slice(0,6); });
fetch('/meta').then(r=>r.json()).then(j=>{ document.getElementById('meta').textContent='Строк в файле: '+(j.rows||0)+' · '+ (j.csv||''); });
function showStatus(cls, html){ st.className='show '+cls; st.innerHTML=html; }
async function poll(){
  const j=await (await fetch('/status')).json();
  const lines=(j.log||[]);
  if(lines.length){ logEl.classList.add('show'); logEl.textContent=lines.join('\\n'); }
  if(j.phase==='running'){
    showStatus('run', '<span class="spin"></span>'+(j.progress||'Загрузка…')+' <small>(не закрывайте вкладку)</small>');
    setTimeout(poll, 1000); return;
  }
  if(j.phase==='done'){ btn.disabled=false; showStatus('ok', '✅ '+j.result); return; }
  if(j.phase==='error'){ btn.disabled=false; showStatus('err', '❌ '+j.result); }
}
f.addEventListener('submit', async e=>{
  e.preventDefault();
  const code=inp.value.replace(/\\D/g,'');
  if(code.length!==6){ showStatus('err','❌ Нужно ровно 6 цифр'); return; }
  btn.disabled=true; showStatus('run','<span class="spin"></span>Старт…'); logEl.classList.add('show'); logEl.textContent='';
  try{
    const r=await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({totp:code})});
    const j=await r.json();
    if(!r.ok||!j.ok){ btn.disabled=false; showStatus('err','❌ '+(j.error||r.statusText)); return; }
    poll();
  }catch(err){ btn.disabled=false; showStatus('err','❌ '+err); }
});
poll();
</script></body></html>"""


def _run_upload(totp: str) -> None:
    STATE["phase"] = "running"
    STATE["result"] = ""
    STATE["progress"] = "Подготовка…"
    STATE["log"] = []
    try:
        rows = load_rows()
        STATE["rows"] = len(rows)
        _log(f"Строк к отправке: {len(rows)}")
        if not rows:
            raise RuntimeError("CSV пустой — батч ещё не дал keep-строк")
        login, password = _creds()
        if not login or not password:
            raise RuntimeError("Нет dashboard login/password в creds")
        sent = load_sent()
        ok = failed = 0
        for ev in dfa.upload_feed_attributes_progress(
            SITE_ID,
            rows,
            login=login,
            password=password,
            totp=totp,
            trigger="feed-loader",
            sent_keys=sent,
            mark_sent_fn=mark_sent,
            fixed_attribute_name=None,
        ):
            phase = ev.get("phase")
            if ev.get("log"):
                _log(str(ev["log"]).replace("**", ""))
            if phase == "item":
                done = int(ev.get("done") or 0)
                total = int(ev.get("total") or len(rows))
                STATE["progress"] = f"Отправлено {done}/{total}"
                if ev.get("ok"):
                    ok += 1
                else:
                    failed += 1
            if phase == "error":
                raise RuntimeError(str(ev.get("log") or ev.get("error") or "upload error"))
            if phase == "done":
                res = ev.get("result")
                if res is not None:
                    ok = getattr(res, "ok", ok)
                    failed = getattr(res, "failed", failed)
        msg = f"ok={ok} failed={failed}"
        STATE["result"] = msg
        STATE["phase"] = "done" if failed == 0 else "error"
        STATE["progress"] = "Готово"
        _log("✅ " + msg if failed == 0 else "⚠ " + msg)
    except Exception as e:
        STATE["phase"] = "error"
        STATE["result"] = str(e)
        STATE["progress"] = ""
        _log("❌ " + str(e))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def _json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/status"):
            self._json(
                {
                    "phase": STATE["phase"],
                    "log": STATE["log"],
                    "result": STATE["result"],
                    "progress": STATE["progress"],
                }
            )
            return
        if self.path.startswith("/meta"):
            n = 0
            if CSV_PATH.exists():
                with CSV_PATH.open(encoding="utf-8-sig") as f:
                    n = max(0, sum(1 for _ in f) - 1)
            self._json({"rows": n, "csv": str(CSV_PATH)})
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self.path.startswith("/upload"):
            self._json({"ok": False, "error": "not found"}, 404)
            return
        if STATE["phase"] == "running":
            self._json({"ok": False, "error": "Уже идёт загрузка"}, 409)
            return
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            totp = json.loads(raw.decode("utf-8")).get("totp") or ""
        except Exception:
            self._json({"ok": False, "error": "bad json"}, 400)
            return
        threading.Thread(target=_run_upload, args=(str(totp),), daemon=True).start()
        self._json({"ok": True})


def main() -> None:
    try:
        rows = load_rows()
        STATE["rows"] = len(rows)
        print(f"CSV rows: {len(rows)} -> {CSV_PATH}")
    except Exception as e:
        print("WARN:", e)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"UI: {url}")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
