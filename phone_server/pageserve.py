#!/usr/bin/env python3
"""pageserve — ~/pages/ 폴더의 HTML을 서빙하는 정적 웹서버 (stdlib).

우분투/다른 기기에서 scp로 HTML을 ~/pages/ 에 넣으면 즉시 웹에 뜬다.
루트(/)는 올라온 페이지 목록을 다크테마 인덱스로 보여준다.

실행:  python pageserve.py [포트]   (기본 8095)
접속:  http://<주소>:8095
"""
import html
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8095
# 기본은 repo의 phone_server/pages/ (git으로 배포됨). PAGES_DIR로 덮어쓰기 가능.
ROOT = os.environ.get("PAGES_DIR") or \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
os.makedirs(ROOT, exist_ok=True)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def list_directory(self, path):
        # 예쁜 다크테마 인덱스로 대체
        try:
            names = sorted(os.listdir(path))
        except OSError:
            self.send_error(404); return None
        rows = []
        for n in names:
            if n.startswith("."):
                continue
            full = os.path.join(path, n)
            size = os.path.getsize(full) if os.path.isfile(full) else 0
            disp = n + ("/" if os.path.isdir(full) else "")
            kb = f"{size/1024:.1f} KB" if size else ""
            rows.append(f"<a href='{html.escape(n)}'>{html.escape(disp)}</a>"
                        f"<span>{kb}</span>")
        body = f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<title>📄 폰서버 페이지</title>
<style>body{{background:#1e1e2e;color:#fff;font-family:"Noto Sans CJK KR",sans-serif;
max-width:640px;margin:0 auto;padding:18px}}h1{{font-size:20px}}
.sub{{color:#898781;font-size:12px;margin-bottom:14px}}
a{{color:#3987e5;text-decoration:none;font-size:16px}}
div.row{{display:flex;justify-content:space-between;padding:11px 4px;
border-bottom:1px solid #313244}}span{{color:#898781;font-size:12px}}
.empty{{color:#898781;padding:20px;text-align:center}}</style>
<h1>📄 폰서버 페이지 호스팅</h1>
<div class=sub>~/pages/ · scp로 HTML 올리면 여기 자동 등록</div>
{''.join(f"<div class=row>{r}</div>" for r in rows) or "<div class=empty>아직 페이지 없음</div>"}"""
        enc = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(enc)))
        self.end_headers()
        self.wfile.write(enc)
        return None


if __name__ == "__main__":
    print(f"[pageserve] http://0.0.0.0:{PORT}  root={ROOT}")
    try:
        ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
    except OSError as e:
        print(f"포트 {PORT} 사용 불가({e})")
        sys.exit(1)
