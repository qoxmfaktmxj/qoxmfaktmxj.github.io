# GitHub Trending 저장소 리뷰

OpenClaw 예약 작업이 매주 화·금 07:10 Asia/Seoul에 이 문서를 읽고 실행한다. 글 작성 모델은 예약 작업에 고정된 `openai/gpt-6-sol`, reasoning `high`다. GitHub Actions나 별도 API 키로 글을 생성하지 않는다.

1. 저장소 `/root/.openclaw/workspace/qoxmfaktmxj.github.io`의 `main`에서 `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`을 수행한다. 기존의 무관한 로컬 파일은 건드리지 않는다.
2. KST 오늘 날짜의 `_posts/YYYY-MM-DD-repo-deep-dive-*.md`가 이미 있으면 `NO_REPLY`로 끝낸다.
3. `python3 scripts/trending_repo.py`를 실행한다. 이 도구는 실행 시점의 [GitHub Trending 일간 전체 언어 목록](https://github.com/trending?since=daily)을 순서대로 읽고, **현재 남아 있는 게시글의 `repo:`**에 있는 저장소를 건너뛰어 첫 미리뷰 저장소와 당시 순위를 반환한다. 삭제된 옛 글은 리뷰한 것으로 취급하지 않는다. 목록 파싱에 실패하면 임의의 GitHub 검색 순위로 대체하지 말고 실패로 보고한다.
4. 선택된 저장소의 현재 README와 공식 문서/사용 예시/릴리스 자료를 확인한다. README의 제품 설명만 복사하지 말고 구체적인 기능과 실제 사용 절차를 교차 확인한다. 확인하지 못한 구현·성능·보안 특성은 단정하지 않는다.
5. `_posts/YYYY-MM-DD-repo-deep-dive-<owner>-<repo>.md`에 한국어 글을 작성한다. 본문은 최소 2,500자 이상, 아래 6개 주제 중심으로 충분히 자세하게 작성한다. 한 문장 요약, 디렉터리·설정 파일 나열, 일반론적 교훈, 다른 개인 프로젝트 적용 아이디어는 넣지 않는다.
   - 프로젝트 소개: 무엇이고 누가 만드는지, 어떤 상황에서 쓰는지
   - 해결하려는 문제: 기존 접근의 불편과 이 프로젝트의 접근 방식
   - 주요 기능: 확인된 기능별 입력·출력과 차이
   - 사용 방법과 동작 흐름: 설치/요구사항, 최소 예시, 결과를 읽는 방법
   - 활용 사례: 공식 예시 또는 문서로 뒷받침되는 시나리오
   - 참고 자료: 저장소/README/공식 문서/검증한 사례 링크
6. front matter에는 `layout: post`, `title`, KST `date`, `categories: [github-repo-analysis]`, `repo`, `trending_rank`, `trending_period: daily`, `trending_checked_at`, `trending_url`을 기록한다. 순위는 글 발행 시점 실시간 순위가 아닌 **선정 시점 스냅샷**임을 본문에 명시한다.
7. 본문에 근거 없는 주장, 빈/중복 섹션, 깨진 링크가 없는지 확인한다. 초안 품질이 부족하거나 소스에 접근할 수 없으면 발행하지 않고 실패 이유를 보고한다.
8. 글 작성 성공 후 `.automation/star_repo_analysis.json`의 `analyzed`에 선택 저장소를 추가하고 `last_run_at`을 KST 시각으로 갱신한다. `selection_mode: github_trending_daily`와 `last_trending_rank`도 기록한다. 글과 상태 파일 **두 개만** stage·commit·push `origin main`한다. push 후 원격 SHA와 새 글 경로를 확인한다.
9. 성공 시 게시글 URL 한 줄을 반환한다. 실패 시 `GitHub Trending 리뷰 실패: <짧은 원인>` 한 줄을 반환한다. 같은 날 재실행에서는 중복 발행하지 않는다.
