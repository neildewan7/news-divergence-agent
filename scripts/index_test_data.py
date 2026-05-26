import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

es_client = Elasticsearch(
    os.getenv("ELASTICSEARCH_ENDPOINT"),
    api_key=os.getenv("ELASTICSEARCH_API_KEY"),
)

INDEX_NAME = "news-articles"

index_mapping = {
    "mappings": {
        "properties": {
            "title": {"type": "text", "copy_to": "semantic_field"},
            "body": {"type": "text", "copy_to": "semantic_field"},
            "source": {"type": "keyword"},
            "language": {"type": "keyword"},
            "publish_date": {"type": "date"},
            "event_id": {"type": "keyword"},
            "semantic_field": {"type": "semantic_text"},
        }
    }
}

if not es_client.indices.exists(index=INDEX_NAME):
    es_client.indices.create(index=INDEX_NAME, body=index_mapping)
    print(f"Created index: {INDEX_NAME}")
else:
    print(f"Index already exists: {INDEX_NAME}")

# 5 fake articles, same event, divergent details — this is your tiny demo case
test_articles = [
    {
        "title": "Eight killed in Kabul market explosion, officials say",
        "body": "A bomb blast at a market in central Kabul on Tuesday killed at least eight people and wounded twelve, according to local police. The cause is under investigation.",
        "source": "Reuters", "language": "en", "publish_date": "2024-09-12",
        "event_id": "kabul-market-2024-09",
    },
    {
        "title": "Kabul blast: civil society groups report 14 dead",
        "body": "The death toll from Tuesday's market bombing has risen to 14, according to civil society monitors. The Taliban government has not confirmed casualties.",
        "source": "ToloNews", "language": "en", "publish_date": "2024-09-13",
        "event_id": "kabul-market-2024-09",
    },
    {
        "title": "Six dead in Kabul incident, ministry says",
        "body": "Afghanistan's Interior Ministry reported six fatalities from Tuesday's market explosion. No group has claimed responsibility.",
        "source": "Pajhwok", "language": "en", "publish_date": "2024-09-13",
        "event_id": "kabul-market-2024-09",
    },
    {
        "title": "Aid workers concerned about Kabul market victims",
        "body": "The ICRC expressed concern about civilian casualties from the Kabul market explosion. The organization called for protection of civilians.",
        "source": "ICRC", "language": "en", "publish_date": "2024-09-14",
        "event_id": "kabul-market-2024-09",
    },
    {
        "title": "Kabul explosion was targeted attack, analysts suggest",
        "body": "Analysts believe Tuesday's market bombing was a targeted attack on a Shia minority neighborhood. Death toll estimates range from 6 to 14 depending on the source.",
        "source": "BBC", "language": "en", "publish_date": "2024-09-15",
        "event_id": "kabul-market-2024-09",
    },
]

actions = [
    {
        "_index": INDEX_NAME,
        "_id": f"{doc['source']}-{doc['event_id']}".lower().replace(" ", "-"),
        "_source": doc,
    }
    for doc in test_articles
]
success, failed = helpers.bulk(es_client, actions, refresh=True)
print(f"Indexed {success} articles")