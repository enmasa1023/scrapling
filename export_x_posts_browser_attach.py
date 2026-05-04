#!/usr/bin/env python3
"""Attach to an already-running Edge/Chrome (CDP) and export X timeline posts.

Prerequisite: launch Edge with remote debugging enabled, e.g.
  msedge.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp\\edge-cdp"
Then open https://x.com/shinkaron in that Edge window and login once if needed.
"""

from __future__ import annotations

import argparse
import hashlib
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


def export_from_page(page, username: str, writer: ChunkedWriter, max_posts: int, scroll_wait_ms: int) -> int:
    seen = set()
    total = 0
    last_height = 0
    stagnant = 0

    while total < max_posts and stagnant < 8:
        page.wait_for_timeout(scroll_wait_ms)
        items = page.query_selector_all('article[data-testid="tweet"]')
        added = 0

        for it in items:
            link = it.query_selector('a[href*="/status/"]')
            href = link.get_attribute("href") if link else ""
            text_node = it.query_selector('div[data-testid="tweetText"]')
            text = text_node.inner_text().strip() if text_node else ""
            if not href or not text:
                continue
            if f"/{username}/status/" not in href:
                continue

            key = hashlib.sha1((href + text).encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)

            writer.write("=" * 80 + f"\nURL: https://x.com{href}\n" + "-" * 80 + f"\n{text}\n\n")
            total += 1
            added += 1
            if total >= max_posts:
                break

        new_height = page.evaluate("document.body.scrollHeight")
        page.mouse.wheel(0, 8000)
        if added == 0 and new_height == last_height:
            stagnant += 1
        else:
            stagnant = 0
        last_height = new_height

    return total


def main() -> None:
    ap = argparse.ArgumentParser(description="Attach to running Edge and export X posts")
    ap.add_argument("--username", required=True)
    ap.add_argument("--outdir", default="./x_archive")
    ap.add_argument("--chunk-mb", type=int, default=20)
    ap.add_argument("--max-posts", type=int, default=500)
    ap.add_argument("--cdp", default="http://127.0.0.1:9222")
    ap.add_argument("--scroll-wait-ms", type=int, default=1200)
    ap.add_argument("--allow-open-new-page", action="store_true",
                    help="If set, open a new tab when target page is not already open")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    writer = ChunkedWriter(outdir, f"{args.username}_posts_{now}", args.chunk_mb * 1024 * 1024)

    target = f"https://x.com/{args.username}"
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(args.cdp)
        if not browser.contexts:
            raise SystemExit(
                "接続先Edgeに利用可能なブラウザコンテキストがありません。\n"
                "通常のEdgeではなく、--remote-debugging-port付きで起動したEdgeを指定してください。"
            )
        context = browser.contexts[0]

        page = None
        for p in context.pages:
            if p.url.startswith(target):
                page = p
                break
        if page is None:
            if not args.allow_open_new_page:
                raise SystemExit(
                    f"既存タブが見つかりません: {target}\n"
                    "Edge側で対象ページを開いた状態で再実行してください。"
                )
            page = context.new_page()
            page.goto(target, wait_until="domcontentloaded")

        print(f"Using page: {page.url}")
        total = export_from_page(page, args.username, writer, args.max_posts, args.scroll_wait_ms)

    writer.close()
    print(f"Done. Exported {total} posts to {outdir}")


if __name__ == "__main__":
    main()
