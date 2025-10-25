import requests
import csv
import time
import subprocess
import shutil
import tempfile
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path

# CONFIGURAÇÃO - Adicione suas chaves aqui
GITHUB_TOKENS = [
    "seu_token_aqui",
]


class GithubAPIManager:
    """Gerenciador de múltiplas chaves de API do GitHub com rotação automática."""

    def __init__(self, tokens: List[str]):
        self.tokens = [
            t
            for t in tokens
            if t and t != "seu_token_aqui" and not t.startswith("seu_token_")
        ]
        self.current_index = 0
        self.rate_limit_info = {}

        if not self.tokens:
            print(
                "AVISO: Nenhum token válido configurado. Usando API sem autenticação (rate limit baixo)."
            )
        else:
            print(f"{len(self.tokens)} token(s) configurado(s)")

    def get_headers(self) -> Dict:
        """Retorna os headers com o token atual."""
        headers = {"Accept": "application/vnd.github.v3+json"}

        if self.tokens:
            headers["Authorization"] = f"token {self.tokens[self.current_index]}"

        return headers

    def get_current_token_name(self) -> str:
        """Retorna o nome do token atual (mascarado)."""
        if not self.tokens:
            return "SEM_TOKEN"

        token = self.tokens[self.current_index]
        return f"Token_{self.current_index + 1}_{token[:4]}***"

    def rotate_token(self):
        """Rotaciona para o próximo token."""
        if not self.tokens:
            return

        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.tokens)
        print(f"Rotacionando token: {old_index + 1} → {self.current_index + 1}")

    def check_rate_limit(self) -> Dict:
        """Verifica o rate limit do token atual."""
        url = "https://api.github.com/rate_limit"
        response = requests.get(url, headers=self.get_headers())

        if response.status_code == 200:
            data = response.json()
            return data["rate"]
        return {}

    def get_best_token(self) -> bool:
        """Encontra o token com mais requisições disponíveis."""
        if not self.tokens:
            return False

        print("\nVerificando disponibilidade de todos os tokens...")

        best_index = 0
        best_remaining = -1

        for i in range(len(self.tokens)):
            self.current_index = i
            rate_info = self.check_rate_limit()

            if rate_info:
                remaining = rate_info.get("remaining", 0)
                reset_time = rate_info.get("reset", 0)
                reset_str = time.strftime("%H:%M:%S", time.localtime(reset_time))

                print(
                    f"   Token {i + 1}: {remaining:,} requisições restantes (reset: {reset_str})"
                )

                if remaining > best_remaining:
                    best_remaining = remaining
                    best_index = i

            time.sleep(0.2)

        self.current_index = best_index
        print(
            f"\nUsando Token {best_index + 1} ({best_remaining:,} requisições disponíveis)"
        )

        return best_remaining > 0

    def make_request(
        self, url: str, params: Optional[Dict] = None, max_retries: int = 3
    ) -> Optional[requests.Response]:
        """Faz uma requisição com gerenciamento automático de rate limit."""

        for attempt in range(max_retries):
            headers = self.get_headers()
            response = requests.get(url, headers=headers, params=params)

            # Verifica rate limit nos headers
            remaining = int(response.headers.get("X-RateLimit-Remaining", 1))

            if response.status_code == 200:
                # Se está ficando sem requisições, rotaciona
                if remaining < 10 and len(self.tokens) > 1:
                    print(
                        f"Apenas {remaining} requisições restantes no {self.get_current_token_name()}"
                    )
                    self.rotate_token()

                return response

            elif response.status_code == 403 and "rate limit" in response.text.lower():
                print(f"Rate limit atingido no {self.get_current_token_name()}")

                if len(self.tokens) > 1:
                    self.rotate_token()
                    print(f"   Tentando com {self.get_current_token_name()}...")
                    time.sleep(1)
                else:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_time = max(reset_time - time.time(), 0)

                    if wait_time > 0:
                        print(
                            f"   Aguardando {int(wait_time/60)} minutos até o reset..."
                        )
                        time.sleep(min(wait_time, 300))

            elif response.status_code == 404:
                print(f"   Recurso não encontrado: {url}")
                return response

            else:
                print(f"   Erro {response.status_code}: {response.text[:100]}")
                time.sleep(2)

        return None


# Inicializa o gerenciador de API
api_manager = GithubAPIManager(GITHUB_TOKENS)


def obter_repos_mais_populares(quantidade: int = 2) -> List[Dict]:
    """Busca os repositórios mais populares do GitHub por estrelas."""
    url = "https://api.github.com/search/repositories"
    params = {"q": "stars:>1", "sort": "stars", "order": "desc", "per_page": quantidade}

    print(f"Buscando os {quantidade} repositórios mais populares...")
    response = api_manager.make_request(url, params=params)

    if response and response.status_code == 200:
        repos = response.json()["items"]
        for repo in repos:
            print(
                f"   Encontrado: {repo['full_name']} ({repo['stargazers_count']:,} estrelas)"
            )
        return repos
    else:
        print("Erro ao buscar repositórios")
        return []


def clonar_repositorio(repo_url: str, repo_name: str) -> Optional[str]:
    """Clona um repositório em um diretório temporário."""
    # Cria diretório temporário único
    temp_dir = tempfile.mkdtemp(prefix=f"github_{repo_name.replace('/', '_')}_")

    print(f"   Clonando repositório em: {temp_dir}")
    print("   Isso pode demorar alguns minutos...")

    try:
        # Clone shallow primeiro (mais rápido)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,  # 10 minutos
        )

        if result.returncode != 0:
            print(f"   Erro ao clonar: {result.stderr}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        # Fazer unshallow para pegar histórico completo
        print("   Baixando histórico completo...")
        subprocess.run(
            ["git", "fetch", "--unshallow"],
            cwd=temp_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,  # 20 minutos
        )

        print("   Repositório clonado com sucesso!")
        return temp_dir

    except subprocess.TimeoutExpired:
        print("   Timeout ao clonar repositório")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None
    except Exception as e:
        print(f"   Erro: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None


def extrair_autores_do_git(repo_dir: str) -> Set[Tuple[str, str]]:
    """Extrai todos os autores únicos do repositório (nome, email)."""
    print("   Extraindo autores do histórico git...")

    try:
        # Obter todos os autores (nome + email) com encoding UTF-8
        result = subprocess.run(
            ["git", "log", "--all", "--format=%an|%ae"],
            cwd=repo_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5 minutos
        )

        if result.returncode != 0:
            print(f"   Erro ao ler git log: {result.stderr}")
            return set()

        # Processar linhas
        autores = set()
        linhas = result.stdout.strip().split("\n")

        for linha in linhas:
            if linha and "|" in linha:
                try:
                    partes = linha.split("|", 1)
                    if len(partes) == 2:
                        nome, email = partes
                        autores.add((nome.strip(), email.strip()))
                except Exception:
                    continue  # Pula linhas problemáticas

        print(f"   {len(autores)} autores únicos encontrados no git")
        return autores

    except Exception as e:
        print(f"   Erro ao extrair autores: {e}")
        return set()


def converter_autor_para_username(nome: str, email: str) -> Optional[str]:
    """Tenta converter nome/email em username do GitHub."""

    # 1. Se o email é do GitHub, extrair username diretamente
    if "@users.noreply.github.com" in email:
        # Formato: username@users.noreply.github.com ou 123456+username@users.noreply.github.com
        username = email.split("@")[0]
        if "+" in username:
            username = username.split("+")[-1]
        return username

    # 2. Buscar na API do GitHub por email
    url = "https://api.github.com/search/users"
    params = {"q": f'"{email}" in:email'}

    response = api_manager.make_request(url, params=params)

    if response and response.status_code == 200:
        data = response.json()
        if data.get("total_count", 0) > 0 and data.get("items"):
            return data["items"][0]["login"]

    # 3. Tentar buscar por nome (se tiver pelo menos 3 caracteres)
    if nome and len(nome) > 2:
        params = {"q": f'"{nome}" in:name'}
        response = api_manager.make_request(url, params=params)

        if response and response.status_code == 200:
            data = response.json()
            if data.get("total_count", 0) > 0 and data.get("items"):
                return data["items"][0]["login"]

    return None


def obter_contribuidores_api_fallback(repo_full_name: str) -> List[str]:
    """Fallback: usa API se git clone falhar (máximo 500)."""
    print("   Usando API como fallback...")
    contribuidores = []
    page = 1

    while page <= 5:  # Max 500 contribuidores
        url = f"https://api.github.com/repos/{repo_full_name}/contributors"
        params = {"per_page": 100, "page": page}

        response = api_manager.make_request(url, params=params)

        if response and response.status_code == 200:
            dados = response.json()
            if not dados:
                break

            for contrib in dados:
                contribuidores.append(contrib["login"])

            page += 1
            time.sleep(0.2)
        else:
            break

    print(f"   {len(contribuidores)} contribuidores obtidos via API")
    return contribuidores


def obter_todos_contribuidores(repo_full_name: str, repo_url: str) -> List[str]:
    """Clona repositório, extrai TODOS os contribuidores e limpa."""
    print(f"\nObtendo TODOS os contribuidores de {repo_full_name}...")

    # 1. Clonar repositório
    repo_dir = clonar_repositorio(repo_url, repo_full_name)

    if not repo_dir:
        print("   Falha ao clonar, usando API como fallback...")
        return obter_contribuidores_api_fallback(repo_full_name)

    try:
        # 2. Extrair autores do git
        autores = extrair_autores_do_git(repo_dir)

        if not autores:
            print("   Nenhum autor encontrado, usando API...")
            return obter_contribuidores_api_fallback(repo_full_name)

        # 3. Converter para usernames do GitHub
        print(f"   Convertendo {len(autores)} autores em usernames do GitHub...")
        usernames = set()

        for i, (nome, email) in enumerate(autores, 1):
            username = converter_autor_para_username(nome, email)

            if username:
                usernames.add(username)

            # Mostrar progresso a cada 50
            if i % 50 == 0:
                print(
                    f"      Progresso: {i}/{len(autores)} autores processados ({len(usernames)} usernames encontrados)"
                )

            time.sleep(0.05)  # Pequeno delay para não sobrecarregar

        print(f"   Total: {len(usernames)} contribuidores únicos identificados")
        return list(usernames)

    finally:
        # 4. SEMPRE limpar o repositório clonado
        print("   Removendo repositório clonado...")
        try:
            shutil.rmtree(repo_dir, ignore_errors=True)
            print("   Repositório removido com sucesso")
        except Exception as e:
            print(f"   Erro ao remover diretório: {e}")


def obter_location_usuario(username: str) -> str:
    """Obtém a location de um usuário."""
    url = f"https://api.github.com/users/{username}"

    response = api_manager.make_request(url)

    if response and response.status_code == 200:
        user_data = response.json()
        location = user_data.get("location", "")
        return location if location else "N/A"
    else:
        return "N/A"


def extrair_dados_completos() -> List[Dict]:
    """Extrai todos os dados necessários."""
    dados_completos = []

    # 1. Obter os 2 repos mais populares
    repos = obter_repos_mais_populares(2)

    if not repos:
        print("Nenhum repositório encontrado!")
        return []

    # 2. Para cada repo, obter contribuidores e suas locations
    for idx, repo in enumerate(repos, 1):
        print(f"\n{'='*60}")
        print(f"Processando repositório {idx}/{len(repos)}: {repo['full_name']}")
        print(f"{'='*60}")

        repo_name = repo["full_name"]
        repo_url = repo["clone_url"]

        # Obter todos os contribuidores (clonando o repositório)
        contribuidores = obter_todos_contribuidores(repo_name, repo_url)

        if not contribuidores:
            print("   Nenhum contribuidor encontrado, pulando...")
            continue

        print(f"\nObtendo locations de {len(contribuidores)} contribuidores...")

        for i, username in enumerate(contribuidores, 1):
            location = obter_location_usuario(username)

            dados_completos.append(
                {"repositorio": repo_name, "usuario": username, "location": location}
            )

            # Mostrar progresso
            if i % 10 == 0 or i == len(contribuidores):
                print(
                    f"   Progresso: {i}/{len(contribuidores)} ({i*100//len(contribuidores)}%)"
                )

            time.sleep(0.05)  # Delay pequeno

    return dados_completos


def salvar_csv(dados: List[Dict], nome_arquivo: str = "github_contribuidores.csv"):
    """Salva os dados em um arquivo CSV."""
    print(f"\nSalvando dados em {nome_arquivo}...")

    with open(nome_arquivo, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["repositorio", "usuario", "location"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(dados)

    print(f"Arquivo salvo com sucesso! Total de registros: {len(dados)}")


def main():
    print("=" * 60)
    print("EXTRATOR DE CONTRIBUIDORES DO GITHUB")
    print("   (Clonando repositórios para obter TODOS os contribuidores)")
    print("=" * 60)
    print("\nAVISO: Este processo pode demorar bastante tempo!")
    print("   - Clonará repositórios grandes")
    print("   - Fará muitas requisições à API")
    print("   - Limpará automaticamente após uso\n")

    # Encontra o melhor token para começar
    api_manager.get_best_token()

    try:
        inicio = time.time()

        # Extrair dados
        dados = extrair_dados_completos()

        if not dados:
            print("\nNenhum dado foi coletado!")
            return

        # Salvar em CSV
        salvar_csv(dados)

        tempo_total = time.time() - inicio
        minutos = int(tempo_total // 60)
        segundos = int(tempo_total % 60)

        print("\n" + "=" * 60)
        print(f"Processo concluído em {minutos}min {segundos}s!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nProcesso interrompido pelo usuário!")
    except Exception as e:
        print(f"\nErro durante a execução: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
