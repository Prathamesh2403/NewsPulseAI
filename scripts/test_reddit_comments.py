"""
Diagnostic: Test comment RSS parsing on known posts with comments.
Finds a popular post, fetches its comment RSS, and dumps the raw parsing.
"""
import asyncio
import re
import sys
from html import unescape

import httpx

sys.path.insert(0, ".")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def strip_html(text):
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    clean = re.sub(r"submitted\s+by\s+/u/\S+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[link\]", "", clean)
    clean = re.sub(r"\[comments\]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


async def main():
    headers = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Step 1: Get a fresh list of posts from r/artificial
    print("=" * 60)
    print("Step 1: Fetching r/artificial hot posts via RSS...")
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        resp = await client.get("https://www.reddit.com/r/artificial/hot/.rss", timeout=20)
        print(f"  RSS status: {resp.status_code}")

        import feedparser
        feed = feedparser.parse(resp.text)
        entries = feed.entries[:5]
        print(f"  Got {len(entries)} entries. Testing comment RSS on each...\n")

        # Step 2: For each post, fetch its comment RSS with delay
        for i, entry in enumerate(entries):
            link = entry.get("link", "")
            title = strip_html(entry.get("title", ""))
            parts = link.split("/comments/")
            post_id = parts[1].split("/")[0] if len(parts) > 1 else ""

            if not post_id:
                print(f"  [{i+1}] SKIP - no post_id in {link}")
                continue

            # Respect rate limiting
            if i > 0:
                await asyncio.sleep(4)

            comment_url = f"https://www.reddit.com/r/artificial/comments/{post_id}/.rss"
            print(f"  [{i+1}] '{title[:60]}...'")
            print(f"       URL: {comment_url}")

            resp2 = await client.get(comment_url, timeout=20)
            print(f"       Status: {resp2.status_code}")

            if resp2.status_code != 200:
                print(f"       FAILED — content-type: {resp2.headers.get('content-type', 'N/A')}")
                continue

            feed2 = feedparser.parse(resp2.text)
            print(f"       Total entries in comment feed: {len(feed2.entries)}")

            # Parse comments — show raw link analysis
            comments = []
            for j, ce in enumerate(feed2.entries):
                ce_link = ce.get("link", "")
                after_comments = ce_link.split("/comments/")[-1] if "/comments/" in ce_link else ""
                segments = [s for s in after_comments.split("/") if s]
                body = strip_html(ce.get("summary", ""))

                is_op = len(segments) <= 2
                if j < 3 or not is_op:
                    print(f"         entry[{j}]: segments={len(segments)} is_op={is_op} body='{body[:60]}...'")

                if not is_op and body and len(body) > 5:
                    comments.append(body)

            print(f"       => Parsed {len(comments)} comments\n")


asyncio.run(main())
