# qoxmfaktmxj.github.io

한국어 자동화 블로그 저장소입니다.

- 매일 AI 뉴스 요약 글 1개 자동 생성
- 매일 개발 학습 글 1개 자동 생성(주제 순환)
- 사이드바 카테고리: AI Daily News / Python / Next.js / Java / SQL / Data Infra

GitHub Actions + Anthropic API로 글을 만들고, GitHub Pages로 배포합니다.

## 1회 설정

1. 저장소 시크릿/변수 설정
- `Settings -> Secrets and variables -> Actions`
- `Repository secrets`에 `ANTHROPIC_API_KEY` 추가
- 선택 사항: `Repository variables`에 `ANTHROPIC_MODEL` 추가
  - 기본값: `claude-haiku-4-5-20251001`

2. GitHub Pages 설정
- `Settings -> Pages`
- Build and deployment -> Source: `GitHub Actions`

3. 배포
- `main` 또는 `master` 브랜치에 push
- `pages-deploy.yml`: 사이트 배포
- `auto-post.yml`: 매일 `00:15 UTC` 자동 실행 + 수동 실행 가능

## 학습 카테고리 정책

- `AI Daily News`: 자동 뉴스 요약
- `Python`: Python/FastAPI/Pydantic 계열
- `Next.js`: Next.js/React/TypeScript 계열
- `Java`: Java/Spring 계열
- `SQL`: Oracle/PostgreSQL/MySQL/Redis 계열
- `Data Infra`: Elasticsearch/Kafka 계열

## 로컬 테스트

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=your_key
python scripts/auto_post.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r scripts/requirements.txt
$env:ANTHROPIC_API_KEY="your_key"
py -3 scripts/auto_post.py
```

## 자동 생성 파일

- 글: `_posts/YYYY-MM-DD-*.md`
- 주제 순환 상태: `.automation/state.json`

## 네이버 블로그 이전

네이버 블로그(`qoxmfaktmxj`) 글을 markdown으로 가져올 수 있습니다.

```powershell
pip install -r scripts/requirements.txt
py -3 scripts/import_naver_blog.py --blog-id qoxmfaktmxj
```

옵션:
- `--limit 10`: 최신 10개만 이전
- `--no-skip-existing`: 기존 파일이 있어도 다시 생성
