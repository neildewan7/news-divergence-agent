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
            "source_type": {"type": "keyword"},
            "language": {"type": "keyword"},
            "published_date": {"type": "date"},
            "event_id": {"type": "keyword"},
            "url": {"type": "keyword"},
            "sourcecountry": {"type": "keyword"},
            "semantic_field": {"type": "semantic_text"},
        }
    }
}

if not es_client.indices.exists(index=INDEX_NAME):
    es_client.indices.create(index=INDEX_NAME, body=index_mapping)
    print(f"Created index: {INDEX_NAME}")
else:
    print(f"Index already exists: {INDEX_NAME}")

# Synthetic articles for the Libya Derna floods demo case (September 2023).
# These are clearly labelled synthetic fallback articles — not real reporting.
# Source names use "Synthetic" prefix so they are distinguishable from real data.
test_articles = [
    {
        "title": "Derna dam collapse kills hundreds as floodwaters tear through city, officials say",
        "body": (
            "Two dams on the outskirts of Derna, Libya collapsed overnight on September 10-11 2023 "
            "following Storm Daniel, releasing a wall of water that tore through residential "
            "neighbourhoods toward the sea. Libyan authorities in the Benghazi-based eastern "
            "government said at least 400 people had been killed and hundreds more were missing. "
            "Rescue teams were hampered by damaged roads and disrupted communications. "
            "[SYNTHETIC ARTICLE — for demonstration purposes only. Casualty figures are illustrative.]"
        ),
        "source": "SyntheticWire",
        "source_type": "wire",
        "language": "en",
        "published_date": "2023-09-11",
        "url": "https://synthetic.example/wire/derna-dam-collapse-2023-09-11",
        "sourcecountry": "Synthetic",
        "event_id": "libya-derna-2023-09",
    },
    {
        "title": "Thousands feared dead after Derna floods, civil society groups warn of higher toll",
        "body": (
            "Civil society monitors operating in eastern Libya warned that the official death toll "
            "from the Derna dam collapse dramatically understated casualties. Volunteer networks "
            "estimated several thousand people may have perished, citing entire neighbourhoods swept "
            "into the Mediterranean. The Libyan Red Crescent said it was impossible to confirm "
            "figures amid the chaos. Government sources had earlier reported around 400 dead. "
            "International organisations called for unimpeded access to the disaster area. "
            "[SYNTHETIC ARTICLE — for demonstration purposes only. Casualty figures are illustrative.]"
        ),
        "source": "SyntheticLocal",
        "source_type": "local_press",
        "language": "en",
        "published_date": "2023-09-12",
        "url": "https://synthetic.example/local/derna-toll-estimate-2023-09-12",
        "sourcecountry": "Synthetic",
        "event_id": "libya-derna-2023-09",
    },
    {
        "title": "Libya flood: UN humanitarian office puts Derna death toll at over 11,000",
        "body": (
            "The UN Office for the Coordination of Humanitarian Affairs said the death toll from "
            "the Derna floods had surpassed 11,000, with another 10,000 people still unaccounted for. "
            "OCHA warned that the true number of casualties could be far higher given the scale of "
            "destruction. The agency called for an international humanitarian operation and noted that "
            "damaged infrastructure was slowing access. Earlier government figures had cited hundreds "
            "of confirmed deaths. The wide gap between official and UN estimates has drawn scrutiny. "
            "[SYNTHETIC ARTICLE — for demonstration purposes only. Casualty figures are illustrative.]"
        ),
        "source": "SyntheticNGO",
        "source_type": "ngo",
        "language": "en",
        "published_date": "2023-09-14",
        "url": "https://synthetic.example/ngo/derna-un-toll-2023-09-14",
        "sourcecountry": "Synthetic",
        "event_id": "libya-derna-2023-09",
    },
    {
        "title": "Inondations à Derna : Bilan provisoire de plusieurs centaines de morts selon Tripoli",
        "body": (
            "Le gouvernement d'unité nationale basé à Tripoli a publié un bilan provisoire "
            "de plusieurs centaines de victimes dans les inondations de Derna. Ce chiffre est "
            "contesté par des sources locales qui évoquent des milliers de disparus. Les autorités "
            "de l'est libyen, sous contrôle du gouvernement rival de Benghazi, n'ont pas confirmé "
            "les chiffres de Tripoli. Les organisations humanitaires soulignent l'impossibilité "
            "d'effectuer des vérifications indépendantes faute d'accès. "
            "[ARTICLE SYNTHÉTIQUE — à des fins de démonstration uniquement.]"
        ),
        "source": "SyntheticFrench",
        "source_type": "international",
        "language": "fr",
        "published_date": "2023-09-13",
        "url": "https://synthetic.example/fr/derna-bilan-tripoli-2023-09-13",
        "sourcecountry": "Synthetic",
        "event_id": "libya-derna-2023-09",
    },
    {
        "title": "Eight Libyan officials arrested over Derna dam failure, prosecutor announces",
        "body": (
            "Libya's top prosecutor ordered the arrest of eight current and former officials in "
            "connection with the collapse of the Abu Mansur and Bilad dams above Derna. "
            "Those detained include the mayor of Derna and officials responsible for dam maintenance. "
            "The prosecutor cited dereliction of duty and alleged that warnings about dam deterioration "
            "had been ignored for years. Human rights groups called the arrests a positive step but "
            "warned that accountability must extend beyond local officials to national authorities. "
            "Death toll estimates by this point ranged from official figures of roughly 3,000 to "
            "UN estimates exceeding 11,000. "
            "[SYNTHETIC ARTICLE — for demonstration purposes only. Casualty figures are illustrative.]"
        ),
        "source": "SyntheticInternational",
        "source_type": "international",
        "language": "en",
        "published_date": "2023-09-25",
        "url": "https://synthetic.example/intl/derna-officials-arrested-2023-09-25",
        "sourcecountry": "Synthetic",
        "event_id": "libya-derna-2023-09",
    },
]

actions = [
    {
        "_index": INDEX_NAME,
        "_id": f"synthetic-{doc['source'].lower()}-{doc['event_id']}",
        "_source": doc,
    }
    for doc in test_articles
]
success, failed = helpers.bulk(es_client, actions, refresh=True)
print(f"Indexed {success} synthetic articles, {failed} failed")
