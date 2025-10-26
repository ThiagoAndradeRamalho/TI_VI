import requests
import csv
import time
import subprocess
import shutil
import tempfile
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

GITHUB_TOKENS = [
    "coloque os tokens aqui",
]

QUANTIDADE_REPOS = 2
REQUEST_TIMEOUT = 10
MAX_WORKERS_SCRAPING = 20  


location_cache = {}
cache_lock = threading.Lock()

current_token_index = 0


def get_next_token() -> Optional[str]:
    global current_token_index

    tokens_validos = [
        t for t in GITHUB_TOKENS if t and t.startswith(("ghp_", "github_pat_"))
    ]

    if not tokens_validos:
        return None

    token = tokens_validos[current_token_index]
    current_token_index = (current_token_index + 1) % len(tokens_validos)
    return token


def obter_repos_mais_populares(quantidade: int) -> List[Dict]:
    print(f"Buscando os {quantidade} repositórios mais populares...")

    url = "https://api.github.com/search/repositories"
    params = {
        "q": "stars:>1",
        "sort": "stars",
        "order": "desc",
        "per_page": min(quantidade, 100),
    }

    repos_total = []
    page = 1

    while len(repos_total) < quantidade:
        params["page"] = page

        token = get_next_token()
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                repos = data["items"]

                if not repos:
                    break

                repos_total.extend(repos)

                if len(repos_total) >= quantidade:
                    repos_total = repos_total[:quantidade]
                    break

                page += 1
                time.sleep(0.5)

            elif response.status_code == 403:
                print("Rate limit, tentando próximo token")
                time.sleep(2)
                continue
            else:
                print(f"Erro {response.status_code}")
                break

        except Exception as e:
            print(f"Erro: {e}")
            break

    print(f"{len(repos_total)} repositórios encontrados\n")

    for i, repo in enumerate(repos_total, 1):
        print(f"   {i}. {repo['full_name']} - {repo['stargazers_count']:,} estrelas")

    return [
        {
            "name": repo["full_name"],
            "url": repo["clone_url"],
            "stars": repo["stargazers_count"],
        }
        for repo in repos_total
    ]


def clonar_repositorio(repo_url: str, repo_name: str) -> Optional[str]:
    temp_dir = tempfile.mkdtemp(prefix=f"github_{repo_name.replace('/', '_')}_")

    print(f"Clonando {repo_name}...")

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )

        if result.returncode != 0:
            print("Erro ao clonar")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        print("Baixando histórico completo...")
        subprocess.run(
            ["git", "fetch", "--unshallow"],
            cwd=temp_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
        )

        print("Clone concluído")
        return temp_dir

    except Exception as e:
        print(f"Erro: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None


def extrair_contribuidores(repo_dir: str) -> Set[str]:

    print("Extraindo contribuidores")

    try:
        result = subprocess.run(
            ["git", "log", "--all", "--format=%ae"],
            cwd=repo_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

        if result.returncode != 0:
            return set()

        usernames = set()

        for linha in result.stdout.strip().split("\n"):
            if linha:
                try:
                    email = linha.strip()

                    if "@users.noreply.github.com" in email:
                        username = email.split("@")[0]
                        if "+" in username:
                            username = username.split("+")[-1]
                    else:
                        username = email.split("@")[0]

                    if username:
                        usernames.add(username)

                except Exception:
                    continue

        print(f"{len(usernames)} contribuidores encontrados")
        return usernames

    except Exception as e:
        print(f"Erro: {e}")
        return set()


def obter_location(username: str) -> str:
    with cache_lock:
        if username in location_cache:
            return location_cache[username]

    try:
        url = f"https://github.com/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            location_span = soup.find("span", {"itemprop": "homeLocation"})
            if location_span:
                location = location_span.get_text(strip=True)
                with cache_lock:
                    location_cache[username] = location
                return location

            location_li = soup.find("li", {"itemprop": "homeLocation"})
            if location_li:
                location = location_li.get_text(strip=True)
                with cache_lock:
                    location_cache[username] = location
                return location

        elif response.status_code == 404:
            with cache_lock:
                location_cache[username] = "N/A"
            return "N/A"

    except Exception:
        pass

    with cache_lock:
        location_cache[username] = "N/A"
    return "N/A"


def scraping_paralelo(usernames: Set[str], repo_name: str) -> List[Dict]:
    print(
        f"Scraping de {len(usernames)} locations (paralelo com {MAX_WORKERS_SCRAPING} workers)."
    )

    dados = []
    total = len(usernames)
    processados = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_SCRAPING) as executor:
        future_to_username = {
            executor.submit(obter_location, username): username
            for username in usernames
        }

        for future in as_completed(future_to_username):
            username = future_to_username[future]

            try:
                location = future.result()

                dados.append(
                    {
                        "repo": repo_name,
                        "user": username,
                        "location": location,
                    }
                )

                processados += 1

                if processados % 100 == 0 or processados == total:
                    com_loc = sum(1 for d in dados if d["location"] != "N/A")
                    print(
                        f"{processados}/{total} ({processados*100//total}%) - {com_loc} com location"
                    )

            except Exception:
                continue

    print(f"{len(dados)} locations obtidas")
    return dados


def processar_repositorio(repo_info: Dict, idx: int, total: int) -> List[Dict]:
    print(f"\n{'='*60}")
    print(f"Repositório {idx}/{total}: {repo_info['name']}")
    print(f"{repo_info['stars']:,} estrelas")
    print(f"{'='*60}")

    repo_dir = clonar_repositorio(repo_info["url"], repo_info["name"])
    if not repo_dir:
        return []

    try:
        usernames = extrair_contribuidores(repo_dir)
        if not usernames:
            return []

        dados = scraping_paralelo(usernames, repo_info["name"])
        return dados

    finally:
        print("Removendo clone...")
        try:
            shutil.rmtree(repo_dir, ignore_errors=True)
        except Exception:
            pass


def salvar_csv(dados: List[Dict], nome_arquivo: str = "github_contribuidores.csv"):
    print(f"\nSalvando {nome_arquivo}...")

    with open(nome_arquivo, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["repo", "user", "location"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dados)

    print(f"Arquivo salvo! Total de registros: {len(dados)}")


def main():
    print("Raspagem de Contribuidores do GitHub")
    print(f"\nQuantidade de repositórios: {QUANTIDADE_REPOS}")
    print(f"Workers de scraping: {MAX_WORKERS_SCRAPING}")
    print(
        f"Tokens configurados: {len([t for t in GITHUB_TOKENS if t.startswith(('ghp_', 'github_pat_'))])}\n"
    )

    try:
        inicio = time.time()
        todos_dados = []

        repos = obter_repos_mais_populares(QUANTIDADE_REPOS)

        if not repos:
            print("\nNenhum repositório encontrado!")
            return

        for idx, repo_info in enumerate(repos, 1):
            dados_repo = processar_repositorio(repo_info, idx, len(repos))

            if dados_repo:
                todos_dados.extend(dados_repo)

                # Backup após cada repo
                salvar_csv(todos_dados, f"github_contribuidores_backup_{idx}.csv")

        if not todos_dados:
            print("\nNenhum dado coletado!")
            return

        # Salvar CSV final
        salvar_csv(todos_dados, "github_contribuidores_final.csv")

        tempo_total = time.time() - inicio
        minutos = int(tempo_total // 60)
        segundos = int(tempo_total % 60)

        print(f"\nProcesso concluído em {minutos}min {segundos}s!")

    except KeyboardInterrupt:
        print("\n\nProcesso interrompido!")
        if todos_dados:
            salvar_csv(todos_dados, "github_contribuidores_INTERROMPIDO.csv")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
