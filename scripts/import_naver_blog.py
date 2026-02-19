import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


ROOT_DIR = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT_DIR / "_posts"
KST = timezone(timedelta(hours=9))


@dataclass
class NaverPost:
    log_no: str
    title: str
    link: str
    category: str
    published_at: datetime
    markdown: str


def quote_yaml(value: str) -> str:
    return value.replace('"', '\\"')


def parse_date(raw: str) -> datetime:
    dt = parsedate_to_datetime(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def extract_log_no(url: str) -> Optional[str]:
    match = re.search(r"/(\d+)", url)
    if not match:
        return None
    return match.group(1)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def convert_indented_code_to_fenced(text: str) -> str:
    """Convert 4-space indented code blocks to fenced code blocks for mobile readability."""
    lines = text.split("\n")
    result: list[str] = []
    code_lines: list[str] = []
    in_code = False

    for line in lines:
        is_code_line = line.startswith("    ") and line.strip()
        is_blank = not line.strip()

        if is_code_line:
            if not in_code:
                in_code = True
                code_lines = []
            code_lines.append(line[4:])
        elif is_blank and in_code:
            code_lines.append("")
        else:
            if in_code:
                # Remove trailing blank lines from code block
                while code_lines and not code_lines[-1].strip():
                    code_lines.pop()
                if code_lines:
                    result.append("```")
                    result.extend(code_lines)
                    result.append("```")
                in_code = False
                code_lines = []
            result.append(line)

    if in_code and code_lines:
        while code_lines and not code_lines[-1].strip():
            code_lines.pop()
        if code_lines:
            result.append("```")
            result.extend(code_lines)
            result.append("```")

    return "\n".join(result)


def sanitize_markdown(text: str) -> str:
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = convert_indented_code_to_fenced(text)
    return text


def classify_category(title: str, category: str, content_text: str) -> str:
    text = f"{title} {category} {content_text}".lower()

    if any(k in text for k in ["elasticsearch", "elastic search", "kafka", "logstash", "kibana"]):
        return "data-infra"
    if any(k in text for k in ["oracle", "postgresql", "mysql", "sql ", " sql", "redis"]):
        return "sql"
    if any(k in text for k in ["python", "pydantic", "fastapi"]):
        return "python"
    if any(k in text for k in ["next.js", "nextjs", "react", "typescript", "javascript", "vue"]):
        return "nextjs"
    if any(k in text for k in ["java", "spring", "springboot", "jpa"]):
        return "java"
    if any(k in text for k in ["ai", "llm", "chatgpt", "claude", "gpt"]):
        return "ai-daily-news"
    return "java"


def fetch_post_markdown(blog_id: str, log_no: str) -> tuple[str, str, str]:
    mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
    response = requests.get(
        mobile_url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = ""
    og_title = soup.select_one("meta[property='og:title']")
    if og_title and og_title.get("content"):
        title = normalize_ws(og_title["content"])
    if not title:
        heading = soup.select_one("h3.se_textarea")
        if heading:
            title = normalize_ws(heading.get_text(" ", strip=True))

    category = ""
    category_anchor = soup.select_one("div.blog_category a")
    if category_anchor:
        category = normalize_ws(category_anchor.get_text(" ", strip=True))

    container = soup.select_one("div.se-main-container")
    if container is None:
        container = soup.select_one("div#postViewArea")
    if container is None:
        raise RuntimeError(f"본문 컨테이너를 찾지 못했습니다. logNo={log_no}")

    for unwanted in container.select("script, style"):
        unwanted.decompose()

    html = str(container)
    markdown = md(html, heading_style="ATX")
    markdown = sanitize_markdown(markdown)

    if not markdown:
        raise RuntimeError(f"본문이 비어 있습니다. logNo={log_no}")

    return title, category, markdown


def load_entries(blog_id: str) -> List[feedparser.FeedParserDict]:
    rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
    feed = feedparser.parse(rss_url)
    if feed.bozo:
        raise RuntimeError(f"RSS 파싱 실패: {feed.bozo_exception}")
    return list(feed.entries)


def write_post(post: NaverPost, blog_id: str) -> Path:
    date_prefix = post.published_at.strftime("%Y-%m-%d")
    filename = f"{date_prefix}-naver-{post.log_no}.md"
    path = POSTS_DIR / filename

    source_url = f"https://blog.naver.com/{blog_id}/{post.log_no}"
    content = (
        "---\n"
        "layout: post\n"
        f'title: "{quote_yaml(post.title)}"\n'
        f"date: {post.published_at.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
        f"categories: [{post.category}, naver-archive]\n"
        "tags: [naver-import]\n"
        f"naver_source: {source_url}\n"
        "---\n\n"
        f"> 원문: [{source_url}]({source_url})\n\n"
        f"{post.markdown}\n"
    )

    path.write_text(content, encoding="utf-8")
    return path


def run(blog_id: str, limit: int, skip_existing: bool) -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_entries(blog_id)
    if limit > 0:
        entries = entries[:limit]

    imported = 0
    skipped = 0

    for entry in entries:
        link = str(entry.get("link", "")).strip()
        log_no = extract_log_no(link)
        if not log_no:
            print(f"[SKIP] logNo 파싱 실패: {link}")
            skipped += 1
            continue

        published_raw = str(entry.get("published", ""))
        published_at = parse_date(published_raw)
        expected_path = POSTS_DIR / f"{published_at.strftime('%Y-%m-%d')}-naver-{log_no}.md"
        if skip_existing and expected_path.exists():
            print(f"[SKIP] 이미 존재: {expected_path.name}")
            skipped += 1
            continue

        try:
            title, source_category, markdown = fetch_post_markdown(blog_id, log_no)
            mapped_category = classify_category(title, source_category, markdown[:1500])
            post = NaverPost(
                log_no=log_no,
                title=title or str(entry.get("title", f"Naver Post {log_no}")),
                link=link,
                category=mapped_category,
                published_at=published_at,
                markdown=markdown,
            )
            path = write_post(post, blog_id=blog_id)
            imported += 1
            print(f"[OK] {path.name} ({mapped_category})")
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {log_no}: {exc}")

    print(f"Done. imported={imported}, skipped={skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Naver blog posts into Jekyll markdown files.")
    parser.add_argument("--blog-id", default="qoxmfaktmxj")
    parser.add_argument("--limit", type=int, default=0, help="0 means all entries from RSS")
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    run(
        blog_id=args.blog_id,
        limit=args.limit,
        skip_existing=not args.no_skip_existing,
    )
