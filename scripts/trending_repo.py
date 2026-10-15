#!/usr/bin/env python3
"""Select the first not-yet-reviewed repository in GitHub Trending (daily)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
TRENDING_URL = "https://github.com/trending?since=daily"
KST = timezone(timedelta(hours=9))
REPO_PATH = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")
POST_REPO = re.compile(r"^repo:\s*([^\s]+)\s*$", re.MULTILINE)


def reviewed_repositories() -> set[str]:
    reviewed: set[str] = set()
    for post in POSTS.glob("*-repo-deep-dive-*.md"):
        match = POST_REPO.search(post.read_text(encoding="utf-8"))
        if match:
            reviewed.add(match.group(1))
    return reviewed


def select_trending(html: str, reviewed: set[str]) -> dict[str, object]:
    repositories: list[str] = []
    for article in re.findall(r'<article\b[^>]*class="[^"]*\bBox-row\b[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL):
        heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", article, re.DOTALL)
        if not heading:
            continue
        link = re.search(r'href="([^"]+)"', heading.group(1))
        match = REPO_PATH.fullmatch(link.group(1)) if link else None
        if match:
            repositories.append(f"{match.group(1)}/{match.group(2)}")
    if not repositories:
        raise RuntimeError("GitHub Trending 목록을 찾지 못했습니다.")
    for rank, repo in enumerate(repositories, start=1):
        if repo not in reviewed:
            return {"repo": repo, "rank": rank, "count": len(repositories)}
    raise RuntimeError("현재 GitHub Trending 목록의 모든 저장소를 이미 리뷰했습니다.")


def main() -> None:
    response = requests.get(TRENDING_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    selection = select_trending(response.text, reviewed_repositories())
    selection.update({
        "trending_url": TRENDING_URL,
        "checked_at": datetime.now(KST).isoformat(timespec="seconds"),
        "period": "daily",
    })
    print(json.dumps(selection, ensure_ascii=False))


if __name__ == "__main__":
    main()
