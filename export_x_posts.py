#!/usr/bin/env python3
"""Export posts from a single X account into 20MB text chunks.

Requirements:
  pip install requests

Environment:
  X_BEARER_TOKEN=...  (X API v2 Bearer Token)

Example:
  python export_x_posts.py --username shinkaron --outdir ./x_archive --chunk-mb 20
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

API_BASE = "https://api.x.com/2"
# If your plan/environment still uses api.twitter.com, switch API_BASE accordingly.


class XApiError(RuntimeError):
    pass


def x_get(session: requests.Session, path: str, params: Optional[Dict[str, str]] = None) -> Dict:
    url = f"{API_BASE}{path}"
    resp = session.get(url, params=params, timeout=30)
    if resp.status_code >= 400:
        raise XApiError(f"{resp.status_code} {resp.text}")
    return resp.json()


def get_user_id(session: requests.Session, username: str) -> str:
    data = x_get(session, f"/users/by/username/{username}")
    try:
        return data["data"]["id"]
    except Exception as exc:
        raise XApiError(f"Could not resolve username={username}: {data}") from exc


def iter_user_posts(
    session: requests.Session,
    user_id: str,
    max_results: int = 100,
    sleep_sec: float = 1.0,
) -> Iterable[Dict]:
    next_token: Optional[str] = None
    while True:
        params = {
            "max_results": str(max_results),
            "tweet.fields": "created_at,lang,public_metrics",
            # オリジナル投稿のみ（リプライ・リポスト除外）
            "exclude": "replies,retweets",
        }
        if next_token:
            params["pagination_token"] = next_token

        data = x_get(session, f"/users/{user_id}/tweets", params=params)
        for post in data.get("data", []):
            yield post

        meta = data.get("meta", {})
        next_token = meta.get("next_token")
        if not next_token:
            break

        time.sleep(sleep_sec)


def format_post(post: Dict, username: str) -> str:
    created = post.get("created_at", "")
    text = post.get("text", "")
    pid = post.get("id", "")
    url = f"https://x.com/{username}/status/{pid}" if pid else ""
    metrics = post.get("public_metrics", {})
    like_count = metrics.get("like_count", 0)
    repost_count = metrics.get("retweet_count", 0)

    return (
        "=" * 80
        + f"\nID: {pid}\n"
        + f"Date(UTC): {created}\n"
        + f"URL: {url}\n"
        + f"Likes: {like_count} / Reposts: {repost_count}\n"
        + "-" * 80
        + f"\n{text}\n\n"
    )


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Export X posts into chunked text files")
    parser.add_argument("--username", required=True, help="X username without @")
    parser.add_argument("--outdir", default="./x_archive", help="Output directory")
    parser.add_argument("--chunk-mb", type=int, default=20, help="Chunk size in MB")
    parser.add_argument("--max-posts", type=int, default=0, help="0 means all available")
    parser.add_argument("--sleep", type=float, default=1.0, help="Sleep seconds between pages")
    args = parser.parse_args()

    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        raise SystemExit("X_BEARER_TOKEN is not set")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    user_id = get_user_id(session, args.username)

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    writer = ChunkedWriter(
        outdir=outdir,
        base_name=f"{args.username}_posts_{now}",
        chunk_bytes=args.chunk_mb * 1024 * 1024,
    )

    total = 0
    try:
        for post in iter_user_posts(session, user_id, sleep_sec=args.sleep):
            writer.write(format_post(post, args.username))
            total += 1
            if args.max_posts and total >= args.max_posts:
                break
    finally:
        writer.close()

    print(f"Done. Exported {total} posts to: {outdir}")


if __name__ == "__main__":
    main()
