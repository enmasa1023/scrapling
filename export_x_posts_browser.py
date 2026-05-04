#!/usr/bin/env python3
"""Export visible X posts via a real browser session (no official API).

Flow:
1) Launch browser (Playwright).
2) User logs in manually if needed.
3) Script scrolls profile timeline and extracts visible tweet text blocks.
4) Save into chunked txt files.

Requirements:
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import argparse
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


class ChunkedWriter:
    def __init__(self, outdir: Path, base_name: str, chunk_bytes: int) -> None:
        self.outdir = outdir
        self.base_name = base_name
        self.chunk_bytes = chunk_bytes
        self.index = 0
        self.current_fp = None
        self.current_size = 0

    def _open_next(self) -> None:
        if self.current_fp:
            self.current_fp.close()
        self.index += 1
        self.current_fp = (self.outdir / f"{self.base_name}_{self.index:04d}.txt").open("wb")
        self.current_size = 0

    def write(self, text: str) -> None:
        data = text.encode("utf-8")
        if self.current_fp is None:
            self._open_next()
        if self.current_size + len(data) > self.chunk_bytes:
            self._open_next()
        self.current_fp.write(data)
        self.current_size += len(data)

    def close(self) -> None:
        if self.current_fp:
            self.current_fp.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Export X posts by browser automation (no API)")
    p.add_argument("--username", required=True)
    p.add_argument("--outdir", default="./x_archive")
    p.add_argument("--chunk-mb", type=int, default=20)
    p.add_argument("--max-posts", type=int, default=500)
    p.add_argument("--headless", action="store_true", help="Run headless (default shows browser)")
    p.add_argument("--scroll-wait", type=float, default=1.2)
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    writer = ChunkedWriter(outdir, f"{args.username}_posts_{now}", args.chunk_mb * 1024 * 1024)

    seen = set()
    total = 0
    profile_url = f"https://x.com/{args.username}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(profile_url, wait_until="domcontentloaded")
        print("If login wall appears, log in manually in the opened browser.")
        print("After timeline is visible, press Enter here to start extraction...")
        input()

        last_height = 0
        stagnant = 0

        while total < args.max_posts and stagnant < 8:
            page.wait_for_timeout(int(args.scroll_wait * 1000))
            items = page.query_selector_all('article[data-testid="tweet"]')

            added_this_round = 0
            for it in items:
                link = it.query_selector('a[href*="/status/"]')
                href = link.get_attribute("href") if link else ""
                text_node = it.query_selector('div[data-testid="tweetText"]')
                text = text_node.inner_text().strip() if text_node else ""
                if not href or not text:
                    continue

                key = hashlib.sha1((href + text).encode("utf-8")).hexdigest()
                if key in seen:
                    continue
                seen.add(key)

                url = "https://x.com" + href
                block = (
                    "=" * 80
                    + f"\nURL: {url}\n"
                    + "-" * 80
                    + f"\n{text}\n\n"
                )
                writer.write(block)
                total += 1
                added_this_round += 1
                if total >= args.max_posts:
                    break

            new_height = page.evaluate("document.body.scrollHeight")
            page.mouse.wheel(0, 8000)

            if added_this_round == 0 and new_height == last_height:
                stagnant += 1
            else:
                stagnant = 0
            last_height = new_height

    writer.close()
    print(f"Done. Exported {total} posts to {outdir}")


if __name__ == "__main__":
    main()
