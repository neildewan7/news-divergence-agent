"""
One-off script: re-classify source_type for all docs in news-articles
using the current classify_source() domain mappings and update any
docs whose stored value differs.
"""
import os
import sys
from collections import Counter
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

sys.path.insert(0, os.path.dirname(__file__))
from gdelt_pipeline import classify_source

load_dotenv()

INDEX = "news-articles"
SCROLL_SIZE = 100

es = Elasticsearch(
    os.getenv("ELASTICSEARCH_ENDPOINT"),
    api_key=os.getenv("ELASTICSEARCH_API_KEY"),
)

# Fetch all docs via scroll
docs = []
resp = es.search(
    index=INDEX,
    body={"query": {"match_all": {}}, "_source": ["source", "source_type"], "size": SCROLL_SIZE},
    scroll="2m",
)
scroll_id = resp["_scroll_id"]
docs.extend(resp["hits"]["hits"])

while True:
    resp = es.scroll(scroll_id=scroll_id, scroll="2m")
    batch = resp["hits"]["hits"]
    if not batch:
        break
    docs.extend(batch)

es.clear_scroll(scroll_id=scroll_id)
print(f"Fetched {len(docs)} documents")

# Classify and build update actions
actions = []
already_correct = 0

for doc in docs:
    source_domain = doc["_source"].get("source", "")
    stored_type = doc["_source"].get("source_type", "")
    correct_type = classify_source(source_domain)

    if stored_type == correct_type:
        already_correct += 1
    else:
        actions.append({
            "_op_type": "update",
            "_index": INDEX,
            "_id": doc["_id"],
            "doc": {"source_type": correct_type},
        })

updated = len(actions)
print(f"Already correct: {already_correct}")
print(f"Needs update:    {updated}")

if actions:
    success, errors = helpers.bulk(es, actions, refresh=True)
    if errors:
        print(f"Bulk update errors: {errors}")

# Final breakdown — re-fetch source_type counts after update
resp = es.search(
    index=INDEX,
    body={
        "query": {"match_all": {}},
        "aggs": {"by_type": {"terms": {"field": "source_type.keyword", "size": 20}}},
        "size": 0,
    },
)
counts = {b["key"]: b["doc_count"] for b in resp["aggregations"]["by_type"]["buckets"]}

print("\nSource type breakdown after update:")
for stype, count in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {stype:<16} {count}")
print(f"\nTotal: {sum(counts.values())}")
