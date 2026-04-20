"""Parse arxiv API XML response and output JSON.

Usage:
    uv run scripts/arxiv_parse.py <xml_file> [--tag <tag>]

Reads an arxiv Atom XML file (possibly with trailing HTTP_CODE line),
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


def clean_xml(content: str) -> str:
    """Remove trailing HTTP_CODE line appended by curl -w."""
    return re.sub(r"\nHTTP_CODE: \d+\s*$", "", content)


def parse_entries(content: str, tag: str) -> list[dict]:
    content = clean_xml(content)
    root = ET.fromstring(content)
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
