# qoxmfaktmxj.github.io

Jekyll 기반 개인 기술 블로그 저장소입니다.  
GitHub Pages로 배포되며, AI 뉴스 요약 글과 개발 학습 글을 함께 운영합니다.

## 현재 구성

- 정적 사이트 엔진: Jekyll (`minima` 테마)
- 배포 주소: `https://qoxmfaktmxj.github.io`
- 시간대: `Asia/Seoul`
- 댓글: giscus
- 방문자 집계: GoatCounter
- 포스트 저장 위치: `_posts/`

## 카테고리

현재 저장소에는 아래 카테고리 페이지가 있습니다.

- `AI`
- `AI Daily News`
- `Python`
- `Next.js`
- `Java`
- `SQL`
- `Data Infra`
- `GitHub Repo Analysis`

## 자동화 워크플로

### 1. 일반 개발 글 (OpenClaw)

매주 수요일 11:40 KST에 `java → python → nextjs → sql → data-infra` 순서로 한 편씩 발행합니다. `openai/gpt-6-sol`, reasoning `high`를 사용하며 AI Daily News와 레포 리뷰는 별도 일정입니다. 작성 절차는 [`scripts/weekly-dev-post-runbook.md`](scripts/weekly-dev-post-runbook.md)를 따릅니다.

### 2. `pages-deploy.yml`

GitHub Pages 배포 워크플로입니다.

- `main` 브랜치 push 시 실행됩니다.
- 수동 실행도 가능합니다.
- Jekyll 빌드 후 GitHub Pages에 배포합니다.

참고:

- 파일 안에는 `workflow_run` 트리거도 정의되어 있지만, 현재 기준으로는 `main` push와 수동 실행 흐름을 기준으로 이해하는 것이 가장 정확합니다.

### 3. `giscus-comment-alert.yml`

GitHub Discussions 기반 댓글 알림 워크플로입니다.

- 새 discussion comment가 생성되면 실행됩니다.
- 저장소 소유자 본인 댓글과 Bot 댓글은 제외합니다.
- Telegram 시크릿이 설정되어 있으면 알림을 보냅니다.

### 4. GitHub Trending 저장소 리뷰

OpenClaw 예약 작업이 GitHub Trending 일간 목록에서 현재 순위가 가장 높은 미리뷰 저장소를 골라 `GitHub Repo Analysis` 글을 작성합니다.

- 매주 화·금 07:10 KST에 실행됩니다.
- 이미 리뷰한 1위는 건너뛰고 당시 목록의 2위, 2위도 리뷰했다면 3위로 내려갑니다.
- 모델은 OpenClaw의 `openai/gpt-6-sol`, reasoning `high`이며 Claude API는 사용하지 않습니다.
- 작성 기준과 발행 절차: [`scripts/trending-repo-review-runbook.md`](scripts/trending-repo-review-runbook.md).

## 필요한 GitHub 설정

### Repository secrets

- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

Telegram 알림이 필요 없으면 `TG_BOT_TOKEN`, `TG_CHAT_ID`는 비워둘 수 있습니다.

### GitHub Pages

- `Settings -> Pages`
- Build and deployment -> Source: `GitHub Actions`

## 콘텐츠 생성 스크립트

### `scripts/import_naver_blog.py`

네이버 블로그 글을 Jekyll 포스트로 가져오는 스크립트입니다.

기능:

- Naver RSS를 읽어 글 목록 수집
- 모바일 본문 HTML 파싱
- Markdown 변환
- 카테고리 자동 분류
- `_posts/YYYY-MM-DD-naver-<logNo>.md` 형식으로 저장

추가 front matter:

- `naver_source`
- `categories: [<mapped-category>, naver-archive]`
- `tags: [naver-import]`

## 로컬 실행

### Python 가상환경 준비

PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r scripts/requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### 네이버 글 가져오기

PowerShell:

```powershell
py -3 scripts/import_naver_blog.py --blog-id qoxmfaktmxj
```

자주 쓰는 옵션:

- `--limit 10`: 최신 10개만 가져오기
- `--no-skip-existing`: 기존 파일이 있어도 다시 생성

## 로컬 사이트 빌드

Jekyll 빌드 확인:

```powershell
bundle exec jekyll build
```

로컬 서버 실행:

```powershell
bundle exec jekyll serve
```

## 파일 구조

```text
.
├─ .github/workflows/
├─ _posts/
├─ categories/
├─ scripts/
├─ _layouts/
├─ _includes/
├─ _data/
├─ _config.yml
└─ README.md
```

## 운영 메모

- 블로그 배포 기준 브랜치는 `main`입니다.
- 자동 생성 워크플로도 `main` 브랜치를 기준으로 동작합니다.
- `_site/`는 Jekyll 빌드 결과물입니다.
- `.automation/state.json`은 학습 글 토픽 순환 상태를 저장합니다.
