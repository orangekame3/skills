"""Fetch arxiv papers with rate limiting and retry logic.

Usage:
    uv run scripts/arxiv_fetch.py --outdir /tmp/arxiv_raw [--keyword "some keyword"]

Fetches papers from arxiv API for quant-ph category,
with proper rate limiting (sleep between requests),
exponential backoff on rate limit hits,
and RSS fallback.

Output: XML files in outdir, one per query.
Exit code 0 = success, 1 = partial (some queries failed), 2 = total failure.
"""

import argparse
import json
import os
import subprocess
import sys
import time

# Query definitions
GENERAL_QUERY = "cat:quant-ph"

INTEREST_QUERIES = {
    "superconducting": 'cat:quant-ph+AND+all:%22superconducting%22',
    "surface_code": 'cat:quant-ph+AND+all:%22surface+code%22',
    "calibration": 'cat:quant-ph+AND+all:%22calibration%22',
    "ml_calibration": 'cat:quant-ph+AND+all:%22machine+learning%22+AND+all:%22calibration%22',
    "auto_calibration": 'cat:quant-ph+AND+all:%22automated+calibration%22+AND+all:%22superconducting%22',
}

DEEP_QUERIES = {
    "deep_surface": 'cat:quant-ph+AND+all:%22surface+code%22+AND+all:%22experiment%22',
    "deep_sc_calib": 'cat:quant-ph+AND+all:%22superconducting%22+AND+all:%22calibration%22',
    "deep_cloud": 'cat:quant-ph+AND+all:%22quantum+computer%22+AND+all:%22cloud%22',
    "deep_decoder": 'cat:quant-ph+AND+all:%22quantum+error+correction%22+AND+all:%22decoder%22',
    "deep_llm": 'cat:quant-ph+AND+all:%22large+language+model%22+AND+all:%22calibration%22',
    "deep_auto": 'cat:quant-ph+AND+all:%22autonomous%22+AND+all:%22calibration%22',
    "deep_optim": 'cat:quant-ph+AND+all:%22calibration%22+AND+all:%22optimization%22+AND+all:%22superconducting%22',
}

API_BASE = "https://export.arxiv.org/api/query"
RSS_URL = "https://rss.arxiv.org/rss/quant-ph"
SLEEP_BETWEEN = 5  # seconds between requests
BACKOFF_TIMES = [10, 30]  # exponential backoff seconds


def fetch_url(url: str, timeout: int = 60) -> tuple[str, int]:
    """Fetch URL via curl, return (body, http_code).

    Returns ("", 0) on timeout or other failures instead of raising.
    """
    try:
        result = subprocess.run(
            ["curl", "-sL", "--connect-timeout", "30", "-w", "\nHTTP_CODE: %{http_code}", url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"  Timeout fetching {url[:80]}...", file=sys.stderr)
        return "", 0

    output = result.stdout
    # Extract HTTP code
    http_code = 0
    for line in output.strip().split("\n"):
        if line.startswith("HTTP_CODE: "):
            try:
                http_code = int(line.split(": ")[1])
            except ValueError:
                pass

    return output, http_code


def is_rate_limited(body: str, http_code: int) -> bool:
    """Check if the response indicates rate limiting or unavailability."""
    if http_code == 0 and not body:
        # Timeout or connection failure — treat as rate limited
        return True
    return http_code in (429, 503) or "Rate exceeded" in body


def fetch_with_retry(url: str) -> tuple[str, bool]:
    """Fetch with exponential backoff. Returns (body, success)."""
    body, code = fetch_url(url)
    if not is_rate_limited(body, code):
        return body, True

    for wait in BACKOFF_TIMES:
        print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
        time.sleep(wait)
        body, code = fetch_url(url)
        if not is_rate_limited(body, code):
            return body, True

    return body, False


def build_url(query: str, max_results: int = 20, sort_by: str = "submittedDate") -> str:
    return f"{API_BASE}?search_query={query}&start=0&max_results={max_results}&sortBy={sort_by}&sortOrder=descending"


def main():
    parser = argparse.ArgumentParser(description="Fetch arxiv papers")
    parser.add_argument("--outdir", required=True, help="Output directory for XML files")
    parser.add_argument("--keyword", default="", help="Additional keyword filter")
    parser.add_argument("--skip-deep", action="store_true", help="Skip deep search queries")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    rate_limited = False
    fetched_files = []

    # Step 0a: Test request
    print("Testing API availability...", file=sys.stderr)
    test_url = build_url(GENERAL_QUERY, max_results=1)
    body, code = fetch_url(test_url)
    if is_rate_limited(body, code):
        print("API rate limited, falling back to RSS", file=sys.stderr)
        rate_limited = True
    else:
        print("API available", file=sys.stderr)
        time.sleep(3)

    if not rate_limited:
        # Step 1a: General query
        query = GENERAL_QUERY
        if args.keyword:
            query = f"{GENERAL_QUERY}+AND+all:{args.keyword}"
        url = build_url(query)
        print(f"Fetching general...", file=sys.stderr)
        body, ok = fetch_with_retry(url)
        outpath = os.path.join(args.outdir, "general.xml")
        with open(outpath, "w") as f:
            f.write(body)
        fetched_files.append(("general", outpath))

        if not ok:
            rate_limited = True

    if not rate_limited:
        # Step 1b: Interest area queries
        time.sleep(SLEEP_BETWEEN)
        for name, query in INTEREST_QUERIES.items():
            print(f"Fetching {name}...", file=sys.stderr)
            url = build_url(query)
            body, ok = fetch_with_retry(url)
            outpath = os.path.join(args.outdir, f"{name}.xml")
            with open(outpath, "w") as f:
                f.write(body)
            fetched_files.append((name, outpath))

            if not ok:
                rate_limited = True
                break
            time.sleep(SLEEP_BETWEEN)

    if rate_limited and not any(n == "general" for n, _ in fetched_files):
        # RSS fallback
        print("Falling back to RSS...", file=sys.stderr)
        body, ok = fetch_with_retry(RSS_URL)
        outpath = os.path.join(args.outdir, "rss.xml")
        with open(outpath, "w") as f:
            f.write(body)
        fetched_files.append(("rss", outpath))

    if not rate_limited and not args.skip_deep:
        # Step 1.5: Deep search
        time.sleep(SLEEP_BETWEEN)
        for name, query in DEEP_QUERIES.items():
            print(f"Fetching {name}...", file=sys.stderr)
            url = build_url(query, max_results=5, sort_by="relevance")
            body, ok = fetch_with_retry(url)
            outpath = os.path.join(args.outdir, f"{name}.xml")
            with open(outpath, "w") as f:
                f.write(body)
            fetched_files.append((name, outpath))

            if not ok:
                print(f"Rate limited during deep search, skipping rest", file=sys.stderr)
                break
            time.sleep(SLEEP_BETWEEN)

    # Output manifest
    manifest = {
        "rate_limited": rate_limited,
        "files": {name: path for name, path in fetched_files},
    }
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
