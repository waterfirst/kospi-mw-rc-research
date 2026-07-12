#!/usr/bin/env python3
"""갤럭시 노트10 Termux 센서/카메라 대시보드 서버 (stdlib 전용).

실행:  python server.py [포트]   (기본 8080)
접속:  http://<폰IP>:8080  (같은 공유기 LAN에서)

termux-api 명령이 실패/멈춤이어도 서버는 죽지 않고
원인 힌트를 JSON으로 돌려준다.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
TMP = "/data/data/com.termux/files/usr/tmp"
if not os.path.isdir(TMP):
    TMP = "/tmp"

# ---------------------------------------------------------------- termux-api
def run_cmd(cmd, timeout=12):
    """termux-* 명령 실행. (ok, data|hint) 반환. 절대 예외를 던지지 않는다."""
    if shutil.which(cmd[0]) is None:
        return False, f"'{cmd[0]}' 없음 → pkg install termux-api 실행 필요"
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, (f"'{' '.join(cmd)}' {timeout}초 초과 → Termux:API 앱 미설치"
                       "(F-Droid에서 Termux와 같은 출처로 설치) 또는 해당 권한 미허용")
    if p.returncode != 0:
        return False, (p.stderr or p.stdout or "unknown").strip()[:300]
    return True, p.stdout


def run_json(cmd, timeout=12):
    ok, out = run_cmd(cmd, timeout)
    if not ok:
        return False, out
    try:
        return True, json.loads(out) if out.strip() else {}
    except ValueError:
        return False, f"JSON 파싱 실패: {out[:200]}"


# 센서 이름은 기기마다 다름 → 최초 1회 목록에서 키워드로 실제 이름 해석
_sensor_names = {}
_sensor_lock = threading.Lock()

def resolve_sensors():
    with _sensor_lock:
        if _sensor_names:
            return _sensor_names
        ok, data = run_json(["termux-sensor", "-l"])
        if not ok:
            return {}
        names = data.get("sensors", [])
        def pick(*kws):
            for n in names:
                low = n.lower()
                if all(k in low for k in kws) and "uncalibrated" not in low:
                    return n
            return None
        _sensor_names.update({k: v for k, v in {
            "accel": pick("accelerometer"),
            "gyro": pick("gyroscope"),
            "light": pick("light"),
            "proximity": pick("proximity"),
            "magnet": pick("magnetic"),
            "pressure": pick("pressure"),
        }.items() if v})
        return _sensor_names


def read_sensors():
    names = resolve_sensors()
    if not names:
        return False, "센서 목록 조회 실패 (termux-sensor -l) → Termux:API 확인"
    ok, data = run_json(["termux-sensor", "-s", ",".join(names.values()), "-n", "1"],
                        timeout=15)
    if not ok:
        return False, data
    out = {}
    for key, real in names.items():
        for k, v in data.items():
            if k == real or k.startswith(real):
                out[key] = v.get("values", [])
                break
    return True, out


def sysinfo():
    info = {"time": time.strftime("%H:%M:%S"), "host": socket.gethostname()}
    try:
        with open("/proc/meminfo") as f:
            m = dict(re.findall(r"(\w+):\s+(\d+)", f.read()))
        info["mem_used_pct"] = round(
            100 * (1 - int(m["MemAvailable"]) / int(m["MemTotal"])), 1)
    except Exception:
        pass
    try:
        with open("/proc/uptime") as f:
            info["uptime_h"] = round(float(f.read().split()[0]) / 3600, 1)
    except Exception:
        pass
    try:
        info["load1"] = round(os.getloadavg()[0], 2)
        info["cpu_n"] = os.cpu_count()
    except Exception:
        pass
    return info


def doctor():
    """설치/권한 상태 자가진단."""
    checks = []
    def add(name, ok, hint=""):
        checks.append({"name": name, "ok": bool(ok), "hint": "" if ok else hint})

    add("python", True)
    has_pkg = shutil.which("termux-battery-status") is not None
    add("termux-api 패키지", has_pkg, "pkg install termux-api")
    if has_pkg:
        ok, _ = run_json(["termux-battery-status"], timeout=8)
        add("Termux:API 앱 응답", ok,
            "F-Droid에서 Termux:API 앱 설치(Play스토어 Termux와 혼용 금지, 서명 불일치)")
        ok2, d = run_json(["termux-camera-info"], timeout=8)
        add("카메라 접근", ok2 and bool(d),
            "설정→앱→Termux:API→권한→카메라 허용")
        oks, _ = run_json(["termux-sensor", "-l"], timeout=8)
        add("센서 접근", oks, "Termux:API 앱 재설치 또는 termux-api 업데이트")
    add("wake-lock 권장", shutil.which("termux-wake-lock") is not None,
        "termux-wake-lock 실행(백그라운드 종료 방지)")
    try:
        rel = int(subprocess.run(["getprop", "ro.build.version.release"],
                                 capture_output=True, text=True, timeout=5)
                  .stdout.strip() or 0)
    except Exception:
        rel = 0
    add(f"Android {rel} phantom killer", rel < 12,
        "Android 12+: PC에서 adb shell settings put global "
        "settings_enable_monitor_phantom_procs false (프로세스 강제종료 방지)")
    return checks


# ------------------------------------------------------------------- HTTP
def take_photo(cam="0"):
    path = os.path.join(TMP, f"cam{cam}.jpg")
    if os.path.exists(path):
        os.remove(path)
    ok, err = run_cmd(["termux-camera-photo", "-c", cam, path], timeout=25)
    if ok and os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            return True, f.read()
    return False, (err if not ok else
                   "촬영 실패 → Termux:API 카메라 권한 확인, 화면 켠 상태에서 재시도")


def load_token():
    """접근 토큰: 환경변수 PHONE_TOKEN 또는 ~/.phone_token / repo/.phone_token.
    미설정이면 '' → 게이트 비활성(하위호환)."""
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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 조용히
        pass

    def end_headers(self):
        c = getattr(self, "_cookie", None)
        if c:
            self.send_header("Set-Cookie", c)
            self._cookie = None
        super().end_headers()

    def _gate(self):
        """토큰 검사. ?k=토큰 최초 접속 시 쿠키 저장 → 이후 무프롬프트."""
        if not TOKEN:
            return True
        if ("pt=" + TOKEN) in self.headers.get("Cookie", ""):
            return True
        if parse_qs(urlparse(self.path).query).get("k", [""])[0] == TOKEN:
            self._cookie = ("pt=" + TOKEN +
                            "; Max-Age=31536000; HttpOnly; SameSite=Lax; Path=/")
            return True
        return False

    def _deny(self):
        body = ("<meta charset=utf-8><body style='font-family:sans-serif;background:#1e1e2e;"
                "color:#fff;text-align:center;padding-top:20%'><h2>🔒 접근 토큰 필요</h2>"
                "<p>주소 뒤에 <b>?k=토큰</b> 을 붙여 한 번 접속하세요.</p></body>").encode()
        self.send_response(401)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._gate():
            try:
                self._deny()
            except Exception:
                pass
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/":
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif u.path == "/api/status":
                ok, bat = run_json(["termux-battery-status"], timeout=8)
                self._json({"ok": True, "battery": bat if ok else None,
                            "battery_err": None if ok else bat, "sys": sysinfo()})
            elif u.path == "/api/sensors":
                ok, data = read_sensors()
                self._json({"ok": ok, "data" if ok else "error": data})
            elif u.path == "/api/doctor":
                self._json({"ok": True, "checks": doctor()})
            elif u.path == "/api/photo":
                ok, data = take_photo(q.get("cam", ["0"])[0])
                if ok:
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self._json({"ok": False, "error": data}, 500)
            elif u.path == "/api/torch":
                state = q.get("state", ["off"])[0]
                ok, err = run_cmd(["termux-torch", state], timeout=8)
                self._json({"ok": ok, "error": None if ok else err})
            elif u.path == "/api/vibrate":
                ok, err = run_cmd(["termux-vibrate", "-d", "300"], timeout=8)
                self._json({"ok": ok, "error": None if ok else err})
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # 서버는 절대 죽지 않는다
            try:
                self._json({"ok": False, "error": repr(e)}, 500)
            except Exception:
                pass


HTML = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "dashboard.html"), encoding="utf-8").read()

if __name__ == "__main__":
    ip = "?"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    print(f"[phone-server] http://{ip}:{PORT}  (Ctrl+C 종료)")
    print("[phone-server] 백그라운드 종료 방지: termux-wake-lock 먼저 실행 권장")
    try:
        ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    except OSError as e:
        print(f"포트 {PORT} 사용 불가({e}) → python server.py 8081 로 재시도")
        sys.exit(1)
