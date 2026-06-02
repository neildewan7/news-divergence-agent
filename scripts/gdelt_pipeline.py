import os
import time
import hashlib
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI

import trafilatura

load_dotenv()

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_HEADERS = {"User-Agent": "news-divergence-agent/1.0"}
GDELT_SLEEP = 5  # minimum seconds between consecutive API calls

GCP_PROJECT = "news-divergence-project"

# Languages to query in addition to English, in GDELT's full-name format
GDELT_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "fr": "French",
    "el": "Greek",
    "es": "Spanish",
    "it": "Italian",
}
EXTRA_LANGUAGES = ["ar", "fr", "el"]

_gemini = None

def _get_gemini():
    global _gemini
    if _gemini is None:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _gemini = ChatVertexAI(
                model="gemini-2.5-flash",
                project=GCP_PROJECT,
                location="us-central1",
            )
    return _gemini


def translate_to_english(text: str, source_lang: str) -> str:
    """Translate text to English using Gemini via Vertex AI."""
    try:
        llm = _get_gemini()
        prompt = (
            f"Translate the following text to English. "
            f"Return only the translated text, no explanation.\n\n{text[:3000]}"
        )
        response = llm.invoke(prompt)
        result = response.content if hasattr(response, "content") else str(response)
        if isinstance(result, list):
            result = "".join(b.get("text", "") for b in result if isinstance(b, dict) and b.get("type") == "text")
        return result.strip() or text
    except Exception as exc:
        print(f"Translation failed for lang={source_lang}: {exc}")
        return text  # fall back to original so the article is still indexed

_WIRE = {
    "reuters.com", "apnews.com", "afp.com",
    "rfi.fr", "france24.com", "africanews.com", "thepeninsulaqatar.com",
}
_INTERNATIONAL = {
    "bbc.com", "bbc.co.uk", "aljazeera.com", "theguardian.com", "nytimes.com",
    "english.aawsat.com", "globalsecurity.org",
}
_LOCAL = {
    "libyaherald.com", "libyanexpress.com", "marsad.ly", "libyaobserver.ly",
    "skai.gr", "hurriyetdailynews.com", "lancashiretelegraph.co.uk",
}
_NGO = {"icrc.org", "msf.org", "unocha.org", "reliefweb.int", "amnesty.org"}
_GOVERNMENT = {"unsmil.unmissions.org", "un.org"}


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
    if d in _GOVERNMENT or ".gov" in d:
        return "government"
    return "unknown"


def map_language(gdelt_language: str) -> str:
    mapping = {"English": "en", "Arabic": "ar", "French": "fr", "Italian": "it"}
    if gdelt_language in mapping:
        return mapping[gdelt_language]
    return gdelt_language[:2].lower() if gdelt_language else "xx"


_FETCH_HEADERS = {"User-Agent": "news-divergence-agent/1.0"}

def fetch_article_text(url: str):
    try:
        resp = requests.get(url, timeout=5, headers=_FETCH_HEADERS)
        resp.raise_for_status()
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
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


def index_articles(
    articles_df: pd.DataFrame,
    index_name: str = "news-articles",
    end_date: str = None,
) -> int:
    """
    Fetch full text and index articles into Elasticsearch.
    Returns count of newly indexed documents.
    """
    if len(articles_df) == 0:
        return 0

    end_date_cutoff = None
    if end_date:
        norm = _normalize_date(end_date)
        end_date_cutoff = f"{norm[0:4]}-{norm[4:6]}-{norm[6:8]}"

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
    to_index = dict(list(
        {doc_id: row for doc_id, row in id_map.items() if doc_id not in existing_ids}.items()
    )[:15])

    fetched = 0
    failed_fetch = 0
    indexed = 0

    # Fetch all article texts concurrently, then index sequentially.
    def _fetch(item):
        doc_id, row = item
        return doc_id, row, fetch_article_text(getattr(row, "url", "") or "")

    with ThreadPoolExecutor(max_workers=10) as pool:
        fetch_results = list(pool.map(_fetch, to_index.items()))

    for doc_id, row, body in fetch_results:
        url = getattr(row, "url", "") or ""
        if body is None:
            failed_fetch += 1
            continue
        fetched += 1

        seendate = getattr(row, "seendate", "") or ""
        try:
            published_date = datetime.strptime(seendate[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            published_date = seendate[:10] if len(seendate) >= 10 else ""

        if end_date_cutoff and published_date and published_date > end_date_cutoff:
            continue

        domain = getattr(row, "domain", "") or ""
        language_raw = getattr(row, "language", "") or ""
        lang_iso = map_language(language_raw)
        sourcecountry = getattr(row, "sourcecountry", "") or ""
        title = getattr(row, "title", "") or ""

        body_en = translate_to_english(body, lang_iso) if lang_iso != "en" else body

        doc = {
            "id": doc_id,
            "title": title,
            "body": body_en,
            "body_original": body,
            "source": domain,
            "source_type": classify_source(domain),
            "language": lang_iso,
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

    newly_indexed = 0

    df_en = search_gdelt(query, start_date, end_date)
    newly_indexed += index_articles(df_en, end_date=end_date)

    for lang_iso in EXTRA_LANGUAGES:
        lang_name = GDELT_LANGUAGE_NAMES[lang_iso]
        lang_query = f"{query} sourcelang:{lang_name}"
        print(f"Fetching {lang_name} articles...")
        time.sleep(GDELT_SLEEP)
        df_lang = search_gdelt(lang_query, start_date, end_date, max_results=25)
        newly_indexed += index_articles(df_lang, end_date=end_date)

    elapsed = round(time.time() - t_start, 1)
    print(f"Pipeline total runtime: {elapsed}s")
    return newly_indexed
