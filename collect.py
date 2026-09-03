"""공모전 일정 수집기 — 피드에서 공모전을 모아 마감일을 뽑고 카테고리로 나눈다.

두 종류의 입력을 합친다.
  * contests.json  직접 관리하는 정기 공모 (신춘문예 등). 공고 전이면 status=pending 으로 둔다.
  * sources.json   공모전 정보 RSS. 설명문에서 deadline.py 로 마감일을 추출한다.

마감일을 확신할 수 없으면 비워둔다. 추측 날짜를 채우지 않는다.
표준 라이브러리만 사용한다 (GitHub Actions 에서 pip install 없이 돌기 위함).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

from deadline import extract

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}


# ---------------------------------------------------------------- 피드 읽기

def fetch(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def text_of(el, *paths):
    for path in paths:
        found = el.find(path, NS)
        if found is None:
            continue
        if found.text and found.text.strip():
            return found.text.strip()
        href = found.get("href")
        if href:
            return href.strip()
    return None


def parse_feed(raw: bytes) -> list:
    root = ET.fromstring(raw)
    entries = root.findall(".//item") or root.findall(".//atom:entry", NS)
    out = []
    for el in entries:
        title = strip_html(text_of(el, "title", "atom:title") or "")
        link = text_of(el, "link", "atom:link[@rel='alternate']", "atom:link", "guid")
        if not title or not link:
            continue
        out.append(
            {
                "title": title,
                "url": link,
                "summary": strip_html(
                    text_of(el, "description", "atom:summary", "atom:content") or ""
                ),
                "published": text_of(el, "pubDate", "atom:published", "atom:updated", "dc:date"),
            }
        )
    return out


def posted_on(raw):
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).astimezone(KST).date()
    except Exception:
        return None


# ---------------------------------------------------------------- 분류

def classify(title: str, summary: str, rules: list) -> str:
    """제목으로 먼저 판정하고, 안 걸리면 설명문까지 본다.

    포털 설명문에는 '등단의 길' 같은 홍보 문구가 섞여 있어, 설명문을 같이 보면
    '한컴문학상 일반부'가 학생부로, '독후감 공모전'이 등단으로 잡힌다.
    제목이 훨씬 깨끗하므로 제목을 우선한다.
    """
    for text in (title, title + " " + summary):
        low = text.lower()
        for cat_id, keywords in rules:
            if any(k in low for k in keywords):
                return cat_id
    return ""


def canonical(url: str) -> str:
    return re.sub(r"[?&](utm_[^=]+|fbclid)=[^&]*", "", url).rstrip("?&/").lower()


def name_key(title: str) -> str:
    """회차 표기·괄호를 지운 이름으로 중복을 잡는다."""
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", title)
    t = re.sub(r"제?\s*\d+\s*[회기차]", " ", t)
    return "".join(ch for ch in t.lower() if ch.isalnum())[:40]


# ---------------------------------------------------------------- 상태 판정

def status_of(deadline, today: date, imminent_days: int) -> tuple:
    """(status, dday) — deadline 이 없으면 확인 필요로 둔다."""
    if deadline is None:
        return "unknown", None
    dday = (deadline - today).days
    if dday < 0:
        return "closed", dday
    if dday <= imminent_days:
        return "imminent", dday
    return "open", dday


def main() -> int:
    cfg = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    curated = json.loads((ROOT / "contests.json").read_text(encoding="utf-8"))
    s = cfg["settings"]
    now = datetime.now(KST)
    today = now.date()

    ranked = sorted(cfg["categories"], key=lambda c: c.get("priority", 50))
    rules = [(c["id"], [k.lower() for k in c["match"]]) for c in ranked]

    buckets = {c["id"]: [] for c in cfg["categories"]}
    feed_log = []
    seen_urls, seen_names = set(), set()

    def add(entry: dict) -> bool:
        ukey, nkey = canonical(entry["url"]), name_key(entry["name"])
        if ukey in seen_urls or (len(nkey) > 10 and nkey in seen_names):
            return False
        seen_urls.add(ukey)
        seen_names.add(nkey)
        buckets.setdefault(entry["category"], []).append(entry)
        return True

    # 1) 직접 관리 목록 — 카테고리가 지정돼 있으므로 분류하지 않는다.
    for c in curated["contests"]:
        deadline = date.fromisoformat(c["deadline"]) if c.get("deadline") else None
        status, dday = status_of(deadline, today, s["imminent_days"])
        if c.get("status") == "pending":
            status, dday = "pending", None
        add(
            {
                "name": c["name"],
                "category": c.get("category", "etc"),
                "host": c.get("host", ""),
                "url": c["url"],
                "deadline": c["deadline"] if c.get("deadline") else None,
                "deadline_note": c.get("deadline_note", ""),
                "window": c.get("window", ""),
                "prize": c.get("prize", ""),
                "note": c.get("note", ""),
                "source": c.get("source", ""),
                "checked": c.get("checked", ""),
                "origin": "curated",
                "status": status,
                "dday": dday,
                "evidence": "직접 확인" if c.get("status") == "confirmed" else "",
            }
        )
    print("직접 관리 목록: {}건".format(len(curated["contests"])))

    # 2) 공모전 RSS — 설명문에서 마감일을 추출한다.
    for feed in cfg["feeds"]:
        log = {"name": feed["name"], "url": feed["url"]}
        try:
            items = parse_feed(fetch(feed["url"], s["request_timeout_sec"]))
        except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as exc:
            log.update(ok=False, count=0, error="{}: {}".format(type(exc).__name__, exc))
            feed_log.append(log)
            print("  [FAIL] {}: {}".format(feed["name"], log["error"]), file=sys.stderr)
            continue

        kept = dated = 0
        for it in items[: s["max_items_per_feed"]]:
            blob = it["title"] + " " + it["summary"]
            cat = classify(it["title"], it["summary"], rules)
            if not cat:
                continue
            deadline, evidence = extract(blob, today=today)
            status, dday = status_of(deadline, today, s["imminent_days"])
            # 한참 지난 공모는 버린다.
            if deadline and dday is not None and dday < -s["keep_closed_days"]:
                continue
            if add(
                {
                    "name": it["title"],
                    "category": cat,
                    "host": feed["name"],
                    "url": it["url"],
                    "deadline": deadline.isoformat() if deadline else None,
                    "deadline_note": "",
                    "window": "",
                    "prize": "",
                    "note": "" if deadline else "피드 설명에서 마감일을 읽지 못했다 — 공고 원문 확인 필요",
                    "source": "",
                    "checked": "",
                    "origin": "feed",
                    "status": status,
                    "dday": dday,
                    "evidence": evidence if deadline else "",
                    "summary": it["summary"][:300],
                    "posted": (posted_on(it["published"]) or today).isoformat(),
                }
            ):
                kept += 1
                dated += 1 if deadline else 0

        log.update(ok=True, count=kept, dated=dated, error=None)
        feed_log.append(log)
        print("  [feed] {}: {}건 (마감일 확인 {}건)".format(feed["name"], kept, dated))

    # 3) 뉴스 피드 — 새 공고를 놓치지 않기 위한 보조 목록 (일정은 넣지 않는다).
    news = []
    news_seen = set()
    for feed in cfg.get("news_feeds", []):
        log = {"name": "[뉴스] " + feed["name"], "url": feed["url"]}
        try:
            items = parse_feed(fetch(feed["url"], s["request_timeout_sec"]))
        except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as exc:
            log.update(ok=False, count=0, error="{}: {}".format(type(exc).__name__, exc))
            feed_log.append(log)
            continue
        kept = 0
        for it in items[:12]:
            key = name_key(it["title"])
            if len(key) > 10 and key in news_seen:
                continue
            news_seen.add(key)
            posted = posted_on(it["published"]) or today
            if (today - posted).days > 30:
                continue
            news.append(
                {
                    "title": it["title"],
                    "url": it["url"],
                    "topic": feed["name"],
                    "posted": posted.isoformat(),
                }
            )
            kept += 1
        log.update(ok=True, count=kept, error=None)
        feed_log.append(log)
        print("  [news] {}: {}건".format(feed["name"], kept))

    news.sort(key=lambda x: x["posted"], reverse=True)

    # 4) 정렬 — 마감 임박 순. 마감일 미정은 뒤로 보낸다.
    order = {"imminent": 0, "open": 1, "pending": 2, "unknown": 3, "closed": 4}
    categories = []
    for cat in cfg["categories"]:
        items = buckets.get(cat["id"], [])
        items.sort(
            key=lambda x: (
                order.get(x["status"], 9),
                x["dday"] if x["dday"] is not None else 9999,
                x["name"],
            )
        )
        categories.append(
            {
                "id": cat["id"],
                "label": cat["label"],
                "items": items,
                "counts": {
                    "open": sum(1 for i in items if i["status"] in ("open", "imminent")),
                    "imminent": sum(1 for i in items if i["status"] == "imminent"),
                    "total": len(items),
                },
            }
        )

    flat = [i for c in categories for i in c["items"]]
    payload = {
        "generated_at": now.isoformat(),
        "generated_kst": now.strftime("%Y-%m-%d %H:%M"),
        "today": today.isoformat(),
        "imminent_days": s["imminent_days"],
        "totals": {
            "all": len(flat),
            "open": sum(1 for i in flat if i["status"] in ("open", "imminent")),
            "imminent": sum(1 for i in flat if i["status"] == "imminent"),
            "pending": sum(1 for i in flat if i["status"] == "pending"),
            "unknown": sum(1 for i in flat if i["status"] == "unknown"),
        },
        "categories": categories,
        "news": news[:24],
        "feeds": feed_log,
    }

    (ROOT / "data").mkdir(exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (ROOT / "data" / "latest.json").write_text(text, encoding="utf-8")
    archive = ROOT / "data" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / (today.isoformat() + ".json")).write_text(text, encoding="utf-8")

    t = payload["totals"]
    print(
        "\n총 {}건 · 접수중 {}건 (임박 {}건) · 공고대기 {}건 · 일정확인필요 {}건".format(
            t["all"], t["open"], t["imminent"], t["pending"], t["unknown"]
        )
    )
    return 0 if t["all"] else 1


if __name__ == "__main__":
    sys.exit(main())
