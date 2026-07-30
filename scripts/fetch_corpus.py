"""Download the Luma Learning Center articles into corpus/ as markdown.

Build-time only. Nothing under apps/ may import this module: at runtime the
chatbot reads corpus/ off local disk and never touches lumalabs.ai. That
separation is what makes "search returned nothing" mean "not in the docs"
rather than "the network was flaky".

    uv run python scripts/fetch_corpus.py [--force] [--limit N]
"""

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

INDEX_URL = "https://lumalabs.ai/learning-center/articles"
ARTICLE_URL = "https://lumalabs.ai/learning-center/articles/{slug}"
CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ask-luma-corpus-fetcher/1.0)"}
CONCURRENCY = 4
MIN_BODY_CHARS = 500


def extract_slugs(index_html: str) -> list[str]:
    """Read slugs off the index page's anchors, not with a regex over the raw HTML.

    A regex is tempting but wrong here: several real slugs contain a dot
    ("seedance-2.0-basics") and a character-class regex silently truncates them
    into slugs that 404.
    """
    soup = BeautifulSoup(index_html, "html.parser")
    return sorted(
        {
            a["href"].rstrip("/").split("/")[-1]
            for a in soup.find_all("a", href=True)
            if "/learning-center/articles/" in a["href"]
        }
    )


def parse_article(html: str, slug: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    heading = soup.find("h1")
    if heading:
        title = heading.get_text(strip=True)
    else:
        title = soup.title.get_text(strip=True).removesuffix(" | Luma").strip()

    main = soup.find("main")
    if main is None:
        raise RuntimeError(f"{slug}: no <main> element, page layout changed")
    for junk in main.find_all(["script", "style", "nav", "header", "footer", "svg", "button"]):
        junk.decompose()
    for h1 in main.find_all("h1"):
        h1.decompose()

    body = markdownify(str(main), heading_style="ATX", bullets="-", strip=["img"]).strip()
    # The CMS wraps every heading in bold. Left in, "## **What a Skill is**" makes
    # the runtime chunker's heading text noisy and hurts keyword matching on it.
    body = re.sub(r"^(#{2,6} )\*\*(.+?)\*\*\s*$", r"\1\2", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = "\n".join(line.rstrip() for line in body.splitlines())

    if len(body) < MIN_BODY_CHARS:
        raise RuntimeError(
            f"{slug}: extracted only {len(body)} chars. Refusing to write a near-empty "
            f"article — it would silently poison the search index."
        )
    return title, body


async def fetch_one(client: httpx.AsyncClient, slug: str, sem: asyncio.Semaphore) -> dict:
    url = ARTICLE_URL.format(slug=slug)
    async with sem:
        response = await client.get(url)
        response.raise_for_status()
        await asyncio.sleep(0.3)

    title, body = parse_article(response.text, slug)
    path = CORPUS_DIR / f"{slug}.md"
    path.write_text(
        f"---\ntitle: {title}\nslug: {slug}\nurl: {url}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    print(f"  {slug}  ({len(body)} chars)  {title}")
    return {"slug": slug, "title": title, "url": url}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download articles already on disk")
    parser.add_argument("--limit", type=int, help="only fetch the first N articles")
    args = parser.parse_args()

    CORPUS_DIR.mkdir(exist_ok=True)

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        index = await client.get(INDEX_URL)
        index.raise_for_status()
        slugs = extract_slugs(index.text)
        print(f"index lists {len(slugs)} articles")

        if args.limit:
            slugs = slugs[: args.limit]
        todo = slugs if args.force else [s for s in slugs if not (CORPUS_DIR / f"{s}.md").exists()]
        print(f"fetching {len(todo)}, skipping {len(slugs) - len(todo)} already on disk\n")

        sem = asyncio.Semaphore(CONCURRENCY)
        await asyncio.gather(*(fetch_one(client, slug, sem) for slug in todo))

    write_index(slugs)


def write_index(slugs: list[str]) -> None:
    """Rebuild index.json and manifest.json from whatever is on disk.

    index.json is the authoritative list of legitimate article titles: step 2's
    citation policy checks model output against it.
    """
    entries, digest = [], hashlib.sha256()
    for slug in slugs:
        path = CORPUS_DIR / f"{slug}.md"
        text = path.read_text(encoding="utf-8")
        title = re.search(r"^title: (.+)$", text, re.MULTILINE).group(1)
        entries.append({"slug": slug, "title": title, "url": ARTICLE_URL.format(slug=slug)})
        digest.update(slug.encode())
        digest.update(hashlib.sha256(text.encode()).digest())

    (CORPUS_DIR / "index.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (CORPUS_DIR / "manifest.json").write_text(
        json.dumps(
            {"corpus_hash": digest.hexdigest()[:16], "article_count": len(entries)},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {len(entries)} articles, corpus_hash={digest.hexdigest()[:16]}")


if __name__ == "__main__":
    if sys.version_info < (3, 12):
        raise SystemExit("needs python 3.12+")
    asyncio.run(main())
