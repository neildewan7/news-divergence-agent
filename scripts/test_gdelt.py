import time
import requests
import pandas as pd

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "news-divergence-agent/1.0"}


def query_gdelt(keyword, start_date, end_date, num_records=50, max_retries=5):
    """Query GDELT with exponential backoff on 429."""
    start_dt = start_date.replace("-", "") + "000000"
    end_dt = end_date.replace("-", "") + "000000"
    params = {
        "query": f'"{keyword}"',
        "startdatetime": start_dt,
        "enddatetime": end_dt,
        "maxrecords": num_records,
        "mode": "artlist",
        "format": "json",
    }
    delay = 10
    for attempt in range(max_retries):
        resp = requests.get(BASE_URL, params=params, headers=HEADERS)
        if resp.status_code == 200:
            if "text/html" in resp.headers.get("content-type", ""):
                print(f"  API message: {resp.text.strip()[:120]}")
                return pd.DataFrame()
            try:
                data = resp.json()
                arts = data.get("articles", [])
                return pd.DataFrame(arts)
            except Exception as e:
                print(f"  JSON parse error: {e} — raw: {resp.text[:120]}")
                return pd.DataFrame()
        elif resp.status_code == 429:
            print(f"  Rate limited (attempt {attempt+1}/{max_retries}), waiting {delay}s...")
            time.sleep(delay)
            delay *= 2
        else:
            print(f"  HTTP {resp.status_code}: {resp.text[:120]}")
            return pd.DataFrame()
    print("  Exhausted retries, giving up.")
    return pd.DataFrame()


queries = [
    {
        "label": "Primary query",
        "keyword": "Derna flood Libya",
        "start_date": "2023-09-10",
        "end_date": "2023-09-25",
    },
    {
        "label": "Broader Libya flood",
        "keyword": "Libya flood Storm Daniel",
        "start_date": "2023-09-08",
        "end_date": "2023-09-30",
    },
    {
        "label": "Arabic angle",
        "keyword": "Derna Libya disaster",
        "start_date": "2023-09-08",
        "end_date": "2023-10-05",
    },
]

for i, q in enumerate(queries):
    if i > 0:
        print("Pausing 12s between queries...")
        time.sleep(12)
    print(f"\n=== {q['label']} ===")
    print(f"  keyword={q['keyword']!r}  {q['start_date']} → {q['end_date']}")
    results = query_gdelt(q["keyword"], q["start_date"], q["end_date"])
    print(f"Found {len(results)} articles")
    if len(results) > 0:
        cols = [c for c in ["title", "domain", "language", "sourcecountry", "seendate"] if c in results.columns]
        print(results[cols].to_string())
