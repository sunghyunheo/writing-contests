"""deadline.extract 검증 — 실제 RSS 문구와, 오판하기 쉬운 사례들."""
import sys
from datetime import date

from deadline import extract

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TODAY = date(2026, 9, 3)

# (설명문, 기대 마감일 or None)
CASES = [
    # --- 실제 RSS 문구
    ("접수 기간 2026년 08월 19일(수) ~ 10월 31일(토) 참여 대상 전 연령", date(2026, 10, 31)),
    ("접수기간 2026. 08. 18 (화) ~ 2026. 09. 18 (금) 16시까지", date(2026, 9, 18)),
    ("문학광장 제121기 신인문학상 공모전 (2026.9.1~9.25)", date(2026, 9, 25)),
    # --- 마감일이 아닌 날짜만 있는 경우 → 뽑지 말아야 한다
    ("■ 개최일시 2026. 10. 16. (금) ■ 개최장소 김유정문학촌", None),
    ("당선작 발표 2027. 1. 1. 시상식 2027. 1. 20.", None),
    # --- '까지' 표현
    ("응모 원고는 2026년 12월 5일까지 제출해야 합니다.", date(2026, 12, 5)),
    ("접수 마감 2026. 11. 30.", date(2026, 11, 30)),
    # --- 연말→연초로 넘어가는 기간
    ("접수기간 2026. 12. 20 ~ 1. 5", date(2027, 1, 5)),
    # --- 날짜가 아예 없음
    ("자세한 일정은 추후 공고", None),
    ("", None),
]


def main() -> int:
    fails = 0
    for text, expected in CASES:
        got, why = extract(text, today=TODAY)
        ok = got == expected
        if not ok:
            fails += 1
        print("{}  기대={} 실제={}".format("PASS" if ok else "FAIL", expected, got))
        print("      입력: {}".format(text[:72] or "(빈 문자열)"))
        if not ok:
            print("      근거: {}".format(why))
    print("\n{}/{} 통과".format(len(CASES) - fails, len(CASES)))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
