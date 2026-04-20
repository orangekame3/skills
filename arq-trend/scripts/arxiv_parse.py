"""Parse arxiv API XML response and output JSON.

Usage:
    uv run scripts/arxiv_parse.py <xml_file> [--tag <tag>]

Reads an arxiv Atom XML file or RSS XML file (possibly with trailing HTTP_CODE line),
extracts paper metadata, and prints JSON array to stdout.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

RSS_NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def clean_xml(content: str) -> str:
    """Remove trailing HTTP_CODE line appended by curl -w."""
    return re.sub(r"\nHTTP_CODE: \d+\s*$", "", content)


def is_rss(root: ET.Element) -> bool:
    """Detect if this is an RSS feed (vs Atom)."""
    return root.tag == "rss" or root.find(".//channel") is not None


def parse_rss_entries(root: ET.Element, tag: str) -> list[dict]:
    """Parse RSS format (from rss.arxiv.org)."""
    papers = []
    for item in root.findall(".//item"):
        link = item.find("link")
        if link is None or link.text is None:
            continue
        eid = link.text.split("/abs/")[-1]
        eid = re.sub(r"v\d+$", "", eid)

        title_el = item.find("title")
        title = " ".join(title_el.text.split()) if title_el is not None and title_el.text else ""

        creator = item.find("dc:creator", RSS_NS)
        authors_str = creator.text.strip() if creator is not None and creator.text else ""
        authors = [a.strip() for a in authors_str.split(",")]

        desc = item.find("description")
        desc_text = desc.text if desc is not None and desc.text else ""
        # Remove 'arXiv:... Abstract: ' prefix
        summary = re.sub(r"^arXiv:.*?Abstract:\s*", "", desc_text, flags=re.DOTALL).strip()
        summary = " ".join(summary.split())

        pub_date = item.find("pubDate")
        date = ""
        if pub_date is not None and pub_date.text:
            # Parse "Mon, 20 Apr 2026 00:00:00 -0400" → "2026-04-20"
            from email.utils import parsedate_to_datetime
            try:
                dt = parsedate_to_datetime(pub_date.text)
                date = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                date = ""

        announce_type = item.find("arxiv:announce_type", RSS_NS)
        atype = announce_type.text.strip() if announce_type is not None and announce_type.text else ""

        # Only include new and cross-listed papers
        if atype not in ("new", "cross"):
            continue

        category = item.find("category")
        primary_cat = category.text.strip() if category is not None and category.text else "quant-ph"

        papers.append(
            {
                "id": eid,
                "title": title,
                "authors": authors,
                "summary": summary,
                "date": date,
                "primary_category": primary_cat,
                "categories": [primary_cat],
                "tags": [tag],
            }
        )
    return papers


def parse_atom_entries(root: ET.Element, tag: str) -> list[dict]:
    """Parse Atom format (from export.arxiv.org API)."""
    papers = []
    for entry in root.findall("a:entry", NS):
        eid_raw = entry.find("a:id", NS).text.split("/abs/")[-1]
        eid = re.sub(r"v\d+$", "", eid_raw)
        title = " ".join(entry.find("a:title", NS).text.split())
        authors = [a.find("a:name", NS).text for a in entry.findall("a:author", NS)]
        summary = " ".join(entry.find("a:summary", NS).text.split())
        updated = entry.find("a:updated", NS).text[:10]

        primary_cat = ""
        pc = entry.find("arxiv:primary_category", NS)
        if pc is not None:
            primary_cat = pc.attrib.get("term", "")

        categories = [
            c.attrib.get("term", "") for c in entry.findall("a:category", NS)
        ]

        papers.append(
            {
                "id": eid,
                "title": title,
                "authors": authors,
                "summary": summary,
                "date": updated,
                "primary_category": primary_cat,
                "categories": categories,
                "tags": [tag],
            }
        )
    return papers


def parse_entries(content: str, tag: str) -> list[dict]:
    content = clean_xml(content)
    root = ET.fromstring(content)

    if is_rss(root):
        return parse_rss_entries(root, tag)
    return parse_atom_entries(root, tag)


def main():
    parser = argparse.ArgumentParser(description="Parse arxiv XML to JSON")
    parser.add_argument("xml_file", help="Path to XML file")
    parser.add_argument("--tag", default="general", help="Tag for categorization")
    args = parser.parse_args()

    with open(args.xml_file) as f:
        content = f.read()

    papers = parse_entries(content, args.tag)
    json.dump(papers, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
