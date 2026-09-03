"""data/latest.json 을 docs/index.html (공모전 마감 트래커) 로 렌더링한다."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://sunghyunheo.github.io/writing-contests/"

STATUS = {
    "imminent": ("마감 임박", "st-hot"),
    "open": ("접수중", "st-open"),
    "pending": ("공고 대기", "st-wait"),
    "unknown": ("일정 확인 필요", "st-unknown"),
    "closed": ("마감", "st-closed"),
}

TEMPLATE = """<title>공모전 마감 트래커</title>
<meta name="description" content="신춘문예·신인문학상·장편공모·웹소설·시나리오 공모전 마감일을 D-Day 순으로 정리한 트래커">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&display=swap">
<style>
:root {
  --paper:#f4f4f6; --card:#ffffff; --ink:#1b1d29; --ink-soft:#5f6274; --rule:#e0e0e6;
  --plum:#6b2d5c; --plum-soft:#f3eaf1;
  --hot:#c0392b; --hot-soft:#fbeae7;
  --warm:#8a6100; --warm-soft:#fdf4e3;
  --cool:#2f5d7c; --cool-soft:#e9f0f5;
  --serif:'Nanum Myeongjo','Batang',serif;
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',sans-serif;
}
@media (prefers-color-scheme:dark) {
  :root:not([data-theme="light"]) {
    --paper:#15161c; --card:#1e202a; --ink:#ececf0; --ink-soft:#9b9eae; --rule:#2c2f3a;
    --plum:#d68fc4; --plum-soft:#2a1d28;
    --hot:#ff8f82; --hot-soft:#3a1e1b; --warm:#e6b657; --warm-soft:#332a16;
    --cool:#8fc0dd; --cool-soft:#1b2833;
  }
}
:root[data-theme="dark"] {
  --paper:#15161c; --card:#1e202a; --ink:#ececeff0; --ink-soft:#9b9eae; --rule:#2c2f3a;
  --plum:#d68fc4; --plum-soft:#2a1d28;
  --hot:#ff8f82; --hot-soft:#3a1e1b; --warm:#e6b657; --warm-soft:#332a16;
  --cool:#8fc0dd; --cool-soft:#1b2833;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.55; }
.wrap { max-width:940px; margin:0 auto; padding:30px 20px 70px; }

header { border-bottom:2px solid var(--ink); padding-bottom:14px; }
h1 { font-family:var(--serif); font-size:1.9rem; font-weight:800; margin:0 0 8px;
     letter-spacing:-.01em; text-wrap:balance; }
.tally { display:flex; flex-wrap:wrap; gap:0; margin:14px 0 0; }
.tally div { padding:0 18px 0 0; margin-right:18px; border-right:1px solid var(--rule); }
.tally div:last-child { border-right:0; }
.tally b { display:block; font-family:var(--serif); font-size:1.5rem; line-height:1.1; }
.tally span { font-size:.72rem; color:var(--ink-soft); letter-spacing:.03em; }
.asof { color:var(--ink-soft); font-size:.76rem; margin:10px 0 0; }

.controls { display:flex; flex-wrap:wrap; gap:8px; margin:24px 0 4px; }
#q { flex:1 1 220px; min-width:170px; padding:9px 12px; border:1px solid var(--rule);
     border-radius:7px; background:var(--card); color:var(--ink); font:inherit; font-size:.9rem; }
.tabs { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0 26px; }
.tab { padding:6px 13px; border:1px solid var(--rule); border-radius:999px; background:var(--card);
       color:var(--ink-soft); font:inherit; font-size:.82rem; cursor:pointer; }
.tab[aria-selected="true"] { background:var(--plum-soft); border-color:var(--plum);
                             color:var(--plum); font-weight:700; }
.tab b { font-weight:700; opacity:.55; }

section { margin-bottom:32px; }
h2 { font-family:var(--serif); font-size:1.12rem; font-weight:700; margin:0 0 10px;
     padding-bottom:7px; border-bottom:1px solid var(--rule);
     display:flex; justify-content:space-between; align-items:baseline; gap:10px; }
h2 span { font-family:var(--sans); color:var(--ink-soft); font-size:.74rem; font-weight:400; }
section.urgent h2 { border-bottom-color:var(--hot); color:var(--hot); }

ul { list-style:none; margin:0; padding:0; }
li { display:grid; grid-template-columns:78px 1fr; gap:14px; align-items:start;
     background:var(--card); border:1px solid var(--rule); border-radius:9px;
     padding:13px 16px; margin-bottom:8px; }
li.hot { border-left:3px solid var(--hot); }
.dday { text-align:center; padding-top:2px; }
.dday .n { display:block; font-family:var(--serif); font-size:1.35rem; font-weight:800;
           line-height:1.05; font-variant-numeric:tabular-nums; }
.dday .n.hot { color:var(--hot); }
.dday .d { display:block; font-size:.68rem; color:var(--ink-soft); margin-top:2px;
           font-variant-numeric:tabular-nums; }
.name { font-family:var(--serif); font-size:1rem; font-weight:700; color:var(--ink);
        text-decoration:none; }
.name:hover { color:var(--plum); text-decoration:underline; }
.meta { margin-top:5px; font-size:.76rem; color:var(--ink-soft);
        display:flex; flex-wrap:wrap; gap:7px; align-items:center; }
.pill { font-size:.68rem; font-weight:700; border-radius:3px; padding:1px 7px; white-space:nowrap; }
.st-hot { color:var(--hot); background:var(--hot-soft); }
.st-open { color:var(--cool); background:var(--cool-soft); }
.st-wait { color:var(--warm); background:var(--warm-soft); }
.st-unknown { color:var(--ink-soft); background:var(--rule); }
.st-closed { color:var(--ink-soft); background:var(--rule); text-decoration:line-through; }
.host { background:var(--plum-soft); color:var(--plum); border-radius:3px; padding:1px 7px; font-size:.7rem; }
.note { margin-top:6px; font-size:.78rem; color:var(--ink-soft); }
.evidence { margin-top:4px; font-size:.68rem; color:var(--ink-soft); opacity:.8; }
.empty { color:var(--ink-soft); font-size:.84rem; padding:8px 0; }

.news li { display:block; padding:10px 14px; }
.news a { font-family:var(--sans); font-size:.88rem; font-weight:600; }

footer { margin-top:44px; padding-top:16px; border-top:1px solid var(--rule);
         color:var(--ink-soft); font-size:.75rem; }
footer a { color:var(--plum); }
footer p { margin:7px 0; }
footer code { background:var(--rule); border-radius:3px; padding:0 4px; font-size:.95em; }
details summary { cursor:pointer; }
.feedgrid { margin-top:8px; font-size:.72rem; columns:2; }
.bad { color:var(--hot); }
:focus-visible { outline:2px solid var(--plum); outline-offset:2px; }
@media (max-width:560px) {
  li { grid-template-columns:62px 1fr; gap:10px; }
  h1 { font-size:1.55rem; }
  .tally div { padding-right:13px; margin-right:13px; }
}
</style>

<div class="wrap">
<header>
  <h1>공모전 마감 트래커</h1>
  <div class="tally">
    <div><b>__OPEN__</b><span>접수중</span></div>
    <div><b>__IMMINENT__</b><span>__IMMDAYS__일 내 마감</span></div>
    <div><b>__PENDING__</b><span>공고 대기</span></div>
    <div><b>__UNKNOWN__</b><span>일정 확인 필요</span></div>
  </div>
  <p class="asof">__TODAY__ 기준 · 자동 갱신 · 전체 __ALL__건</p>
</header>

<div class="controls">
  <input id="q" type="search" placeholder="공모전 검색 (예: 신춘문예, 장편, 시나리오)" autocomplete="off">
</div>
<div class="tabs" role="tablist">__TABS__</div>

__URGENT__
__SECTIONS__
__NEWS__

<footer>
  <p><b>마감일 표기 원칙</b> — 공고에서 확인한 날짜만 D-Day 로 계산합니다.
     피드 설명문에서 마감일을 읽어내지 못하면 날짜를 추측하지 않고
     <span class="pill st-unknown">일정 확인 필요</span> 로 표시합니다.
     <span class="pill st-wait">공고 대기</span> 는 매년 열리지만 올해 공고가 아직 안 난 공모로,
     적어둔 시기는 전년 기준이므로 반드시 원문을 확인하세요.</p>
  <p><b>접수 전 반드시 공고 원문을 확인하세요.</b> 마감 시각(자정 / 오후 6시 등), 분량,
     제출 형식, 응모 자격은 회차마다 달라집니다. 이 페이지는 일정 파악용 요약입니다.</p>
  <details><summary>수집 소스 __FEED_OK__/__FEED_TOTAL__개 정상</summary>
    <div class="feedgrid">__FEEDLOG__</div>
  </details>
  <p><a href="__SITE__">__SITE__</a></p>
</footer>
</div>
<script>
const q = document.getElementById('q');
const tabs = [...document.querySelectorAll('.tab')];
const sections = [...document.querySelectorAll('section[data-cat]')];

function apply() {
  const term = q.value.trim().toLowerCase();
  const cat = tabs.find(t => t.getAttribute('aria-selected') === 'true').dataset.cat;
  for (const sec of sections) {
    const isUrgent = sec.dataset.cat === 'urgent';
    const catMatch = cat === 'all' ? true : (isUrgent ? !term : sec.dataset.cat === cat);
    let shown = 0;
    for (const li of sec.querySelectorAll('li')) {
      const hit = !term || li.dataset.search.includes(term);
      li.hidden = !(catMatch && hit);
      if (!li.hidden) shown++;
    }
    sec.hidden = !catMatch || shown === 0;
    const empty = sec.querySelector('.empty');
    if (empty) empty.hidden = shown > 0;
    const count = sec.querySelector('h2 span');
    if (count && count.dataset.fmt) count.textContent = count.dataset.fmt.replace('#', shown);
  }
}
q.addEventListener('input', apply);
tabs.forEach(t => t.addEventListener('click', () => {
  tabs.forEach(o => o.setAttribute('aria-selected', String(o === t)));
  apply();
}));
apply();
</script>
"""


def dday_cell(item: dict) -> str:
    dday = item.get("dday")
    if dday is None:
        return '<span class="n">–</span><span class="d">미정</span>'
    hot = " hot" if item["status"] == "imminent" or dday < 0 else ""
    label = "D{:+d}".format(dday) if dday else "D-DAY"
    return '<span class="n{}">{}</span><span class="d">{}</span>'.format(
        hot, escape(label), escape(item.get("deadline") or "")
    )


def row(item: dict) -> str:
    label, cls = STATUS.get(item["status"], ("", "st-unknown"))
    bits = ['<span class="pill {}">{}</span>'.format(cls, escape(label))]
    if item.get("host"):
        bits.append('<span class="host">{}</span>'.format(escape(item["host"])))
    if item.get("deadline_note"):
        bits.append("<span>{}</span>".format(escape(item["deadline_note"])))
    if item.get("window"):
        bits.append("<span>{}</span>".format(escape(item["window"])))
    if item.get("prize"):
        bits.append("<span>{}</span>".format(escape(item["prize"])))
    if item.get("checked"):
        bits.append("<span>{} 확인</span>".format(escape(item["checked"])))

    extras = ""
    if item.get("note"):
        extras += '<div class="note">{}</div>'.format(escape(item["note"]))
    if item.get("evidence") and item.get("origin") == "feed":
        extras += '<div class="evidence">마감일 근거: {}</div>'.format(
            escape(item["evidence"][:110])
        )
    if item.get("source"):
        extras += '<div class="evidence"><a href="{}">공고 출처</a></div>'.format(
            escape(item["source"], quote=True)
        )

    search = escape(
        " ".join([item["name"], item.get("host", ""), item.get("window", "")]).lower(), quote=True
    )
    return (
        '<li class="{hot}" data-search="{search}">'
        '<div class="dday">{dday}</div>'
        "<div>"
        '<a class="name" href="{url}" target="_blank" rel="noopener noreferrer">{name}</a>'
        '<div class="meta">{bits}</div>{extras}'
        "</div></li>"
    ).format(
        hot="hot" if item["status"] == "imminent" else "",
        search=search,
        dday=dday_cell(item),
        url=escape(item["url"], quote=True),
        name=escape(item["name"]),
        bits="".join(bits),
        extras=extras,
    )


def render() -> str:
    data = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))
    t = data["totals"]

    tabs = ['<button class="tab" role="tab" data-cat="all" aria-selected="true">전체</button>']
    sections = []
    for cat in data["categories"]:
        if not cat["items"]:
            continue
        tabs.append(
            '<button class="tab" role="tab" data-cat="{}" aria-selected="false">{} <b>{}</b></button>'.format(
                cat["id"], escape(cat["label"]), cat["counts"]["total"]
            )
        )
        sections.append(
            '<section data-cat="{id}">'
            "<h2>{label}"
            '<span data-fmt="#건 · 접수중 {open}건">{total}건 · 접수중 {open}건</span></h2>'
            "<ul>{rows}</ul>"
            '<p class="empty" hidden>검색 결과가 없습니다.</p></section>'.format(
                id=cat["id"],
                label=escape(cat["label"]),
                total=cat["counts"]["total"],
                open=cat["counts"]["open"],
                rows="".join(row(i) for i in cat["items"]),
            )
        )

    # 마감 임박 — 카테고리를 가로질러 가장 급한 것만 위로 끌어올린다.
    urgent_items = sorted(
        (i for c in data["categories"] for i in c["items"] if i["status"] == "imminent"),
        key=lambda x: x["dday"],
    )
    urgent = ""
    if urgent_items:
        urgent = (
            '<section class="urgent" data-cat="urgent">'
            "<h2>마감 임박 — {days}일 내<span>{n}건</span></h2>"
            "<ul>{rows}</ul></section>"
        ).format(
            days=data["imminent_days"],
            n=len(urgent_items),
            rows="".join(row(i) for i in urgent_items),
        )

    news = ""
    if data.get("news"):
        news = (
            '<section class="news" data-cat="news">'
            "<h2>새 공고 · 관련 소식<span>{n}건</span></h2>"
            "<ul>{rows}</ul></section>"
        ).format(
            n=len(data["news"]),
            rows="".join(
                '<li data-search="{s}">'
                '<a class="name" href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
                '<div class="meta"><span class="host">{topic}</span><span>{posted}</span></div>'
                "</li>".format(
                    s=escape((n["title"] + " " + n["topic"]).lower(), quote=True),
                    url=escape(n["url"], quote=True),
                    title=escape(n["title"]),
                    topic=escape(n["topic"]),
                    posted=escape(n["posted"]),
                )
                for n in data["news"]
            ),
        )
        tabs.append(
            '<button class="tab" role="tab" data-cat="news" aria-selected="false">새 공고 소식 <b>{}</b></button>'.format(
                len(data["news"])
            )
        )

    feedlog = "".join(
        '<div class="{}">{} {} ({})</div>'.format(
            "" if f["ok"] else "bad", "·" if f["ok"] else "×", escape(f["name"]), f["count"]
        )
        for f in data["feeds"]
    )

    html = TEMPLATE
    for key, val in {
        "__OPEN__": str(t["open"]),
        "__IMMINENT__": str(t["imminent"]),
        "__PENDING__": str(t["pending"]),
        "__UNKNOWN__": str(t["unknown"]),
        "__ALL__": str(t["all"]),
        "__IMMDAYS__": str(data["imminent_days"]),
        "__TODAY__": data["generated_kst"],
        "__TABS__": "".join(tabs),
        "__URGENT__": urgent,
        "__SECTIONS__": "".join(sections),
        "__NEWS__": news,
        "__FEEDLOG__": feedlog,
        "__FEED_OK__": str(sum(1 for f in data["feeds"] if f["ok"])),
        "__FEED_TOTAL__": str(len(data["feeds"])),
        "__SITE__": SITE_URL,
    }.items():
        html = html.replace(key, val)
    return html


def full_page() -> str:
    return (
        '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + render()
        + "</html>\n"
    )


if __name__ == "__main__":
    import sys

    if "--artifact" in sys.argv:
        target = ROOT / "artifact.html"
        target.write_text(render(), encoding="utf-8")
        print("artifact.html 생성 ({:,} bytes)".format(target.stat().st_size))
        raise SystemExit(0)

    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(full_page(), encoding="utf-8")
    (out / "latest.json").write_text(
        (ROOT / "data" / "latest.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print("docs/index.html 생성 ({:,} bytes)".format((out / "index.html").stat().st_size))
