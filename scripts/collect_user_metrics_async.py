"""
Script assíncrono de coleta rápida de métricas de usuários do GitHub.

Este script utiliza programação assíncrona (asyncio/aiohttp) e rotação de múltiplos tokens
do GitHub para acelerar significativamente a coleta de métricas de usuários. Usa os 8 tokens
disponíveis em sistema round-robin para maximizar o throughput e evitar rate limits.

Coleta as mesmas métricas de usuários mas de forma muito mais rápida:
- PRs (abertos, merged, taxa de aceitação, tempo médio)
- Commits, issues, reviews
- Estrelas em repositórios próprios
- Métricas de atividade e permissões

Resultado: Gera um arquivo CSV especificado via linha de comando com todas as métricas.
Uso: python collect_user_metrics_async.py input.csv output.csv
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
from tqdm.asyncio import tqdm_asyncio
import itertools
from token_loader import load_github_tokens

TOKENS = load_github_tokens()

# Cria um iterador infinito de tokens para round-robin
token_cycle = itertools.cycle(TOKENS) if TOKENS else itertools.cycle([''])

BASE_URL = "https://api.github.com"
MAX_CONCURRENT = len(TOKENS) * 4 if TOKENS else 1  # Permite múltiplas requisições por token

# Semáforo para controlar concorrência
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# Helper: GET request com round-robin de tokens e tratamento de rate limit
async def fetch(session, url, retries=3):
    async with semaphore:
        for attempt in range(retries):
            token = next(token_cycle)
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json"
            }
            try:
                async with session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status == 403:
                        # Rate limit neste token, tenta próximo
                        await asyncio.sleep(0.5)
                        continue
                    if resp.status == 404:
                        return None
                    if resp.status == 200:
                        return await resp.json()
                    await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                print(f"Erro ao buscar {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
        return None

async def get_user_metrics(session, user, repo_name, repo_url):
    try:
        login = user['login']
        repo_owner = repo_url.split('/')[3]
        repo = repo_url.split('/')[4]

        # Executa múltiplas requisições em paralelo para acelerar
        prs_url = f"{BASE_URL}/search/issues?q=type:pr+author:{login}+repo:{repo_owner}/{repo}"
        commits_url = f"{BASE_URL}/search/commits?q=author:{login}+repo:{repo_owner}/{repo}"
        issues_url = f"{BASE_URL}/search/issues?q=type:issue+author:{login}+repo:{repo_owner}/{repo}"
        pulls_url = f"{BASE_URL}/repos/{repo_owner}/{repo}/pulls?state=all&per_page=100"
        user_repos_url = f"{BASE_URL}/users/{login}/repos?per_page=100"
        collab_url = f"{BASE_URL}/repos/{repo_owner}/{repo}/collaborators/{login}/permission"

        # Busca tudo em paralelo
        results = await asyncio.gather(
            fetch(session, prs_url),
            fetch(session, commits_url),
            fetch(session, issues_url),
            fetch(session, pulls_url),
            fetch(session, user_repos_url),
            fetch(session, collab_url),
            return_exceptions=True
        )

        prs_data, commits_data, issues_data, pulls, user_repos, perm = results

        # 1. PRs enviados e aceitos
        prs_opened = prs_data.get('total_count', 0) if prs_data else 0
        prs_merged = 0
        pr_times = []
        
        if pulls and isinstance(pulls, list):
            for pr in pulls:
                if pr.get('user', {}).get('login') == login:
                    if pr.get('merged_at'):
                        prs_merged += 1
                        try:
                            created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                            merged = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                            pr_times.append((merged - created).total_seconds())
                        except:
                            pass
        
        pr_accept_rate = prs_merged / prs_opened if prs_opened else 0
        avg_time_to_merge = sum(pr_times) / len(pr_times) / 3600 if pr_times else 0

        # 2. Commits totais
        commits_total = commits_data.get('total_count', 0) if commits_data else 0

        # 3. Issues abertas
        issues_opened = issues_data.get('total_count', 0) if issues_data else 0

        # 4. Reviews feitos (busca em paralelo)
        reviews_submitted = 0
        if pulls and isinstance(pulls, list):
            review_tasks = []
            for pr in pulls[:50]:  # Limita para não sobrecarregar
                reviews_url = f"{BASE_URL}/repos/{repo_owner}/{repo}/pulls/{pr['number']}/reviews"
                review_tasks.append(fetch(session, reviews_url))
            
            if review_tasks:
                reviews_results = await asyncio.gather(*review_tasks, return_exceptions=True)
                for reviews in reviews_results:
                    if reviews and isinstance(reviews, list):
                        reviews_submitted += sum(1 for r in reviews if r.get('user', {}).get('login') == login)

        # 5. Soma de estrelas em repositórios próprios
        stars_own_repos = 0
        if user_repos and isinstance(user_repos, list):
            stars_own_repos = sum(repo_.get('stargazers_count', 0) for repo_ in user_repos)

        # 6. Tempo de contribuição
        contribution_period = 0
        if commits_total > 0:
            commit_events_url = f"{BASE_URL}/repos/{repo_owner}/{repo}/commits?author={login}&per_page=100"
            commits = await fetch(session, commit_events_url)
            if commits and isinstance(commits, list):
                try:
                    dates = [datetime.fromisoformat(c['commit']['author']['date'].replace('Z', '+00:00')) for c in commits if 'commit' in c]
                    if dates:
                        contribution_period = (max(dates) - min(dates)).days
                except:
                    pass

        # 7. Frequência e regularidade de atividade
        activity_frequency = commits_total / contribution_period if contribution_period else 0
        activity_regularidade = activity_frequency

        # 8. Permissão no repositório
        permission_level = perm.get('permission', '') if perm else ''

        # 9. Proporção de PRs em que foi requisitado como reviewer
        pr_requested_as_reviewer_rate = 0
        if pulls and isinstance(pulls, list):
            requested_count = sum(1 for pr in pulls if any(r.get('login') == login for r in pr.get('requested_reviewers', [])))
            pr_requested_as_reviewer_rate = requested_count / len(pulls) if pulls else 0

        return {
            **user,
            "prs_opened": prs_opened,
            "prs_merged": prs_merged,
            "pr_accept_rate": pr_accept_rate,
            "avg_time_to_merge": avg_time_to_merge,
            "commits_total": commits_total,
            "issues_opened": issues_opened,
            "reviews_submitted": reviews_submitted,
            "stars_own_repos": stars_own_repos,
            "contribution_period": contribution_period,
            "activity_frequency": activity_frequency,
            "activity_regularidade": activity_regularidade,
            "permission_level": permission_level,
            "pr_requested_as_reviewer_rate": pr_requested_as_reviewer_rate
        }
    except Exception as e:
        print(f"Erro ao processar usuário {user.get('login', 'unknown')}: {e}")
        return {**user, "error": str(e)}

async def main():
    input_csv = 'users_countries.csv'
    output_csv = 'users_metrics_async.csv'
    
    print(f"Iniciando coleta com {len(TOKENS)} tokens e concorrência de {MAX_CONCURRENT}...")
    print(f"Lendo arquivo: {input_csv}")
    
    df = pd.read_csv(input_csv)
    users = df.to_dict(orient='records')
    results = []
    
    # Configuração otimizada de sessão
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, limit_per_host=10)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            get_user_metrics(session, user, user.get('repo_name', ''), user.get('repo_url', ''))
            for user in users
        ]
        print(f"Processando {len(tasks)} usuários...")
        
        # Processa com barra de progresso
        for f in tqdm_asyncio.as_completed(tasks, total=len(tasks), desc="Coletando métricas"):
            result = await f
            results.append(result)
            
            # Salva parcialmente a cada 10 usuários
            if len(results) % 10 == 0:
                pd.DataFrame(results).to_csv('users_metrics_partial.csv', index=False)
    
    # Salva resultado final
    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"\n✓ Coleta finalizada! {len(results)} usuários processados.")
    print(f"✓ Salvo em: {output_csv}")
    print(f"✓ Backup parcial salvo em: users_metrics_partial.csv")

if __name__ == "__main__":
    asyncio.run(main())