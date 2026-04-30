"""Orchestrate the full arxiv trend pipeline: fetch → parse → merge → arq check.

Usage:
    uv run scripts/arxiv_pipeline.py --known data/known_arxiv_ids.txt [--keyword "some keyword"] [--skip-deep]

Runs all steps and outputs a JSON manifest to stdout:
{
  "daily": "/tmp/arxiv_daily.json",
  "deep": "/tmp/arxiv_deep.json",
  "read_ids": ["2604.xxxxx", ...],
  "stats": { "new": 51, "total": 96, "deep_new": 3, "categories": {...} }
}
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
OUTDIR = "/tmp/arxiv_raw"

DAILY_TAGS = ["general", "rss", "superconducting", "surface_code", "calibration", "ml_calibration", "auto_calibration"]
DEEP_TAGS = ["deep_surface", "deep_sc_calib", "deep_cloud", "deep_decoder", "deep_llm", "deep_auto", "deep_optim"]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kwargs)


def step_fetch(keyword: str = "", skip_deep: bool = False) -> dict:
    """Run arxiv_fetch.py and return its manifest."""
    if os.path.exists(OUTDIR):
        shutil.rmtree(OUTDIR)

    cmd = ["uv", "run", str(SCRIPTS_DIR / "arxiv_fetch.py"), "--outdir", OUTDIR]
    if keyword:
        cmd += ["--keyword", keyword]
    if skip_deep:
        cmd += ["--skip-deep"]

    print("Step 1: Fetching papers...", file=sys.stderr)
    result = run(cmd)
    print(result.stderr, end="", file=sys.stderr)

    if result.returncode != 0 or not result.stdout.strip():
        print("Fetch script failed or returned empty output", file=sys.stderr)
        # Return a minimal manifest indicating RSS-only fallback
        return {"rate_limited": True, "files": {}}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Failed to parse fetch manifest: {e}", file=sys.stderr)
        return {"rate_limited": True, "files": {}}


def step_parse(manifest: dict) -> tuple[list[str], list[str]]:
    """Parse XML files to JSON. Returns (daily_jsons, deep_jsons)."""
    print("Step 2: Parsing XML → JSON...", file=sys.stderr)
    daily_jsons = []
    deep_jsons = []

    for tag in DAILY_TAGS + DEEP_TAGS:
        xml_path = os.path.join(OUTDIR, f"{tag}.xml")
        if not os.path.exists(xml_path):
            continue

        json_path = f"/tmp/arxiv_{tag}.json"
        result = run(["uv", "run", str(SCRIPTS_DIR / "arxiv_parse.py"), xml_path, "--tag", tag])
        with open(json_path, "w") as f:
            f.write(result.stdout)

        if tag in DAILY_TAGS:
            daily_jsons.append(json_path)
        else:
            deep_jsons.append(json_path)

    return daily_jsons, deep_jsons


def step_merge(known_ids: str, daily_jsons: list[str], deep_jsons: list[str]) -> dict:
    """Merge and categorize papers. Returns stats dict."""
    print("Step 3: Merging and categorizing...", file=sys.stderr)
    cmd = [
        "uv", "run", str(SCRIPTS_DIR / "arxiv_merge.py"),
        *daily_jsons,
        "--known", known_ids,
        "--output-daily", "/tmp/arxiv_daily.json",
        "--output-deep", "/tmp/arxiv_deep.json",
    ]
    if deep_jsons:
        cmd += ["--deep", *deep_jsons]

    result = run(cmd)
    print(result.stderr, end="", file=sys.stderr)

    # Parse stats from daily JSON
    with open("/tmp/arxiv_daily.json") as f:
        daily = json.load(f)

    stats = {
        "new": daily["new_papers"],
        "total": daily["total_fetched"],
        "categories": {k: len(v) for k, v in daily["categorized"].items()},
        "general": len(daily.get("general", [])),
    }

    if os.path.exists("/tmp/arxiv_deep.json"):
        with open("/tmp/arxiv_deep.json") as f:
            deep = json.load(f)
        stats["deep_new"] = deep["new_papers"]
    else:
        stats["deep_new"] = 0

    return stats


def step_arq_check() -> list[str]:
    """Check which papers are already read via arq."""
    print("Step 4: Checking arq for read papers...", file=sys.stderr)

    # Collect all paper IDs from daily and deep
    ids = []
    for path in ["/tmp/arxiv_daily.json", "/tmp/arxiv_deep.json"]:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        ids.extend(data.get("papers", {}).keys())

    if not ids:
        return []

    # Check via arq has -
    result = run(["arq", "has", "-"], input="\n".join(ids))
    read_ids = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    if read_ids:
        print(f"  Found {len(read_ids)} read paper(s): {', '.join(read_ids)}", file=sys.stderr)
    else:
        print("  No read papers found", file=sys.stderr)

    return read_ids


def main():
    parser = argparse.ArgumentParser(description="Full arxiv trend pipeline")
    parser.add_argument("--known", required=True, help="Path to known_arxiv_ids.txt")
    parser.add_argument("--keyword", default="", help="Additional keyword filter")
    parser.add_argument("--skip-deep", action="store_true", help="Skip deep search queries")
    args = parser.parse_args()

    manifest = step_fetch(keyword=args.keyword, skip_deep=args.skip_deep)

    if manifest.get("rate_limited") and not manifest.get("files"):
        print("No data fetched (rate limited, no RSS fallback)", file=sys.stderr)
        sys.exit(2)

    daily_jsons, deep_jsons = step_parse(manifest)

    if not daily_jsons:
        print("No daily JSON files produced", file=sys.stderr)
        sys.exit(2)

    stats = step_merge(args.known, daily_jsons, deep_jsons)
    read_ids = step_arq_check()

    output = {
        "daily": "/tmp/arxiv_daily.json",
        "deep": "/tmp/arxiv_deep.json",
        "read_ids": read_ids,
        "stats": stats,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
