import os
import time
import hashlib
import requests
import pandas as pd
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

import trafilatura

load_dotenv()

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_HEADERS = {"User-Agent": "news-divergence-agent/1.0"}
GDELT_SLEEP = 15  # minimum seconds between consecutive API calls

_WIRE = {"reuters.com", "apnews.com", "afp.com"}
_INTERNATIONAL = {"bbc.com", "bbc.co.uk", "aljazeera.com", "theguardian.com", "nytimes.com"}
_LOCAL = {"libyaherald.com", "libyanexpress.com", "marsad.ly", "libyaobserver.ly"}
_NGO = {"icrc.org", "msf.org", "unocha.org", "reliefweb.int"}


def classify_source(domain: str) -> str:
    d = domain.lower().lstrip("www.")
    if d in _WIRE:
        return "wire"
    if d in _INTERNATIONAL:
        return "international"
    if d in _LOCAL:
        return "local_press"
    if d in _NGO:
        return "ngo"
    if ".gov" in d:
        return "government"
    return "unknown"


def map_language(gdelt_language: str) -> str:
    mapping = {"English": "en", "Arabic": "ar", "French": "fr", "Italian": "it"}
    if gdelt_language in mapping:
        return mapping[gdelt_language]
    return gdelt_language[:2].lower() if gdelt_language else "xx"


def fetch_article_text(url: str):
    try:
        downloaded = trafilatura.fetch_url(url, no_ssl=False)
        if downloaded is None:
            return None
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        return text if text and len(text.strip()) > 50 else None
    except Exception:
        return None


def _gdelt_request(query: str, start_dt: str, end_dt: str, max_results: int):
    """Single GDELT API call; returns DataFrame or None on rate limit."""
    try:
        r = requests.get(
            GDELT_BASE,
            params={
                "query": query,
                "startdatetime": start_dt,
                "enddatetime": end_dt,
                "maxrecords": max_results,
                "mode": "artlist",
                "format": "json",
            },
            headers=GDELT_HEADERS,
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"GDELT network error: {exc}")
        return pd.DataFrame()

    if r.status_code == 429:
        return None  # signal: rate limited
    if r.status_code != 200:
        print(f"GDELT HTTP {r.status_code}: {r.text[:120]}")
        return pd.DataFrame()
    if "text/html" in r.headers.get("content-type", ""):
        print(f"GDELT API message: {r.text.strip()[:120]}")
        return pd.DataFrame()
    try:
        data = r.json()
        return pd.DataFrame(data.get("articles", []))
    except Exception as exc:
        print(f"GDELT JSON parse error: {exc}")
        return pd.DataFrame()


def _normalize_date(d: str) -> str:
    """Accept YYYY-MM-DD or YYYYMMDD000000, always return YYYYMMDD000000."""
    if len(d) == 10:
        return d.replace("-", "") + "000000"
    return d


def search_gdelt(query: str, start_date: str, end_date: str, max_results: int = 50) -> pd.DataFrame:
    """
    Query GDELT with AND keyword syntax.
    Auto-widens date range by 7 days each side and retries once if 0 results.
    """
    s = _normalize_date(start_date)
    e = _normalize_date(end_date)

    df = _gdelt_request(query, s, e, max_results)

    if df is None:
        # Rate limited — wait and retry once
        print("GDELT rate limited, waiting 20s before retry...")
        time.sleep(20)
        df = _gdelt_request(query, s, e, max_results)
        if df is None:
            print("GDELT rate limit persisted, returning empty.")
            df = pd.DataFrame()

    if len(df) == 0:
        s_wide = (datetime.strptime(s[:8], "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d") + "000000"
        e_wide = (datetime.strptime(e[:8], "%Y%m%d") + timedelta(days=7)).strftime("%Y%m%d") + "000000"
        print(f"0 results, widening to {s_wide[:8]}–{e_wide[:8]} and retrying...")
        time.sleep(GDELT_SLEEP)
        df2 = _gdelt_request(query, s_wide, e_wide, max_results)
        if df2 is not None and len(df2) > 0:
            df = df2

    if len(df) > 0:
        langs = df["language"].unique().tolist() if "language" in df.columns else []
        countries = df["sourcecountry"].dropna().unique().tolist()[:8] if "sourcecountry" in df.columns else []
        print(f"GDELT found {len(df)} articles | languages: {langs} | countries: {countries}")
    else:
        print("GDELT found 0 articles after retry.")

    return df


def index_articles(articles_df: pd.DataFrame, index_name: str = "news-articles") -> int:
    """
    Fetch full text and index articles into Elasticsearch.
    Returns count of newly indexed documents.
    """
    if len(articles_df) == 0:
        return 0

    es = Elasticsearch(
        os.getenv("ELASTICSEARCH_ENDPOINT"),
        api_key=os.getenv("ELASTICSEARCH_API_KEY"),
    )

    # Compute IDs and batch-check which already exist
    rows = list(articles_df.itertuples(index=False))
    url_col = "url" if hasattr(rows[0], "url") else None
    if url_col is None:
        print("No url column in DataFrame, skipping indexing.")
        return 0

    id_map = {}
    for row in rows:
        url = getattr(row, "url", "") or ""
        doc_id = hashlib.sha256(url.encode()).hexdigest()
        id_map[doc_id] = row

    # mget to check existing documents
    all_ids = list(id_map.keys())
    try:
        mget_resp = es.mget(index=index_name, body={"ids": all_ids}, source=False)
        existing_ids = {doc["_id"] for doc in mget_resp["docs"] if doc.get("found")}
    except Exception as exc:
        print(f"mget check failed ({exc}), assuming all new.")
        existing_ids = set()

    skipped_dupes = len(existing_ids)
    to_index = {doc_id: row for doc_id, row in id_map.items() if doc_id not in existing_ids}

    fetched = 0
    failed_fetch = 0
    indexed = 0

    for doc_id, row in to_index.items():
        url = getattr(row, "url", "") or ""
        body = fetch_article_text(url)
        if body is None:
            failed_fetch += 1
            continue
        fetched += 1

        seendate = getattr(row, "seendate", "") or ""
        try:
            published_date = datetime.strptime(seendate[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            published_date = seendate[:10] if len(seendate) >= 10 else ""

        domain = getattr(row, "domain", "") or ""
        language_raw = getattr(row, "language", "") or ""
        sourcecountry = getattr(row, "sourcecountry", "") or ""
        title = getattr(row, "title", "") or ""

        doc = {
            "id": doc_id,
            "title": title,
            "body": body,
            "source": domain,
            "source_type": classify_source(domain),
            "language": map_language(language_raw),
            "published_date": published_date,
            "url": url,
            "sourcecountry": sourcecountry,
            "event_id": "libya-derna-2023-09",
        }

        try:
            es.index(index=index_name, id=doc_id, document=doc)
            indexed += 1
        except Exception as exc:
            print(f"Index error for {url[:60]}: {exc}")
            failed_fetch += 1

    print(f"Indexed {indexed} new articles")
    print(f"Skipped {skipped_dupes} duplicates")
    print(f"Failed to fetch {failed_fetch} articles")
    return indexed


def populate_index_for_query(
    query: str,
    start_date: str = None,
    end_date: str = None,
) -> int:
    """
    Full pipeline: GDELT search → text fetch → Elastic index.
    Returns count of newly indexed articles.
    """
    t_start = time.time()

    if start_date is None or end_date is None:
        today = datetime.utcnow()
        end_date = today.strftime("%Y%m%d") + "000000"
        start_date = (today - timedelta(days=180)).strftime("%Y%m%d") + "000000"

    df = search_gdelt(query, start_date, end_date)
    newly_indexed = index_articles(df)

    elapsed = round(time.time() - t_start, 1)
    print(f"Pipeline total runtime: {elapsed}s")
    return newly_indexed
