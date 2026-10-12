# Commit Canvas 🎨

1년치 GitHub 기여를 **흐르는 데이터 페인팅**으로 그려주는 프로필 위젯이에요.
기여 하나하나가 입자가 되어 유체처럼 흐르며 한 점의 그림을 만들어요. 같은 그림은 하나도 없어요.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/demo-dark.svg">
  <img alt="Commit Canvas demo" src="docs/demo-light.svg">
</picture>

## 그림 규칙

| 데이터 | 그림 |
|---|---|
| 시간 | 왼쪽 → 오른쪽으로 흐름. 첫 기여 이전의 빈 기간은 잘라냄 |
| 기여한 날 | 그날 칸에서 출발하는 입자들. 기여가 많을수록 입자 수·길이·굵기가 늘어남 |
| 흐름 | curl noise + 도메인 워핑으로 만든 유체장. 깃허브 아이디가 시드라 사람마다 다름 |
| 색 | 데이터에 맞춰 자동 선택 (아래 참고) |

### 색 기준 자동 선택 (`--color auto`)

한 가지 언어만 쓰는 사람도 그림이 단색이 되지 않도록, 색의 기준을 데이터에 맞춰 골라요.

| 상황 | 색 기준 |
|---|---|
| 여러 언어를 고르게 씀 | **언어별** (`Languages`) |
| 한 언어가 80% 이상 | **레포별** (`Projects`) |
| 레포도 하나뿐 | **그날 기여량별** (`Daily`: 1–2 / 3–5 / 6–9 / 10+) |

직접 고르고 싶다면 `--color language | repo | intensity`를 쓰면 돼요.

## 동작 방식

그림 한 장은 아래 6단계를 거쳐 만들어져요. 코드는 모두 [`src/generate.py`](src/generate.py) 한 파일에 있어요.

```mermaid
flowchart LR
  A[GitHub GraphQL<br/>기여 데이터] --> B[날짜 → 캔버스 칸]
  B --> C[색 기준 선택]
  C --> D[유체장 만들기]
  D --> E[입자 흘려보내기]
  E --> F[SVG 조립]
  F --> G[Actions가<br/>output 브랜치에 저장]
```

### 1. 기여 데이터 가져오기

GitHub GraphQL API에서 두 가지를 가져와요.

| 데이터 | 쓰임 |
|---|---|
| `contributionCalendar` | 날짜별 기여 수. 입자의 개수·길이·굵기를 정함 |
| `commitContributionsByRepository` | 레포별 커밋 기록과 레포의 주 언어. 그날의 색을 정함 |

하루에 여러 레포에 커밋했다면 커밋이 가장 많은 레포(또는 언어)가 그날의 대표가 돼요.

### 2. 날짜를 캔버스 위치로 바꾸기

달력처럼 **주(week)는 가로, 요일은 세로**로 배치해요. 그날의 칸 중심에 약간의 무작위 흔들림을 더해서, 격자 느낌이 나지 않게 해요.
첫 기여가 나오기 전의 빈 주는 잘라내서, 최근에 시작한 사람도 캔버스가 꽉 차게 그려져요. (최소 16주는 유지)

### 3. 색 기준 고르기

언어 비율을 먼저 보고, 한 언어가 80% 이상이면 레포 기준으로, 레포도 하나뿐이면 기여량 기준으로 넘어가요.
그다음 **많이 쓴 순서대로** 팔레트 색을 배정해요. GitHub 공식 언어 색은 TypeScript와 Python처럼 서로 비슷한 경우가 있어서, 서로 확실히 구분되는 자체 팔레트를 써요.

### 4. 유체장 만들기

캔버스의 모든 위치에 "여기서는 이 방향으로 흘러라"라는 방향을 정해두는 단계예요.

| 단계 | 하는 일 |
|---|---|
| Perlin noise | 위치마다 부드럽게 변하는 값을 만듦. 가까운 위치끼리는 값도 비슷함 |
| 도메인 워핑 | 노이즈 값으로 좌표 자체를 한 번 더 비틀어서, 마블링 같은 소용돌이 모양을 만듦 |
| curl | 노이즈 값의 기울기를 구한 뒤 90도 돌려 흐름 방향으로 씀. 입자가 한 점으로 빨려 들지 않는 유체 흐름이 됨 |
| 오른쪽 바람 | 모든 방향에 오른쪽 성분을 조금 더함. 그림 전체가 시간 방향으로 흐름 |
| 시드 | 깃허브 아이디의 SHA-256 해시로 노이즈를 섞음. 아이디마다 다른 유체장, 같은 아이디는 매일 같은 유체장 |

```python
def angle(x, y):
    vx =  d(potential)/dy        # curl: 퍼텐셜의 기울기를 90도 회전
    vy = -d(potential)/dx
    return atan2(vy, vx + 0.55)  # 오른쪽으로 흐르는 바람 추가
```

### 5. 입자 흘려보내기

기여한 날마다 그 칸 주변에 입자를 뿌리고, 각 입자를 유체장을 따라 한 걸음(5px)씩 움직이며 궤적을 기록해요.

| 기여량이 많을수록 | 결과 |
|---|---|
| 입자 수 증가 (하루 최대 36개) | 색이 더 진하게 겹침 |
| 이동 거리 증가 | 더 멀리 흐르며 큰 곡선을 그림 |
| 굵은 입자 비율 증가 | 붓질이 두껍게 보임 |

입자 하나하나는 얇고 반투명해서, 수천 개가 겹치는 곳에서 색이 섞이며 물감처럼 보여요.
전체 입자 수는 약 2,200개로 제한해서, 기여가 아주 많은 사람도 파일이 너무 무거워지지 않아요.

### 6. SVG 조립

| 요소 | 하는 일 |
|---|---|
| 상대 좌표 경로 | 점마다 절대 위치 대신 이동량(`5 -1`)만 적어서 용량을 줄임 |
| 그룹·클래스 | 같은 날 입자의 색·시작 시간은 그룹에 한 번만, 굵기·투명도는 CSS 클래스로 재사용 |
| 마스크 | 위아래·좌우 가장자리와 제목 뒤쪽에서 입자가 부드럽게 사라짐 |
| 애니메이션 | `stroke-dashoffset`으로 입자가 그려지는 효과. 오래된 주부터 차례로 흘러나옴. `prefers-reduced-motion` 설정 시 정지 |
| 테마 | 라이트·다크 두 벌 생성. 다크에서는 블러를 겹쳐 빛 번짐 추가 |

README 이미지 안에서는 JavaScript가 실행되지 않기 때문에, 움직임은 모두 SVG 안의 CSS 애니메이션으로만 만들어요.

### 7. 자동 갱신

GitHub Actions가 매일 자정(KST)과 main에 push할 때마다 위 과정을 실행하고, 결과 SVG를 `output` 브랜치에 덮어써요.
이미지 주소가 항상 같아서, 프로필 README에 한 번만 붙여두면 커밋할수록 그림이 저절로 자라나요.

## 내 프로필에 붙이기

1. 이 레포를 Fork 해요.
2. Fork한 레포의 **Actions** 탭에서 워크플로를 활성화하고, `Generate Commit Canvas` → **Run workflow**를 눌러요.
3. 프로필 README에 아래를 붙여요 (`USER`를 내 아이디로).

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/USER/commit-canvas/output/commit-canvas-dark.svg">
  <img alt="Commit Canvas" src="https://raw.githubusercontent.com/USER/commit-canvas/output/commit-canvas.svg">
</picture>
```

## 로컬에서 돌려보기

```bash
python src/generate.py --user HHHv-v --demo --out dist/demo.svg            # 샘플 (여러 언어)
python src/generate.py --user HHHv-v --demo single --out dist/demo.svg     # 샘플 (한 언어, 여러 레포)
GITHUB_TOKEN=... python src/generate.py --user HHHv-v                      # 실제 데이터
```

| 옵션 | 값 | 기본값 |
|---|---|---|
| `--theme` | `dark` / `light` | `dark` |
| `--style` | `fluid` (입자 흐름) / `petal` (붓터치) | `fluid` |
| `--color` | `auto` / `language` / `repo` / `intensity` | `auto` |
| `--demo` | `multi` / `single` / `mono` (샘플 데이터 종류) | 실제 데이터 |

의존성 없이 Python 표준 라이브러리만 사용해요.

## 로드맵

- [x] 입자 유체 스타일 (`--style fluid`, 기본) / 붓터치 스타일 (`--style petal`)
- [x] 한 언어 사용자를 위한 색 기준 자동 선택
- [ ] Vercel API 버전 (`/api?user=...`) — Fork 없이 바로 사용
- [ ] 테마 추가 (수묵, 수채, 네온)

## License

MIT
