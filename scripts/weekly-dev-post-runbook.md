# 일반 개발 글 주간 발행

OpenClaw 예약 작업이 매주 수요일 11:40 Asia/Seoul에 이 문서를 읽고 실행한다. 모델은 예약 작업에 고정된 `openai/gpt-6-sol`, reasoning `high`다. 매주 **한 편**을 쓰며, 카테고리를 순환한다.

순환 순서: `java` → `python` → `nextjs` → `sql` → `data-infra` → 다시 `java`. `ai`/`ai-daily-news`와 `github-repo-analysis`는 별도 작업이므로 포함하지 않는다.

1. `/root/.openclaw/workspace/qoxmfaktmxj.github.io`에서 `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`을 수행한다. 무관한 로컬 변경은 보존한다.
2. KST 오늘 날짜로 이미 일반 개발 글(`_posts/YYYY-MM-DD-study-*.md`)이 있으면 `NO_REPLY`로 종료한다.
3. `.automation/weekly_study_rotation.json`을 읽어 `next_index`에 해당하는 카테고리를 선택한다. 파일이 없으면 0(`java`)부터 시작한다. 기존 `.automation/state.json`은 과거 수동 워크플로의 상태이므로 건드리지 않는다.
4. 선택 카테고리의 기존 글 제목과 최근 내용을 먼저 살펴 중복 주제를 피한다. 공개 공식 문서/릴리스 노트/표준 문서를 우선 조사한다. 확인되지 않은 버전·API·성능 주장은 쓰지 않는다.
5. 중급 개발자 이상을 위한 한국어 실무 글을 작성한다. 단순 입문 정의보다 문제 상황, 동작 원리, 설계 선택과 트레이드오프, 구체적인 코드/SQL 예시, 실패 사례와 검증 방법을 깊게 다룬다. 기존 짧은 글보다 약 2배 이상 자세하게 작성한다. 근거 링크를 끝에 둔다.
6. `_posts/YYYY-MM-DD-study-<구체적-주제-slug>.md`로 저장한다. front matter에는 `layout: post`, 제목, KST `date`, 선택 `categories: [<category>]`, 관련 `tags`를 넣는다. 한 주에 한 편만 발행한다.
7. 중복·사실관계·마크다운/코드 블록을 점검한다. 품질이 부족하면 발행하지 말고 짧게 실패를 보고한다.
8. 발행에 성공한 뒤에만 `.automation/weekly_study_rotation.json`의 `next_index`를 `(현재+1) % 5`로 갱신하고, `last_category`와 `last_published_at`을 기록한다. 새 글과 이 상태 파일만 stage·commit·push `origin main`한다. 원격 반영을 확인한다.
9. 성공 시 실제 게시글 URL 한 줄을 반환한다. 이미 오늘 글이 있으면 `NO_REPLY`, 실패 시 `일반 개발 글 발행 실패: <짧은 원인>` 한 줄을 반환한다.
