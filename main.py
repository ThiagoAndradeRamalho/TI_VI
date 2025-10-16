import requests
import pandas as pd
import sqlite3
import pycountry
from geopy.geocoders import Nominatim
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import os
import json
import itertools

TOKENS = [
    
]

token_cycle = itertools.cycle(TOKENS)

def get_next_token():
    return next(token_cycle)

START_DATE = "2022-01-01T00:00:00Z"
END_DATE = "2024-12-31T23:59:59Z"
MAX_WORKERS = 5
PER_PAGE = 10
DB_PATH = "github_cache.db"

#cache
def init_cache():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, data TEXT)")
    conn.commit()
    conn.close()

def cache_get(url):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT data FROM cache WHERE url=?", (url,))
    row = cur.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def cache_set(url, data):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (url, json.dumps(data)))
    conn.commit()
    conn.close()

def safe_request(url, max_retries=5):
    cached = cache_get(url)
    if cached:
        return cached

    retry_delay = 3
    for attempt in range(max_retries):
        token = get_next_token()
        headers = {"Authorization": f"token {token}"}
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 403 and "X-RateLimit-Reset" in r.headers:
                reset = int(r.headers["X-RateLimit-Reset"])
                sleep_time = max(0, reset - time.time()) + 5
                print(f"[Rate limit] Token {token[:6]}... bloqueado. Esperando {sleep_time:.0f}s para reset.")
                time.sleep(sleep_time)
                continue
            elif r.status_code in [500, 502, 503, 504]:
                print(f"[Retry] Erro {r.status_code} temporário. Repetindo...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Backoff exponencial
                continue
            elif r.status_code == 404:
                print(f"[Aviso] URL não encontrada: {url}")
                return None
            elif r.status_code == 422:
                print(f"[Erro 422] Query malformada: {url}")
                return None
            elif r.status_code != 200:
                print(f"[Erro HTTP {r.status_code}] {url}")
                print("→ Resposta:", r.text[:200])
                time.sleep(5)
                continue

            data = r.json()
            cache_set(url, data)
            return data
        except requests.exceptions.ConnectionError as e:
            print(f"[Erro] Tentativa {attempt + 1}/{max_retries}: {e}")
            time.sleep(retry_delay)
            retry_delay *= 2  # Backoff exponencial
    print(f"[Erro] Falha ao conectar após {max_retries} tentativas: {url}")
    return None


def paginated_request(base_url):
    all_data, page = [], 1
    while page <= 10:
        url = f"{base_url}&per_page={PER_PAGE}&page={page}"
        data = safe_request(url)
        if not data:
            break
        all_data.extend(data)
        if len(data) < PER_PAGE:
            break
        page += 1
        time.sleep(0.5)
    return all_data

#detecta pais
geolocator = Nominatim(user_agent="gh_country")

def normalize_country(location_str):
    if not location_str:
        return None
    location = str(location_str).lower()
    try:
        for country in pycountry.countries:
            if country.name.lower() in location or (country.alpha_2.lower() in location):
                return country.name
        geo = geolocator.geocode(location, timeout=10)
        if geo and geo.address:
            for country in pycountry.countries:
                if country.name in geo.address:
                    return country.name
    except Exception:
        pass
    return None

# coleta dados baseando nas starts
def get_popular_repositories(min_stars=200, pages=10, limit=200):
    repos = []
    for page in range(1, pages + 1):
        url = (
            f"https://api.github.com/search/repositories"
            f"?q=stars:>{min_stars}&sort=stars&order=desc&per_page={PER_PAGE}&page={page}"
        )
        data = safe_request(url)
        if data and "items" in data:
            repos.extend(data["items"])
        time.sleep(1)
    repos = repos[:limit]
    print(f"[Repos] Coletados {len(repos)} repositórios.")
    return repos

# contribuidores apenas dos 5 paises
COUNTRIES_FILTER = {"Brazil", "India", "United States", "Germany", "United Kingdom"}

def get_contributors(full_name):
    url = f"https://api.github.com/repos/{full_name}/contributors?anon=false"
    contributors = paginated_request(url)
    enriched = []

    for c in contributors[:50]:
        user_url = f"https://api.github.com/users/{c['login']}"
        user = safe_request(user_url)

        if not user:
            continue

        raw_location = user.get("location")
        country_norm = normalize_country(raw_location)

        if not country_norm or country_norm not in COUNTRIES_FILTER:
            continue

        enriched.append({
            "repo": full_name,
            "login": c["login"],
            "followers": user.get("followers"),
            "public_repos": user.get("public_repos"),
            "country_raw": raw_location,
            "country": country_norm,
        })

        time.sleep(0.3)

    unique_countries = {c["country"] for c in enriched}
    if len(unique_countries) < 2:
        return []
    return enriched

# pipeline paraelelo
def collect_repo(repo):
    name = repo["full_name"]
    try:
        contribs = get_contributors(name)

        return {"repo": name, "contributors": contribs}
    except Exception as e:
        print(f"[Erro] {name}: {e}")
        return None


def incremental_save(df, filename):
    if not os.path.exists(filename):
        df.to_csv(filename, index=False)
    else:
        df.to_csv(filename, mode="a", header=False, index=False)


if __name__ == "__main__":
    init_cache()
    repos = get_popular_repositories(pages=10)

    all_contribs = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(collect_repo, repo) for repo in repos]
        for future in tqdm(as_completed(futures), total=len(repos), desc="Coletando repositórios"):
            result = future.result()
            if result:
                all_contribs.extend(result["contributors"])

                if len(all_contribs) >= 200:
                    pd.DataFrame(all_contribs).to_csv("contributors.csv", mode="a", header=False, index=False)
                    all_contribs.clear()


    print("Coleta concluída")
