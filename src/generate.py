"""Commit Canvas — 1년치 GitHub 기여를 한 점의 추상화로 그리는 SVG 생성기.

사용법
  python src/generate.py --user HHHv-v --out dist/commit-canvas.svg   # 실제 데이터 (GITHUB_TOKEN 필요)
  python src/generate.py --user HHHv-v --demo --out dist/demo.svg      # 샘플 데이터

그림 규칙
- 1주 = 세로 한 줄, 왼쪽 → 오른쪽으로 1년이 흐름
- 기여한 날 = 붓터치. 많을수록 길고 굵고 여러 번 덧칠
- 색 = 그날 커밋한 레포의 주 언어 (GitHub 언어 색)
- 붓 방향 = 아이디로 시드를 만든 흐름장 → 사람마다 다른 그림
- 7일 이상 연속 기여 = 금색 점선
"""
import argparse, hashlib, json, math, os, random, urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta

NEUTRAL_INK = "#4a433a"  # 커밋 외 기여(PR, 이슈 등)만 있는 날

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        repository { primaryLanguage { name color } }
        contributions(first: 100) { nodes { occurredAt commitCount } }
      }
    }
  }
}"""


# ── 데이터 ────────────────────────────────────────────────
def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    cc = body["data"]["user"]["contributionsCollection"]

    day_langs = defaultdict(Counter)
    colors = {}
    for item in cc["commitContributionsByRepository"]:
        lang = item["repository"]["primaryLanguage"]
        if not lang:
            continue
        colors[lang["name"]] = lang["color"] or NEUTRAL_INK
        for n in item["contributions"]["nodes"]:
            day_langs[n["occurredAt"][:10]][lang["name"]] += n["commitCount"]

    weeks = []
    for w in cc["contributionCalendar"]["weeks"]:
        weeks.append([
            {"date": d["date"], "weekday": d["weekday"], "count": d["contributionCount"],
             "lang": day_langs[d["date"]].most_common(1)[0][0] if day_langs[d["date"]] else None}
            for d in w["contributionDays"]
        ])
    return weeks, colors


def demo_data(seed):
    rng = random.Random(seed)
    langs = [("TypeScript", "#3178c6", .42), ("Python", "#e0a82e", .22),
             ("JavaScript", "#d8643a", .14), ("C", "#5b7a5e", .12), ("CSS", "#a2507a", .10)]
    colors = {n: c for n, c, _ in langs}
    start = date.today() - timedelta(days=date.today().weekday() + 1 + 52 * 7)
    weeks = []
    for w in range(53):
        season = .5 + .5 * math.sin(w / 52 * 2 * math.pi * 1.5)
        busy = 1.6 if w in (18, 19, 40, 41) else 1.0
        days = []
        for d in range(7):
            p = .25 + .55 * season * (.7 if d in (0, 6) else 1)
            c = 0 if rng.random() > p else max(1, int(rng.expovariate(1 / (3 * busy))))
            lang = rng.choices([l[0] for l in langs], [l[2] for l in langs])[0] if c else None
            days.append({"date": str(start + timedelta(days=w * 7 + d)), "weekday": d, "count": c, "lang": lang})
        weeks.append(days)
    return weeks, colors


# ── 그리기 ────────────────────────────────────────────────
def render(login, weeks, colors, theme="light"):
    W, H = 1200, 540
    PAD_X, TOP, BOTTOM = 70, 60, 400
    pal = {
        "light": dict(bg="#f4eee2", grain="#8a7a5c", frame="#d9cfbd", title="#2b2620", sub="#5e564b", gold="#c9a43a"),
        "dark":  dict(bg="#16130f", grain="#c8b896", frame="#3a332a", title="#efe6d4", sub="#a89d8a", gold="#e2c25a"),
    }[theme]

    seed = int(hashlib.sha256(login.encode()).hexdigest(), 16) % 10**8
    rng = random.Random(seed)
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]

    def angle(x, y):
        return (math.sin(x * .006 + ph[0]) + math.cos(y * .011 + ph[1])
                + .5 * math.sin((x + y) * .004 + ph[2])) * .9

    def brush(x, y, length, width, color, opacity, delay):
        pts, step = [(x, y)], 4
        for _ in range(int(length / step)):
            a = angle(x, y)
            x += math.cos(a) * step
            y += math.sin(a) * step
            pts.append((x, y))
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        return (f'<path d="{d}" stroke="{color}" stroke-width="{width:.1f}" stroke-opacity="{opacity:.2f}" '
                f'fill="none" stroke-linecap="round" pathLength="1" style="animation-delay:{delay:.2f}s"/>')

    n_weeks = len(weeks)
    col_w = (W - 2 * PAD_X) / n_weeks
    row_h = (BOTTOM - TOP) / 7
    strokes, streak_lines = [], []
    lang_total, total, streak, best, run = Counter(), 0, 0, 0, []

    for wi, days in enumerate(weeks):
        for day in days:
            c = day["count"]
            cx = PAD_X + wi * col_w + col_w / 2 + rng.uniform(-6, 6)
            cy = TOP + day["weekday"] * row_h + row_h / 2 + rng.uniform(-8, 8)
            if c == 0:
                if streak >= 7:
                    streak_lines.append(run)
                streak, run = 0, []
                continue
            total += c
            streak += 1
            best = max(best, streak)
            run.append((cx, cy))
            color = colors.get(day["lang"], NEUTRAL_INK) if day["lang"] else NEUTRAL_INK
            if day["lang"]:
                lang_total[day["lang"]] += c
            delay = wi / n_weeks * 3  # 1년이 왼쪽부터 차례로 그려짐
            for _ in range(1 + min(c // 3, 4)):
                strokes.append(brush(cx + rng.uniform(-4, 4), cy + rng.uniform(-4, 4),
                                     18 + min(c, 15) * 7 + rng.uniform(-6, 6),
                                     2 + min(c, 12) * .9, color, rng.uniform(.35, .7), delay))
            strokes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{3 + min(c, 10) * 1.6:.1f}" '
                           f'fill="{color}" fill-opacity="0.08"/>')
    if streak >= 7:
        streak_lines.append(run)

    gold = "".join(
        f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" stroke="{pal["gold"]}" stroke-width="1.2" '
        f'fill="none" stroke-dasharray="1 6" stroke-linecap="round" opacity="0.55"/>' for pts in streak_lines)
    grain = "".join(
        f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H):.0f}" r="{rng.uniform(.4, 1.2):.1f}" '
        f'fill="{pal["grain"]}" fill-opacity="{rng.uniform(.05, .18):.2f}"/>' for _ in range(1800))

    legend, lx = [], PAD_X
    lt = sum(lang_total.values()) or 1
    for name, cnt in lang_total.most_common(5):
        legend.append(f'<circle cx="{lx + 6}" cy="{H - 40}" r="6" fill="{colors[name]}"/>'
                      f'<text x="{lx + 18}" y="{H - 35}" class="s">{name} {round(cnt / lt * 100)}%</text>')
        lx += 150

    first, last = weeks[0][0]["date"][:7].replace("-", "."), weeks[-1][-1]["date"][:7].replace("-", ".")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
  .t{{font-family:'Noto Serif KR','Noto Serif CJK KR',Georgia,serif;font-size:26px;fill:{pal["title"]};font-weight:700}}
  .s{{font-family:'Noto Sans KR','Noto Sans CJK KR',-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;font-size:14px;fill:{pal["sub"]}}}
  .ink path{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.4s ease-out forwards}}
  @keyframes draw{{to{{stroke-dashoffset:0}}}}
  @media (prefers-reduced-motion:reduce){{.ink path{{animation:none;stroke-dashoffset:0}}}}
</style>
<clipPath id="frame"><rect x="30" y="30" width="{W - 60}" height="{BOTTOM - 10}"/></clipPath>
<rect width="{W}" height="{H}" fill="{pal["bg"]}"/>
{grain}
<rect x="30" y="30" width="{W - 60}" height="{BOTTOM - 10}" fill="none" stroke="{pal["frame"]}"/>
<g class="ink" clip-path="url(#frame)">{"".join(strokes)}</g>
<g clip-path="url(#frame)">{gold}</g>
<text x="{PAD_X}" y="{H - 78}" class="t">Commit Canvas</text>
<text x="{PAD_X + 215}" y="{H - 78}" class="s">@{login} · {first} – {last} · {total:,} contributions · 최장 연속 {best}일</text>
{"".join(legend)}
<text x="{W - PAD_X}" y="{H - 78}" class="s" text-anchor="end">← 1년의 흐름 →</text>
<rect x="{W - PAD_X - 34}" y="{H - 62}" width="34" height="34" fill="#b0352b" rx="3"/>
<text x="{W - PAD_X - 17}" y="{H - 40}" text-anchor="middle" style="font-family:Georgia,serif;font-size:11px;fill:#f4eee2;font-weight:700">{login[:3]}</text>
</svg>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", default="dist/commit-canvas.svg")
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--demo", action="store_true", help="샘플 데이터로 그리기 (토큰 불필요)")
    a = ap.parse_args()

    if a.demo:
        weeks, colors = demo_data(a.user)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN 환경변수가 필요해요. 샘플로 보려면 --demo")
        weeks, colors = fetch(a.user, token)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(a.user, weeks, colors, a.theme))
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()
