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
MAX_CONCURRENT = min(len(TOKENS), 10) if TOKENS else 1  # Concorrência mais conservadora

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
                timeout = aiohttp.ClientTimeout(total=20, connect=10)
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status == 403:
                        # Rate limit neste token, tenta próximo
                        await asyncio.sleep(0.3)
                        continue
                    if resp.status == 404:
                        return None
                    if resp.status == 200:
                        return await resp.json()
                    # Para outros status, espera um pouco
                    if resp.status >= 400:
                        await asyncio.sleep(0.2)
                        continue
            except asyncio.TimeoutError:
                print(f"Timeout na URL: {url[:50]}...")
                if attempt < retries - 1:
                    await asyncio.sleep(0.5)
                    continue
            except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError) as e:
                print(f"Erro de conexão {url[:50]}...: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1.0)  # Espera mais em caso de erro de conexão
                    continue
            except Exception as e:
                print(f"Erro ao buscar {url[:50]}...: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(0.5)
                    continue
        return None

# Wrapper para função fetch que cria nova sessão se necessário
async def fetch_with_token(session, url, semaphore, timeout=20):
    try:
        return await fetch(session, url)
    except Exception as e:
        if "Session is closed" in str(e):
            # Cria nova sessão temporária para esta requisição
            async with aiohttp.ClientSession() as temp_session:
                return await fetch(temp_session, url)
        return None

async def get_user_metrics(session, user, repo_name, repo_url):
    try:
        login = user['login']
        
        # Valida se tem as informações necessárias
        if not repo_url or pd.isna(repo_url):
            return {**user, "error": "repo_url missing"}
            
        repo_parts = repo_url.split('/')
        if len(repo_parts) < 5:
            return {**user, "error": "invalid repo_url format"}
            
        repo_owner = repo_parts[3]
        repo = repo_parts[4]

        print(f"Processando usuário: {login}")  # Debug log
        
        # Busca dados básicos primeiro (menos requisições)
        prs_url = f"{BASE_URL}/search/issues?q=type:pr+author:{login}+repo:{repo_owner}/{repo}"
        commits_url = f"{BASE_URL}/search/commits?q=author:{login}+repo:{repo_owner}/{repo}"
        issues_url = f"{BASE_URL}/search/issues?q=type:issue+author:{login}+repo:{repo_owner}/{repo}"

        # Busca os dados mais importantes primeiro
        basic_results = await asyncio.gather(
            fetch_with_token(session, prs_url, semaphore),
            fetch_with_token(session, commits_url, semaphore), 
            fetch_with_token(session, issues_url, semaphore),
            return_exceptions=True
        )

        prs_data, commits_data, issues_data = basic_results

        # Extrai dados básicos das requisições
        prs_opened = prs_data.get('total_count', 0) if prs_data and isinstance(prs_data, dict) else 0
        commits_total = commits_data.get('total_count', 0) if commits_data and isinstance(commits_data, dict) else 0
        issues_opened = issues_data.get('total_count', 0) if issues_data and isinstance(issues_data, dict) else 0

        # Buscar dados adicionais usando Search API (mais eficiente)
        prs_merged_url = f"{BASE_URL}/search/issues?q=type:pr+author:{login}+repo:{repo_owner}/{repo}+is:merged"
        user_repos_url = f"{BASE_URL}/users/{login}/repos?per_page=100"
        
        # Busca dados em paralelo
        additional_results = await asyncio.gather(
            fetch_with_token(session, prs_merged_url, semaphore),
            fetch_with_token(session, user_repos_url, semaphore),
            return_exceptions=True
        )
        
        prs_merged_data, user_repos_data = additional_results
        
        # Calcular PRs merged usando Search API (muito mais eficiente)
        prs_merged = 0
        if prs_merged_data and isinstance(prs_merged_data, dict):
            prs_merged = prs_merged_data.get('total_count', 0)
        
        # Calcular taxa de aceitação
        pr_accept_rate = round(prs_merged / prs_opened * 100, 2) if prs_opened > 0 else 0
        
        # Calcular tempo médio de merge (se tem PRs merged)
        avg_time_to_merge = 0
        if prs_merged > 0:
            # Buscar detalhes dos PRs merged para calcular tempo
            prs_details_url = f"{BASE_URL}/search/issues?q=type:pr+author:{login}+repo:{repo_owner}/{repo}+is:merged&per_page=10"
            prs_details_data = await fetch_with_token(session, prs_details_url, semaphore)
            
            if prs_details_data and isinstance(prs_details_data, dict):
                items = prs_details_data.get('items', [])
                merge_times = []
                
                for pr in items[:5]:  # Limitar a 5 PRs para performance
                    created_at = pr.get('created_at')
                    closed_at = pr.get('closed_at')  # Para PRs merged, closed_at é quando foi merged
                    
                    if created_at and closed_at:
                        try:
                            from datetime import datetime
                            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            closed = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                            time_diff = (closed - created).total_seconds() / 3600  # em horas
                            merge_times.append(time_diff)
                        except:
                            pass
                
                if merge_times:
                    avg_time_to_merge = round(sum(merge_times) / len(merge_times), 2)
        
        # Calcular estrelas em repos próprios
        stars_own_repos = 0
        if user_repos_data and isinstance(user_repos_data, list):
            stars_own_repos = sum(repo.get('stargazers_count', 0) for repo in user_repos_data)
        
        # Calcular estrelas em repos onde contribuiu (ponderadas pela contribuição)
        stars_contrib_repos = 0
        if prs_merged > 0:  # Só calcular se tem PRs mergeados
            # Buscar informações do repositório atual onde está contribuindo
            repo_info_url = f"{BASE_URL}/repos/{repo_owner}/{repo}"
            repo_info = await fetch_with_token(session, repo_info_url, semaphore)
            
            if repo_info and isinstance(repo_info, dict):
                repo_stars = repo_info.get('stargazers_count', 0)
                
                # Buscar total de PRs mergeados no repositório
                total_prs_repo_url = f"{BASE_URL}/search/issues?q=type:pr+repo:{repo_owner}/{repo}+is:merged"
                total_prs_data = await fetch_with_token(session, total_prs_repo_url, semaphore)
                
                if total_prs_data and isinstance(total_prs_data, dict):
                    total_prs_merged_repo = total_prs_data.get('total_count', 0)
                    
                    # Calcular peso da contribuição (PRs do dev / Total de PRs do repo)
                    if total_prs_merged_repo > 0:
                        contribution_weight = prs_merged / total_prs_merged_repo
                        # Estrelas ponderadas pela contribuição
                        stars_contrib_repos = repo_stars * contribution_weight
        
        # Calcular reviews submetidos pelo usuário
        reviews_submitted = 0
        reviews_url = f"{BASE_URL}/search/issues?q=type:pr+repo:{repo_owner}/{repo}+reviewed-by:{login}"
        reviews_data = await fetch_with_token(session, reviews_url, semaphore)
        if reviews_data and isinstance(reviews_data, dict):
            reviews_submitted = reviews_data.get('total_count', 0)
        
        # Estimativas para métricas menos críticas (para manter velocidade)
        contribution_period = max(1, commits_total // 10) if commits_total > 0 else 0  # Estimativa baseada em commits
        activity_frequency = commits_total / 365 if commits_total > 0 else 0  # Commits por dia (estimativa anual)
        activity_regularidade = activity_frequency
        permission_level = 'contributor' if (prs_opened > 0 or commits_total > 0) else 'viewer'

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
            "stars_contrib_repos": round(stars_contrib_repos, 2),
            "contribution_period": contribution_period,
            "activity_frequency": activity_frequency,
            "activity_regularidade": activity_regularidade,
            "permission_level": permission_level
        }
    except Exception as e:
        print(f"Erro ao processar usuário {user.get('login', 'unknown')}: {e}")
        return {**user, "error": str(e)}

async def main():
    input_csv = 'scripts/csv/users_countries.csv'
    output_csv = 'scripts/csv/users_metrics.csv'
    
    print(f"✅ {len(TOKENS)} token(s) do GitHub carregados")
    print(f"Iniciando coleta com {len(TOKENS)} tokens e concorrência de {MAX_CONCURRENT}...")
    print(f"Lendo arquivo: {input_csv}")
    
    df = pd.read_csv(input_csv)
    print(f"Arquivo carregado: {len(df)} registros encontrados")
    
    # Verifica se as colunas necessárias existem
    required_cols = ['login', 'repo_url']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Colunas obrigatórias faltando: {missing_cols}")
        return
    
    users = df.to_dict(orient='records')
    results = []
    
    # MODO COMPLETO: processar todos os usuários
    TEST_MODE = False  # ATIVAR MODO COMPLETO
    if TEST_MODE:
        users = users[:3]
        print(f"🧪 MODO TESTE: processando apenas {len(users)} usuários para validação")
    else:
        print(f"🚀 Modo completo: processando todos os {len(users)} usuários")
    
    # Processamento em lotes para melhor controle e recuperação
    BATCH_SIZE = 50  # Processar 50 usuários por vez
    total_users = len(users)
    
    print(f"📦 Processamento em lotes de {BATCH_SIZE} usuários")
    print(f"📊 Total de lotes: {(total_users + BATCH_SIZE - 1) // BATCH_SIZE}")
    
    # Configuração conservadora para evitar travamento
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # Processar em lotes
        for batch_start in range(0, total_users, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_users)
            batch_users = users[batch_start:batch_end]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (total_users + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"\n🚀 Processando lote {batch_num}/{total_batches} ({len(batch_users)} usuários)")
            print(f"📍 Posição: {batch_start+1}-{batch_end} de {total_users}")
            
            # Criar tarefas para este lote
            batch_tasks = [
                get_user_metrics(session, user, user.get('repo_name', ''), user.get('repo_url', ''))
                for user in batch_users
            ]
            
            # Processar lote com barra de progresso
            batch_results = []
            for f in tqdm_asyncio.as_completed(batch_tasks, total=len(batch_tasks), 
                                               desc=f"Lote {batch_num}"):
                try:
                    result = await f
                    batch_results.append(result)
                except Exception as e:
                    print(f"Erro ao processar usuário: {e}")
                    batch_results.append({"error": str(e)})
            
            # Adicionar resultados do lote aos resultados totais
            results.extend(batch_results)
            
            # Salvar backup após cada lote
            pd.DataFrame(results).to_csv('users_metrics_partial.csv', index=False)
            print(f"✅ Lote {batch_num} concluído! Total processado: {len(results)}/{total_users}")
            
            # Pequena pausa entre lotes para dar respiro às APIs
            if batch_num < total_batches:
                print("⏳ Pausa de 2s entre lotes...")
                await asyncio.sleep(2)
    
    # Salva resultado final
    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"\n🎉 Coleta finalizada! {len(results)} usuários processados em {total_batches} lotes.")
    print(f"✓ Salvo em: {output_csv}")
    print(f"✓ Backup parcial salvo em: users_metrics_partial.csv")

if __name__ == "__main__":
    asyncio.run(main())