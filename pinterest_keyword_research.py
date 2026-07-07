"""
PINTEREST KEYWORD RESEARCH TOOL
=================================
Scrapes Pinterest search auto-suggest to expand your keyword list.
Pinterest's search bar drops related phrases as you type —
this script automates that discovery process.

SETUP:
  pip install requests beautifulsoup4

USAGE:
  python pinterest_keyword_research.py --seed "budget planner"
  python pinterest_keyword_research.py --seed "side hustle ideas" --depth 2
  python pinterest_keyword_research.py --seeds-file seeds.txt
"""

import os
import sys
import json
import argparse
import time
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


def get_pinterest_suggestions(query: str) -> list:
    suggestions = []
    try:
        url = "https://www.pinterest.com/resource/SearchSuggestionResource/get/"
        params = {
            "source_url": f"/search/pins/?q={quote(query)}",
            "data": json.dumps({"options": {"query": query}}),
        }
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get("resource_response", {}).get("data", {}).get("results", [])
            for item in results:
                name = item.get("name", "")
                if name and name.lower() != query.lower():
                    suggestions.append(name)
        else:
            # Fallback: scrape the search page
            search_url = f"https://www.pinterest.com/search/pins/?q={quote(query)}"
            resp = requests.get(search_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                import re
                patterns = re.findall(r'"related_terms":\[(.*?)\]', resp.text)
                if patterns:
                    terms = re.findall(r'"(.*?)"', patterns[0])
                    suggestions.extend([t for t in terms if t.lower() != query.lower()])
    except requests.RequestException as e:
        print(f"  Request error for '{query}': {e}")

    # Deduplicate
    seen, unique = set(), []
    for s in suggestions:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)
    return unique


def expand_keyword(seed: str, depth: int = 1) -> list:
    all_keywords = []
    print(f"\n  Seed: '{seed}'")
    suggestions = get_pinterest_suggestions(seed)
    print(f"  Found {len(suggestions)} suggestions")

    for kw in suggestions:
        all_keywords.append({"keyword": kw, "seed": seed, "depth": 1})
        if depth >= 2:
            time.sleep(0.5)
            sub = get_pinterest_suggestions(kw)
            for sub_kw in sub:
                all_keywords.append({"keyword": sub_kw, "seed": kw, "depth": 2})
    return all_keywords


def assess_competition(keyword: str) -> str:
    words = keyword.split()
    if len(words) >= 5:
        return "low"
    elif len(words) >= 3:
        return "medium"
    return "high"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pinterest Keyword Research Tool")
    parser.add_argument("--seed", type=str, help="Seed keyword")
    parser.add_argument("--seeds-file", type=str, help="File with one seed per line")
    parser.add_argument("--depth", type=int, default=1, choices=[1, 2])
    parser.add_argument("--output", type=str, default="keywords_research.json")

    args = parser.parse_args()

    seeds = []
    if args.seeds_file:
        seeds = [s.strip() for s in Path(args.seeds_file).read_text().strip().splitlines() if s.strip()]
    elif args.seed:
        seeds = [args.seed]
    else:
        parser.print_help()
        sys.exit(1)

    print(f"{'='*60}")
    print(f"PINTEREST KEYWORD RESEARCH")
    print(f"{'='*60}")
    print(f"Seeds: {len(seeds)} | Depth: {args.depth}")
    print(f"{'='*60}")

    all_results = []
    for seed in seeds:
        all_results.extend(expand_keyword(seed, args.depth))
        if seed != seeds[-1]:
            time.sleep(1)

    # Add competition assessment
    for kw in all_results:
        kw["competition"] = assess_competition(kw["keyword"])
        kw["discovered_at"] = datetime.now().isoformat()

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_keywords": len(all_results),
        "keywords": all_results,
    }
    Path(args.output).write_text(json.dumps(output, indent=2))

    print(f"\n{'='*60}")
    print(f"Total keywords: {output['total_keywords']}")
    print(f"Saved to: {args.output}")

    low = [k for k in all_results if k["competition"] == "low"]
    for kw in low[:10]:
        print(f"  [LOW]  {kw['keyword']}")
    med = [k for k in all_results if k["competition"] == "medium"]
    for kw in med[:5]:
        print(f"  [MED]  {kw['keyword']}")