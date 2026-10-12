# Commit Canvas 🎨

1년치 GitHub 기여를 **흐르는 데이터 페인팅**으로 그려주는 프로필 위젯이에요.
레픽 아나돌(Refik Anadol)의 데이터 페인팅에서 영감을 받아, 기여 하나하나가 입자가 되어 유체처럼 흐르며 그림을 만들어요.
같은 그림은 하나도 없어요.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/demo-dark.svg">
  <img alt="Commit Canvas demo" src="docs/demo-light.svg">
</picture>

## 그림 규칙

| 데이터 | 그림 |
|---|---|
| 시간 | 왼쪽 → 오른쪽 (첫 기여 이전의 빈 기간은 잘라내요) |
| 기여한 날 | 그날 칸에서 출발하는 입자들 — 많을수록 입자 수·길이·굵기가 늘어나요 |
| 흐름 | curl noise + 도메인 워핑으로 만든 유체장. 깃허브 아이디가 시드라 사람마다 달라요 |
| 색 | 데이터에 맞춰 자동 선택 (아래) |

### 색 기준 자동 선택 (`--color auto`)

한 가지 언어만 쓰는 사람도 그림이 단색이 되지 않도록, 색의 기준을 데이터에 맞춰 골라요.

| 상황 | 색 기준 |
|---|---|
| 여러 언어를 고르게 씀 | **언어별** (`Languages`) |
| 한 언어가 80% 이상 | **레포별** (`Projects`) |
| 레포도 하나뿐 | **그날 기여량별** (`Daily`: 1–2 / 3–5 / 6–9 / 10+) |

직접 고르고 싶다면 `--color language | repo | intensity`를 쓰면 돼요.

## 내 프로필에 붙이기

1. 이 레포를 Fork 해요.
2. **Actions** 탭 → `Generate Commit Canvas` → **Run workflow**
3. 프로필 README에 아래를 붙여요 (`USER`를 내 아이디로).

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/USER/commit-canvas/output/commit-canvas-dark.svg">
  <img alt="Commit Canvas" src="https://raw.githubusercontent.com/USER/commit-canvas/output/commit-canvas.svg">
</picture>
```

매일 자정(KST)에 자동으로 새로 그려져요.

## 로컬에서 돌려보기

```bash
python src/generate.py --user HHHv-v --demo --out dist/demo.svg            # 샘플 (여러 언어)
python src/generate.py --user HHHv-v --demo single --out dist/demo.svg     # 샘플 (한 언어, 여러 레포)
GITHUB_TOKEN=... python src/generate.py --user HHHv-v               # 실제 데이터
```

의존성 없이 Python 표준 라이브러리만 사용해요.

## 로드맵

- [x] 입자 유체 스타일 (`--style fluid`, 기본) / 붓터치 스타일 (`--style petal`)
- [x] 한 언어 사용자를 위한 색 기준 자동 선택
- [ ] Vercel API 버전 (`/api?user=...`) — Fork 없이 바로 사용
- [ ] 테마 추가 (수묵, 수채, 네온)

## License

MIT
