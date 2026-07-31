#!/usr/bin/env python3
"""출퇴근 날씨 카드 이미지 생성 + 텔레그램 전송.

- 날씨: Open-Meteo (무료, API키 불필요, stdlib urllib)
- 위치: WEATHER_LAT/WEATHER_LON(.env) → 없으면 termux-location(GPS) → 서울 폴백
- 이미지: Pillow (Termux: pkg install python-pillow)
- 한글 폰트: /system/fonts (삼성 기본) 등에서 자동 탐색

사용:
  python weather_card.py            # 카드 생성만 (weather.png)
  python weather_card.py --telegram # 생성 + 텔레그램 전송
  WEATHER_MORNING=5 WEATHER_EVENING=18  # 출근/퇴근 시각(기본 5,18)
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

MORNING = int(os.environ.get("WEATHER_MORNING", "5"))   # 05시대 (출근 05:30)
EVENING = int(os.environ.get("WEATHER_EVENING", "18"))  # 18시대 (퇴근 18:00)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather.png")

# --- 색상 (Catppuccin Mocha 다크테마) ---
BG = (30, 30, 46)
CARD = (24, 24, 37)
INK = (255, 255, 255)
INK2 = (195, 194, 183)
MUTED = (137, 135, 129)
BLUE = (57, 135, 229)
AQUA = (25, 158, 112)
YELLOW = (201, 133, 0)
RED = (230, 103, 103)
LINE = (49, 50, 68)

# WMO weathercode → (아이콘종류, 한글).  아이콘은 PIL로 직접 그림(폰트 무관).
WMO = {
    0: ("sun", "맑음"), 1: ("sun", "대체로 맑음"), 2: ("partly", "구름 조금"),
    3: ("cloud", "흐림"), 45: ("fog", "안개"), 48: ("fog", "짙은 안개"),
    51: ("rain", "약한 이슬비"), 53: ("rain", "이슬비"), 55: ("rain", "강한 이슬비"),
    61: ("rain", "약한 비"), 63: ("rain", "비"), 65: ("rain", "강한 비"),
    66: ("snow", "어는 비"), 67: ("snow", "강한 어는 비"),
    71: ("snow", "약한 눈"), 73: ("snow", "눈"), 75: ("snow", "강한 눈"),
    77: ("snow", "싸락눈"), 80: ("rain", "소나기"), 81: ("rain", "소나기"),
    82: ("storm", "강한 소나기"), 85: ("snow", "약한 눈보라"), 86: ("snow", "눈보라"),
    95: ("storm", "뇌우"), 96: ("storm", "우박 뇌우"), 99: ("storm", "강한 우박 뇌우"),
}

FONT_DIRS = [
    "/system/fonts",  # 삼성 노트10 기본 (한글 포함)
    "/data/data/com.termux/files/usr/share/fonts",
    "/usr/share/fonts/truetype/nanum",
    "/usr/share/fonts",
]
FONT_HINTS = ["NotoSansCJK", "NotoSansKR", "NanumGothic", "SamsungKorean",
              "SECRobotoLight", "Roboto", "DroidSans", "DejaVuSans"]


def find_font():
    import glob
    cands = []
    for d in FONT_DIRS:
        for ext in ("ttf", "ttc", "otf"):
            cands += glob.glob(os.path.join(d, f"**/*.{ext}"), recursive=True)
    for hint in FONT_HINTS:  # 한글 지원 우선순위
        for c in cands:
            if hint.lower() in os.path.basename(c).lower():
                return c
    return cands[0] if cands else None


FONT_PATH = find_font()


def font(sz):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def get_location():
    lat = os.environ.get("WEATHER_LAT")
    lon = os.environ.get("WEATHER_LON")
    if lat and lon:
        return float(lat), float(lon), os.environ.get("WEATHER_PLACE", "")
    # GPS 시도 (폰)
    try:
        p = subprocess.run(["termux-location", "-p", "network"],
                           capture_output=True, text=True, timeout=20)
        d = json.loads(p.stdout)
        return d["latitude"], d["longitude"], ""
    except Exception:
        return 37.5665, 126.9780, "서울"  # 폴백


def fetch_weather(lat, lon):
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,precipitation_probability,"
                  "weathercode,windspeed_10m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Seoul", "forecast_days": 1,
    })
    url = "https://api.open-meteo.com/v1/forecast?" + q
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def slot(data, hour):
    h = data["hourly"]
    times = h["time"]
    idx = hour
    for i, t in enumerate(times):
        if int(t[11:13]) == hour:
            idx = i
            break
    code = h["weathercode"][idx]
    icon, desc = WMO.get(code, ("cloud", "―"))
    return {
        "time": f"{hour:02d}:00",
        "temp": round(h["temperature_2m"][idx]),
        "feels": round(h["apparent_temperature"][idx]),
        "pop": h["precipitation_probability"][idx] or 0,
        "wind": round(h["windspeed_10m"][idx]),
        "desc": desc, "icon": icon, "code": code,
    }


# --- 날씨 아이콘을 벡터로 직접 그림 (이모지 폰트 불필요) ---
SUN = (255, 200, 60)
CLOUD_C = (210, 214, 228)
CLOUD_D = (150, 156, 178)
RAINC = (110, 170, 240)
SNOWC = (225, 235, 255)
BOLT = (255, 214, 90)


def draw_icon(d, cx, cy, kind, s=1.0):
    """cx,cy 중심에 날씨 아이콘. s=크기 배율."""
    def circle(x, y, r, fill):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def sun(x, y, r, rays=True):
        if rays:
            import math
            for a in range(0, 360, 45):
                rad = math.radians(a)
                x1 = x + math.cos(rad) * (r + 6 * s)
                y1 = y + math.sin(rad) * (r + 6 * s)
                x2 = x + math.cos(rad) * (r + 16 * s)
                y2 = y + math.sin(rad) * (r + 16 * s)
                d.line([x1, y1, x2, y2], fill=SUN, width=max(2, int(4 * s)))
        circle(x, y, r, SUN)

    def cloud(x, y, col=CLOUD_C):
        r = 26 * s
        circle(x - 22 * s, y, r * 0.8, col)
        circle(x + 22 * s, y, r * 0.85, col)
        circle(x, y - 14 * s, r, col)
        d.rounded_rectangle([x - 40 * s, y - 4 * s, x + 42 * s, y + 24 * s],
                            int(20 * s), fill=col)

    if kind == "sun":
        sun(cx, cy, 34 * s)
    elif kind == "partly":
        sun(cx - 26 * s, cy - 22 * s, 24 * s, rays=True)
        cloud(cx + 6 * s, cy + 6 * s)
    elif kind == "cloud":
        cloud(cx, cy - 4 * s, CLOUD_D)
        cloud(cx + 6 * s, cy + 4 * s, CLOUD_C)
    elif kind == "fog":
        cloud(cx, cy - 12 * s, CLOUD_D)
        for i in range(3):
            yy = cy + 20 * s + i * 12 * s
            d.line([cx - 40 * s, yy, cx + 42 * s, yy], fill=CLOUD_C,
                   width=max(2, int(4 * s)))
    elif kind == "rain":
        cloud(cx, cy - 14 * s, CLOUD_D)
        for i in range(4):
            xx = cx - 30 * s + i * 20 * s
            d.line([xx, cy + 22 * s, xx - 6 * s, cy + 42 * s], fill=RAINC,
                   width=max(2, int(4 * s)))
    elif kind == "snow":
        cloud(cx, cy - 14 * s, CLOUD_D)
        for i in range(4):
            xx = cx - 30 * s + i * 20 * s
            circle(xx, cy + 32 * s, 4 * s, SNOWC)
    elif kind == "storm":
        cloud(cx, cy - 14 * s, CLOUD_D)
        d.polygon([(cx - 4 * s, cy + 20 * s), (cx + 14 * s, cy + 20 * s),
                   (cx + 2 * s, cy + 38 * s), (cx + 10 * s, cy + 38 * s),
                   (cx - 10 * s, cy + 62 * s), (cx - 2 * s, cy + 40 * s),
                   (cx - 16 * s, cy + 40 * s)], fill=BOLT)


def draw_card(place, mo, ev, tmax, tmin):
    W, H = 900, 620
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    def text(xy, s, f, fill, anchor="la"):
        d.text(xy, s, font=f, fill=fill, anchor=anchor)

    # 헤더
    today = datetime.now().strftime("%Y년 %m월 %d일 (%a)")
    text((40, 34), "오늘의 출퇴근 날씨", font(40), INK)
    head = today + (f"  ·  {place}" if place else "")
    text((40, 88), head, font(24), MUTED)
    text((W - 40, 40), f"최고 {tmax}°  최저 {tmin}°", font(26), INK2, anchor="ra")

    # 두 개 패널 (출근 / 퇴근)
    panels = [("출근", "05:30", mo, BLUE), ("퇴근", "18:00", ev, YELLOW)]
    pw, ph, gap = (W - 80 - 30) // 2, 380, 30
    for i, (label, clock, s, accent) in enumerate(panels):
        x = 40 + i * (pw + gap)
        y = 140
        d.rounded_rectangle([x, y, x + pw, y + ph], 20, fill=CARD)
        d.rounded_rectangle([x, y, x + pw, y + 8], 4, fill=accent)  # 상단 컬러바
        cx = x + pw // 2
        text((x + 28, y + 30), label, font(30), INK)
        text((x + pw - 28, y + 34), clock, font(26), MUTED, anchor="ra")
        draw_icon(d, cx, y + 130, s["icon"], s=1.15)  # 벡터 아이콘
        text((cx, y + 195), f"{s['temp']}°", font(84), INK, anchor="ma")
        text((cx, y + 292), s["desc"], font(30), INK2, anchor="ma")
        # 하단 3지표
        yb = y + 335
        for j, (k, v) in enumerate([("체감", f"{s['feels']}°"),
                                    ("강수", f"{s['pop']}%"),
                                    ("바람", f"{s['wind']}m/s")]):
            bx = x + 28 + j * ((pw - 56) // 3) + (pw - 56) // 6
            col = RED if (k == "강수" and s["pop"] >= 60) else INK2
            text((bx, yb), k, font(20), MUTED, anchor="ma")
            text((bx, yb + 26), v, font(26), col, anchor="ma")

    # 우산 안내 배너
    pmax = max(mo["pop"], ev["pop"])
    if pmax >= 60:
        msg, col = f"우산 꼭 챙기세요  ·  강수확률 {pmax}%", RED
    elif pmax >= 30:
        msg, col = f"우산을 챙기면 좋아요  ·  강수확률 {pmax}%", YELLOW
    else:
        msg, col = "우산 없이 좋은 날이에요", AQUA
    by = 540
    d.rounded_rectangle([40, by, W - 40, by + 56], 14, fill=CARD)
    d.ellipse([64, by + 22, 76, by + 34], fill=col)  # 상태 점
    text((W // 2 + 8, by + 28), msg, font(28), col, anchor="mm")
    img.save(OUT)
    return OUT


def send_telegram(path, caption):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("텔레그램 토큰/챗ID 없음(.env) → 전송 생략")
        return False
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    boundary = "----wxcard"
    with open(path, "rb") as f:
        photo = f.read()
    parts = []
    for k, v in [("chat_id", chat), ("caption", caption)]:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
                 f"filename=\"weather.png\"\r\nContent-Type: image/png\r\n\r\n".encode()
                 + photo + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ok = json.load(r).get("ok")
            print("텔레그램 전송", "성공" if ok else "실패")
            return ok
    except Exception as e:
        print("텔레그램 전송 오류:", e)
        return False


def main():
    lat, lon, place = get_location()
    data = fetch_weather(lat, lon)
    mo = slot(data, MORNING)
    ev = slot(data, EVENING)
    tmax = round(data["daily"]["temperature_2m_max"][0])
    tmin = round(data["daily"]["temperature_2m_min"][0])
    path = draw_card(place, mo, ev, tmax, tmin)
    print("생성:", path)
    if "--telegram" in sys.argv:
        cap = (f"오늘 출퇴근 날씨\n"
               f"출근 {mo['time']}  {mo['temp']}° {mo['desc']} 강수{mo['pop']}%\n"
               f"퇴근 {ev['time']}  {ev['temp']}° {ev['desc']} 강수{ev['pop']}%")
        send_telegram(path, cap)


if __name__ == "__main__":
    main()
