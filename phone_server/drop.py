#!/usr/bin/env python3
"""Drop — 기기 간 텍스트·파일 전송 (개인 서버, stdlib 전용).

PC에서 텍스트/파일을 올리면 폰·다른 기기에서 바로 받는다. Tailscale과 궁합 최고.
- 업로드는 멀티파트 대신 raw PUT (Python 3.14에서 cgi 제거 대응)
- 저장: ~/drop_data/  (메타=SQLite, 파일=files/)
- 포트 8090 (대시보드 8080과 공존)

실행:  python drop.py [포트]
접속:  http://<주소>:8090
"""
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, "drop_data")
FILES = os.path.join(DATA, "files")
DB = os.path.join(DATA, "drop.db")
MAX_BYTES = 200 * 1024 * 1024  # 200MB 상한
os.makedirs(FILES, exist_ok=True)


def db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT, name TEXT, size INTEGER, ts INTEGER, body TEXT)""")
    return c


def safe_name(n):
    n = os.path.basename(n or "file")
    n = re.sub(r"[^\w.\-() ]+", "_", n)[:120]
    return n or "file"


def add_note(text):
    c = db()
    c.execute("INSERT INTO items(kind,name,size,ts,body) VALUES('note','메모',?,?,?)",
              (len(text.encode()), int(time.time()), text))
    c.commit(); rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.close()
    return rid


def add_file(name, data):
    name = safe_name(name)
    c = db()
    c.execute("INSERT INTO items(kind,name,size,ts,body) VALUES('file',?,?,?,'')",
              (name, len(data), int(time.time())))
    c.commit()
    rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.close()
    with open(os.path.join(FILES, f"{rid}_{name}"), "wb") as f:
        f.write(data)
    return rid


def list_items():
    c = db()
    rows = c.execute("SELECT id,kind,name,size,ts,body FROM items ORDER BY id DESC "
                     "LIMIT 200").fetchall()
    c.close()
    out = []
    for i, k, n, s, t, b in rows:
        out.append({"id": i, "kind": k, "name": n, "size": s, "ts": t,
                    "preview": (b[:280] if k == "note" else "")})
    return out


def get_file(rid):
    c = db()
    r = c.execute("SELECT name FROM items WHERE id=? AND kind='file'", (rid,)).fetchone()
    c.close()
    if not r:
        return None, None
    path = os.path.join(FILES, f"{rid}_{r[0]}")
    return (path, r[0]) if os.path.exists(path) else (None, None)


def delete(rid):
    path, _ = get_file(rid)
    if path and os.path.exists(path):
        os.remove(path)
    c = db(); c.execute("DELETE FROM items WHERE id=?", (rid,)); c.commit(); c.close()


def load_token():
    t = os.environ.get("PHONE_TOKEN", "").strip()
    if t:
        return t
    for p in (os.path.expanduser("~/.phone_token"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           ".phone_token")):
        try:
            with open(p) as f:
                v = f.read().strip()
                if v:
                    return v
        except OSError:
            pass
    return ""


TOKEN = load_token()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        c = getattr(self, "_cookie", None)
        if c:
            self.send_header("Set-Cookie", c)
            self._cookie = None
        super().end_headers()

    def _gate(self):
        if not TOKEN:
            return True
        if ("pt=" + TOKEN) in self.headers.get("Cookie", ""):
            return True
        if urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query
                                 ).get("k", [""])[0] == TOKEN:
            self._cookie = ("pt=" + TOKEN +
                            "; Max-Age=31536000; HttpOnly; SameSite=Lax; Path=/")
            return True
        return False

    def _deny(self):
        self._send(401, "text/html; charset=utf-8",
                   "<meta charset=utf-8><body style='font-family:sans-serif;background:#1e1e2e;"
                   "color:#fff;text-align:center;padding-top:20%'><h2>🔒 접근 토큰 필요</h2>"
                   "<p>주소 뒤에 <b>?k=토큰</b> 을 붙여 접속하세요.</p></body>")

    def _send(self, code, ctype, body, extra=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        if not self._gate():
            try:
                self._deny()
            except Exception:
                pass
            return
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/":
                self._send(200, "text/html; charset=utf-8", HTML)
            elif u.path == "/api/list":
                self._json({"ok": True, "items": list_items()})
            elif u.path == "/api/get":
                rid = int(q.get("id", ["0"])[0])
                path, name = get_file(rid)
                if not path:
                    return self._json({"ok": False, "error": "없음"}, 404)
                with open(path, "rb") as f:
                    data = f.read()
                dispo = "attachment; filename*=UTF-8''" + urllib.parse.quote(name)
                self._send(200, "application/octet-stream", data,
                           {"Content-Disposition": dispo})
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._json({"ok": False, "error": repr(e)}, 500)
            except Exception:
                pass

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BYTES:
            raise ValueError("파일이 너무 큼(200MB 초과)")
        return self.rfile.read(n)

    def do_POST(self):
        if not self._gate():
            try:
                self._deny()
            except Exception:
                pass
            return
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/api/note":
                text = self._body().decode("utf-8", "replace").strip()
                if not text:
                    return self._json({"ok": False, "error": "빈 메모"}, 400)
                self._json({"ok": True, "id": add_note(text)})
            elif u.path == "/api/upload":
                name = urllib.parse.unquote(q.get("name", ["file"])[0])
                data = self._body()
                if not data:
                    return self._json({"ok": False, "error": "빈 파일"}, 400)
                self._json({"ok": True, "id": add_file(name, data)})
            elif u.path == "/api/del":
                delete(int(q.get("id", ["0"])[0]))
                self._json({"ok": True})
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    do_PUT = do_POST


HTML = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "drop.html"),
            encoding="utf-8").read()

if __name__ == "__main__":
    print(f"[drop] http://0.0.0.0:{PORT}  data={DATA}")
    try:
        ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
    except OSError as e:
        print(f"포트 {PORT} 사용 불가({e}) → python drop.py 8091")
        sys.exit(1)
