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

## 자동화 워크플로

### 1. `auto-post.yml`

수동 실행용 글 생성 워크플로입니다.

- GitHub Actions의 `workflow_dispatch`로만 실행됩니다.
- 항상 `main` 브랜치를 기준으로 체크아웃합니다.
- `scripts/auto_post.py`를 실행해 당일 포스트를 생성합니다.
- 변경이 있으면 GitHub Actions 봇 계정으로 커밋 후 `main`에 푸시합니다.
- 실패 시 GitHub Issue를 만들고, Telegram 시크릿이 있으면 알림을 보냅니다.

중요:

- 현재는 스케줄 실행이 아니라 수동 실행만 설정되어 있습니다.
- 워크플로 내부도 `main only` 기준으로 보호되어 있습니다.

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

## 필요한 GitHub 설정

### Repository secrets

- `ANTHROPIC_API_KEY`
- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

Telegram 알림이 필요 없으면 `TG_BOT_TOKEN`, `TG_CHAT_ID`는 비워둘 수 있습니다.

### Repository variables

- `ANTHROPIC_MODEL` (선택)

지정하지 않으면 `scripts/auto_post.py`에서 기본값 `claude-haiku-4-5-20251001`을 사용합니다.

### GitHub Pages

- `Settings -> Pages`
- Build and deployment -> Source: `GitHub Actions`

## 콘텐츠 생성 스크립트

### 1. `scripts/auto_post.py`

하루 글 생성 스크립트입니다.

생성 대상:

- AI 뉴스 요약 글 1개
- 개발 학습 글 1개

동작 방식:

- RSS 피드를 읽어 AI 뉴스 후보를 수집합니다.
- Anthropic API를 호출해 한국어 블로그 글을 생성합니다.
- 학습 글은 내부 토픽 순환 목록을 따라 생성합니다.
- 상태 파일 `.automation/state.json`에 다음 학습 주제를 기록합니다.

현재 학습 토픽 순환:

- Python
- Next.js
- Java
- PostgreSQL SQL
- MySQL SQL
- Oracle SQL
- Redis
- Elasticsearch
- Apache Kafka

생성 파일 위치:

- `_posts/YYYY-MM-DD-ai-news-daily.md`
- `_posts/YYYY-MM-DD-study-<topic>.md`

### 2. `scripts/import_naver_blog.py`

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

### 자동 글 생성

PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your_key"
$env:ANTHROPIC_MODEL="claude-haiku-4-5-20251001"  # 선택
py -3 scripts/auto_post.py
```

macOS/Linux:

```bash
export ANTHROPIC_API_KEY=your_key
export ANTHROPIC_MODEL=claude-haiku-4-5-20251001  # 선택
python scripts/auto_post.py
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
