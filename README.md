# Commit Canvas 🎨

1년치 GitHub 기여를 **한 점의 추상화**로 그려주는 프로필 위젯이에요.
같은 그림은 하나도 없어요. 내가 커밋한 날, 쓴 언어, 쉬어간 시간이 모두 붓터치와 여백이 됩니다.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/demo-dark.svg">
  <img alt="Commit Canvas demo" src="docs/demo-light.svg">
</picture>

## 그림 규칙

| 데이터 | 그림 |
|---|---|
| 1주 | 세로 한 줄 (왼쪽 → 오른쪽으로 1년이 흐름) |
| 기여한 날 | 붓터치 — 많을수록 길고 굵고 여러 번 덧칠 |
| 커밋한 레포의 주 언어 | 물감 색 (GitHub 언어 색) |
| 깃허브 아이디 | 붓이 흐르는 방향 → 사람마다 다른 그림 |
| 7일 이상 연속 기여 | 금색 점선 |
| 쉬어간 기간 | 여백 |

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
python src/generate.py --user HHHv-v --demo --out dist/demo.svg     # 샘플 데이터
GITHUB_TOKEN=... python src/generate.py --user HHHv-v               # 실제 데이터
```

의존성 없이 Python 표준 라이브러리만 사용해요.

## 로드맵

- [ ] 끝이 가늘어지는 붓 모양 터치
- [ ] Vercel API 버전 (`/api?user=...`) — Fork 없이 바로 사용
- [ ] 테마 추가 (수묵, 수채, 네온)

## License

MIT
