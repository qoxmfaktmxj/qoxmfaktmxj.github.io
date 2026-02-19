import json
import os
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple
from zoneinfo import ZoneInfo

import feedparser
import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT_DIR / "_posts"
STATE_FILE = ROOT_DIR / ".automation" / "state.json"

PRIMARY_NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
]

FALLBACK_NEWS_FEEDS = [
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
]

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published: str
    ts: float


@dataclass
class StudyTopic:
    slug: str
    prompt_topic: str
    category: str
    tags: List[str]


STUDY_TOPICS: List[StudyTopic] = [
    StudyTopic(
        slug="python",
        prompt_topic="Python",
        category="python",
        tags=["python", "backend"],
    ),
    StudyTopic(
        slug="nextjs",
        prompt_topic="Next.js",
        category="nextjs",
        tags=["nextjs", "react", "frontend"],
    ),
    StudyTopic(
        slug="java",
        prompt_topic="Java",
        category="java",
        tags=["java", "spring", "backend"],
    ),
    StudyTopic(
        slug="sql-postgresql",
        prompt_topic="PostgreSQL SQL",
        category="sql",
        tags=["sql", "postgresql", "database"],
    ),
    StudyTopic(
        slug="sql-mysql",
        prompt_topic="MySQL SQL",
        category="sql",
        tags=["sql", "mysql", "database"],
    ),
    StudyTopic(
        slug="sql-oracle",
        prompt_topic="Oracle SQL",
        category="sql",
        tags=["sql", "oracle", "database"],
    ),
    StudyTopic(
        slug="redis",
        prompt_topic="Redis",
        category="sql",
        tags=["redis", "caching", "database"],
    ),
    StudyTopic(
        slug="elasticsearch",
        prompt_topic="Elasticsearch",
        category="data-infra",
        tags=["elasticsearch", "search", "infra"],
    ),
    StudyTopic(
        slug="kafka",
        prompt_topic="Apache Kafka",
        category="data-infra",
        tags=["kafka", "streaming", "infra"],
    ),
]


def now_kst() -> datetime:
    return datetime.now(ZoneInfo("Asia/Seoul"))


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"topic_index": 0}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"topic_index": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_rss_time(entry: dict) -> float:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(
                parsed.tm_year,
                parsed.tm_mon,
                parsed.tm_mday,
                parsed.tm_hour,
                parsed.tm_min,
                parsed.tm_sec,
                tzinfo=timezone.utc,
            ).timestamp()
    return 0.0


def collect_news_from_feeds(feed_urls: List[str], seen_urls: set) -> List[NewsItem]:
    items: List[NewsItem] = []

    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)
        source_name = feed.feed.get("title", "Unknown source")
        if getattr(feed, "bozo", False):
            print(f"[WARN] RSS parse issue: {feed_url}")

        for entry in feed.entries:
            url = entry.get("link")
            title = str(entry.get("title", "")).strip()
            if not url or not title or url in seen_urls:
                continue

            seen_urls.add(url)
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source=source_name,
                    published=str(entry.get("published", entry.get("updated", ""))),
                    ts=parse_rss_time(entry),
                )
            )

    return items


def fetch_news_items(limit: int = 8, min_items: int = 5) -> List[NewsItem]:
    seen_urls = set()
    items = collect_news_from_feeds(PRIMARY_NEWS_FEEDS, seen_urls)

    if len(items) < min_items:
        print(
            f"[INFO] Primary news items are low ({len(items)}). "
            f"Loading fallback feeds..."
        )
        items.extend(collect_news_from_feeds(FALLBACK_NEWS_FEEDS, seen_urls))

    items.sort(key=lambda item: item.ts, reverse=True)
    return items[:limit]


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_response(text: str) -> Tuple[str, str]:
    candidate = strip_code_fence(text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))

    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()
    if not title or not content:
        raise ValueError("Model response missing title/content")
    return title, content


def call_claude(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload = {
        "model": model,
        "max_tokens": 2200,
        "temperature": 0.4,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(f"Anthropic API error: {response.status_code} {response.text}")

    body = response.json()
    chunks = [
        part.get("text", "")
        for part in body.get("content", [])
        if part.get("type") == "text"
    ]
    text = "\n".join(chunks).strip()
    if not text:
        raise RuntimeError("Anthropic API returned empty content")
    return text


def build_news_prompt(items: List[NewsItem], today: str) -> str:
    refs = "\n".join(
        [
            f"{idx}. {item.title} | {item.source} | {item.url}"
            for idx, item in enumerate(items, start=1)
        ]
    )
    return f"""
Date: {today} (Asia/Seoul)

Write a Korean blog post in Markdown about today's AI news.
Use only the references below.

References:
{refs}

Output requirements:
1) Respond with JSON only.
2) JSON schema: {{"title":"...","content":"..."}}
3) content must be valid Markdown (no code fences).
4) Include:
   - short intro
   - "Top News" section with at least 5 bullets
   - "What This Means for Developers" section
   - "Source Links" section with the URLs
5) Keep a practical, concise tone.
6) Do NOT include any "팁" or "Tip" section. Do NOT add motivational closing remarks.

Mobile-friendly formatting rules (MUST follow):
- Keep paragraphs short: max 2-3 sentences per paragraph.
- For bullet points, use bold title on one line, then description on the next line. Example:
  - **Title here**
    Description text here.
- Never write a bullet as a single long sentence. Always split title and detail.
- If any code is included, always use fenced code blocks (```language), never 4-space indent.
""".strip()


def build_study_prompt(topic: StudyTopic, today: str) -> str:
    return f"""
Date: {today} (Asia/Seoul)
Topic: {topic.prompt_topic}
Category hint: {topic.category}

Write a Korean daily study post in Markdown for developers.

Output requirements:
1) Respond with JSON only.
2) JSON schema: {{"title":"...","content":"..."}}
3) content must be valid Markdown (no code fences).
4) Include:
   - Why this topic matters in real projects
   - Core concepts (3-5 bullets)
   - Hands-on mini example (code block allowed inside Markdown)
   - Common mistakes
   - One-day practice checklist
5) Keep it practical and focused.
6) Do NOT include any "팁" or "Tip" section at the end. Do NOT add motivational closing remarks or preview of next day's topic.

Mobile-friendly formatting rules (MUST follow):
- Keep paragraphs short: max 2-3 sentences per paragraph. Break long paragraphs into multiple short ones.
- For bullet points, use bold title on one line, then description on the next line. Example:
  - **Title here**
    Description text here.
- Never write a bullet as a single long sentence. Always split title and detail.
- Always use fenced code blocks (```language), NEVER use 4-space indented code blocks.
- If a code example is longer than 15 lines, split it into multiple separate fenced code blocks with a short explanation between each block.
- For "Common mistakes" section, format each item as a bold title + newline + description, not a single long line.
""".strip()


def quote_yaml(value: str) -> str:
    return value.replace('"', '\\"')


def write_post_file(
    path: Path,
    title: str,
    now: datetime,
    categories: List[str],
    tags: List[str],
    content: str,
) -> None:
    frontmatter = (
        "---\n"
        "layout: post\n"
        f'title: "{quote_yaml(title)}"\n'
        f"date: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
        f"categories: [{', '.join(categories)}]\n"
        f"tags: [{', '.join(tags)}]\n"
        "---\n\n"
    )
    path.write_text(frontmatter + content.strip() + "\n", encoding="utf-8")


def create_news_post(now: datetime) -> bool:
    date_str = now.strftime("%Y-%m-%d")
    post_path = POSTS_DIR / f"{date_str}-ai-news-daily.md"
    if post_path.exists():
        print(f"Skip news post. Already exists: {post_path.name}")
        return False

    items = fetch_news_items(limit=8)
    if not items:
        print("No RSS items found. Skip news post.")
        return False

    system_prompt = (
        "You are a technical blog writer. "
        "You return strict JSON exactly matching requested schema."
    )
    model_output = call_claude(
        system_prompt=system_prompt,
        user_prompt=build_news_prompt(items=items, today=date_str),
    )
    title, content = parse_json_response(model_output)
    write_post_file(
        path=post_path,
        title=title,
        now=now,
        categories=["ai-daily-news"],
        tags=["ai", "news", "automation"],
        content=content,
    )
    print(f"Created: {post_path.name}")
    return True


def create_study_post(now: datetime, state: dict) -> bool:
    topic_index = int(state.get("topic_index", 0)) % len(STUDY_TOPICS)
    topic = STUDY_TOPICS[topic_index]
    date_str = now.strftime("%Y-%m-%d")
    post_path = POSTS_DIR / f"{date_str}-study-{topic.slug}.md"
    if post_path.exists():
        print(f"Skip study post. Already exists: {post_path.name}")
        return False

    system_prompt = (
        "You are a senior software engineer writing practical study guides. "
        "You return strict JSON exactly matching requested schema."
    )
    model_output = call_claude(
        system_prompt=system_prompt,
        user_prompt=build_study_prompt(topic=topic, today=date_str),
    )
    title, content = parse_json_response(model_output)
    write_post_file(
        path=post_path,
        title=title,
        now=now,
        categories=[topic.category],
        tags=["study", *topic.tags, "automation"],
        content=content,
    )
    state["topic_index"] = (topic_index + 1) % len(STUDY_TOPICS)
    print(f"Created: {post_path.name}")
    return True


def main() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    now = now_kst()

    created_news = False
    created_study = False
    errors: List[str] = []

    try:
        created_news = create_news_post(now)
    except Exception as exc:
        errors.append(f"news: {exc}")
        traceback.print_exc()

    try:
        created_study = create_study_post(now, state)
    except Exception as exc:
        errors.append(f"study: {exc}")
        traceback.print_exc()

    if created_study:
        save_state(state)

    if errors:
        print("Generation errors:")
        for err in errors:
            print(f"- {err}")

    if not (created_news or created_study):
        print("No new posts created.")
        if errors:
            raise SystemExit(1)
    else:
        print("Post generation completed.")


if __name__ == "__main__":
    main()
