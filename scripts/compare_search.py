"""
Side-by-side retrieval comparison: BM25 vs semantic vs hybrid (RRF).

Usage:
    python scripts/compare_search.py "your query here"
    python scripts/compare_search.py            # runs the default demo queries

Read-only — queries the indices, never writes. Used to evaluate whether a
semantic / hybrid cutover beats the current BM25 search before committing to
a destructive reindex of `news-articles`. See docs/CHANGELOG.md Day 8.

Indices:
- news-articles      : live index, plain text fields (BM25 only, no semantic field)
- news-articles-v2   : staging index, multilingual semantic_text field
                       (multilingual-e5-small), bodies stored in original language
"""
import os
import sys
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

es = Elasticsearch(
    os.getenv("ELASTICSEARCH_ENDPOINT"),
    api_key=os.getenv("ELASTICSEARCH_API_KEY"),
    request_timeout=120,
)

SEMANTIC_INDEX = "news-articles-v2"
SRC = ["source", "language", "title"]


def _fmt(hits):
    lines = []
    for h in hits:
        s = h["_source"]
        lines.append(
            f"    [{s.get('language', '?')}] {s.get('source', '?'):<22} "
            f"{s.get('title', '')[:46]}"
        )
    return "\n".join(lines) or "    (no hits)"


def bm25(q, k=6, index=SEMANTIC_INDEX):
    r = es.search(index=index, size=k, _source=SRC,
                  query={"multi_match": {"query": q, "fields": ["title", "body"]}})
    return r["hits"]["hits"]


def semantic(q, k=6):
    r = es.search(index=SEMANTIC_INDEX, size=k, _source=SRC,
                  query={"semantic": {"field": "semantic_field", "query": q}})
    return r["hits"]["hits"]


def hybrid(q, k=6):
    r = es.search(
        index=SEMANTIC_INDEX, size=k, source=SRC,
        retriever={
            "rrf": {
                "retrievers": [
                    {"standard": {"query": {"multi_match": {"query": q, "fields": ["title", "body"]}}}},
                    {"standard": {"query": {"semantic": {"field": "semantic_field", "query": q}}}},
                ],
                "rank_window_size": 50,
                "rank_constant": 20,
            }
        },
    )
    return r["hits"]["hits"]


def _nonen(hits):
    return sum(1 for h in hits if h["_source"].get("language") != "en")


def run(q):
    print("=" * 74)
    print("QUERY:", q)
    for label, fn in [("BM25", bm25), ("SEMANTIC", semantic), ("HYBRID (RRF)", hybrid)]:
        try:
            hits = fn(q)
            print(f"  {label}  (non-English in top {len(hits)}: {_nonen(hits)})")
            print(_fmt(hits))
        except Exception as exc:
            print(f"  {label} ERROR: {repr(exc)[:200]}")
    print()


DEFAULT_QUERIES = [
    "How many people died in the Derna dam collapse?",
    "criticism of the government response to the floods",
    "humanitarian aid and reconstruction efforts",
]

if __name__ == "__main__":
    queries = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else DEFAULT_QUERIES
    for q in queries:
        run(q)
