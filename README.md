# Automated Blog Content — Pinterest Traffic Machine

A production-ready Jekyll blog + Python content pipeline that auto-generates SEO-optimised articles, Pinterest pin images, and bulk-upload CSVs — then pushes everything to GitHub for automatic deployment.

## Architecture

```
Pinterest Keyword Research → AI Article Generation → GitHub Push → Auto-Deploy → Pinterest Pins → Traffic → AdSense
```

## Quick Start

### 1. Prerequisites

- **Python 3.9+** with `requests`, `Pillow`
- **Ruby 3.0+** with Bundler (for Jekyll)
- A **Gemini** or **OpenAI** API key
- A **GitHub Personal Access Token** (repo scope)

### 2. Install Dependencies

```bash
# Python
pip install requests Pillow

# Ruby / Jekyll (local preview only)
bundle install
```

### 3. Configure Environment

Create a `.env` file (see `.env.example`) or export directly:

```bash
export GEMINI_API_KEY="your-key-here"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export GITHUB_REPO="your-username/automated-blog-content"
export GITHUB_USERNAME="your-username"
export GITHUB_EMAIL="you@email.com"
export SITE_URL="https://your-blog.github.io"
```

### 4. Run the Pipeline

```bash
# Single article
python content_pipeline.py --keyword "budget planner printable 2026"

# Batch from keyword file
python content_pipeline.py --keywords-file keywords.txt

# Also generate legal pages (first run only)
python content_pipeline.py --init-legal --keyword "test"
```

### 5. Generate Pinterest Pins

```bash
# Pin metadata + CSV + images
python bulk_pin_creator.py --keywords-file keywords.txt --csv --generate-images --base-url "https://your-blog.github.io"

# Upload the CSV at https://www.pinterest.com/ads/bulk-create/
# Upload generated images from pin_images/ to Pinterest
```

### 6. Preview Locally

```bash
bundle exec jekyll serve
# → http://localhost:4000
```

## Repository Structure

```
├── _config.yml              # Jekyll configuration (SEO, plugins, navigation)
├── _layouts/
│   ├── default.html         # Base HTML shell with OG tags
│   ├── post.html            # Article layout with JSON-LD, author box, ads
│   └── page.html            # Legal/info pages
├── _includes/
│   ├── head.html            # Meta tags, fonts, CSS
│   ├── header.html          # Navigation bar
│   ├── footer.html          # Footer with links
│   ├── author-box.html      # Author bio section
│   ├── related-posts.html   # Related articles widget
│   └── ad-slot.html         # AdSense placeholder
├── _posts/                  # Jekyll posts (YYYY-MM-DD-title.md)
├── assets/
│   ├── css/style.css        # Custom styles
│   └── images/pins/         # Pin images (committed after generation)
├── .github/workflows/
│   └── deploy.yml           # Auto-deploy on push to main
├── index.html               # Homepage
├── blog.html                # Blog listing page
├── privacy-policy.md        # AdSense-required legal page
├── terms-of-service.md      # AdSense-required legal page
├── contact.md               # AdSense-required contact page
├── content_pipeline.py      # AI article generator + GitHub pusher
├── bulk_pin_creator.py      # Pin metadata + CSV + Pillow image gen
├── pinterest_keyword_research.py  # Pinterest auto-suggest scraper
└── keywords.txt             # Seed keywords (one per line)
```

## Deployment

This repo auto-deploys via GitHub Actions. Just push to `main` and the `.github/workflows/deploy.yml` workflow builds the Jekyll site and publishes to GitHub Pages.

**To enable:**
1. Go to repo **Settings → Pages**
2. Set Source to **GitHub Actions**
3. Update `url` in `_config.yml` with your live URL
4. Push — the workflow handles the rest

## Pinterest Strategy

1. **Research** — Run `pinterest_keyword_research.py --seed "budget planner"` to find high-volume, low-competition long-tail keywords
2. **Create** — Run `content_pipeline.py --keywords-file keywords.txt` to generate SEO articles
3. **Pin** — Run `bulk_pin_creator.py --keywords-file keywords.txt --csv --generate-images` to create pin images and bulk-upload CSV
4. **Upload** — Upload CSV to Pinterest Bulk Create and pin images manually
5. **Rinse** — Repeat weekly with new keywords

## License

MIT