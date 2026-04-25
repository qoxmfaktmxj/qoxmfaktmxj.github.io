#!/usr/bin/env python3
"""Generate a Korean GitHub 50k+ star repository deep-dive draft.

Safety defaults:
- never overwrites an existing post
- tracks analyzed repositories in .automation/star_repo_analysis.json
- respects a 2-day cadence unless --force is passed
- uses GITHUB_TOKEN when present, but works unauthenticated with lower rate limits
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT_DIR / "_posts"
STATE_FILE = ROOT_DIR / ".automation" / "star_repo_analysis.json"
CONFIG_FILE = ROOT_DIR / "_config.yml"
KST = timezone(timedelta(hours=9))

DEFAULT_STATE = {
    "min_stars": 50000,
    "cadence_days": 2,
    "last_generated_at": None,
    "last_generated_repo": None,
    "analyzed_repos": [],
}


@dataclass(frozen=True)
class RepoCandidate:
    full_name: str
    html_url: str
    description: str
    stars: int
    forks: int
    open_issues: int
    language: str
    default_branch: str
    pushed_at: str
    updated_at: str
    topics: list[str]
    license_name: str


def now_kst() -> datetime:
    return datetime.now(KST)


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return dict(DEFAULT_STATE)
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    state = dict(DEFAULT_STATE)
    state.update(data)
    if not isinstance(state.get("analyzed_repos"), list):
        state["analyzed_repos"] = []
    return state


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "qoxmfaktmxj-github-deep-dive-bot",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(url: str, *, raw: bool = False, timeout: int = 30) -> Any:
    headers = github_headers()
    if raw:
        headers["Accept"] = "application/vnd.github.raw"
    response = requests.get(url, headers=headers, timeout=timeout)
    if response.status_code == 403 and "rate limit" in response.text.lower():
        raise RuntimeError("GitHub API rate limit reached. Set GITHUB_TOKEN or retry later.")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    if raw:
        return response.text
    return response.json()


def scan_existing_analyzed_repos() -> set[str]:
    repos: set[str] = set()
    for path in POSTS_DIR.glob("*-github-deep-dive-*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")[:2000]
        match = re.search(r"^source_repo:\s*\"?([^\"\n]+)\"?\s*$", text, flags=re.MULTILINE)
        if match:
            repos.add(match.group(1).strip())
    return repos


def parse_repo(item: dict[str, Any]) -> RepoCandidate:
    license_info = item.get("license") or {}
    return RepoCandidate(
        full_name=str(item.get("full_name", "")),
        html_url=str(item.get("html_url", "")),
        description=str(item.get("description") or ""),
        stars=int(item.get("stargazers_count") or 0),
        forks=int(item.get("forks_count") or 0),
        open_issues=int(item.get("open_issues_count") or 0),
        language=str(item.get("language") or "Unknown"),
        default_branch=str(item.get("default_branch") or "main"),
        pushed_at=str(item.get("pushed_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
        topics=list(item.get("topics") or []),
        license_name=str(license_info.get("spdx_id") or license_info.get("name") or "Unknown"),
    )


def find_next_candidate(min_stars: int, analyzed: set[str]) -> RepoCandidate | None:
    # The search API caps at 1,000 results. We only need the next highest-star unseen repo.
    query = quote(f"stars:>={min_stars}")
    for page in range(1, 11):
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=100&page={page}"
        data = github_get(url)
        for item in data.get("items", []):
            repo = parse_repo(item)
            if repo.full_name and repo.full_name not in analyzed:
                return repo
    return None


def fetch_languages(full_name: str) -> dict[str, int]:
    data = github_get(f"https://api.github.com/repos/{full_name}/languages")
    return data or {}


def fetch_readme(full_name: str) -> str:
    data = github_get(f"https://api.github.com/repos/{full_name}/readme")
    if not data:
        return ""
    content = data.get("content")
    if not content:
        return ""
    try:
        return base64.b64decode(content).decode("utf-8", errors="ignore")[:12000]
    except Exception:
        return ""


def fetch_tree(full_name: str, branch: str) -> list[str]:
    data = github_get(f"https://api.github.com/repos/{full_name}/git/trees/{quote(branch, safe='')}?recursive=1")
    if not data:
        return []
    paths = []
    for item in data.get("tree", []):
        path = str(item.get("path") or "")
        if not path or item.get("type") != "blob":
            continue
        if any(part in path for part in [".git/", "node_modules/", "vendor/", "dist/", "build/"]):
            continue
        paths.append(path)
    return paths[:800]


def top_dirs(paths: list[str], limit: int = 12) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for path in paths:
        first = path.split("/", 1)[0]
        if first and not first.startswith("."):
            counts[first] = counts.get(first, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]


def notable_files(paths: list[str]) -> list[str]:
    wanted_names = {
        "README.md", "package.json", "pnpm-workspace.yaml", "pyproject.toml", "Cargo.toml",
        "go.mod", "pom.xml", "build.gradle", "docker-compose.yml", "Dockerfile", "Makefile",
        "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md", "CODE_OF_CONDUCT.md",
    }
    picked = [p for p in paths if p.split("/")[-1] in wanted_names]
    workflow = [p for p in paths if p.startswith(".github/workflows/")]
    return sorted(set(picked + workflow))[:40]


def extract_readme_signals(readme: str) -> list[str]:
    signals = []
    for line in readme.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            signals.append(stripped[:160])
        elif len(signals) < 4 and len(stripped) > 40:
            signals.append(stripped[:220])
        if len(signals) >= 12:
            break
    return signals


def slugify(value: str) -> str:
    value = value.lower().replace("/", "-")
    value = re.sub(r"[^a-z0-9가-힣-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "repo"


def quote_yaml(value: str) -> str:
    return value.replace('"', '\\"')


def format_number(value: int) -> str:
    return f"{value:,}"


def language_summary(languages: dict[str, int]) -> str:
    if not languages:
        return "확인 필요"
    total = sum(languages.values()) or 1
    rows = []
    for name, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:8]:
        rows.append(f"- **{name}**: {count / total * 100:.1f}%")
    return "\n".join(rows)


def build_post(repo: RepoCandidate, languages: dict[str, int], readme: str, paths: list[str], now: datetime) -> tuple[str, str]:
    title = f"GitHub 50K+ Repo Deep Dive: {repo.full_name}"
    dirs = top_dirs(paths)
    files = notable_files(paths)
    readme_signals = extract_readme_signals(readme)
    topic_text = ", ".join(repo.topics[:12]) if repo.topics else "확인 필요"
    dirs_text = "\n".join(f"- `{name}/`: {count} files" for name, count in dirs) or "- 확인 필요"
    files_text = "\n".join(f"- `{path}`" for path in files) or "- 확인 필요"
    signals_text = "\n".join(f"- {line}" for line in readme_signals) or "- 확인 필요"

    content = f'''## 한 줄 요약

`{repo.full_name}`는 GitHub star {format_number(repo.stars)}개 이상을 받은 오픈소스 프로젝트다. 이 글은 README, repository metadata, language breakdown, file tree를 기준으로 구조와 설계 포인트를 분석한다.

> 분석 기준 시각: {now.strftime('%Y-%m-%d %H:%M KST')}  
> Source: [{repo.full_name}]({repo.html_url})

## Repository Snapshot

| 항목 | 값 |
|---|---|
| Stars | {format_number(repo.stars)} |
| Forks | {format_number(repo.forks)} |
| Open Issues | {format_number(repo.open_issues)} |
| Primary Language | {repo.language} |
| Default Branch | `{repo.default_branch}` |
| License | {repo.license_name} |
| Last Pushed | {repo.pushed_at or '확인 필요'} |
| Topics | {topic_text} |

## 이 프로젝트가 해결하는 문제

{repo.description or 'README/description 기준 설명이 부족해 확인 필요.'}

README에서 확인되는 초기 신호는 다음과 같다.

{signals_text}

## 기술 스택과 언어 구성

{language_summary(languages)}

언어 비중만으로 아키텍처를 단정할 수는 없다. 다만 primary language와 상위 language 조합은 runtime, tooling, extension surface를 추정하는 첫 단서가 된다.

## 코드베이스 구조 관찰

상위 디렉터리 분포:

{dirs_text}

눈에 띄는 운영/빌드/문서 파일:

{files_text}

이 구조에서 먼저 확인할 지점은 다음이다.

- **진입점**  
  README의 quickstart와 실제 build/test entrypoint가 일치하는지 확인해야 한다.
- **확장 경계**  
  plugin, package, module, examples 디렉터리가 있는 경우 public API와 internal API의 경계를 봐야 한다.
- **운영 성숙도**  
  CI workflow, security policy, contributing guide, changelog 유무가 유지보수 성숙도를 보여준다.

## 설계적으로 배울 점

- **작은 진입 장벽**  
  50K+ star 프로젝트는 대개 첫 실행 경험이 강하다. README, examples, quickstart가 제품의 일부처럼 관리된다.
- **문서와 코드의 연결**  
  문서가 단순 소개가 아니라 구조 탐색 지도 역할을 해야 대규모 사용자가 유입돼도 유지보수 비용이 낮아진다.
- **기여 경로의 명확성**  
  issue, PR, release, changelog 흐름이 명확할수록 외부 기여가 제품 품질로 흡수된다.

## 석의 프로젝트에 적용할 인사이트

### Vibe 계열

- README만 보고 local dev와 핵심 demo를 실행할 수 있어야 한다.
- `examples/`, `docs/`, `tests/`가 제품 신뢰도를 만드는 핵심 표면이다.
- VibeGrid처럼 라이브러리 성격이 강한 repo는 public API stability 문서가 중요하다.

### Jarvis / LLM Wiki

- raw 자료보다 compiled documentation이 탐색성을 만든다.
- wiki page, lint report, examples를 repo root에서 쉽게 찾을 수 있어야 한다.

### Blog 운영

- 단순 소개 글보다 “구조 → 설계 선택 → 트레이드오프 → 내 프로젝트 적용점” 형식을 반복하면 장기적으로 학습 자산이 된다.

## 더 깊게 볼 다음 질문

- 이 repo의 가장 작은 실행 단위는 무엇인가?
- public API와 internal implementation의 경계는 어디인가?
- CI가 실제 사용자 시나리오를 얼마나 보호하는가?
- breaking change를 어떻게 관리하는가?
- 내 프로젝트에 가져올 수 있는 문서/테스트/릴리즈 패턴은 무엇인가?

## Source Links

- GitHub: {repo.html_url}
- README/API metadata inspected through GitHub API
'''
    return title, content


def should_skip_for_cadence(state: dict[str, Any], now: datetime, force: bool) -> str | None:
    if force:
        return None
    last = state.get("last_generated_at")
    if not last:
        return None
    try:
        last_dt = datetime.fromisoformat(str(last))
    except ValueError:
        return None
    cadence_days = int(state.get("cadence_days") or 2)
    next_allowed = last_dt + timedelta(days=cadence_days)
    if now < next_allowed:
        return f"Cadence skip. Next allowed at {next_allowed.isoformat()}"
    return None


def write_post(path: Path, repo: RepoCandidate, title: str, content: str, now: datetime) -> None:
    frontmatter = (
        "---\n"
        "layout: post\n"
        f'title: "{quote_yaml(title)}"\n'
        f"date: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
        "categories: [github-deep-dive]\n"
        "tags: [github, open-source, architecture, deep-dive, automation]\n"
        f'source_repo: "{repo.full_name}"\n'
        f'source_url: "{repo.html_url}"\n'
        f"source_stars: {repo.stars}\n"
        "---\n\n"
    )
    path.write_text(frontmatter + content.strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-stars", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Ignore 2-day cadence guard")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and render candidate summary without writing files")
    args = parser.parse_args()

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    now = now_kst()

    skip_reason = should_skip_for_cadence(state, now, args.force)
    if skip_reason:
        print(skip_reason)
        return 0

    min_stars = int(args.min_stars or state.get("min_stars") or 50000)
    analyzed = set(str(x) for x in state.get("analyzed_repos", []))
    analyzed |= scan_existing_analyzed_repos()

    repo = find_next_candidate(min_stars=min_stars, analyzed=analyzed)
    if not repo:
        print(f"No unanalyzed GitHub repository found with stars >= {min_stars}.")
        state["exhausted_at"] = now.isoformat()
        if not args.dry_run:
            save_state(state)
        return 0

    languages = fetch_languages(repo.full_name)
    readme = fetch_readme(repo.full_name)
    paths = fetch_tree(repo.full_name, repo.default_branch)
    title, content = build_post(repo, languages, readme, paths, now)

    slug = slugify(repo.full_name)
    post_path = POSTS_DIR / f"{now.strftime('%Y-%m-%d')}-github-deep-dive-{slug}.md"
    if post_path.exists():
        print(f"Post already exists for today: {post_path.name}")
        return 0

    if args.dry_run:
        print(f"DRY RUN candidate: {repo.full_name} ({repo.stars:,} stars)")
        print(f"Would create: {post_path}")
        print(title)
        return 0

    write_post(post_path, repo, title, content, now)
    analyzed.add(repo.full_name)
    state["min_stars"] = min_stars
    state["last_generated_at"] = now.isoformat()
    state["last_generated_repo"] = repo.full_name
    state["analyzed_repos"] = sorted(analyzed)
    state.pop("exhausted_at", None)
    save_state(state)

    print(f"Created: {post_path.relative_to(ROOT_DIR)}")
    print(f"Repo: {repo.full_name} ({repo.stars:,} stars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
