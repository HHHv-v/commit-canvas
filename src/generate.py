"""Commit Canvas — 1년치 GitHub 기여를 한 점의 추상화로 그리는 SVG 생성기.

사용법
  python src/generate.py --user HHHv-v --out dist/commit-canvas.svg   # 실제 데이터 (GITHUB_TOKEN 필요)
  python src/generate.py --user HHHv-v --demo --out dist/demo.svg      # 샘플 데이터

그림 규칙
- 1주 = 세로 한 줄, 왼쪽 → 오른쪽으로 시간이 흐름 (첫 기여 이전의 빈 기간은 잘라냄)
- 기여한 날 = 그날 칸에서 출발하는 입자들. 기여가 많을수록 입자 수·길이·굵기가 늘어남
- 입자는 curl noise(+도메인 워핑) 유체장을 따라 흐름 — 레픽 아나돌의 '데이터 페인팅'에서 영감
- 색 기준은 데이터에 맞춰 자동 선택 (--color auto)
    · language  : 여러 언어를 고르게 쓰면 언어별 색
    · repo      : 한 언어가 80% 이상이면 레포별 색 (한 언어만 써도 프로젝트는 여러 개)
    · intensity : 레포도 하나뿐이면 그날 기여량에 따라 색이 달라짐
- 유체장은 아이디로 시드를 만듦 → 사람마다 다른 그림, 같은 사람은 매일 같은 흐름 위에서 자라남
"""
import argparse, hashlib, json, math, os, random, urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta

# 많이 쓴 언어부터 순서대로 배정되는 팔레트 (서로 확실히 구분되는 색)
PALETTE = ["#7C5CFF", "#FF5C93", "#14B8A6", "#F5A524", "#3B82F6", "#FF7A45"]
OTHER = "Other"

THEMES = {
    "light": dict(bg="#FFFFFF", border="#ECECF2", text="#111118", sub="#6B6B7B",
                  chip="#F4F4F8", other="#B4B4C2", aurora=.10, glow=False),
    "dark":  dict(bg="#0B0B10", border="#1F1F2A", text="#F5F5FA", sub="#8E8EA0",
                  chip="#16161F", other="#4A4A5A", aurora=.22, glow=True),
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner name primaryLanguage { name } }
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

    day_langs, day_repos = defaultdict(Counter), defaultdict(Counter)
    for item in cc["commitContributionsByRepository"]:
        repo = item["repository"]
        lang = repo["primaryLanguage"]
        for n in item["contributions"]["nodes"]:
            day = n["occurredAt"][:10]
            day_repos[day][repo["name"]] += n["commitCount"]
            if lang:
                day_langs[day][lang["name"]] += n["commitCount"]

    top = lambda counter: counter.most_common(1)[0][0] if counter else None
    return [[{"date": d["date"], "weekday": d["weekday"], "count": d["contributionCount"],
              "lang": top(day_langs[d["date"]]), "repo": top(day_repos[d["date"]])}
             for d in w["contributionDays"]]
            for w in cc["contributionCalendar"]["weeks"]]


def demo_data(seed, profile="multi"):
    """최근 몇 달에 활동이 몰린 샘플. profile: multi(여러 언어) / single(한 언어·여러 레포) / mono(한 레포)"""
    rng = random.Random(seed)
    langs = {"multi": [("TypeScript", .55), ("Python", .28), ("Jupyter Notebook", .07), ("CSS", .06), ("C", .04)],
             "single": [("TypeScript", 1)], "mono": [("TypeScript", 1)]}[profile]
    repos = {"multi": [("samdan", .4), ("hearo", .3), ("python-course", .3)],
             "single": [("samdan", .35), ("hearo", .25), ("haedal-home", .2), ("commit-canvas", .12), ("dh-lms", .08)],
             "mono": [("samdan", 1)]}[profile]
    start = date.today() - timedelta(days=date.today().weekday() + 1 + 52 * 7)
    weeks = []
    for w in range(53):
        p = 0 if w < 20 else (.15 if w < 32 else .65)
        days = []
        for d in range(7):
            c = 0 if rng.random() > p else max(1, int(rng.expovariate(1 / 3.5)))
            lang = rng.choices([l[0] for l in langs], [l[1] for l in langs])[0] if c else None
            repo = rng.choices([r[0] for r in repos], [r[1] for r in repos])[0] if c else None
            days.append({"date": str(start + timedelta(days=w * 7 + d)), "weekday": d, "count": c,
                         "lang": lang, "repo": repo})
        weeks.append(days)
    return weeks


# ── 노이즈 ────────────────────────────────────────────────
class Perlin:
    """2D Perlin noise. 같은 시드 → 같은 흐름."""
    def __init__(self, seed):
        p = list(range(256))
        random.Random(seed).shuffle(p)
        self.p = p * 2

    @staticmethod
    def _fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _grad(self, h, x, y):
        return ((x if h & 1 else -x) + (y if h & 2 else -y)) if h & 4 else ((x if h & 1 else -x) * 1.4 if h & 2 else (y if h & 1 else -y) * 1.4)

    def __call__(self, x, y):
        xi, yi = int(math.floor(x)) & 255, int(math.floor(y)) & 255
        xf, yf = x - math.floor(x), y - math.floor(y)
        u, v = self._fade(xf), self._fade(yf)
        p = self.p
        aa, ab, ba, bb = p[p[xi] + yi], p[p[xi] + yi + 1], p[p[xi + 1] + yi], p[p[xi + 1] + yi + 1]
        x1 = self._grad(aa, xf, yf) + u * (self._grad(ba, xf - 1, yf) - self._grad(aa, xf, yf))
        x2 = self._grad(ab, xf, yf - 1) + u * (self._grad(bb, xf - 1, yf - 1) - self._grad(ab, xf, yf - 1))
        return x1 + v * (x2 - x1)


# ── 그리기 ────────────────────────────────────────────────
def tint(hex_color, amount):
    """amount만큼 흰색과 섞은 색."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    mix = lambda c: round(c + (255 - c) * amount)
    return f"#{mix(r):02X}{mix(g):02X}{mix(b):02X}"


INTENSITY_PALETTE = ["#14B8A6", "#3B82F6", "#7C5CFF", "#FF5C93"]   # 적음 → 많음
INTENSITY_LABELS = ["1–2", "3–5", "6–9", "10+"]


def intensity_label(count):
    return INTENSITY_LABELS[0 if count <= 2 else 1 if count <= 5 else 2 if count <= 9 else 3]


def choose_mode(weeks, requested="auto"):
    """색을 무엇 기준으로 나눌지 정한다. 한 언어만 쓰는 사람도 그림이 단색이 되지 않게."""
    langs, repos = Counter(), Counter()
    for w in weeks:
        for d in w:
            if d["count"]:
                if d.get("lang"):
                    langs[d["lang"]] += d["count"]
                if d.get("repo"):
                    repos[d["repo"]] += d["count"]
    if requested == "auto":
        top_lang_share = langs.most_common(1)[0][1] / sum(langs.values()) if langs else 1
        if len(langs) >= 2 and top_lang_share < .8:
            requested = "language"
        elif len(repos) >= 2:
            requested = "repo"
        else:
            requested = "intensity"
    return {
        "language":  ("language", lambda d: d.get("lang"), "Languages"),
        "repo":      ("repo", lambda d: d.get("repo"), "Projects"),
        "intensity": ("intensity", lambda d: intensity_label(d["count"]), "Daily"),
    }[requested]


def render(login, weeks, theme="dark", color_mode="auto", style="fluid"):
    t = THEMES[theme]
    W, H = 1200, 560
    ART_X0, ART_X1, ART_Y0, ART_Y1 = 64, 1136, 150, 450

    # 첫 기여 이전의 빈 주는 잘라서 캔버스를 채움 (최소 16주는 유지)
    first = next((i for i, w in enumerate(weeks) if any(d["count"] for d in w)), len(weeks) - 1)
    weeks = weeks[max(0, min(first, len(weeks) - 16)):]

    mode, key_of, legend_title = choose_mode(weeks, color_mode)
    key_total = Counter()
    for w in weeks:
        for d in w:
            if d["count"]:
                key_total[key_of(d)] += d["count"]
    key_total.pop(None, None)
    if mode == "intensity":
        ranked = [k for k in INTENSITY_LABELS if k in key_total]   # 고정 순서
    else:
        ranked = [k for k, _ in key_total.most_common()]
    palette = INTENSITY_PALETTE if mode == "intensity" else PALETTE
    color_of = {k: palette[i] for i, k in enumerate(ranked[:len(palette)])}
    for k in ranked[len(palette):]:
        color_of[k] = t["other"]

    seed = int(hashlib.sha256(login.encode()).hexdigest(), 16) % 10**8
    rng = random.Random(seed)
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]

    if style == "fluid":
        noise = Perlin(seed)
        S = .0042

        def potential(x, y):
            # 도메인 워핑: 노이즈로 좌표를 한 번 비틀어 마블링 같은 소용돌이 모양을 만듦
            qx, qy = noise(x * S, y * S), noise(x * S + 5.2, y * S + 1.3)
            return noise(x * S + 1.8 * qx, y * S + 1.8 * qy)

        def angle(x, y, e=1.0):
            # curl noise: 퍼텐셜의 회전 성분만 써서 입자가 한 점으로 빨려 들지 않는 유체 흐름
            vx = (potential(x, y + e) - potential(x, y - e)) / (2 * e)
            vy = -(potential(x + e, y) - potential(x - e, y)) / (2 * e)
            mag = math.hypot(vx, vy) or 1e-9
            vx, vy = vx / mag, vy / mag
            # 오른쪽으로 살짝 흐르는 바람을 섞어 '시간의 흐름'을 유지
            return math.atan2(vy, vx + .55)
    else:
        def angle(x, y):
            return (math.sin(x * .004 + ph[0]) + math.cos(y * .008 + ph[1])
                    + .5 * math.sin((x + y) * .003 + ph[2])) * .95

    def trail(x, y, length, step=5):
        """흐름장을 따라 움직인 입자의 궤적."""
        pts = [(x, y)]
        for _ in range(max(2, int(length / step))):
            a = angle(x, y)
            x += math.cos(a) * step
            y += math.sin(a) * step
            pts.append((x, y))
        return "M" + " ".join(f"{a:.0f},{b:.0f}" for a, b in pts)

    def ribbon(x, y, length, width):
        """흐름장을 따라가는 중심선 → 시작은 굵고 끝은 가늘어지는 리본 폴리곤."""
        pts, step = [(x, y)], 4
        for _ in range(max(3, int(length / step))):
            a = angle(x, y)
            x += math.cos(a) * step
            y += math.sin(a) * step
            pts.append((x, y))
        n = len(pts) - 1
        left, right = [], []
        for i, (px, py) in enumerate(pts):
            ax, ay = pts[min(i + 1, n)]
            bx, by = pts[max(i - 1, 0)]
            dx, dy = ax - bx, ay - by
            norm = math.hypot(dx, dy) or 1
            nx, ny = -dy / norm, dx / norm
            hw = width * math.sin(math.pi * (.12 + .88 * i / n)) + .4
            left.append((px + nx * hw, py + ny * hw))
            right.append((px - nx * hw, py - ny * hw))
        poly = left + right[::-1]
        return "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in poly) + "Z"

    n_weeks = len(weeks)
    col_w = (ART_X1 - ART_X0) / n_weeks
    row_h = (ART_Y1 - ART_Y0) / 7
    shapes, total, active, streak, best = [], 0, 0, 0, 0
    raw = sum(min(4 + d["count"] * 3, 36) for w in weeks for d in w if d["count"])
    budget = min(1.0, 2200 / raw) if raw else 1.0   # SVG가 너무 무거워지지 않게 전체 입자 수 제한

    for wi, days in enumerate(weeks):
        for day in days:
            c = day["count"]
            if c == 0:
                streak = 0
                continue
            total += c
            active += 1
            streak += 1
            best = max(best, streak)
            cx = ART_X0 + wi * col_w + col_w / 2 + rng.uniform(-8, 8)
            cy = ART_Y0 + day["weekday"] * row_h + row_h / 2 + rng.uniform(-10, 10)
            key = key_of(day)
            grad = f"g{ranked.index(key)}" if key in color_of and color_of[key] != t["other"] else "gx"
            delay = wi / n_weeks * 2.4
            if style == "fluid":
                n = max(2, round(min(4 + c * 3, 36) * budget))
                spread = 10 + min(c, 12) * 1.5
                for _ in range(n):
                    d = trail(cx + rng.gauss(0, spread * .5), cy + rng.gauss(0, spread * .5),
                              rng.uniform(70, 150) + min(c, 15) * 6)
                    shapes.append(f'<path d="{d}" stroke="url(#{grad})" stroke-width="{rng.uniform(.6, 1.6 + min(c, 10) * .12):.1f}" '
                                  f'stroke-opacity="{rng.uniform(.3, .75):.2f}" pathLength="1" style="animation-delay:{delay + rng.uniform(0, .5):.2f}s"/>')
                continue
            for _ in range(1 + min(c // 4, 3)):
                d = ribbon(cx + rng.uniform(-5, 5), cy + rng.uniform(-5, 5),
                           30 + min(c, 15) * 8 + rng.uniform(-8, 8),
                           2.2 + min(c, 12) * 1.0)
                shapes.append(f'<path d="{d}" fill="url(#{grad})" fill-opacity="{rng.uniform(.7, .95):.2f}" '
                              f'style="animation-delay:{delay:.2f}s"/>')

    # 그라데이션 정의 (언어별 + 기타)
    grads = "".join(
        f'<linearGradient id="g{i}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{palette[i]}"/><stop offset="1" stop-color="{tint(palette[i], .45)}"/>'
        f'</linearGradient>' for i in range(min(len(ranked), len(palette))))
    grads += (f'<linearGradient id="gx" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["other"]}"/>'
              f'<stop offset="1" stop-color="{t["other"]}"/></linearGradient>')

    # 배경 오로라: 가장 많이 쓴 두 언어 색
    aurora = ""
    for i, (ax, ay, r) in enumerate([(W * .78, H * .35, 420), (W * .25, H * .75, 380)][:max(1, min(2, len(ranked)))]):
        col = color_of[ranked[-1 - i] if mode == "intensity" else ranked[i]] if ranked else PALETTE[0]
        aurora += (f'<radialGradient id="a{i}"><stop offset="0" stop-color="{col}" stop-opacity="{t["aurora"]}"/>'
                   f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
                   f'<circle cx="{ax:.0f}" cy="{ay:.0f}" r="{r}" fill="url(#a{i})"/>')

    # 범례 칩 (색 기준 + 상위 4개)
    lt = sum(key_total.values()) or 1
    chips, cx = [], ART_X0
    chips.append(f'<text x="{cx}" y="506" class="meta">{legend_title}</text>')
    cx += len(legend_title) * 7.6 + 14
    for name in ranked[:4]:
        short = name if len(name) <= 16 else name[:15] + "…"
        label = (f"{name} commits" if mode == "intensity"
                 else f"{short}  {round(key_total[name] / lt * 100)}%")
        w = 34 + len(label) * 7.4
        if cx + w > ART_X1 - 330:   # 오른쪽 통계와 겹치지 않게
            break
        chips.append(f'<rect x="{cx}" y="486" width="{w:.0f}" height="30" rx="15" fill="{t["chip"]}"/>'
                     f'<circle cx="{cx + 17}" cy="501" r="5" fill="{color_of[name]}"/>'
                     f'<text x="{cx + 29}" y="506" class="chip">{label}</text>')
        cx += w + 10

    def fmt(s):
        y, m, _ = s.split("-")
        return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m) - 1]} {y}"

    if style == "fluid":
        art_css = (".art path{fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;"
                   "animation:flow 2.2s cubic-bezier(.2,.7,.2,1) forwards}"
                   "@keyframes flow{to{stroke-dashoffset:0}}"
                   "@media (prefers-reduced-motion:reduce){.art path{animation:none;stroke-dashoffset:0}}")
    else:
        art_css = (".art path{opacity:0;animation:in .9s ease-out forwards}@keyframes in{to{opacity:1}}"
                   "@media (prefers-reduced-motion:reduce){.art path{animation:none;opacity:1}}")
    glow = '<use href="#art" filter="url(#glow)" opacity=".7"/>' if t["glow"] else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  {grads}
  <clipPath id="card"><rect width="{W}" height="{H}" rx="24"/></clipPath>
  <linearGradient id="fadeY" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".14" stop-color="#fff"/>
    <stop offset=".86" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="fadeX" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".05" stop-color="#fff"/>
    <stop offset=".95" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <mask id="artzone" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect x="0" y="122" width="{W}" height="{ART_Y1 + 30 - 122}" fill="url(#fadeY)"/>
  </mask>
  <mask id="artzoneX" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect x="0" y="0" width="{W}" height="{H}" fill="url(#fadeX)"/>
  </mask>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="{6 if style == "fluid" else 7}"/></filter>
  <style>
    text{{font-family:Inter,'Segoe UI',system-ui,-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif}}
    .eyebrow{{font-size:13px;font-weight:600;letter-spacing:2.6px;fill:{t["sub"]}}}
    .big{{font-size:46px;font-weight:700;letter-spacing:-1.5px;fill:{t["text"]}}}
    .unit{{font-size:17px;font-weight:500;fill:{t["sub"]}}}
    .meta{{font-size:15px;font-weight:500;fill:{t["sub"]}}}
    .stat{{font-size:15px;font-weight:600;fill:{t["text"]}}}
    .chip{{font-size:13px;font-weight:500;fill:{t["text"]}}}
    {art_css}
  </style>
</defs>
<g clip-path="url(#card)">
  <rect width="{W}" height="{H}" fill="{t["bg"]}"/>
  {aurora}
  <g mask="url(#artzone)"><g mask="url(#artzoneX)">
    <g id="art" class="art">{"".join(shapes)}</g>
    {glow}
  </g></g>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="24" fill="none" stroke="{t["border"]}"/>
<text x="{ART_X0}" y="62" class="eyebrow">COMMIT CANVAS · @{login.upper()}</text>
<text x="{ART_X0}" y="114" class="big">{total:,}<tspan class="unit" dx="10">contributions</tspan></text>
<text x="{ART_X1}" y="62" class="meta" text-anchor="end">{fmt(weeks[0][0]["date"])} — {fmt(weeks[-1][-1]["date"])}</text>
{"".join(chips)}
<text x="{ART_X1}" y="506" class="meta" text-anchor="end">active days</text>
<text x="{ART_X1 - 90}" y="506" class="stat" text-anchor="end">{active}</text>
<text x="{ART_X1 - 130}" y="506" class="meta" text-anchor="end">longest streak</text>
<text x="{ART_X1 - 240}" y="506" class="stat" text-anchor="end">{best}d</text>
</svg>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", default="dist/commit-canvas.svg")
    ap.add_argument("--theme", choices=list(THEMES), default="dark")
    ap.add_argument("--style", choices=["fluid", "petal"], default="fluid",
                    help="fluid: 입자 흐름(기본) / petal: 붓터치")
    ap.add_argument("--color", choices=["auto", "language", "repo", "intensity"], default="auto",
                    help="색 기준 (기본 auto: 데이터에 맞춰 자동 선택)")
    ap.add_argument("--demo", choices=["multi", "single", "mono"], nargs="?", const="multi",
                    help="샘플 데이터로 그리기 (토큰 불필요)")
    a = ap.parse_args()

    if a.demo:
        weeks = demo_data(a.user, a.demo)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN 환경변수가 필요해요. 샘플로 보려면 --demo")
        weeks = fetch(a.user, token)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(a.user, weeks, a.theme, a.color, a.style))
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()
