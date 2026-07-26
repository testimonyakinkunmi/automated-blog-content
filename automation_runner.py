"""
AUTOMATION RUNNER — one hands-off cycle, start to finish
============================================================
1. Picks the next unused keyword from keywords.txt
2. Generates the article and pushes it to GitHub (content_pipeline.py)
3. Builds the Pinterest pin image + copy (bulk_pin_creator.py)
4. Publishes the pin directly to Pinterest (pinterest_publisher.py)
5. Records the keyword as used so it's never repeated

Meant to run on a schedule via GitHub Actions, but works locally too.

USAGE:
  python automation_runner.py
  python automation_runner.py --dry-run
"""

import argparse
import os
from pathlib import Path

import content_pipeline as cp
import bulk_pin_creator as bpc
import pinterest_publisher as pp

KEYWORDS_FILE = "keywords.txt"
USED_FILE = "keywords_used.txt"


def pick_next_keyword() -> str:
    """Pop the first real keyword off keywords.txt, preserving comments/order."""
    path = Path(KEYWORDS_FILE)
    if not path.exists():
        raise SystemExit(f"{KEYWORDS_FILE} not found.")

    lines = path.read_text().splitlines()
    remaining, picked = [], None
    for line in lines:
        stripped = line.strip()
        if picked is None and stripped and not stripped.startswith("#"):
            picked = stripped
            continue
        remaining.append(line)

    if picked is None:
        raise SystemExit(
            f"No unused keywords left in {KEYWORDS_FILE}. Add more seeds, "
            f"or run pinterest_keyword_research.py to generate fresh ones."
        )

    path.write_text("\n".join(remaining) + "\n")
    used_path = Path(USED_FILE)
    existing = used_path.read_text() if used_path.exists() else ""
    used_path.write_text(existing + f"{picked}\n")
    return picked


def build_post_url(article: dict, keyword: str) -> str:
    """Mirror Jekyll's `permalink: /:year/:month/:day/:title/` from _config.yml."""
    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    if not site_url:
        raise SystemExit("SITE_URL env var not set (should include baseurl, e.g. https://you.github.io/repo-name)")
    slug = cp.validate_slug(cp.slugify(article["title"]))
    year, month, day = cp.TODAY.split("-")
    return f"{site_url}/{year}/{month}/{day}/{slug}/"


def run(dry_run: bool = False):
    keyword = pick_next_keyword()
    print(f"[RUNNER] Keyword selected: {keyword}")

    print("[RUNNER] Step 1/3 — generating + pushing article...")
    article = cp.run_pipeline(keyword, tone="informative", dry_run=dry_run)
    post_url = build_post_url(article, keyword)
    print(f"[RUNNER] Post URL will be: {post_url}")

    print("\n[RUNNER] Step 2/3 — building Pinterest pin...")
    board_name = os.environ.get("PINTEREST_BOARD_NAME", "Money Tips")
    pin = bpc.generate_pin_metadata(keyword, board_name=board_name, article_url=post_url)
    image_path = bpc.generate_pin_image(pin, output_dir="pin_images")
    print(f"[RUNNER] Pin image: {image_path}")
    print(f"[RUNNER] Pin title: {pin['pin_title']}")

    print("\n[RUNNER] Step 3/3 — publishing to Pinterest...")
    if dry_run or not image_path:
        print("[RUNNER] DRY RUN (or Pillow missing) — skipping actual Pinterest post.")
    else:
        result = pp.create_pin(
            image_path=image_path,
            title=pin["pin_title"],
            description=pin["pin_description"],
            link=post_url,
        )
        print(f"[RUNNER] Pinterest pin created: id={result.get('id')}")

    print("\n[RUNNER] Cycle complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run one full automation cycle")
    parser.add_argument("--dry-run", action="store_true", help="Generate everything but don't push/publish")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
