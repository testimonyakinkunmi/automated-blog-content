"""
BULK PIN CREATOR
=================
Generates optimized pin metadata (titles + descriptions) from
your keyword list. Exports Pinterest Bulk Upload CSV + auto-generates
pin images using Pillow.

SETUP:
  pip install requests Pillow

USAGE:
  python bulk_pin_creator.py --keywords "digital thrift apps,fintech savings,budget tools"
  python bulk_pin_creator.py --keywords-file keywords_research.json
  python bulk_pin_creator.py --keyword "fintech budget" --board "Digital Finance Tools"
  python bulk_pin_creator.py --keyword "fintech budget" --generate-images  # auto-create pin PNGs
"""

import csv
import io
import json
import os
import sys
import argparse
import random
from datetime import datetime
from pathlib import Path

THIS_YEAR = datetime.now().year

# ============ TEMPLATES (dynamic year) ============

TITLE_TEMPLATES = [
    "{count} {keyword} You Need to Try This Year",
    "Best {keyword} for Beginners (Step by Step)",
    "How I Use {keyword} to Save {amount} Every Month",
    "Stop Overpaying — {count} {keyword} That Actually Work",
    "The {keyword} Guide Nobody Tells You About",
    "{keyword}: {count} Expert Tips That Changed Everything",
    "I Tried {count} {keyword} — Here's What Actually Works",
    f"{{keyword}} for {{audience}}: Complete {THIS_YEAR} Guide",
    "How to Master {keyword} in {timeframe} (Realistic Plan)",
    "Why {keyword} Is the Secret to Saving More Money",
]

DESCRIPTION_TEMPLATES = [
    "Discover the best {keyword} that actually deliver results. This guide breaks down {count} proven strategies with real examples you can start using today. Save this pin for later and click through for the full breakdown.",
    "Tired of wasting time on {keyword} that don't work? I tested {count} options and narrowed it down to the ones worth your time. Click to read the full comparison and find your perfect match.",
    "The ultimate {keyword} resource for {audience}. Learn how to get started, avoid common mistakes, and build a system that works on autopilot. Full guide with actionable steps inside.",
    "If you're looking for {keyword} that actually move the needle, this is for you. {count} no-nonsense tips backed by real experience. Click through to read the complete guide.",
    "Ready to level up your {keyword} game? These {count} strategies helped me transform my approach completely. Detailed breakdown inside — click to read now and save for later.",
]

AUDIENCES = [
    "beginners", "busy people", "side hustlers", "smart savers",
    "students", "young professionals", "anyone on a budget",
]

TIMEFRAMES = ["30 Days", "a Week", "a Month", "90 Days", "7 Days"]

AMOUNTS = ["$200", "$500", "$1,000", "hundreds", "thousands"]

# ============ IMAGE GENERATION CONFIG ============

PIN_WIDTH = 1000
PIN_HEIGHT = 1500

BACKGROUND_GRADIENTS = [
    ((232, 93, 47), (220, 38, 38), (185, 28, 28)),       # orange → red
    ((234, 88, 12), (202, 78, 8), (154, 52, 18)),         # amber → deep amber
    ((220, 38, 38), (185, 28, 28), (127, 29, 29)),        # red → dark red
    ((234, 88, 12), (234, 134, 55), (251, 191, 36)),      # amber → warm
    ((249, 115, 22), (234, 88, 12), (220, 38, 38)),       # orange gradient
]

TEXT_COLORS = [
    (255, 255, 255),   # white
    (255, 255, 255),   # white (more likely)
    (30, 30, 30),      # near-black (for light backgrounds)
]


def generate_pin_metadata(keyword: str, board_name: str = "", article_url: str = "") -> dict:
    """Generate optimized pin title and description for a keyword."""

    title = random.choice(TITLE_TEMPLATES).format(
        keyword=keyword.title(),
        count=random.randint(5, 10),
        amount=random.choice(AMOUNTS),
    )

    description = random.choice(DESCRIPTION_TEMPLATES).format(
        keyword=keyword.lower(),
        count=random.randint(5, 10),
        audience=random.choice(AUDIENCES),
    )

    image_text = title[:60] + ("..." if len(title) > 60 else "")

    words = keyword.lower().split()
    hashtags = []
    for w in words:
        hashtags.append(f"#{w.replace(' ', '')}")
    hashtags.extend([f"#{w}" for w in words if len(w) > 3])
    hashtags = list(dict.fromkeys(hashtags))[:5]

    return {
        "keyword": keyword,
        "board": board_name,
        "pin_title": title,
        "pin_description": description,
        "image_text_overlay": image_text,
        "hashtags": " ".join(hashtags),
        "article_url": article_url,
        "ideal_image_ratio": "2:3 (1000x1500px)",
        "text_position": "Center or bottom third",
    }


def load_keywords_from_json(filepath: str) -> list[str]:
    """Load keywords from the research tool's JSON output."""
    data = json.loads(Path(filepath).read_text())
    return [k["keyword"] for k in data.get("keywords", [])]


# ============ CSV EXPORT (Pinterest Bulk Upload) ============

def export_pinterest_csv(pins: list[dict], output_path: str, base_url: str = ""):
    """
    Export pins as Pinterest Bulk Upload CSV.
    Pinterest expects columns: URL, Title, Description, Link, Board Section (optional)
    """
    csv_path = output_path.replace(".json", ".csv").replace(".txt", ".csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Pinterest Bulk Upload header
        writer.writerow(["Title", "Description", "Link", "Board"])

        for pin in pins:
            link = pin.get("article_url") or base_url or ""
            board = pin.get("board", "My Blog Pins")
            title = pin["pin_title"]
            desc = f"{pin['pin_description']}\n\n{pin['hashtags']}"
            writer.writerow([title, desc, link, board])

    return csv_path


# ============ PILLOW IMAGE GENERATION ============

def generate_pin_image(pin: dict, output_dir: str = "pin_images") -> str:
    """
    Auto-generate a Pinterest pin image (1000x1500px) using Pillow.
    Gradient background + bold white text overlay.
    Returns the file path of the generated PNG.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  WARNING: Pillow not installed. Run: pip install Pillow")
        print("  Skipping image generation for this pin.")
        return ""

    os.makedirs(output_dir, exist_ok=True)

    # Create image with gradient background
    img = Image.new("RGB", (PIN_WIDTH, PIN_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Pick a gradient
    colors = random.choice(BACKGROUND_GRADIENTS)

    # Draw vertical gradient
    for y in range(PIN_HEIGHT):
        ratio = y / PIN_HEIGHT
        if ratio < 0.5:
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * (ratio * 2))
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * (ratio * 2))
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * (ratio * 2))
        else:
            r2 = (ratio - 0.5) * 2
            r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * r2)
            g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * r2)
            b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * r2)
        draw.line([(0, y), (PIN_WIDTH, y)], fill=(r, g, b))

    # Load font — try system fonts, fall back to default
    text_color = random.choice(TEXT_COLORS)
    font_path = None
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            font_path = fp
            break

    # Main title font
    if font_path:
        try:
            font_large = ImageFont.truetype(font_path, 72)
            font_small = ImageFont.truetype(font_path, 36)
            font_cta = ImageFont.truetype(font_path, 28)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_cta = ImageFont.load_default()
    else:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_cta = ImageFont.load_default()

    # Draw text — word wrap
    text = pin["image_text_overlay"]
    max_width = PIN_WIDTH - 120  # 60px padding each side

    def word_wrap(text, font, max_w):
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_w and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    lines = word_wrap(text, font_large, max_width)
    line_height = 90
    total_height = len(lines) * line_height
    start_y = (PIN_HEIGHT - total_height) // 2 - 60  # shift up for CTA

    # Draw subtle text shadow
    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_large)
        w = bbox[2] - bbox[0]
        x = (PIN_WIDTH - w) // 2
        # Shadow
        draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 80), font=font_large)
        # Main text
        draw.text((x, y), line, fill=text_color, font=font_large)

    # Draw "Click to read more →" at bottom
    cta_text = "Click to read more →"
    cta_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0]
    cta_x = (PIN_WIDTH - cta_w) // 2
    cta_y = PIN_HEIGHT - 100
    draw.text((cta_x, cta_y), cta_text, fill=(255, 255, 255, 200), font=font_cta)

    # Draw a subtle decorative line
    line_y = cta_y - 20
    draw.line([(200, line_y), (PIN_WIDTH - 200, line_y)], fill=(255, 255, 255, 100), width=2)

    # Save
    safe_name = pin["keyword"].lower().replace(" ", "-").replace("/", "-")[:40]
    filename = f"{safe_name}-{random.randint(1000,9999)}.png"
    filepath = os.path.join(output_dir, filename)
    img.save(filepath, "PNG", quality=95)

    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Pin Creator with CSV Export + Image Generation")
    parser.add_argument("--keywords", type=str, help="Comma-separated keywords")
    parser.add_argument("--keywords-file", type=str, help="JSON file from keyword research tool")
    parser.add_argument("--keyword", type=str, help="Single keyword")
    parser.add_argument("--board", type=str, default="My Blog Pins", help="Default board name")
    parser.add_argument("--base-url", type=str, default="", help="Your blog's base URL for pin links")
    parser.add_argument("--output", type=str, default="pin_metadata.json", help="Output JSON file")
    parser.add_argument("--csv", action="store_true", help="Also export Pinterest Bulk Upload CSV")
    parser.add_argument("--generate-images", action="store_true", help="Auto-generate pin images using Pillow")
    parser.add_argument("--image-dir", type=str, default="pin_images", help="Output dir for generated images")
    parser.add_argument("--canva-instructions", action="store_true", help="Print Canva fallback instructions")

    args = parser.parse_args()

    keywords = []

    if args.keyword:
        keywords = [args.keyword]
    elif args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    elif args.keywords_file:
        keywords = load_keywords_from_json(args.keywords_file)
    else:
        parser.print_help()
        print("\nExample: python bulk_pin_creator.py --keyword 'fintech budget' --csv --generate-images")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"BULK PIN CREATOR")
    print(f"{'='*60}")
    print(f"Keywords: {len(keywords)}")
    print(f"Board: {args.board}")
    print(f"Year: {THIS_YEAR} (dynamic)")
    print(f"CSV Export: {'Yes' if args.csv else 'No'}")
    print(f"Image Gen: {'Yes' if args.generate_images else 'No'}")
    print(f"{'='*60}\n")

    results = []
    for kw in keywords:
        pin = generate_pin_metadata(kw, args.board, args.base_url)
        results.append(pin)

        print(f"Keyword: {kw}")
        print(f"  Title: {pin['pin_title']}")
        print(f"  Desc:  {pin['pin_description'][:80]}...")

        if args.generate_images:
            img_path = generate_pin_image(pin, args.image_dir)
            if img_path:
                pin["generated_image"] = img_path
                print(f"  Image: {img_path}")
        print()

    # Save JSON
    with open(args.output, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "board": args.board,
            "total_pins": len(results),
            "pins": results,
        }, f, indent=2)
    print(f"Saved {len(results)} pins → {args.output}")

    # CSV export
    if args.csv:
        csv_path = export_pinterest_csv(results, args.output, args.base_url)
        print(f"Saved Pinterest Bulk Upload CSV → {csv_path}")
        print(f"  → Upload this file at: https://www.pinterest.com/ads/bulk-create/")

    # Image generation summary
    if args.generate_images:
        img_count = len([p for p in results if p.get("generated_image")])
        print(f"Generated {img_count} pin images → {args.image_dir}/")
        if img_count < len(results):
            print("  (Some images skipped — install Pillow: pip install Pillow)")