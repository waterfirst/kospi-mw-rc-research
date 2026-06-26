#!/usr/bin/env python3
"""
KOSPI 가격·수급 데이터 수집 (네이버 금융) — 백테스트 재현용
=============================================================
2026-06-26 | Claude

수집:
  · data/kospi_price.csv : 일별 OHLCV (네이버 siseJson)
  · data/kospi_flow.csv  : 일별 개인·외국인·기관 순매매 (네이버 investorDealTrendDay)

사용:
  python3 fetch_data.py            # 기본 구간 수집
  (네트워크 차단 환경에서는 실패 → 정상 환경 PC에서 실행)
"""
import requests, re, csv, json, time, os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(OUT_DIR, exist_ok=True)

HEAD = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.naver.com/'}


def fetch_price(start="20240101", end="20260626"):
    """KOSPI 일별 OHLCV"""
    url = (f"https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           f"&requestType=1&startTime={start}&endTime={end}&timeframe=day")
    r = requests.get(url, timeout=30, headers=HEAD)
    rows = json.loads(r.text.strip().replace("'", '"'))
    path = os.path.join(OUT_DIR, 'kospi_price.csv')
    with open(path, 'w') as f:
        csv.writer(f).writerows(rows)
    print(f"가격: {len(rows)-1}일 → {path}")
    return len(rows) - 1


def fetch_flow(max_pages=80):
    """일별 투자자별 순매매 (개인/외국인/기관). 페이징으로 과거까지."""
    s = requests.Session(); s.headers.update(HEAD)
    allrows = {}
    empty = 0
    for page in range(1, max_pages + 1):
        url = (f"https://finance.naver.com/sise/investorDealTrendDay.naver"
               f"?bizdate=20260626&sosok=01&page={page}")
        r = s.get(url, timeout=20); r.encoding = 'euc-kr'
        found = False
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', r.text, re.S):
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
            c = [re.sub(r'<[^>]+>', '', x).replace('&nbsp;', '').replace(',', '').strip()
                 for x in cells]
            if c and re.match(r'\d{2}\.\d{2}\.\d{2}$', c[0]):
                try:
                    d = '20' + c[0].replace('.', '')
                    allrows[d] = (int(c[1]), int(c[2]), int(c[3]))  # 개인,외국인,기관
                    found = True
                except (ValueError, IndexError):
                    pass
        empty = 0 if found else empty + 1
        if empty >= 3:
            break
        time.sleep(0.15)
    path = os.path.join(OUT_DIR, 'kospi_flow.csv')
    dates = sorted(allrows)
    with open(path, 'w') as f:
        w = csv.writer(f); w.writerow(['date', 'individual', 'foreign', 'institution'])
        for d in dates:
            w.writerow([d, *allrows[d]])
    print(f"수급: {len(dates)}일 ({dates[0]}~{dates[-1]}) → {path}")
    return len(dates)


if __name__ == '__main__':
    try:
        fetch_price()
        fetch_flow()
        print("완료. python3 MODEL_v5_backtest.py 로 백테스트 실행.")
    except Exception as e:
        print(f"수집 실패 (네트워크 차단?): {type(e).__name__}: {e}")
        print("정상 네트워크 PC에서 재실행하세요.")
