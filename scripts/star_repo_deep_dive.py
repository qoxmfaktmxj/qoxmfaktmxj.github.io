#!/usr/bin/env python3
"""Generate a GitHub 50k+ star repository deep-dive post.

Contract:
- GitHub query: stars:>50000 fork:false archived:false, stars desc
- Exclude repos listed in .automation/star_repo_analysis.json: analyzed
- Skip if last_run_at is within 48 hours
- Mark exhausted=true when no candidate remains
- Never print API keys/secrets
- Write state atomically so failures do not corrupt it
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT_DIR / "_posts"
STATE_FILE = ROOT_DIR / ".automation" / "star_repo_analysis.json"
KST = timezone(timedelta(hours=9))

DEFAULT_STATE: dict[str, Any] = {
    "min_stars": 50000,
    "last_run_at": None,
    "analyzed": [],
    "exhausted": False,
    "last_candidate_refresh": None,
}

QUERY_TEMPLATE = "stars:>{min_stars} fork:false archived:false"


@dataclass(frozen=True)
class RepoCandidate:
    owner: str
    name: str
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


def iso_now_kst() -> str:
    return now_kst().isoformat(timespec="seconds")


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return dict(DEFAULT_STATE)

    try:
        loaded = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("[WARN] State file is invalid JSON. Using default state without overwriting it yet.")
        return dict(DEFAULT_STATE)

    state = dict(DEFAULT_STATE)
    state.update(loaded if isinstance(loaded, dict) else {})
    if not isinstance(state.get("analyzed"), list):
        state["analyzed"] = []
    if not isinstance(state.get("exhausted"), bool):
        state["exhausted"] = False
    return state


def atomic_save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        tmp.write(serialized)
        tmp_path = Path(tmp.name)
    tmp_path.replace(STATE_FILE)


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "qoxmfaktmxj-star-repo-deep-dive",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(url: str, *, timeout: int = 30) -> Any:
    response = requests.get(url, headers=github_headers(), timeout=timeout)
    if response.status_code == 403 and "rate limit" in response.text.lower():
        raise RuntimeError("GitHub API rate limit reached. Set GITHUB_TOKEN or retry later.")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def parse_repo(item: dict[str, Any]) -> RepoCandidate:
    owner = str((item.get("owner") or {}).get("login") or "")
    name = str(item.get("name") or "")
    license_info = item.get("license") or {}
    return RepoCandidate(
        owner=owner,
        name=name,
        full_name=str(item.get("full_name") or f"{owner}/{name}"),
        html_url=str(item.get("html_url") or ""),
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
    query = quote(QUERY_TEMPLATE.format(min_stars=min_stars))
    for page in range(1, 11):
        url = (
            "https://api.github.com/search/repositories"
            f"?q={query}&sort=stars&order=desc&per_page=100&page={page}"
        )
        data = github_get(url)
        for item in data.get("items", []):
            repo = parse_repo(item)
            if repo.full_name and repo.full_name not in analyzed:
                return repo
    return None


def fetch_languages(repo: RepoCandidate) -> dict[str, int]:
    return github_get(f"https://api.github.com/repos/{repo.full_name}/languages") or {}


def fetch_readme(repo: RepoCandidate) -> str:
    data = github_get(f"https://api.github.com/repos/{repo.full_name}/readme")
    if not data or not data.get("content"):
        return ""
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")[:16000]
    except Exception:
        return ""


def fetch_tree(repo: RepoCandidate) -> list[str]:
    branch = quote(repo.default_branch, safe="")
    data = github_get(f"https://api.github.com/repos/{repo.full_name}/git/trees/{branch}?recursive=1")
    if not data:
        return []
    paths: list[str] = []
    for item in data.get("tree", []):
        path = str(item.get("path") or "")
        if item.get("type") != "blob" or not path:
            continue
        if any(part in path for part in ["node_modules/", "vendor/", "dist/", "build/", ".git/"]):
            continue
        paths.append(path)
    return paths[:1000]


def fetch_config_files(repo: RepoCandidate, paths: list[str]) -> dict[str, str]:
    important_names = {
        "package.json",
        "pnpm-workspace.yaml",
        "pyproject.toml",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "settings.gradle",
        "docker-compose.yml",
        "Dockerfile",
        "Makefile",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
    }
    selected = [p for p in paths if p.split("/")[-1] in important_names or p.startswith(".github/workflows/")]
    result: dict[str, str] = {}
    for path in selected[:20]:
        url = f"https://api.github.com/repos/{repo.full_name}/contents/{quote(path, safe='/')}?ref={quote(repo.default_branch, safe='')}"
        data = github_get(url)
        if not data or not data.get("content") or data.get("encoding") != "base64":
            continue
        try:
            text = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        except Exception:
            continue
        result[path] = text[:3000]
    return result


def top_dirs(paths: list[str], limit: int = 12) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    root_files = 0
    for path in paths:
        if "/" not in path:
            root_files += 1
            continue
        first = path.split("/", 1)[0]
        if first and not first.startswith("."):
            counts[first] = counts.get(first, 0) + 1
    if root_files:
        counts["<root files>"] = root_files
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]


def readme_signals(readme: str) -> list[str]:
    signals: list[str] = []
    for line in readme.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("#") or len(text) >= 60:
            signals.append(text[:220])
        if len(signals) >= 12:
            break
    return signals


def language_summary(languages: dict[str, int]) -> str:
    if not languages:
        return "- 확인 필요"
    total = sum(languages.values()) or 1
    return "\n".join(
        f"- **{name}**: {count / total * 100:.1f}%"
        for name, count in sorted(languages.items(), key=lambda item: item[1], reverse=True)[:10]
    )


def config_summary(config_files: dict[str, str]) -> str:
    if not config_files:
        return "- 확인 필요"
    rows = []
    for path, content in config_files.items():
        first_lines = [line.strip() for line in content.splitlines() if line.strip()][:3]
        preview = " / ".join(first_lines)[:180] if first_lines else "내용 확인 필요"
        rows.append(f"- `{path}`: {preview}")
    return "\n".join(rows)


def safe_json_from_text(text: str) -> dict[str, str] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    return {str(k): str(v).strip() for k, v in data.items() if str(v).strip()}


def call_anthropic(prompt: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    payload = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        "max_tokens": 3500,
        "temperature": 0.35,
        "system": "You are a senior backend architect writing Korean technical analysis. Return JSON only.",
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    if not response.ok:
        print(f"[WARN] Anthropic request failed with status {response.status_code}.")
        return None
    body = response.json()
    return "\n".join(part.get("text", "") for part in body.get("content", []) if part.get("type") == "text").strip()


def call_openai(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": "You are a senior backend architect writing Korean technical analysis. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.35,
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if not response.ok:
        print(f"[WARN] OpenAI request failed with status {response.status_code}.")
        return None
    data = response.json()
    return str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()


def build_llm_prompt(
    repo: RepoCandidate,
    languages: dict[str, int],
    readme: str,
    paths: list[str],
    config_files: dict[str, str],
) -> str:
    dirs = top_dirs(paths)
    config_names = list(config_files.keys())
    return f"""
다음 GitHub repo를 한국어로 깊게 분석해라.
출력은 JSON only. key는 아래 10개를 정확히 사용해라.

keys:
important_reason, one_sentence, product_problem, architecture, core_modules, backend_lessons, stealable_patterns, cautions, apply_to_my_projects, source_links

Repo: {repo.full_name}
URL: {repo.html_url}
Description: {repo.description}
Stars: {repo.stars}
Forks: {repo.forks}
Language: {repo.language}
Topics: {', '.join(repo.topics)}
Languages: {languages}
Top directories: {dirs}
Config files: {config_names}
README excerpt:
{readme[:8000]}
""".strip()


def llm_sections(
    repo: RepoCandidate,
    languages: dict[str, int],
    readme: str,
    paths: list[str],
    config_files: dict[str, str],
) -> dict[str, str] | None:
    prompt = build_llm_prompt(repo, languages, readme, paths, config_files)
    text = call_anthropic(prompt) or call_openai(prompt)
    if not text:
        return None
    return safe_json_from_text(text)


def structured_sections(
    repo: RepoCandidate,
    languages: dict[str, int],
    readme: str,
    paths: list[str],
    config_files: dict[str, str],
) -> dict[str, str]:
    dirs = top_dirs(paths)
    dirs_text = "\n".join(f"- `{name}/`: {count} files" for name, count in dirs) or "- 확인 필요"
    signals = "\n".join(f"- {line}" for line in readme_signals(readme)) or "- 확인 필요"
    return {
        "important_reason": (
            f"`{repo.full_name}`는 GitHub star {repo.stars:,}개를 가진 대규모 오픈소스 프로젝트다. "
            "많은 개발자가 선택한 프로젝트이므로 README, 구조, 설정 파일만 봐도 제품화와 운영 성숙도에 대한 단서를 얻을 수 있다."
        ),
        "one_sentence": repo.description or "README/metadata만으로는 한 문장 요약을 확정하기 어렵다. 확인 필요.",
        "product_problem": (
            f"GitHub description: {repo.description or '확인 필요'}\n\nREADME 초기 신호:\n{signals}"
        ),
        "architecture": (
            f"Primary language는 `{repo.language}`이고 언어 구성은 다음과 같다.\n\n{language_summary(languages)}\n\n"
            f"상위 디렉터리 분포:\n{dirs_text}"
        ),
        "core_modules": config_summary(config_files),
        "backend_lessons": (
            "- README에서 quickstart와 실제 설정 파일이 연결되는지 확인해야 한다.\n"
            "- CI, Dockerfile, package/build 설정은 재현 가능한 개발환경의 핵심이다.\n"
            "- 대형 repo일수록 public API와 internal 구현 경계를 문서화해야 유지보수가 가능하다."
        ),
        "stealable_patterns": (
            "- 루트 README를 제품 랜딩처럼 구성한다.\n"
            "- examples/docs/tests를 같은 흐름으로 연결한다.\n"
            "- release, contributing, security 문서를 운영 표면으로 둔다."
        ),
        "cautions": (
            "- star 수만으로 코드 품질을 단정하면 안 된다.\n"
            "- README와 실제 코드 구조가 다를 수 있으므로 build/test 실행 검증이 필요하다.\n"
            "- 대형 repo의 패턴을 작은 프로젝트에 그대로 복사하면 과설계가 될 수 있다."
        ),
        "apply_to_my_projects": (
            "- `vibe-grid`: public API, examples, QA matrix를 repo root에서 쉽게 찾게 만든다.\n"
            "- `vibe-hr`: HR 업무 cycle별 demo와 검증 시나리오를 README/docs에 연결한다.\n"
            "- `jarvis`: raw 자료보다 compiled wiki page를 제품 표면으로 만든다.\n"
            "- `ehr-harness`: 설치, 실행, 안전장치, release log를 명확히 분리한다."
        ),
        "source_links": f"- GitHub: {repo.html_url}\n- README: {repo.html_url}#readme",
    }


def quote_yaml(value: str) -> str:
    return value.replace('"', '\\"')


def repo_slug(full_name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", full_name.lower().replace("/", "-")).strip("-")


def build_post(repo: RepoCandidate, sections: dict[str, str], analyzed_at: datetime) -> str:
    title = f"Repo Deep Dive: {repo.full_name}"
    frontmatter = (
        "---\n"
        "layout: post\n"
        f'title: "{quote_yaml(title)}"\n'
        f"date: {analyzed_at.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
        "categories: [github-repo-analysis]\n"
        "tags: [github, architecture, backend, open-source, deep-dive]\n"
        f"repo: {repo.full_name}\n"
        f"stars: {repo.stars}\n"
        f"analyzed_at: {analyzed_at.strftime('%Y-%m-%d')}\n"
        "---\n\n"
    )
    body = f"""## 1. 이 repo가 중요한 이유

{sections.get('important_reason', '확인 필요')}

## 2. 한 문장 요약

{sections.get('one_sentence', '확인 필요')}

## 3. 제품/문제 정의

{sections.get('product_problem', '확인 필요')}

## 4. 아키텍처 구조

{sections.get('architecture', '확인 필요')}

## 5. 핵심 모듈

{sections.get('core_modules', '확인 필요')}

## 6. 백엔드 개발자가 배울 점

{sections.get('backend_lessons', '확인 필요')}

## 7. 내 프로젝트에 훔쳐올 패턴

{sections.get('stealable_patterns', '확인 필요')}

## 8. 주의할 점 / 안티패턴

{sections.get('cautions', '확인 필요')}

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

{sections.get('apply_to_my_projects', '확인 필요')}

## 10. Source Links

{sections.get('source_links', f'- GitHub: {repo.html_url}')}
"""
    return frontmatter + body.strip() + "\n"


def within_48_hours(last_run_at: Any, now: datetime) -> bool:
    if not last_run_at:
        return False
    try:
        last = datetime.fromisoformat(str(last_run_at))
    except ValueError:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=KST)
    return now - last < timedelta(hours=48)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Ignore 48-hour guard")
    parser.add_argument("--dry-run", action="store_true", help="Do not write post/state")
    args = parser.parse_args()

    state = load_state()
    now = now_kst()

    if not args.force and within_48_hours(state.get("last_run_at"), now):
        print("Skip: last_run_at is within 48 hours.")
        return 0

    min_stars = int(state.get("min_stars") or 50000)
    analyzed = {str(repo) for repo in state.get("analyzed", [])}

    repo = find_next_candidate(min_stars, analyzed)
    refreshed_at = iso_now_kst()
    if not repo:
        print("No candidate found. Mark exhausted=true.")
        if not args.dry_run:
            next_state = dict(state)
            next_state["exhausted"] = True
            next_state["last_candidate_refresh"] = refreshed_at
            atomic_save_state(next_state)
        return 0

    print(f"Selected repo: {repo.full_name} ({repo.stars:,} stars)")
    languages = fetch_languages(repo)
    readme = fetch_readme(repo)
    paths = fetch_tree(repo)
    config_files = fetch_config_files(repo, paths)

    sections = llm_sections(repo, languages, readme, paths, config_files)
    if sections:
        print("LLM draft generated.")
    else:
        print("LLM draft unavailable. Using structured draft.")
        sections = structured_sections(repo, languages, readme, paths, config_files)

    post_path = POSTS_DIR / f"{now.strftime('%Y-%m-%d')}-repo-deep-dive-{repo_slug(repo.full_name)}.md"
    if post_path.exists():
        print(f"Skip: post already exists: {post_path.name}")
        return 0

    if args.dry_run:
        print(f"Dry run. Would create: {post_path.relative_to(ROOT_DIR)}")
        return 0

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    post_path.write_text(build_post(repo, sections, now), encoding="utf-8")

    next_state = dict(state)
    next_state["min_stars"] = min_stars
    next_state["last_run_at"] = now.isoformat(timespec="seconds")
    next_state["last_candidate_refresh"] = refreshed_at
    next_state["exhausted"] = False
    analyzed.add(repo.full_name)
    next_state["analyzed"] = sorted(analyzed)
    atomic_save_state(next_state)

    print(f"Created: {post_path.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
