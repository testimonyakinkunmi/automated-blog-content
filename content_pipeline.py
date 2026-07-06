"""
CONTENT PIPELINE — Blog + Pinterest Traffic System
====================================================
Generates SEO-optimized articles using an AI API (Gemini or OpenAI),
formats them as Markdown, and pushes them to your GitHub repo.
Vercel/Netlify auto-deploys on push.

Also generates mandatory legal pages (privacy, terms, contact) for
AdSense approval on first run.

SETUP:
1. pip install requests
2. Set environment variables (or fill in below):
   - GEMINI_API_KEY (or OPENAI_API_KEY)
   - GITHUB_TOKEN (Personal Access Token with repo access)
   - GITHUB_REPO (e.g., "username/blog-repo")
   - GITHUB_USERNAME
   - GITHUB_EMAIL

USAGE:
  python content_pipeline.py --keyword "digital thrift savings tools"
  python content_pipeline.py --keyword "fintech budget apps" --tone casual
  python content_pipeline.py --keywords-file keywords.txt
  python content_pipeline.py --init-legal          # generate legal pages only
  python content_pipeline.py --keyword "test" --init-legal  # both
"""

import os
import sys
import json
import argparse
import base64
import requests
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

THIS_YEAR = datetime.now().year

# ============ CONFIGURATION ============
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "username/your-blog-repo")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "your-github-username")
GITHUB_EMAIL = os.environ.get("GITHUB_EMAIL", "your@email.com")
SITE_URL = os.environ.get("SITE_URL", "https://your-blog.vercel.app")
SITE_NAME = os.environ.get("SITE_NAME", "Your Blog Name")
BLOG_BRANCH = "main"
ARTICLES_DIR = "content/posts"
PAGES_DIR = "content/pages"


# ============ LEGAL PAGE GENERATORS ============

def generate_privacy_policy() -> str:
    """Generate a privacy policy page for AdSense compliance."""
    return f"""---
title: "Privacy Policy"
date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
layout: page
---

# Privacy Policy

**Last Updated:** {datetime.now(timezone.utc).strftime("%B %d, %Y")}

This Privacy Policy describes how {SITE_NAME} ("we", "us", or "our") collects, uses, and protects information when you visit our website at {SITE_URL} (the "Site").

## Information We Collect

### Automatically Collected Information
When you visit our Site, we may automatically collect certain information about your device, including:
- **IP address** and approximate geographic location
- **Browser type and version**
- **Operating system**
- **Referring website** and **exit pages**
- **Pages viewed** and **time spent** on pages
- **Date and time** of visits

We collect this information using cookies and similar technologies, as well as through third-party analytics services.

### Third-Party Advertising
We use **Google AdSense** to display advertisements on our Site. Google AdSense may use cookies and web beacons to serve ads based on your prior visits to our Site and other websites. Google's use of advertising cookies enables it and its partners to serve ads based on your visit to our Site and/or other sites on the Internet.

You may opt out of personalized advertising by visiting [Google Ads Settings](https://www.google.com/settings/ads).

We may also participate in **affiliate programs** (e.g., Amazon Associates). These third parties may use cookies to track referrals and attribute sales.

## How We Use Your Information

We use the information we collect to:
- Provide, operate, and maintain our Site
- Improve and personalize your experience on our Site
- Analyze usage trends and optimize our content
- Display relevant advertisements
- Comply with legal obligations

## Cookies

Our Site uses cookies for:
- **Essential functionality**: Remembering your preferences
- **Analytics**: Understanding how visitors interact with our Site (Google Analytics)
- **Advertising**: Serving relevant ads through Google AdSense

You can control cookies through your browser settings. Disabling cookies may affect some Site functionality.

## Third-Party Services

Our Site integrates with the following third-party services, each with their own privacy policies:

| Service | Purpose | Privacy Policy |
|---------|---------|----------------|
| Google Analytics | Traffic analysis | [Google Privacy Policy](https://policies.google.com/privacy) |
| Google AdSense | Advertising | [Google Privacy Policy](https://policies.google.com/privacy) |
| Amazon Associates | Affiliate links | [Amazon Privacy Notice](https://www.amazon.com/privacy) |

## Data Retention

We retain automatically collected information for up to **26 months** from the date of collection, after which it is automatically deleted. You may request earlier deletion by contacting us.

## Your Rights

Depending on your location, you may have the following rights:
- **Access**: Request a copy of the data we hold about you
- **Deletion**: Request that we delete your personal data
- **Opt-out**: Disable cookies or opt out of personalized advertising
- **Correction**: Request correction of inaccurate data

To exercise any of these rights, contact us at the email address below.

## Children's Privacy

Our Site is not directed to children under the age of 13. We do not knowingly collect personal information from children under 13. If we become aware that we have collected data from a child under 13, we will take steps to delete that information.

## Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date.

## Contact Us

If you have questions about this Privacy Policy, please contact us:

- **Email**: privacy@{SITE_URL.replace('https://', '').replace('http://', '').split('/')[0]}
- **Site**: {SITE_URL}
"""


def generate_terms_of_service() -> str:
    """Generate a terms of service page for AdSense compliance."""
    return f"""---
title: "Terms of Service"
date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
layout: page
---

# Terms of Service

**Last Updated:** {datetime.now(timezone.utc).strftime("%B %d, %Y")}

Please read these Terms of Service ("Terms") carefully before using {SITE_NAME} at {SITE_URL} (the "Site"). By accessing or using the Site, you agree to be bound by these Terms.

## 1. Acceptance of Terms

By accessing and using the Site, you acknowledge that you have read, understood, and agree to be bound by these Terms. If you do not agree, please do not use the Site.

## 2. Description of Service

{SITE_NAME} provides informational blog content about personal finance, technology tools, and related topics. Our content is for **informational purposes only** and should not be considered professional financial, legal, or tax advice.

## 3. User Conduct

When using the Site, you agree not to:
- Use the Site for any unlawful purpose
- Attempt to gain unauthorized access to any portion of the Site
- Interfere with or disrupt the Site's functionality
- Reproduce, distribute, or commercially exploit our content without written permission
- Use automated tools to scrape or collect data from the Site

## 4. Intellectual Property

All content on the Site — including text, graphics, logos, images, and software — is the property of {SITE_NAME} or its content creators and is protected by applicable intellectual property laws.

You may share links to our content on social media platforms (including Pinterest) provided that you do not modify the content and include proper attribution.

## 5. Affiliate Links and Advertising

The Site contains:
- **Affiliate links**: We may earn a commission when you purchase products through links on our Site (e.g., Amazon Associates). This does not affect the price you pay.
- **Third-party advertising**: We display ads provided by Google AdSense. We do not control the content of these advertisements.

## 6. Disclaimer of Warranties

THE SITE AND ITS CONTENT ARE PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

We do not warrant that the Site will be uninterrupted, error-free, or free of harmful components.

## 7. Limitation of Liability

TO THE FULLEST EXTENT PERMITTED BY LAW, {SITE_NAME} AND ITS OPERATORS SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF THE SITE.

This includes, but is not limited to, damages for loss of profits, data, or other intangible losses, even if we have been advised of the possibility of such damages.

## 8. Accuracy of Information

While we strive to provide accurate and up-to-date information, we make no representations or warranties about the accuracy, completeness, or reliability of any content. Financial information, tool recommendations, and strategies mentioned on the Site may change after publication.

**Always do your own research** and consult qualified professionals before making financial decisions.

## 9. External Links

The Site may contain links to third-party websites. We do not control and are not responsible for the content, privacy policies, or practices of any third-party websites. Accessing external links is at your own risk.

## 10. Changes to Terms

We reserve the right to modify these Terms at any time. Changes will be effective immediately upon posting to the Site. Your continued use of the Site after changes constitutes acceptance of the revised Terms.

## 11. Governing Law

These Terms shall be governed by and construed in accordance with the laws of the jurisdiction in which {SITE_NAME} operates, without regard to its conflict of law provisions.

## 12. Contact

For questions about these Terms, contact us:

- **Email**: legal@{SITE_URL.replace('https://', '').replace('http://', '').split('/')[0]}
- **Site**: {SITE_URL}
"""


def generate_contact_page() -> str:
    """Generate a contact page for AdSense compliance."""
    return f"""---
title: "Contact Us"
date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
layout: page
---

# Contact Us

We'd love to hear from you. Whether you have a question about our content, a collaboration proposal, or feedback — reach out using any of the methods below.

## Email

**General Inquiries**: hello@{SITE_URL.replace('https://', '').replace('http://', '').split('/')[0]}

**Privacy & Legal**: privacy@{SITE_URL.replace('https://', '').replace('http://', '').split('/')[0]}

## Social Media

You can also find us on:
- **Pinterest**: [{SITE_NAME} on Pinterest]({SITE_URL})

## Response Time

We aim to respond to all inquiries within **48 hours** during business days.

## Privacy

Any personal information you provide in your message will be handled in accordance with our [Privacy Policy]({{< relref "/privacy-policy" >}}). We will only use your contact information to respond to your inquiry.
"""


def push_legal_pages(dry_run: bool = False):
    """Generate and push all mandatory legal pages."""
    pages = {
        f"{PAGES_DIR}/privacy-policy.md": generate_privacy_policy(),
        f"{PAGES_DIR}/terms-of-service.md": generate_terms_of_service(),
        f"{PAGES_DIR}/contact.md": generate_contact_page(),
    }

    print(f"\n{'='*60}")
    print("LEGAL PAGES GENERATION")
    print(f"{'='*60}")
    print(f"Site: {SITE_NAME} ({SITE_URL})")
    print(f"{'='*60}\n")

    for filename, content in pages.items():
        print(f"[LEGAL] {filename}")
        if dry_run:
            print(f"  DRY RUN — would push {len(content)} bytes")
        else:
            try:
                result = push_to_github(filename, content, f"Add {filename.split('/')[-1]}")
                print(f"  Pushed: {result['content']['html_url']}")
            except Exception as e:
                print(f"  ERROR: {e}")

    print(f"\n{'='*60}")
    print("LEGAL PAGES COMPLETE")
    print(f"{'='*60}")
    print("\nThese pages are required for Google AdSense approval.")
    print("Make sure to update SITE_URL and SITE_NAME in the script or env vars.")
    print("Also add navigation links to these pages in your site's layout.\n")


# ============ ARTICLE GENERATION ============

def generate_article_gemini(keyword: str, tone: str = "informative") -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""Write a comprehensive, SEO-optimized blog article about "{keyword}".

Requirements:
- Tone: {tone}
- Include a compelling introduction
- 5-7 actionable sections with H2/H3 headings
- Practical tips the reader can implement today
- A "getting started" or "first steps" section
- Common mistakes to avoid
- 1500-2500 words
- No fluff or filler content
- Use the keyword "{keyword}" naturally 5-8 times
- IMPORTANT: The current year is {THIS_YEAR}. Use "{THIS_YEAR}" (not 2025 or any past year) in headings and references. Never hardcode a year.

Return ONLY valid JSON in this exact format (no markdown, no code fences):
{{
  "title": "Article Title Here (include {THIS_YEAR} if appropriate)",
  "excerpt": "A 2-sentence summary for SEO meta description",
  "tags": "tag1, tag2, tag3, {keyword}",
  "seo_title": "SEO Title (under 60 chars)",
  "seo_description": "SEO meta description (under 160 chars)",
  "content": "The full article in Markdown format here..."
}}"""

    response = requests.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096}
    })

    if response.status_code != 200:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

    text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def generate_article_openai(keyword: str, tone: str = "informative") -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"""Write a comprehensive, SEO-optimized blog article about "{keyword}".

Requirements:
- Tone: {tone}
- 5-7 actionable sections with H2/H3 headings
- Practical tips, a getting started section, common mistakes
- 1500-2500 words, no fluff
- Use keyword "{keyword}" naturally 5-8 times
- IMPORTANT: The current year is {THIS_YEAR}. Use "{THIS_YEAR}" in headings and references. Never hardcode a past year.

Return ONLY valid JSON:
{{"title": "...", "excerpt": "...", "tags": "...", "seo_title": "...", "seo_description": "...", "content": "markdown..."}}"""

    response = requests.post(url, headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }, json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8, "max_tokens": 4096,
    })

    if response.status_code != 200:
        raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

    text = response.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def slugify(text: str) -> str:
    slug = text.lower()
    for c in ["'", '"', "(", ")", "[", "]", ":", ";", ",", ".", "!", "?", "&", "+"]:
        slug = slug.replace(c, "")
    return slug.replace(" ", "-").replace("--", "-").strip("-")[:80]


def create_frontmatter(article: dict, keyword: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""---
title: "{article['title']}"
date: {now}
description: "{article['seo_description']}"
tags: [{article['tags']}]
keywords: ["{keyword}"]
seo:
  title: "{article['seo_title']}"
  description: "{article['seo_description']}"
---"""


def push_to_github(filename: str, content: str, commit_message: str):
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
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
        raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
    return response.json()


def run_pipeline(keyword: str, tone: str = "informative", dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"CONTENT PIPELINE")
    print(f"{'='*60}")
    print(f"Keyword: {keyword} | Tone: {tone} | Dry Run: {dry_run}")
    print(f"{'='*60}\n")

    print("[1/3] Generating article...")
    if GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
        article = generate_article_gemini(keyword, tone)
    elif OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
        article = generate_article_openai(keyword, tone)
    else:
        print("ERROR: Set GEMINI_API_KEY or OPENAI_API_KEY environment variable.")
        sys.exit(1)

    print(f"  Title: {article['title']}")
    print(f"  Tags: {article['tags']}")

    print("\n[2/3] Formatting as Markdown...")
    slug = slugify(article["title"])
    filename = f"{ARTICLES_DIR}/{slug}.md"
    frontmatter = create_frontmatter(article, keyword)
    full_content = f"{frontmatter}\n\n{article['content']}"
    print(f"  File: {filename}")

    if dry_run:
        print(f"\n[3/3] DRY RUN - would push to {GITHUB_REPO}")
        print(f"\n--- PREVIEW ---\n{full_content[:500]}...")
    else:
        print("\n[3/3] Pushing to GitHub...")
        result = push_to_github(filename, full_content, f"New article: {article['title']}")
        print(f"  Commit: {result['commit']['sha'][:8]}")
        print(f"  URL: {result['content']['html_url']}")

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"\nNext: Create a Pinterest pin with keyword '{keyword}'")
    print(f"  Run: python bulk_pin_creator.py --keyword '{keyword}' --csv --generate-images")
    print(f"  Pin title should match the search query exactly")
    print(f"  Pin image text: {article['title'][:60]}")
    return article


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blog Content Pipeline + Legal Pages")
    parser.add_argument("--keyword", type=str, help="Target keyword")
    parser.add_argument("--keywords-file", type=str, help="File with one keyword per line")
    parser.add_argument("--tone", type=str, default="informative",
                       choices=["informative", "casual", "professional", "persuasive"])
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't push")
    parser.add_argument("--init-legal", action="store_true",
                       help="Generate and push legal pages (privacy, terms, contact)")

    args = parser.parse_args()

    # Legal pages first if requested
    if args.init_legal:
        push_legal_pages(dry_run=args.dry_run)

    # Article generation
    if args.keywords_file:
        keywords = Path(args.keywords_file).read_text().strip().split("\n")
        keywords = [k.strip() for k in keywords if k.strip()]
        print(f"Batch mode: {len(keywords)} keywords")
        for kw in keywords:
            run_pipeline(kw, args.tone, args.dry_run)
    elif args.keyword:
        run_pipeline(args.keyword, args.tone, args.dry_run)
    elif not args.init_legal:
        parser.print_help()
        print("\nExamples:")
        print("  python content_pipeline.py --keyword 'digital thrift savings tools'")
        print("  python content_pipeline.py --init-legal --dry-run")
        print("  python content_pipeline.py --keyword 'test' --init-legal")