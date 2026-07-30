"""Loads corpus/ into memory at startup and chunks it by heading.

Everything here is read-only and offline. The fetch script under scripts/ is the
only thing that talks to lumalabs.ai, and nothing in this package may import it.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus"


@dataclass(frozen=True)
class Chunk:
    article_title: str
    slug: str
    url: str
    heading: str
    text: str


_chunks: list[Chunk] = []
_articles: list[dict[str, str]] = []
_corpus_hash: str = ""


def load() -> None:
    """Read the corpus off disk. Refuses to start on an empty corpus.

    A missing corpus would present as "the chatbot answers 'I don't know' to
    everything", which looks like a prompt or model problem and sends debugging
    in completely the wrong direction. Better to die at startup.
    """
    global _chunks, _articles, _corpus_hash

    index_path = CORPUS_DIR / "index.json"
    if not index_path.exists():
        raise RuntimeError(
            f"No corpus at {CORPUS_DIR}. Run: uv run python scripts/fetch_corpus.py"
        )

    _articles = json.loads(index_path.read_text(encoding="utf-8"))
    _corpus_hash = json.loads((CORPUS_DIR / "manifest.json").read_text())["corpus_hash"]

    _chunks = []
    for article in _articles:
        path = CORPUS_DIR / f"{article['slug']}.md"
        body = path.read_text(encoding="utf-8").split("---", 2)[2]
        _chunks.extend(_chunk_article(article, body))

    if not _chunks:
        raise RuntimeError(f"Corpus at {CORPUS_DIR} produced zero chunks")


def _chunk_article(article: dict[str, str], body: str) -> list[Chunk]:
    """Split on ## and ### so a chunk is one coherent section, not N tokens.

    Heading-based chunks keep their own title, which is what lets the model cite
    a real section instead of a page number.
    """
    chunks, heading, buffer = [], "", []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(
                Chunk(
                    article_title=article["title"],
                    slug=article["slug"],
                    url=article["url"],
                    heading=heading,
                    text=text,
                )
            )

    for line in body.splitlines():
        match = re.match(r"^(#{2,3})\s+(.*)$", line)
        if match:
            flush()
            heading, buffer = match.group(2).strip(), []
        else:
            buffer.append(line)
    flush()
    return chunks


def chunks() -> list[Chunk]:
    return _chunks


def article_titles() -> set[str]:
    """Authoritative list of citable titles, used by step 2's citation check."""
    return {a["title"] for a in _articles}


def stats() -> tuple[str, int, int]:
    return _corpus_hash, len(_articles), len(_chunks)
