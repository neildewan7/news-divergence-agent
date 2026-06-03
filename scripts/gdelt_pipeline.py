import os
import time
import hashlib
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

import trafilatura

load_dotenv()

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_HEADERS = {"User-Agent": "news-divergence-agent/1.0"}
GDELT_SLEEP = 5  # minimum seconds between consecutive API calls

# Languages to query in addition to English, in GDELT's full-name format.
# Articles are stored in their original language; Elastic's multilingual
# semantic_text field handles cross-language retrieval — no translation step.
GDELT_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "fr": "French",
    "el": "Greek",
    "es": "Spanish",
    "it": "Italian",
}
EXTRA_LANGUAGES = ["ar", "fr", "el"]

_WIRE = {
    "reuters.com", "apnews.com", "ap.org", "afp.com",
    "rfi.fr", "france24.com", "africanews.com", "thepeninsulaqatar.com",
    "xinhuanet.com", "tass.com", "anadoluagency.com", "aa.com.tr",
    "rtbf.be", "antaranews.com", "article.wn.com",
}
_INTERNATIONAL = {
    "bbc.com", "bbc.co.uk", "aljazeera.com", "theguardian.com", "nytimes.com",
    "washingtonpost.com", "dw.com", "english.aawsat.com", "globalsecurity.org",
    "cnn.com", "middleeasteye.net", "pbs.org", "thestar.com.my", "the-star.co.ke",
    "foxnews.com", "artnews.com", "mprnews.org", "middleeastmonitor.com",
    "al-monitor.com", "the-independent.com", "independent.co.uk",
    "lemonde.fr", "fr.timesofisrael.com", "lematin.ch", "bfmtv.com",
    "alquds.co.uk", "arabic.people.com.cn", "modernghana.com",
}
_LOCAL = {
    "libyaherald.com", "libyanexpress.com", "marsad.ly", "libyaobserver.ly",
    "tolonews.com", "pajhwok.com", "ariananews.com",
    "skai.gr", "hurriyetdailynews.com", "lancashiretelegraph.co.uk",
    "sandiegouniontribune.com", "jamaicaobserver.com", "protothema.gr",
    "english.ahram.org.eg",
    "newsit.gr", "capital.gr", "alwasat.ly", "sudanile.com",
    "bucksfreepress.co.uk", "ceskenoviny.cz",
    "dostor.org", "almasryalyoum.com", "vetogate.com", "albayan.ae",
}
_NGO = {
    "icrc.org", "msf.org", "unocha.org", "reliefweb.int",
    "amnesty.org", "hrw.org", "acleddata.com",
}
_GOVERNMENT = {
    "unsmil.unmissions.org", "un.org", "state.gov", "fco.gov.uk", "gov.uk",
}
_OPINION = {
    "mondaq.com", "ruthfullyyours.com", "algemeiner.com",
    "antiwar.com", "honestreporting.com",
}


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
    if d in _OPINION:
        return "opinion"
    if d in _GOVERNMENT or ".gov" in d:
        return "government"
    return "unknown"


def map_language(gdelt_language: str) -> str:
    mapping = {
        "English": "en",
        "Arabic": "ar",
        "French": "fr",
        "Italian": "it",
        "Greek": "el",
        "Spanish": "es",
        "German": "de",
        "Portuguese": "pt",
        "Russian": "ru",
        "Turkish": "tr",
    }
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
    max_date: str = None,
    event_id: str = "unknown",
) -> int:
    """
    Fetch full text and index articles into Elasticsearch.
    max_date: YYYYMMDD000000 string — skip articles whose seendate exceeds this
              (prevents future-recrawled articles from corrupting historical corpora).
    Returns count of newly indexed documents.
    """
    if len(articles_df) == 0:
        return 0

    # Parse max_date cutoff once
    max_date_dt = None
    if max_date:
        try:
            max_date_dt = datetime.strptime(max_date[:8], "%Y%m%d")
        except Exception:
            pass

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

        seendate = getattr(row, "seendate", "") or ""
        try:
            article_dt = datetime.strptime(seendate[:8], "%Y%m%d")
            published_date = article_dt.strftime("%Y-%m-%d")
        except Exception:
            article_dt = None
            published_date = seendate[:10] if len(seendate) >= 10 else ""

        # Skip future-recrawled articles that exceed the query end date
        if max_date_dt and article_dt and article_dt > max_date_dt:
            print(f"Skipping future-dated article ({published_date}): {url[:60]}")
            failed_fetch += 1
            continue

        fetched += 1

        domain = getattr(row, "domain", "") or ""
        language_raw = getattr(row, "language", "") or ""
        lang_iso = map_language(language_raw)
        sourcecountry = getattr(row, "sourcecountry", "") or ""
        title = getattr(row, "title", "") or ""

        # Store the article in its ORIGINAL language. Elastic's multilingual
        # semantic_text field (multilingual-e5) embeds it directly, so no
        # translation is needed — cross-language retrieval happens in the
        # shared embedding space. See docs/CONVENTIONS.md (Semantic search).
        doc = {
            "id": doc_id,
            "title": title,
            "body": body,
            "source": domain,
            "source_type": classify_source(domain),
            "language": lang_iso,
            "published_date": published_date,
            "url": url,
            "sourcecountry": sourcecountry,
            "event_id": event_id,
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


# Term synonyms for English synonym-expansion pass
_SYNONYMS = {
    "flood":     ["flooding", "inundation"],
    "floods":    ["flooding", "inundation"],
    "earthquake": ["quake", "tremor"],
    "explosion": ["blast", "bombing"],
    "conflict":  ["clashes", "fighting"],
    "disaster":  ["catastrophe", "emergency"],
    "attack":    ["assault", "strike"],
    "crisis":    ["emergency", "catastrophe"],
}


def _synonym_query(query: str):
    """Return a synonym-variant query string, or None if no known synonyms present."""
    words = [w for w in query.split() if w.upper() != "AND"]
    alt_words = []
    found = False
    for w in words:
        syns = _SYNONYMS.get(w.lower())
        if syns:
            alt_words.append(syns[0])
            found = True
        else:
            alt_words.append(w)
    return " AND ".join(alt_words) if found else None


def _df_language_counts(df: pd.DataFrame) -> dict:
    if df.empty or "language" not in df.columns:
        return {}
    return {
        map_language(lang): int(count)
        for lang, count in df["language"].value_counts().items()
    }


def _df_source_type_counts(df: pd.DataFrame) -> dict:
    if df.empty or "domain" not in df.columns:
        return {}
    counts: dict = {}
    for domain in df["domain"].dropna():
        st = classify_source(str(domain).lower().lstrip("www."))
        counts[st] = counts.get(st, 0) + 1
    return counts


def populate_index_for_query(
    query: str,
    start_date: str = None,
    end_date: str = None,
    event_id: str = None,
) -> int:
    """
    Full pipeline: GDELT search → text fetch → Elastic index.

    Runs multiple passes:
      Pass 1: English, primary keywords
      Pass 2: English, synonym variants (if any synonyms found)
      Pass 3-5: French, Arabic, Greek with primary keywords

    Passes end_date as max_date to reject future-recrawled articles.
    Returns count of newly indexed articles.
    """
    t_start = time.time()

    if start_date is None or end_date is None:
        today = datetime.utcnow()
        end_date = today.strftime("%Y%m%d") + "000000"
        start_date = (today - timedelta(days=180)).strftime("%Y%m%d") + "000000"

    if event_id is None:
        event_id = f"query-{start_date[:8]}-{end_date[:8]}"

    total_found = 0
    total_indexed = 0
    by_language: dict = {}
    by_source_type: dict = {}

    def _run_pass(q: str, label: str, max_results: int = 50):
        nonlocal total_found, total_indexed
        df = search_gdelt(q, start_date, end_date, max_results=max_results)
        if df.empty:
            return
        total_found += len(df)
        for lang, cnt in _df_language_counts(df).items():
            by_language[lang] = by_language.get(lang, 0) + cnt
        for st, cnt in _df_source_type_counts(df).items():
            by_source_type[st] = by_source_type.get(st, 0) + cnt
        n = index_articles(df, max_date=end_date, event_id=event_id)
        total_indexed += n
        print(f"  Pass '{label}': found {len(df)}, indexed {n}")

    # Pass 1: English primary keywords
    _run_pass(query, "en-primary")

    # Pass 2: English synonym expansion
    syn_q = _synonym_query(query)
    if syn_q and syn_q != query:
        print(f"Synonym pass: {syn_q}")
        time.sleep(GDELT_SLEEP)
        _run_pass(syn_q, "en-synonyms")

    # Passes 3-5: Language-specific
    for lang_iso in EXTRA_LANGUAGES:
        lang_name = GDELT_LANGUAGE_NAMES[lang_iso]
        lang_query = f"{query} sourcelang:{lang_name}"
        print(f"Fetching {lang_name} articles...")
        time.sleep(GDELT_SLEEP)
        _run_pass(lang_query, f"{lang_iso}-primary", max_results=25)

    elapsed = round(time.time() - t_start, 1)
    print(f"Pipeline total: found={total_found}, indexed={total_indexed}, "
          f"by_lang={by_language}, by_type={by_source_type}, runtime={elapsed}s")
    return total_indexed
