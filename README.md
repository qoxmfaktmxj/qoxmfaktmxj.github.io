# qoxmfaktmxj.github.io

Automated blog pipeline for:

- Daily AI news summary post
- Daily developer study post (topic rotation)

The pipeline uses GitHub Actions + Anthropic API and publishes via GitHub Pages.

## One-time setup

1. Repository Secrets and Variables
- Add secret: `ANTHROPIC_API_KEY`
- Optional repository variable: `ANTHROPIC_MODEL`
  - Default model is `claude-haiku-4-5-20251001`

2. Enable GitHub Pages
- Settings -> Pages -> Build and deployment -> Source: `GitHub Actions`

3. Push to `main` or `master`
- `pages-deploy.yml` deploys the site
- `auto-post.yml` runs daily at `00:15 UTC` and can be run manually

## Local test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=your_key
python scripts/auto_post.py
```

## Generated files

- Posts: `_posts/YYYY-MM-DD-*.md`
- Topic state: `.automation/state.json`
