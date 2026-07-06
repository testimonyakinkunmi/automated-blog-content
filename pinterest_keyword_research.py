"""
PINTEREST KEYWORD RESEARCH TOOL
=================================
Scrapes Pinterest search auto-suggest to expand your keyword list.
Pinterest's search bar drops related phrases as you type —
this script automates that discovery process.

SETUP:
  pip install requests beautifulsoup4

USAGE:
  python pinterest_keyword_research.py --seed "fintech"
  python pinterest_keyword_research.py --seed "digital savings" --depth 2
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

# ============ CONFIGURATION ============
# Pinterest doesn't require auth for search suggestions
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


def get_pinterest_suggestions(query: str) -> list[str]:
    """
    Get auto-suggest keywords from Pinterest search.
    Pinterest returns suggestions as JSON for typeahead queries.
    """
    suggestions = []

    try:
        # Pinterest's search suggestion endpoint
        url = f"https://www.pinterest.com/resource/SearchSuggestionResource/get/"
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
            # Fallback: scrape the search page for related terms
            print(f"  API returned {response.status_code}, trying page scrape...")
            search_url = f"https://www.pinterest.com/search/pins/?q={quote(query)}"
            resp = requests.get(search_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                # Look for related search terms in the HTML
                import re
                patterns = re.findall(r'"related_terms":\[(.*?)\]', resp.text)
                if patterns:
                    terms = re.findall(r'"(.*?)"', patterns[0])
                    suggestions.extend([t for t in terms if t.lower() != query.lower()])

    except requests.RequestException as e:
        print(f"  Request error for '{query}': {e}")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in suggestions:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)

    return unique


def expand_keyword(seed: str, depth: int = 1) -> list[dict]:
    """
    Recursively expand a seed keyword using Pinterest suggestions.
    depth=1: only direct suggestions
    depth=2: also get suggestions for each suggestion
    """
    all_keywords = []

    print(f"\n  Seed: '{seed}'")
    suggestions = get_pinterest_suggestions(seed)
    print(f"  Found {len(suggestions)} suggestions")

    for kw in suggestions:
        all_keywords.append({
            "keyword": kw,
            "seed": seed,
            "depth": 1,
        })

        if depth >= 2:
            time.sleep(0.5)  # Be polite to Pinterest
            sub_suggestions = get_pinterest_suggestions(kw)
            for sub_kw in sub_suggestions:
                all_keywords.append({
                    "keyword": sub_kw,
                    "seed": kw,
                    "depth": 2,
                })

    return all_keywords


def assess_competition(keyword: str) -> str:
    """
    Simple heuristic for competition level.
    Longer, more specific keywords = lower competition.
    """
    words = keyword.split()
    if len(words) >= 5:
        return "low"
    elif len(words) >= 3:
        return "medium"
    else:
        return "high"


def save_results(keywords: list[dict], output_file: str):
    """Save results to JSON file."""
    # Add competition assessment
    for kw in keywords:
        kw["competition"] = assess_competition(kw["keyword"])
        kw["discovered_at"] = datetime.now().isoformat()

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_keywords": len(keywords),
        "by_depth": {
            "1": len([k for k in keywords if k["depth"] == 1]),
            "2": len([k for k in keywords if k["depth"] == 2]),
        },
        "keywords": keywords,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pinterest Keyword Research Tool")
    parser.add_argument("--seed", type=str, help="Seed keyword to expand")
    parser.add_argument("--seeds-file", type=str, help="File with one seed keyword per line")
    parser.add_argument("--depth", type=int, default=1, choices=[1, 2],
                       help="Expansion depth (default: 1)")
    parser.add_argument("--output", type=str, default="keywords_research.json",
                       help="Output JSON file (default: keywords_research.json)")

    args = parser.parse_args()

    all_results = []

    seeds = []
    if args.seeds_file:
        seeds = Path(args.seeds_file).read_text().strip().split("\n")
        seeds = [s.strip() for s in seeds if s.strip()]
    elif args.seed:
        seeds = [args.seed]
    else:
        parser.print_help()
        print("\nExample: python pinterest_keyword_research.py --seed 'fintech'")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"PINTEREST KEYWORD RESEARCH")
    print(f"{'='*60}")
    print(f"Seeds: {len(seeds)}")
    print(f"Depth: {args.depth}")
    print(f"{'='*60}")

    for seed in seeds:
        results = expand_keyword(seed, args.depth)
        all_results.extend(results)
        if seed != seeds[-1]:
            time.sleep(1)  # Rate limiting

    output = save_results(all_results, args.output)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Total keywords discovered: {output['total_keywords']}")
    print(f"  Depth 1: {output['by_depth']['1']}")
    print(f"  Depth 2: {output['by_depth']['2']}")
    print(f"\nSaved to: {args.output}")

    # Print top keywords
    print(f"\nTop keywords by specificity (lowest competition):")
    low_comp = [k for k in all_results if assess_competition(k["keyword"]) == "low"]
    for kw in low_comp[:15]:
        print(f"  [LOW]   {kw['keyword']}")
    med_comp = [k for k in all_results if assess_competition(k["keyword"]) == "medium"]
    for kw in med_comp[:10]:
        print(f"  [MED]   {kw['keyword']}")

    print(f"\nNext step: Import these into your Agentic Pipeline dashboard")