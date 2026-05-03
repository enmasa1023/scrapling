#!/usr/bin/env python3
"""Export posts from a single X account without using X paid API.

This uses `snscrape` (unofficial scraping library), so availability depends on
X site changes and may occasionally break.

Requirements:
  pip install snscrape

Example:
  python export_x_posts_snscrape.py --username shinkaron --outdir ./x_archive --chunk-mb 20
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import snscrape.modules.twitter as sntwitter


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
        path = self.outdir / f"{self.base_name}_{self.index:04d}.txt"
        self.current_fp = path.open("wb")
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


def format_post(post: sntwitter.Tweet) -> str:
    return (
        "=" * 80
        + f"\nID: {post.id}\n"
        + f"Date(UTC): {post.date.astimezone(timezone.utc).isoformat()}\n"
        + f"URL: {post.url}\n"
        + f"Likes: {post.likeCount} / Reposts: {post.retweetCount}\n"
        + "-" * 80
        + f"\n{post.rawContent}\n\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export X posts into chunked text files (no paid API)")
    parser.add_argument("--username", required=True, help="X username without @")
    parser.add_argument("--outdir", default="./x_archive", help="Output directory")
    parser.add_argument("--chunk-mb", type=int, default=20, help="Chunk size in MB")
    parser.add_argument("--max-posts", type=int, default=0, help="0 means as many as available")
    parser.add_argument("--include-replies", action="store_true", help="Include replies")
    parser.add_argument("--include-retweets", action="store_true", help="Include reposts/retweets")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    writer = ChunkedWriter(
        outdir=outdir,
        base_name=f"{args.username}_posts_{now}",
        chunk_bytes=args.chunk_mb * 1024 * 1024,
    )

    query = f"from:{args.username}"
    scraper = sntwitter.TwitterSearchScraper(query)

    total = 0
    try:
        for post in scraper.get_items():
            if not args.include_replies and post.inReplyToTweetId is not None:
                continue
            if not args.include_retweets and post.retweetedTweet is not None:
                continue

            writer.write(format_post(post))
            total += 1

            if args.max_posts and total >= args.max_posts:
                break
    finally:
        writer.close()

    print(f"Done. Exported {total} posts to: {outdir}")


if __name__ == "__main__":
    main()
