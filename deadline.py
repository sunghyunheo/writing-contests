"""공모전 설명문에서 접수 마감일을 뽑아낸다.

마감일을 잘못 읽으면 실제 마감을 놓치게 되므로, 규칙은 보수적으로 잡는다.
확신이 서지 않으면 None 을 돌려주고 화면에는 "일정 확인 필요" 로 표시한다.
추측한 날짜를 채우지 않는 것이 이 모듈의 목적이다.
"""
from __future__ import annotations

import re
from datetime import date

# 2026. 08. 19 / 2026-08-19 / 2026년 8월 19일 / 2026.8.19
FULL = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
# 8월 19일 / 08.19 (연도 없음 — 앞쪽 날짜에서 연도를 물려받는다)
PARTIAL = re.compile(r"(?<!\d)(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?")

# 접수 기간을 가리키는 말. 이 말이 있는 구간만 마감일 후보로 본다.
PERIOD_HINT = re.compile(r"접수\s*기간|응모\s*기간|공모\s*기간|모집\s*기간|접수|응모|제출|마감|까지")
# 마감이 아닌 날짜를 걸러낸다 (시상식·발표·개최일 등).
NOT_DEADLINE = re.compile(r"발표|시상|당선|심사|개최\s*일시|행사|공고일|등록일|작성일")


def _as_date(y: int, m: int, d: int):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _dates_in(text: str) -> list:
    """텍스트에서 (위치, date) 목록을 순서대로 뽑는다. 연도 없는 날짜는 직전 연도를 물려받는다."""
    found = []
    for m in FULL.finditer(text):
        dt = _as_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if dt:
            found.append((m.start(), m.end(), dt))

    if not found:
        return []

    # 연도 없는 날짜: 바로 앞에 나온 완전한 날짜의 연도를 쓴다.
    spans = [(s, e) for s, e, _ in found]
    for m in PARTIAL.finditer(text):
        if any(s <= m.start() < e for s, e in spans):
            continue  # 이미 완전한 날짜의 일부다
        prior = [d for s, _, d in found if s < m.start()]
        if not prior:
            continue
        year = prior[-1].year
        dt = _as_date(year, int(m.group(1)), int(m.group(2)))
        if not dt:
            continue
        # 연말~연초로 넘어가는 기간 (12월 ~ 1월) 은 다음 해로 본다.
        if dt < prior[-1]:
            dt = _as_date(year + 1, int(m.group(1)), int(m.group(2))) or dt
        found.append((m.start(), m.end(), dt))

    found.sort(key=lambda x: x[0])
    return [(s, d) for s, _, d in found]


def extract(text: str, today: date | None = None):
    """(마감일, 근거 문구) 또는 (None, 이유) 를 돌려준다.

    규칙:
      1) '~' 로 이어진 기간 표현에서 '~' 뒤의 날짜를 마감일로 본다.
      2) '까지' / '마감' 바로 앞의 날짜를 마감일로 본다.
      3) 위 둘이 없으면 판정하지 않는다 (None).
    발표일·시상식 날짜만 있는 글에서 날짜를 끌어오지 않도록 문맥을 함께 본다.
    """
    if not text:
        return None, "설명 없음"
    today = today or date.today()
    flat = re.sub(r"\s+", " ", text)

    # 1) 기간 표현: <날짜> ~ <날짜>
    for m in re.finditer(r"[~∼〜]\s*", flat):
        window = flat[max(0, m.start() - 90) : m.start()]
        after = flat[m.end() : m.end() + 40]
        if NOT_DEADLINE.search(window) and not PERIOD_HINT.search(window):
            continue
        tail = _dates_in(flat[max(0, m.start() - 90) : m.end() + 40])
        if len(tail) < 2:
            continue
        deadline = tail[-1][1]
        if deadline >= today.replace(year=today.year - 1):
            return deadline, ("기간 표현: …" + window[-40:] + "~" + after[:20]).strip()

    # 2) '<날짜> 까지' / '<날짜> 마감' — 날짜가 키워드 앞에 오는 형태
    for kw in ("까지", "마감"):
        for m in re.finditer(kw, flat):
            window = flat[max(0, m.start() - 60) : m.start()]
            if NOT_DEADLINE.search(window) and not PERIOD_HINT.search(window):
                continue
            dts = _dates_in(window)
            if not dts:
                continue
            deadline = dts[-1][1]
            if deadline >= today.replace(year=today.year - 1):
                return deadline, ("'{}' 앞: …{}".format(kw, window[-45:])).strip()

    # 3) '마감 <날짜>' / '마감일 <날짜>' — 날짜가 키워드 뒤에 오는 형태
    for m in re.finditer(r"(접수|응모|공모|제출)?\s*마감(일|일자)?\s*[:：]?\s*", flat):
        after = flat[m.end() : m.end() + 40]
        dts = _dates_in(after)
        if not dts:
            continue
        deadline = dts[0][1]
        if deadline >= today.replace(year=today.year - 1):
            return deadline, ("'마감' 뒤: {}…".format(after[:45])).strip()

    return None, "마감일 표현을 찾지 못함"
