"""Merge multiple arxiv JSON files, deduplicate, and categorize.

Usage:
    uv run scripts/arxiv_merge.py <json_file1> [json_file2 ...] \
        --known data/known_arxiv_ids.txt \
        [--deep <deep_json1> ...] \
        [--output-daily /tmp/daily.json] \
        [--output-deep /tmp/deep.json]

Reads parsed paper JSON files, deduplicates by arxiv ID,
filters out known IDs, categorizes into interest areas,
and outputs organized JSON.
"""

import argparse
import json
import sys
from pathlib import Path

# Interest area keywords for categorization
INTEREST_KEYWORDS = {
    "superconducting": {
        "tags": ["superconducting"],
        "title_kw": ["superconducting", "transmon", "xmon", "fluxonium"],
        "summary_kw": ["superconducting qubit", "transmon", "josephson"],
    },
    "surface_code": {
        "tags": ["surface_code"],
        "title_kw": ["surface code", "topological code", "toric code"],
        "summary_kw": ["surface code"],
    },
    "calibration": {
        "tags": ["calibration", "ml_calibration", "auto_calibration"],
        "title_kw": ["calibration", "benchmarking", "characterization"],
        "summary_kw": ["calibration", "characterization", "benchmarking"],
    },
    "qec": {
        "tags": ["qec"],
        "title_kw": ["error correction", "decoder", "fault-tolerant", "fault tolerant"],
        "summary_kw": ["error correction", "decoder", "logical qubit"],
    },
    "ai_quantum": {
        "tags": ["ml_calibration", "auto_calibration"],
        "title_kw": [
            "machine learning",
            "neural network",
            "large language model",
            "llm",
            "automated",
            "autonomous",
        ],
        "summary_kw": [
            "machine learning",
            "neural network",
            "large language model",
            "automated calibration",
        ],
    },
    "system_arch": {
        "tags": [],
        "title_kw": ["cloud", "architecture", "system", "processor", "neutral-atom", "neutral atom"],
        "summary_kw": ["cloud quantum", "quantum processor", "atom array"],
    },
}


def load_known_ids(path: str) -> set[str]:
    known = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                known.add(line)
    return known


def merge_papers(json_files: list[str]) -> dict[str, dict]:
    merged = {}
    for path in json_files:
        with open(path) as f:
            papers = json.load(f)
        for p in papers:
            pid = p["id"]
            if pid in merged:
                merged[pid]["tags"] = list(set(merged[pid]["tags"] + p["tags"]))
            else:
                merged[pid] = p
    return merged


def categorize(paper: dict) -> list[str]:
    """Return list of matching interest area keys."""
    tags = set(paper.get("tags", []))
    title_lower = paper["title"].lower()
    summary_lower = paper["summary"].lower()[:500]

    matched = []
    for area, rules in INTEREST_KEYWORDS.items():
        # Check tag match
        if tags & set(rules["tags"]):
            matched.append(area)
            continue
        # Check title keywords
        if any(kw in title_lower for kw in rules["title_kw"]):
            matched.append(area)
            continue
        # Check summary keywords
        if any(kw in summary_lower for kw in rules["summary_kw"]):
            matched.append(area)
            continue

    return matched


def main():
    parser = argparse.ArgumentParser(description="Merge and categorize arxiv papers")
    parser.add_argument("json_files", nargs="+", help="Daily JSON files to merge")
    parser.add_argument("--known", required=True, help="Path to known_arxiv_ids.txt")
    parser.add_argument("--deep", nargs="*", default=[], help="Deep search JSON files")
    parser.add_argument("--output-daily", default="/tmp/arxiv_daily.json")
    parser.add_argument("--output-deep", default="/tmp/arxiv_deep.json")
    args = parser.parse_args()

    known = load_known_ids(args.known)

    # Merge daily papers
    all_daily = merge_papers(args.json_files)
    new_daily = {k: v for k, v in all_daily.items() if k not in known}

    # Categorize daily papers
    categorized = {}
    general = []
    for pid, paper in new_daily.items():
        areas = categorize(paper)
        paper["interest_areas"] = areas
        if areas:
            for area in areas:
                categorized.setdefault(area, []).append(paper)
        else:
            general.append(paper)

    daily_output = {
        "total_fetched": len(all_daily),
        "known_filtered": len(all_daily) - len(new_daily),
        "new_papers": len(new_daily),
        "categorized": {k: [p["id"] for p in v] for k, v in categorized.items()},
        "general": [p["id"] for p in general],
        "papers": new_daily,
    }

    with open(args.output_daily, "w") as f:
        json.dump(daily_output, f, ensure_ascii=False, indent=2)

    # Merge deep search papers (exclude known + daily)
    if args.deep:
        all_deep = merge_papers(args.deep)
        daily_ids = set(new_daily.keys())
        new_deep = {
            k: v for k, v in all_deep.items() if k not in known and k not in daily_ids
        }
        for pid, paper in new_deep.items():
            paper["interest_areas"] = categorize(paper)

        deep_output = {
            "total_fetched": len(all_deep),
            "new_papers": len(new_deep),
            "papers": new_deep,
        }
        with open(args.output_deep, "w") as f:
            json.dump(deep_output, f, ensure_ascii=False, indent=2)
        print(f"Deep: {len(new_deep)} new papers", file=sys.stderr)

    # Summary to stderr
    print(f"Daily: {len(new_daily)} new / {len(all_daily)} total", file=sys.stderr)
    for area, pids in daily_output["categorized"].items():
        print(f"  {area}: {len(pids)}", file=sys.stderr)
    print(f"  general: {len(general)}", file=sys.stderr)


if __name__ == "__main__":
    main()
