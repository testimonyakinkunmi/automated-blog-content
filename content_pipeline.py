"""
CONTENT PIPELINE — Production Blog + Pinterest Traffic System
================================================================
Generates SEO-optimised articles using Gemini or OpenAI,
formats them as Jekyll-compatible Markdown with date-prefix
filenames, and pushes them to GitHub for auto-deploy.

Also generates mandatory legal pages for AdSense approval.

KEY FIXES vs. previous version:
  • Outputs to _posts/YYYY-MM-DD-slug.md (Jekyll standard)
  • Strict slug sanitisation (regex strips garbage chars)
  • 3 randomised structural templates to break AI footprint
  • Dynamic year via datetime.now().year (never hardcoded)
  • Rich Pinterest-optimised front matter (image, pin_image, seo)
  • Accepts keywords from file (one per line)

SETUP:
  pip install requests
  export GEMINI_API_KEY="your-key"
  export GITHUB_TOKEN="ghp_xxx"
  export GITHUB_REPO="username/repo"

USAGE:
  python content_pipeline.py --keyword "budget planner printable 2026"
  python content_pipeline.py --keywords-file keywords.txt
  python content_pipeline.py --init-legal
  python content_pipeline.py --keyword "test" --init-legal --dry-run
"""

import os
import re
import sys
import json
import argparse
import base64
import random
import requests
from datetime import datetime, timezone
from pathlib import Path

THIS_YEAR = datetime.now().year
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ─────────────────────────────────────────────────────────────
# CONFIGURATION — override with env vars or .env file
# ─────────────────────────────────────────────────────────────
def load_env():
    """Load .env file if it exists (simple parser, no dotenv dependency)."""
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

load_env()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
GITHUB_EMAIL   = os.environ.get("GITHUB_EMAIL", "")
SITE_URL       = os.environ.get("SITE_URL", "")
SITE_NAME      = os.environ.get("SITE_NAME", "Smart Cents Hub")
BLOG_BRANCH    = os.environ.get("BLOG_BRANCH", "main")
POSTS_DIR      = "_posts"  # ← Jekyll standard


# ─────────────────────────────────────────────────────────────
# 3 STRUCTURAL TEMPLATES (randomised per article)
# ─────────────────────────────────────────────────────────────
TEMPLATES = {
    "tutorial": {
        "label": "Step-by-Step Tutorial",
        "structure": (
            "Start with a relatable HOOK (a common frustration or desire the reader has right now). "
            "Then a brief 'Why This Matters in {year}' section (2-3 sentences, no heading). "
            "Follow with 5-7 numbered H2 sections, each being a clear STEP the reader can take TODAY. "
            "Each step should include: what to do, why it works, and a concrete example. "
            "Include a 'Pro Tips' H2 section with 3-4 bullet-point advanced tactics. "
            "End with a 'What to Do Right Now' H2 — a 3-item checklist the reader can execute immediately. "
            "DO NOT use a generic 'Conclusion' section. End naturally after the checklist."
        ),
        "heading_style": "action verbs: 'Step 1: ...', 'How to ...', 'Setting Up ...'",
    },
    "listicle": {
        "label": "Curated Listicle (Best Tools / Methods)",
        "structure": (
            "Open with a bold CLAIM about the topic (e.g., 'These 7 tools saved me $500/month'). "
            "Then a quick 'Who This Is For' section (1-2 sentences, no heading — just a paragraph). "
            "Then 5-10 H2 sections, each covering ONE item/method/tool from the list. "
            "For each item: Name it clearly in the H2, explain what it is in 1-2 sentences, "
            "list 2-3 specific pros, 1 con or caveat, and who it's best for. "
            "Include a 'My #1 Recommendation' H2 section at the end where you pick your top pick "
            "and explain WHY in 2-3 sentences. "
            "End with a 'How to Get Started in Under 10 Minutes' H2 with 3 actionable bullet points. "
            "DO NOT use a generic conclusion."
        ),
        "heading_style": "'7. [Tool Name] — Best for [specific use case]'",
    },
    "mistakes": {
        "label": "Mistakes & Case Study Guide",
        "structure": (
            "Open with a SURPRISING STATISTIC or counter-intuitive fact about the topic. "
            "Then a brief 'I Used to Do This Wrong Too' personal anecdote (2-3 sentences, no heading). "
            "Follow with 4-6 H2 sections, each exposing a COMMON MISTAKE people make with this topic. "
            "For each mistake: state the mistake clearly, explain WHY people make it, "
            "show the CONSEQUENCE (what goes wrong), then give the CORRECT approach with a before/after example. "
            "Include a 'The One Change That Made the Biggest Difference' H2 section — your top insight. "
            "End with a 'Your Fix-It Checklist' H2 — 4-5 items to audit/fix right now. "
            "DO NOT use a generic conclusion."
        ),
        "heading_style": "'Mistake #1: [Short Punchy Description of the Mistake]'",
    },
}


# ─────────────────────────────────────────────────────────────
# SLUG SANITISATION — strict regex, no garbage chars
# ─────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug for Jekyll filenames.
    Strips all non-alphanumeric chars except hyphens.
    """
    slug = text.lower().strip()
    # Remove anything that isn't a letter, number, or space
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Collapse multiple spaces/hyphens into single hyphen
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    # Remove trailing/leading hyphens
    slug = re.sub(r"^-+|-+$", "", slug)
    # Truncate to 72 chars (Jekyll filename limit after date prefix)
    return slug[:72] or "untitled"


def validate_slug(slug: str) -> str:
    """Reject slugs that are too short, generic, or look like garbage."""
    slug = slugify(slug)
    # Reject if too short
    if len(slug) < 10:
        raise ValueError(f"Slug '{slug}' is too short — the keyword is likely invalid or too generic.")
    # Reject if it looks like code/special chars survived
    if re.match(r"^[=\-\_]+$", slug):
        raise ValueError(f"Slug '{slug}' is garbage — the keyword contains no usable words.")
    return slug


# ─────────────────────────────────────────────────────────────
# LLM ARTICLE GENERATION
# ─────────────────────────────────────────────────────────────
def pick_template() -> tuple[str, dict]:
    """Randomly select one of the 3 structural templates."""
    name = random.choice(list(TEMPLATES.keys()))
    return name, TEMPLATES[name]


def generate_article_gemini(keyword: str, tone: str, template_name: str, template: dict) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""You are an expert personal-finance blogger writing for a US-based audience. Write a comprehensive, SEO-optimised blog article.

TOPIC / KEYWORD: "{keyword}"
TONE: {tone}
CURRENT YEAR: {THIS_YEAR} (use this year, never hardcode past years)

STRUCTURAL TEMPLATE: {template['label']}
FOLLOW THIS STRUCTURE EXACTLY:
{template['structure']}

HEADING STYLE: {template['heading_style']}

ADDITIONAL RULES:
- 1500-2500 words total
- Use the keyword "{keyword}" naturally 4-6 times in the body (not forced)
- Include 2-3 internal link suggestions in brackets like [Related: other topic] (these are placeholders)
- Write in a conversational but authoritative tone — like a knowledgeable friend
- Every section must deliver real value, not filler
- No "In conclusion" or "To sum up" — end naturally
- Include specific dollar amounts, percentages, or data points where relevant
- Use short paragraphs (2-4 sentences max)
- Use bullet points and numbered lists where appropriate

Return ONLY valid JSON in this exact format (no markdown fences, no commentary):
{{
  "title": "Compelling SEO Title That Includes the Keyword Naturally ({keyword})",
  "excerpt": "A 1-2 sentence hook that makes someone want to click on Pinterest. Include a number or specific result if possible.",
  "tags": ["tag1", "tag2", "{keyword}"],
  "seo_title": "SEO title under 60 characters for Google",
  "seo_description": "Meta description under 160 characters that compels clicks",
  "content": "The full article body in Markdown format..."
}}"""

    response = requests.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 6144}
    })

    if response.status_code != 200:
        raise Exception(f"Gemini API error {response.status_code}: {response.text[:300]}")

    text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Strip code fences if the LLM wraps them
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def generate_article_openai(keyword: str, tone: str, template_name: str, template: dict) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"""You are an expert personal-finance blogger. Write a comprehensive, SEO-optimised blog article.

TOPIC / KEYWORD: "{keyword}"
TONE: {tone}
CURRENT YEAR: {THIS_YEAR}
STRUCTURAL TEMPLATE: {template['label']}
STRUCTURE: {template['structure']}
HEADING STYLE: {template['heading_style']}

RULES: 1500-2500 words, keyword used 4-6 times naturally, conversational but authoritative, specific data points, no "in conclusion", short paragraphs.

Return ONLY valid JSON:
{{"title": "...", "excerpt": "...", "tags": ["..."], "seo_title": "...", "seo_description": "...", "content": "markdown..."}}"""

    response = requests.post(url, headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }, json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 4096,
    })

    if response.status_code != 200:
        raise Exception(f"OpenAI API error {response.status_code}: {response.text[:300]}")

    text = response.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def generate_article(keyword: str, tone: str) -> dict:
    """Generate an article using a randomised template."""
    template_name, template = pick_template()
    print(f"  Template: {template['label']}")

    if GEMINI_API_KEY:
        article = generate_article_gemini(keyword, tone, template_name, template)
    elif OPENAI_API_KEY:
        article = generate_article_openai(keyword, tone, template_name, template)
    else:
        print("ERROR: Set GEMINI_API_KEY or OPENAI_API_KEY environment variable.")
        sys.exit(1)

    article["_template"] = template_name
    return article


# ─────────────────────────────────────────────────────────────
# FRONT MATTER GENERATION (Jekyll + Pinterest SEO)
# ─────────────────────────────────────────────────────────────
def create_frontmatter(article: dict, keyword: str) -> str:
    """Generate Jekyll front matter with Pinterest-optimised fields."""
    # Generate pin image path based on slug
    slug = slugify(article["title"])
    pin_image = f"/assets/images/pins/{slug}.png"

    tags_str = ", ".join(article.get("tags", [keyword]))
    if isinstance(article.get("tags"), list):
        tags_str = ", ".join(article["tags"])

    # Ensure keyword is in tags
    if keyword.lower() not in tags_str.lower():
        tags_str = f"{tags_str}, {keyword}"

    return f"""---
layout: post
title: "{article['title']}"
date: {TODAY}
description: "{article.get('excerpt', article.get('seo_description', ''))}"
tags: [{tags_str}]
keywords: ["{keyword}"]
image: "/assets/images/default-pin.png"
pin_image: "{pin_image}"
description: "{article.get('seo_description', article.get('excerpt', ''))}"
---"""


# ─────────────────────────────────────────────────────────────
# GITHUB API — push file to repo
# ─────────────────────────────────────────────────────────────
def push_to_github(filename: str, content: str, commit_message: str) -> dict:
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    existing = requests.get(api_url, headers=headers)
    data = {
        "message": commit_message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": BLOG_BRANCH,
    }
    if existing.status_code == 200:
        data["sha"] = existing.json()["sha"]

    response = requests.put(api_url, headers=headers, json=data)
    if response.status_code not in [200, 201]:
        raise Exception(f"GitHub API {response.status_code}: {response.text[:300]}")
    return response.json()


# ─────────────────────────────────────────────────────────────
# LEGAL PAGE GENERATORS (AdSense compliance)
# ─────────────────────────────────────────────────────────────
def generate_privacy_policy() -> str:
    return f"""---
layout: page
title: "Privacy Policy"
description: "Privacy policy for {SITE_NAME} — how we collect, use, and protect your information."
---

**Last Updated:** {datetime.now(timezone.utc).strftime("%B %d, %Y")}

This Privacy Policy describes how {SITE_NAME} ("we", "us", or "our") collects, uses, and protects information when you visit our website (the "Site").

## Information We Collect

### Automatically Collected Information
When you visit our Site, we may automatically collect certain information about your device, including IP address, browser type, operating system, referring website, pages viewed, time spent on pages, and visit dates. We collect this information using cookies and similar technologies.

### Third-Party Advertising
We use **Google AdSense** to display advertisements on our Site. Google AdSense may use cookies and web beacons to serve ads based on your prior visits. You may opt out of personalized advertising by visiting [Google Ads Settings](https://www.google.com/settings/ads).

## How We Use Your Information
We use collected information to provide and maintain our Site, improve your experience, analyze usage trends, display relevant advertisements, and comply with legal obligations.

## Third-Party Services
| Service | Purpose | Privacy Policy |
|---------|---------|----------------|
| Google Analytics | Traffic analysis | [Google Privacy Policy](https://policies.google.com/privacy) |
| Google AdSense | Advertising | [Google Privacy Policy](https://policies.google.com/privacy) |

## Data Retention
We retain information for up to 26 months. You may request earlier deletion by contacting us.

## Your Rights
You may have rights to access, delete, or correct your data. Contact us to exercise these rights.

## Children's Privacy
Our Site is not directed to children under 13. We do not knowingly collect data from children under 13.

## Contact Us
Email: {{ site.author.email }}
"""


def generate_terms_of_service() -> str:
    return f"""---
layout: page
title: "Terms of Service"
description: "Terms of service for {SITE_NAME}."
---

**Last Updated:** {datetime.now(timezone.utc).strftime("%B %d, %Y")}

## 1. Acceptance of Terms
By using {SITE_NAME}, you agree to these Terms.

## 2. Description of Service
{SITE_NAME} provides informational blog content about personal finance, budgeting, and related topics. Content is for **informational purposes only** and is not professional financial, legal, or tax advice.

## 3. User Conduct
You agree not to use the Site unlawfully, attempt unauthorized access, or exploit our content without permission.

## 4. Intellectual Property
All content is property of {SITE_NAME}. You may share links on social media (including Pinterest) with proper attribution.

## 5. Affiliate Links and Advertising
The Site contains affiliate links and Google AdSense ads. Affiliate commissions do not affect prices you pay.

## 6. Disclaimer of Warranties
THE SITE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND.

## 7. Limitation of Liability
{SITE_NAME} shall not be liable for indirect, incidental, or consequential damages.

## 8. Accuracy of Information
We strive for accuracy but make no warranties about content completeness. Always do your own research.

## 9. External Links
External links are at your own risk. We are not responsible for third-party content.

## 10. Changes to Terms
Changes are effective immediately upon posting.

## 11. Contact
Email: {{ site.author.email }}
"""


def generate_contact_page() -> str:
    return f"""---
layout: page
title: "Contact Us"
description: "Get in touch with {SITE_NAME}."
---

## Email
**General Inquiries**: {{ site.author.email }}

## Social Media
- **Pinterest**: [{{ site.title }} on Pinterest]({{ site.author.pinterest | default: '#' }})

## Response Time
We aim to respond within 48 hours during business days.

## Privacy
Any information you provide is handled per our [Privacy Policy]({{ '/privacy-policy/' | relative_url }}).
"""


def push_legal_pages(dry_run: bool = False):
    pages = {
        "privacy-policy.md": generate_privacy_policy(),
        "terms-of-service.md": generate_terms_of_service(),
        "contact.md": generate_contact_page(),
    }

    print(f"\n{'='*60}")
    print("LEGAL PAGES GENERATION")
    print(f"{'='*60}")
    print(f"Site: {SITE_NAME} ({SITE_URL or 'URL not set'})")
    print(f"{'='*60}\n")

    for filename, content in pages.items():
        print(f"[LEGAL] {filename}")
        if dry_run:
            print(f"  DRY RUN — would push {len(content)} bytes")
        else:
            try:
                result = push_to_github(filename, content, f"Add {filename}")
                print(f"  Pushed: {result['content']['html_url']}")
            except Exception as e:
                print(f"  ERROR: {e}")

    print(f"\n{'='*60}")
    print("LEGAL PAGES COMPLETE")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────
def run_pipeline(keyword: str, tone: str = "informative", dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"CONTENT PIPELINE")
    print(f"{'='*60}")
    print(f"Keyword : {keyword}")
    print(f"Tone    : {tone}")
    print(f"Year    : {THIS_YEAR} (dynamic)")
    print(f"Dry Run : {dry_run}")
    print(f"{'='*60}\n")

    # 1. Generate
    print("[1/4] Generating article...")
    article = generate_article(keyword, tone)
    print(f"  Title   : {article['title']}")
    print(f"  Template: {article['_template']}")
    print(f"  Tags    : {article.get('tags', [])}")

    # 2. Create Jekyll-compatible filename
    print("\n[2/4] Creating Jekyll post file...")
    slug = validate_slug(slugify(article["title"]))
    filename = f"{POSTS_DIR}/{TODAY}-{slug}.md"
    print(f"  File    : {filename}")

    # 3. Build full content
    print("\n[3/4] Building Markdown with front matter...")
    frontmatter = create_frontmatter(article, keyword)
    full_content = f"{frontmatter}\n\n{article['content']}"

    # 4. Push to GitHub
    if dry_run:
        print(f"\n[4/4] DRY RUN — would push to {GITHUB_REPO}")
        print(f"\n--- PREVIEW (first 500 chars) ---\n{full_content[:500]}...")
    else:
        print("\n[4/4] Pushing to GitHub...")
        result = push_to_github(filename, full_content, f"New article: {article['title']}")
        print(f"  Commit : {result['commit']['sha'][:8]}")
        print(f"  URL    : {result['content']['html_url']}")

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"  1. Generate pin images: python bulk_pin_creator.py --keyword '{keyword}' --csv --generate-images")
    print(f"  2. Upload CSV to: https://www.pinterest.com/ads/bulk-create/")
    return article


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Blog Content Pipeline — AI articles to GitHub Pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python content_pipeline.py --keyword "budget planner printable 2026"
  python content_pipeline.py --keywords-file keywords.txt --tone casual
  python content_pipeline.py --init-legal --dry-run
  python content_pipeline.py --keyword "side hustle ideas" --init-legal
""")
    parser.add_argument("--keyword", type=str, help="Target keyword for a single article")
    parser.add_argument("--keywords-file", type=str, help="Text file with one keyword per line")
    parser.add_argument("--tone", type=str, default="informative",
                        choices=["informative", "casual", "professional", "persuasive"],
                        help="Article tone (default: informative)")
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't push to GitHub")
    parser.add_argument("--init-legal", action="store_true",
                        help="Generate and push legal pages (privacy, terms, contact)")

    args = parser.parse_args()

    # Validate critical config
    if not args.init_legal and not args.dry_run:
        if not GITHUB_TOKEN:
            print("ERROR: GITHUB_TOKEN not set. Export it or add to .env")
            sys.exit(1)
        if not GITHUB_REPO:
            print("ERROR: GITHUB_REPO not set (e.g., 'username/repo'). Export it or add to .env")
            sys.exit(1)

    # Legal pages first
    if args.init_legal:
        push_legal_pages(dry_run=args.dry_run)

    # Article generation
    if args.keywords_file:
        keywords = Path(args.keywords_file).read_text().strip().splitlines()
        keywords = [k.strip() for k in keywords if k.strip() and not k.startswith("#")]
        print(f"Batch mode: {len(keywords)} keywords")
        for i, kw in enumerate(keywords, 1):
            print(f"\n{'='*60}")
            print(f"ARTICLE {i}/{len(keywords)}")
            print(f"{'='*60}")
            run_pipeline(kw, args.tone, args.dry_run)
    elif args.keyword:
        run_pipeline(args.keyword, args.tone, args.dry_run)
    elif not args.init_legal:
        parser.print_help()