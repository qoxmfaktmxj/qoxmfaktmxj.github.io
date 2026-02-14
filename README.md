# qoxmfaktmxj.github.io

개발 블로그 자동화 저장소입니다.

- 매일 AI 뉴스 요약 글 1개 자동 생성
- 매일 개발 학습 글 1개 자동 생성(주제 순환)
- Hashnode 스타일 그리드 레이아웃
- 좌측 검색: 제목/본문 검색 후 클릭 이동

## 현재 카테고리

- `AI Daily News`
- `Python`
- `Next.js`
- `Java`
- `SQL` (Oracle/PostgreSQL/MySQL/Redis)
- `Data Infra` (Elasticsearch/Kafka)

## 1회 설정

1. 저장소 시크릿/변수
- `Settings -> Secrets and variables -> Actions`
- `Repository secrets`에 `ANTHROPIC_API_KEY` 추가
- 선택: `Repository variables`에 `ANTHROPIC_MODEL` 추가
  - 기본값: `claude-haiku-4-5-20251001`

2. GitHub Pages
- `Settings -> Pages`
- Build and deployment -> Source: `GitHub Actions`

3. 배포
- `main` 또는 `master` 브랜치에 push
- `pages-deploy.yml`: 사이트 배포
- `auto-post.yml`: 매일 `00:15 UTC` 자동 실행 + 수동 실행 가능

## 댓글(giscus) 설정

giscus는 GitHub Discussions 기반 댓글입니다.

1. `Settings -> General`에서 Discussions 활성화
2. https://giscus.app/ 에서 레포 선택 후 설정 생성
3. 출력된 값 중 아래를 `_config.yml`에 반영
- `comments.giscus.repo_id`
- `comments.giscus.category`
- `comments.giscus.category_id`

`category_id`가 비어 있으면 댓글 영역에 안내 문구가 표시됩니다.

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

## 네이버 블로그 이전

네이버 블로그(`qoxmfaktmxj`) 글을 markdown으로 가져옵니다.

```powershell
pip install -r scripts/requirements.txt
py -3 scripts/import_naver_blog.py --blog-id qoxmfaktmxj
```

옵션:
- `--limit 10`: 최신 10개만 이전
- `--no-skip-existing`: 기존 파일이 있어도 다시 생성

