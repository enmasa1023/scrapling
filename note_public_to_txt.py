#!/usr/bin/env python3
"""Export publicly visible articles from a note.com /all page into txt files.

Usage:
  python note_public_to_txt.py --all-url https://note.com/shinkaron/all --out-dir output
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch_html(url: str, session: requests.Session) -> str:
    r = session.get(url, timeout=25)
    r.raise_for_status()
    return r.text


def parse_article_links(all_html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(all_html, "html.parser")
    links: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if not href or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        if re.match(r"^https://note\.com/[^/]+/n/[a-zA-Z0-9]+", full):
            links.add(full)
    return sorted(links)


def parse_article(html: str, url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    published = ""
    t = soup.find("time")
    if t:
        published = t.get("datetime", "").strip() or t.get_text(strip=True)

    body = ""
    article = soup.find("article")
    if article:
        body = article.get_text("\n", strip=True)
    else:
        body = soup.get_text("\n", strip=True)

    return {
        "url": url,
        "title": title,
        "published": published,
        "body": body,
    }


def safe_filename(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120] if s else "untitled"


def write_txt(article: dict[str, str], out_dir: Path, idx: int) -> Path:
    name = safe_filename(article["title"]) or f"article_{idx:03d}"
    path = out_dir / f"{idx:03d}_{name}.txt"
    text = (
        f"Title: {article['title']}\n"
        f"Published: {article['published']}\n"
        f"URL: {article['url']}\n"
        f"\n"
        f"{article['body']}\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-url", required=True, help="e.g. https://note.com/shinkaron/all")
    ap.add_argument("--out-dir", default="note_export_txt")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    all_html = fetch_html(args.all_url, s)
    links = parse_article_links(all_html, args.all_url)

    if not links:
        print("No public article links found.")
        return

    print(f"Found {len(links)} candidate articles")
    for i, link in enumerate(links, start=1):
        try:
            html = fetch_html(link, s)
            article = parse_article(html, link)
            p = write_txt(article, out_dir, i)
            print(f"[{i}/{len(links)}] saved: {p}")
        except Exception as e:
            print(f"[{i}/{len(links)}] failed: {link} ({e})")
        time.sleep(max(args.delay, 0.0))


if __name__ == "__main__":
    main()
