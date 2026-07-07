"""
BULK PIN CREATOR — Pinterest Traffic Engine
=============================================
Generates Pinterest-optimised pin metadata, exports
Pinterest Bulk Upload CSVs, and auto-generates 1000x1500px
pin images using Pillow.

SETUP:
  pip install requests Pillow

USAGE:
  python bulk_pin_creator.py --keywords "budget planner printable,side hustle ideas"
  python bulk_pin_creator.py --keywords-file keywords.txt --csv --generate-images
  python bulk_pin_creator.py --keyword "fintech budget" --board "Money Tips" --base-url "https://yoursite.com"
"""

import csv
import json
import os
import sys
import argparse
import random
from datetime import datetime
from pathlib import Path

THIS_YEAR = datetime.now().year

# ─────────────────────────────────────────────────────────────
# TEMPLATES — dynamic year, Pinterest-optimised
# ─────────────────────────────────────────────────────────────
TITLE_TEMPLATES = [
    "{count} {keyword} You Need to Try in {year}",
    "Best {keyword} for Beginners (Step by Step)",
    "How I Use {keyword} to Save {amount} Every Month",
    "Stop Overpaying — {count} {keyword} That Actually Work",
    "The {keyword} Guide Nobody Tells You About",
    "{keyword}: {count} Expert Tips That Changed Everything",
    "I Tried {count} {keyword} — Here's What Actually Works",
    "{keyword} for {audience}: Complete {year} Guide",
    "How to Master {keyword} in {timeframe} (Realistic Plan)",
    "Why {keyword} Is the Secret to Saving More Money",
    "{count} {keyword} That Will Save You {amount} This {year}",
    "The Honest Truth About {keyword} (What Works in {year})",
]

DESCRIPTION_TEMPLATES = [
    "Discover the best {keyword} that actually deliver results. This guide breaks down {count} proven strategies with real examples you can start using today. Save this pin and click through for the full breakdown.",
    "Tired of wasting time on {keyword} that don't work? I tested {count} options and narrowed it down to the ones worth your time. Click to read the full comparison and find your perfect match.",
    "The ultimate {keyword} resource for {audience}. Learn how to get started, avoid common mistakes, and build a system that works on autopilot. Full guide with actionable steps inside.",
    "If you're looking for {keyword} that actually move the needle, this is for you. {count} no-nonsense tips backed by real experience. Click through to read the complete guide.",
    "Ready to level up your {keyword} game? These {count} strategies helped me transform my approach completely. Detailed breakdown inside — click to read now and save for later.",
    "Stop guessing with {keyword}. These {count} methods are backed by real results and are perfect for {audience}. Click through for the complete guide and start saving today.",
]

AUDIENCES = [
    "beginners", "busy people", "side hustlers", "smart savers",
    "students", "young professionals", "anyone on a budget",
    "moms", "freelancers",
]

TIMEFRAMES = ["30 Days", "a Week", "a Month", "90 Days", "7 Days"]
AMOUNTS = ["$200", "$500", "$1,000", "hundreds", "thousands"]

# ─────────────────────────────────────────────────────────────
# IMAGE GENERATION CONFIG
# ─────────────────────────────────────────────────────────────
PIN_WIDTH = 1000
PIN_HEIGHT = 1500

BACKGROUND_GRADIENTS = [
    ((230, 57, 70), (180, 40, 50), (120, 25, 35)),         # red
    ((14, 51, 96), (22, 33, 62), (26, 26, 46)),           # navy
    ((0, 128, 128), (0, 100, 100), (0, 70, 70)),          # teal
    ((230, 57, 70), (180, 50, 60), (14, 51, 96)),          # red → navy
    ((45, 106, 79), (30, 80, 60), (20, 55, 40)),          # green
    ((199, 125, 46), (160, 95, 30), (110, 65, 15)),       # amber/brown
]

TEXT_COLORS = [
    (255, 255, 255),
    (255, 255, 255),
    (255, 248, 240),
]


# ─────────────────────────────────────────────────────────────
# PIN METADATA GENERATION
# ─────────────────────────────────────────────────────────────
def generate_pin_metadata(keyword: str, board_name: str = "", article_url: str = "") -> dict:
    title = random.choice(TITLE_TEMPLATES).format(
        keyword=keyword.title(),
        count=random.randint(5, 10),
        amount=random.choice(AMOUNTS),
        year=THIS_YEAR,
        timeframe=random.choice(TIMEFRAMES),
    )

    description = random.choice(DESCRIPTION_TEMPLATES).format(
        keyword=keyword.lower(),
        count=random.randint(5, 10),
        audience=random.choice(AUDIENCES),
    )

    image_text = title[:55] + ("..." if len(title) > 55 else "")

    # Hashtags
    words = keyword.lower().split()
    hashtags = [f"#{w}" for w in words if len(w) > 2]
    hashtags.append(f"#budgettips")
    hashtags = list(dict.fromkeys(hashtags))[:6]

    return {
        "keyword": keyword,
        "board": board_name,
        "pin_title": title,
        "pin_description": f"{description}\n\n{' '.join(hashtags)}",
        "image_text_overlay": image_text,
        "hashtags": " ".join(hashtags),
        "article_url": article_url,
    }


def load_keywords_from_json(filepath: str) -> list:
    data = json.loads(Path(filepath).read_text())
    return [k["keyword"] for k in data.get("keywords", [])]


# ─────────────────────────────────────────────────────────────
# CSV EXPORT (Pinterest Bulk Upload format)
# ─────────────────────────────────────────────────────────────
def export_pinterest_csv(pins: list, output_path: str, base_url: str = "") -> str:
    csv_path = output_path.replace(".json", ".csv").replace(".txt", ".csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Description", "Link", "Board"])

        for pin in pins:
            link = pin.get("article_url") or base_url or ""
            board = pin.get("board", "My Blog Pins")
            writer.writerow([
                pin["pin_title"],
                pin["pin_description"],
                link,
                board,
            ])

    return csv_path


# ─────────────────────────────────────────────────────────────
# PILLOW IMAGE GENERATION (1000x1500px pin images)
# ─────────────────────────────────────────────────────────────
def generate_pin_image(pin: dict, output_dir: str = "pin_images") -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  WARNING: Pillow not installed. Run: pip install Pillow")
        return ""

    os.makedirs(output_dir, exist_ok=True)

    img = Image.new("RGB", (PIN_WIDTH, PIN_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Gradient background
    colors = random.choice(BACKGROUND_GRADIENTS)
    for y in range(PIN_HEIGHT):
        ratio = y / PIN_HEIGHT
        if ratio < 0.5:
            t = ratio * 2
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * t)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * t)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * t)
        else:
            t = (ratio - 0.5) * 2
            r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * t)
            g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * t)
            b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * t)
        draw.line([(0, y), (PIN_WIDTH, y)], fill=(r, g, b))

    # Load font
    text_color = random.choice(TEXT_COLORS)
    font_path = None
    for fp in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if os.path.exists(fp):
            font_path = fp
            break

    try:
        if font_path:
            font_large = ImageFont.truetype(font_path, 68)
            font_small = ImageFont.truetype(font_path, 32)
            font_cta = ImageFont.truetype(font_path, 26)
        else:
            font_large = ImageFont.load_default()
            font_small = font_large
            font_cta = font_large
    except Exception:
        font_large = ImageFont.load_default()
        font_small = font_large
        font_cta = font_large

    # Word wrap
    text = pin["image_text_overlay"]
    max_width = PIN_WIDTH - 120

    def word_wrap(t, font, max_w):
        words = t.split()
        lines, current = [], ""
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
    line_height = 88
    total_height = len(lines) * line_height
    start_y = (PIN_HEIGHT - total_height) // 2 - 50

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_large)
        w = bbox[2] - bbox[0]
        x = (PIN_WIDTH - w) // 2
        draw.text((x + 3, y + 3), line, fill=(0, 0, 0), font=font_large)  # shadow
        draw.text((x, y), line, fill=text_color, font=font_large)

    # CTA
    cta_text = "Click to read more"
    cta_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0]
    cta_x = (PIN_WIDTH - cta_w) // 2
    cta_y = PIN_HEIGHT - 90
    draw.line([(250, cta_y - 16), (PIN_WIDTH - 250, cta_y - 16)], fill=(*text_color, 120), width=2)
    draw.text((cta_x, cta_y), cta_text, fill=text_color, font=font_cta)

    # Save
    safe_name = pin["keyword"].lower().replace(" ", "-").replace("/", "-")[:40]
    filename = f"{safe_name}-{random.randint(1000, 9999)}.png"
    filepath = os.path.join(output_dir, filename)
    img.save(filepath, "PNG")
    return filepath


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Pin Creator — CSV + Image Generation")
    parser.add_argument("--keywords", type=str, help="Comma-separated keywords")
    parser.add_argument("--keywords-file", type=str, help="JSON file from keyword research or text file")
    parser.add_argument("--keyword", type=str, help="Single keyword")
    parser.add_argument("--board", type=str, default="Money Tips", help="Default board name")
    parser.add_argument("--base-url", type=str, default="", help="Blog base URL for pin links")
    parser.add_argument("--output", type=str, default="pin_metadata.json", help="Output JSON file")
    parser.add_argument("--csv", action="store_true", help="Export Pinterest Bulk Upload CSV")
    parser.add_argument("--generate-images", action="store_true", help="Auto-generate pin images")
    parser.add_argument("--image-dir", type=str, default="pin_images", help="Output dir for images")

    args = parser.parse_args()

    keywords = []
    if args.keyword:
        keywords = [args.keyword]
    elif args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    elif args.keywords_file:
        path = Path(args.keywords_file)
        if path.suffix == ".json":
            keywords = load_keywords_from_json(str(path))
        else:
            keywords = [k.strip() for k in path.read_text().strip().splitlines()
                        if k.strip() and not k.startswith("#")]
    else:
        parser.print_help()
        print("\nExample: python bulk_pin_creator.py --keyword 'budget planner' --csv --generate-images")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"BULK PIN CREATOR")
    print(f"{'='*60}")
    print(f"Keywords  : {len(keywords)}")
    print(f"Board     : {args.board}")
    print(f"Year      : {THIS_YEAR} (dynamic)")
    print(f"CSV Export: {'Yes' if args.csv else 'No'}")
    print(f"Image Gen : {'Yes' if args.generate_images else 'No'}")
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
    print(f"Saved {len(results)} pins -> {args.output}")

    if args.csv:
        csv_path = export_pinterest_csv(results, args.output, args.base_url)
        print(f"Saved Pinterest Bulk Upload CSV -> {csv_path}")
        print(f"  Upload at: https://www.pinterest.com/ads/bulk-create/")

    if args.generate_images:
        img_count = len([p for p in results if p.get("generated_image")])
        print(f"Generated {img_count} pin images -> {args.image_dir}/")