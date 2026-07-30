"""Keyword search over the in-memory corpus. Deliberately not RAG.

Weak recall is a feature here, not a shortcoming to apologise for. A retriever
that misses things regularly is what makes "does the model admit it doesn't
know?" a testable behavior instead of a hypothetical one.
"""

import re

from ask_luma import corpus

TOP_K = 5
SNIPPET_CHARS = 800
MIN_COVERAGE = 0.5  # a chunk must contain at least half the query terms

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "to", "use", "using", "what", "when",
    "where", "which", "who", "why", "with", "you", "your",
}


def _terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9.]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def search_docs(query: str) -> list[dict[str, str]]:
    """Return up to TOP_K matching chunks, or an empty list.

    Returning [] rather than the least-bad five is the important decision. If
    every query returns something, the model always has plausible-looking text
    to lean on and the "say you don't know" policy can never be exercised.
    """
    query_terms = _terms(query)
    if not query_terms:
        return []

    scored = []
    for chunk in corpus.chunks():
        title_terms = _terms(chunk.article_title)
        heading_terms = _terms(chunk.heading)
        body_terms = _terms(chunk.text)

        score, matched = 0, 0
        for term in query_terms:
            hits = 0
            if term in title_terms:
                score += 3
                hits += 1
            if term in heading_terms:
                score += 2
                hits += 1
            in_body = body_terms.count(term)
            if in_body:
                score += min(in_body, 3)
                hits += 1
            matched += bool(hits)

        if matched / len(query_terms) >= MIN_COVERAGE:
            scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "article_title": chunk.article_title,
            "heading": chunk.heading,
            "slug": chunk.slug,
            "url": chunk.url,
            "text": chunk.text[:SNIPPET_CHARS],
        }
        for _, chunk in scored[:TOP_K]
    ]
