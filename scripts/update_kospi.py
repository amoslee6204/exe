"""Yahoo Finance에서 코스피(^KS11) 현재가와 전일 종가를 받아 kospi.json으로 저장한다.

브라우저에서는 CORS 때문에 Yahoo를 직접 호출할 수 없으므로,
GitHub Actions가 이 스크립트를 주기적으로 실행해 같은 사이트에 JSON을 올려 둔다.
표준 라이브러리만 사용한다.
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?range=5d&interval=1d"
OUT = Path(__file__).resolve().parent.parent / "kospi.json"
KST = timezone(timedelta(hours=9))


def kst_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception as e:  # 일시적 실패 시 기존 파일을 그대로 둔다
        print(f"fetch failed: {e}", file=sys.stderr)
        return 0

    res = data["chart"]["result"][0]
    meta = res["meta"]
    bars = [
        (ts, c)
        for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"])
        if c is not None
    ]
    if len(bars) < 2:
        print("not enough data", file=sys.stderr)
        return 0

    # 마지막 봉 = 가장 최근 거래일(장중이면 오늘), 그 앞 봉 = 전 거래일
    (cur_ts, _), (prev_ts, prev_close) = bars[-1], bars[-2]
    current = float(meta.get("regularMarketPrice") or bars[-1][1])
    change = current - prev_close

    result = {
        "name": "KOSPI",
        "current": {"date": kst_date(cur_ts), "value": round(current, 2)},
        "previous": {"date": kst_date(prev_ts), "value": round(prev_close, 2)},
        "change": round(change, 2),
        "changePct": round(change / prev_close * 100, 2),
        "asOf": datetime.fromtimestamp(meta["regularMarketTime"], KST).strftime("%Y-%m-%d %H:%M"),
        "source": "Yahoo Finance",
    }

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
        print("no change")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
