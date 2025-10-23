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
from datetime import datetime
import atexit, signal, csv
from pathlib import Path
import argparse

# ===================== Config =====================

TOKENS = [

]
token_cycle = itertools.cycle(TOKENS)
def get_next_token():
    return next(token_cycle)

PR_START_DATE = "2020-01-01T00:00:00Z"    # PRs criadas a partir de 2020
END_DATE      = "2024-12-31T23:59:59Z"    # limite superior opcional para busca de repos
MAX_WORKERS   = 7
PER_PAGE      = 100                       # maior eficiência nas listagens
DB_PATH       = "github_cache.db"

# Arquivo de checkpoint para retomar progresso
CHECKPOINT_FILE = Path("processed_repos.txt")

# Buffers em memória (flushados frequentemente)
all_contribs, all_metrics, all_reviews, all_prs = [], [], [], []

# ===================== Cache (SQLite) =====================

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
                retry_delay *= 2
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
            retry_delay *= 2
    print(f"[Erro] Falha ao conectar após {max_retries} tentativas: {url}")
    return None

def paginated_request(base_url, max_pages=10):
    all_data, page = [], 1
    while page <= max_pages:
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}per_page={PER_PAGE}&page={page}"
        data = safe_request(url)
        if not data:
            break
        # Search API retorna dict com "items"; REST comum retorna lista
        items = data["items"] if isinstance(data, dict) and "items" in data else data
        all_data.extend(items)
        if len(items) < PER_PAGE:
            break
        page += 1
        time.sleep(0.3)
    return all_data

# ===================== CSV robusto + Checkpoint =====================

def append_csv_atomic(rows, filename, header):
    """Acrescenta rows (lista de dicts) em CSV, criando cabeçalho se o arquivo não existir."""
    if not rows:
        return
    file_exists = os.path.exists(filename)
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in header})

def flush_all():
    """Despeja buffers em disco e limpa-os."""
    global all_contribs, all_metrics, all_reviews, all_prs
    append_csv_atomic(all_metrics, "repo_metrics.csv",
        ["repo","stars","forks","open_issues"])
    append_csv_atomic(all_contribs, "contributors.csv",
        ["repo","login","followers","public_repos","country_raw","country"])
    append_csv_atomic(all_reviews, "reviews.csv",
        ["repo","pr_number","pr_author","reviewer","review_state","review_submitted_at",
         "pr_state","pr_created_at","pr_merged_at","is_merged"])
    append_csv_atomic(all_prs, "prs.csv",
        ["repo","number","title","author","state","created_at","merged_at","is_merged"])
    all_contribs.clear(); all_metrics.clear(); all_reviews.clear(); all_prs.clear()
    print("[Flush] Dados salvos em CSV.")

def mark_done(repo_full_name):
    with open(CHECKPOINT_FILE, "a", encoding="utf-8") as f:
        f.write(repo_full_name + "\n")

def load_done():
    done = set()
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    done.add(line)
    return done

# Flush ao sair normalmente
atexit.register(flush_all)

# Flush também em sinais (Ctrl+C / kill)
def _sig_handler(signum, frame):
    print(f"\n[Sinal {signum}] Encerrando com flush...")
    flush_all()
    # reeleva para encerrar com código correto
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)

for _sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(_sig, _sig_handler)
    except Exception:
        pass  # Windows pode não suportar SIGTERM

# ===================== Geolocalização (país) =====================

geolocator = Nominatim(user_agent="gh_country")

def normalize_country(location_str):
    if not location_str:
        return None
    location = str(location_str).lower()
    try:
        # match simples por nome/alpha_2
        for country in pycountry.countries:
            if country.name.lower() in location or (country.alpha_2.lower() in location):
                return country.name
        # fallback geocoding
        geo = geolocator.geocode(location, timeout=10)
        if geo and geo.address:
            for country in pycountry.countries:
                if country.name in geo.address:
                    return country.name
    except Exception:
        pass
    return None

# ===================== Coleta de Repositórios =====================

def get_popular_repositories(min_stars=200, pages=10, limit=200):
    repos = []
    for page in range(1, pages + 1):
        url = (
            "https://api.github.com/search/repositories"
            f"?q=stars:>{min_stars}+created:<={END_DATE[:10]}"
            "&sort=stars&order=desc"
            f"&per_page={PER_PAGE}&page={page}"
        )
        data = safe_request(url)
        if data and "items" in data:
            repos.extend(data["items"])
        time.sleep(0.5)
    repos = repos[:limit]
    print(f"[Repos] Coletados {len(repos)} repositórios.")
    return repos

# ===================== Filtro de Países (Contribuidores) =====================

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
        time.sleep(0.2)

    # exige pelo menos 2 países distintos no repo (evita viés)
    unique_countries = {c["country"] for c in enriched}
    if len(unique_countries) < 2:
        return []
    return enriched

# ===================== PRs: abertas ou mergeadas (criadas ≥ 2020) =====================

def iso_to_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def search_pr_numbers(full_name, q_suffix):
    # Search API para filtrar por estado e data de criação
    base = f'https://api.github.com/search/issues?q=repo:{full_name}+is:pr+{q_suffix}+created:>={PR_START_DATE}'
    results = paginated_request(base, max_pages=10)
    return [item["number"] for item in results if "number" in item]

def get_filtered_prs(full_name):
    # PRs abertas
    open_pr_numbers = search_pr_numbers(full_name, "is:open")
    # PRs mergeadas
    merged_pr_numbers = search_pr_numbers(full_name, "is:merged")

    wanted_numbers = set(open_pr_numbers) | set(merged_pr_numbers)
    filtered_prs = []

    for num in wanted_numbers:
        pr = safe_request(f"https://api.github.com/repos/{full_name}/pulls/{num}")
        if not pr:
            continue
        # garante created >= 2020
        created_ok = pr.get("created_at") and (iso_to_dt(pr["created_at"]) >= iso_to_dt(PR_START_DATE))
        if not created_ok:
            continue

        state = pr.get("state")              # "open" ou "closed"
        merged_at = pr.get("merged_at")      # None ou timestamp
        # apenas abertas OU mergeadas
        if state == "open" or merged_at is not None:
            filtered_prs.append(pr)
        time.sleep(0.12)

    return filtered_prs

def get_pr_reviews(full_name):
    prs = get_filtered_prs(full_name)
    review_records = []

    for pr in prs:
        pr_number = pr["number"]
        reviews_url = f"https://api.github.com/repos/{full_name}/pulls/{pr_number}/reviews"
        reviews = paginated_request(reviews_url, max_pages=3)
        for r in (reviews or []):
            review_records.append({
                "repo": full_name,
                "pr_number": pr_number,
                "pr_author": (pr.get("user") or {}).get("login"),
                "reviewer": (r.get("user") or {}).get("login"),
                "review_state": r.get("state"),
                "review_submitted_at": r.get("submitted_at"),
                "pr_state": pr.get("state"),
                "pr_created_at": pr.get("created_at"),
                "pr_merged_at": pr.get("merged_at"),
                "is_merged": pr.get("merged_at") is not None,
            })
        time.sleep(0.08)

    return review_records, prs

# ===================== Métricas do Repositório (básicas) =====================

def get_repo_metrics(full_name):
    base = f"https://api.github.com/repos/{full_name}"
    repo_data = safe_request(base)
    return {
        "repo": full_name,
        "stars": repo_data["stargazers_count"] if repo_data else None,
        "forks": repo_data["forks_count"] if repo_data else None,
        "open_issues": repo_data["open_issues_count"] if repo_data else None,
        # Removido: eventos/métricas marcados em vermelho na imagem
    }

# ===================== Pipeline por repositório =====================

def collect_repo(repo):
    name = repo["full_name"]
    try:
        contribs = get_contributors(name)
        metrics = get_repo_metrics(name)
        reviews, filtered_prs = get_pr_reviews(name)

        prs_rows = [{
            "repo": name,
            "number": pr["number"],
            "title": pr.get("title"),
            "author": (pr.get("user") or {}).get("login"),
            "state": pr.get("state"),
            "created_at": pr.get("created_at"),
            "merged_at": pr.get("merged_at"),
            "is_merged": pr.get("merged_at") is not None,
        } for pr in filtered_prs]

        return {"repo": name, "contributors": contribs, "metrics": metrics, "reviews": reviews, "prs": prs_rows}
    except Exception as e:
        print(f"[Erro] {name}: {e}")
        return None

# ===================== Main =====================

if __name__ == "__main__":
    if not TOKENS:
        raise RuntimeError("Preencha a lista TOKENS com pelo menos um token de acesso do GitHub.")

    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Número de threads (I/O-bound).")
    parser.add_argument("--pages", type=int, default=10, help="Páginas na busca de repositórios (Search API).")
    parser.add_argument("--limit", type=int, default=200, help="Limite de repositórios.")
    parser.add_argument("--min-stars", type=int, default=200, help="Mínimo de estrelas por repositório.")
    args = parser.parse_args()

    MAX_WORKERS = args.workers

    init_cache()
    already_done = load_done()

    repos = get_popular_repositories(min_stars=args.min_stars, pages=args.pages, limit=args.limit)
    # pula os já processados
    repos = [r for r in repos if r["full_name"] not in already_done]
    print(f"[Checkpoint] {len(already_done)} já finalizados. Restantes nesta execução: {len(repos)}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(collect_repo, repo) for repo in repos]
        for future in tqdm(as_completed(futures), total=len(repos), desc="Coletando repositórios"):
            result = future.result()
            if not result:
                continue

            # Envia para buffers
            if result.get("contributors"):
                all_contribs.extend(result["contributors"])
            if result.get("metrics"):
                all_metrics.append(result["metrics"])
            if result.get("reviews"):
                all_reviews.extend(result["reviews"])
            if result.get("prs"):
                all_prs.extend(result["prs"])

            # Salva imediatamente para minimizar perda em quedas
            flush_all()
            # Marca como concluído para retomada
            mark_done(result["repo"])

    print("Coleta concluída (PRs: abertas + mergeadas, criadas ≥ 2020; métricas vermelhas excluídas; robusto a quedas).")
