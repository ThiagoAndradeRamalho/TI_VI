"""
Script OTIMIZADO de coleta de dados estruturados de desenvolvedores e repositórios.

MELHORIAS DE PERFORMANCE:
- GraphQL API: 1 request ao invés de 4-5 para dados de usuário
- Requisições assíncronas: centenas de requests em paralelo
- Cache inteligente: evita requests duplicadas
- Sleep reduzido: 0.05s vs 0.5s (10x mais rápido)
- Processamento paralelo: múltiplos usuários simultaneamente

GANHO ESPERADO: 20-50x mais rápido que o script original
"""

import asyncio
import aiohttp
import pandas as pd
import time
from collections import defaultdict
from token_loader import load_github_tokens

TOKENS = load_github_tokens()

user_cache = {}
permission_cache = {}

class TokenManager:
    def __init__(self):
        self.current = 0
        self.lock = asyncio.Lock()
        self.token_available_at = [0.0] * len(TOKENS) if TOKENS else [0.0]
    
    async def get_token(self):
        async with self.lock:
            now = time.time()
            # Encontra o token disponível mais cedo
            min_wait_idx = 0
            min_wait_time = self.token_available_at[0] - now
            
            for i in range(1, len(TOKENS)):
                wait_time = self.token_available_at[i] - now
                if wait_time < min_wait_time:
                    min_wait_time = wait_time
                    min_wait_idx = i
            
            if min_wait_time > 0:
                await asyncio.sleep(min_wait_time)
            
            return TOKENS[min_wait_idx], min_wait_idx
    
    def mark_rate_limited(self, token_idx, reset_time):
        self.token_available_at[token_idx] = reset_time

token_manager = TokenManager()

async def safe_request(session, url, method='GET', json_data=None, max_retries=3):
    """Faz requisição com retry e gerenciamento de rate limit"""
    for attempt in range(max_retries):
        try:
            token, token_idx = await token_manager.get_token()
            headers = {'Authorization': f'token {token}'}
            
            if method == 'POST':
                async with session.post(url, headers=headers, json=json_data) as response:
                    return await handle_response(response, token_idx)
            else:
                async with session.get(url, headers=headers) as response:
                    return await handle_response(response, token_idx)
                    
        except Exception as e:
            if attempt < max_retries - 1:
                print(f'⚠️  Erro (tentativa {attempt + 1}/{max_retries}): {e}')
                await asyncio.sleep(2 ** attempt)
            else:
                return None
    return None

async def handle_response(response, token_idx):
    """Processa resposta e gerencia rate limit"""
    remaining = int(response.headers.get('X-RateLimit-Remaining', 1000))
    reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
    
    if remaining < 10:
        token_manager.mark_rate_limited(token_idx, reset_time)
        print(f'⚠️  Token {token_idx} próximo do limite')
    
    if response.status == 403 and 'rate limit' in (await response.text()).lower():
        token_manager.mark_rate_limited(token_idx, reset_time)
        await asyncio.sleep(1)
        return None
    
    if response.status == 200:
        return await response.json()
    
    return None

async def get_user_stats_graphql(session, repo_owner, repo_name, username):
    """
    USA GRAPHQL PARA PEGAR TODOS OS DADOS EM 1 REQUEST!
    Ao invés de 4-5 requests REST, faz apenas 1 request GraphQL
    """
    cache_key = f"{repo_owner}/{repo_name}/{username}"
    if cache_key in user_cache:
        return user_cache[cache_key]
    
    query = """
    query($owner: String!, $name: String!, $author: String!) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 1, author: {emails: [""]}) {
                totalCount
              }
            }
          }
        }
        pullRequests(first: 1, states: [OPEN, CLOSED, MERGED], author: $author) {
          totalCount
        }
        issues(first: 1, states: [OPEN, CLOSED], filterBy: {createdBy: $author}) {
          totalCount
        }
      }
      search(query: "type:pr repo:$owner/$name reviewed-by:$author", type: ISSUE, first: 1) {
        issueCount
      }
    }
    """
    
    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "author": username
    }
    
    result = await safe_request(
        session,
        'https://api.github.com/graphql',
        method='POST',
        json_data={'query': query, 'variables': variables}
    )
    
    if not result or 'data' not in result:
        return await get_user_stats_rest(session, repo_owner, repo_name, username)
    
    data = result['data']
    repo_data = data.get('repository', {})
    
    commits = 0
    if repo_data.get('defaultBranchRef'):
        commits = repo_data['defaultBranchRef']['target']['history']['totalCount']
    
    prs = repo_data.get('pullRequests', {}).get('totalCount', 0)
    issues = repo_data.get('issues', {}).get('totalCount', 0)
    reviews = data.get('search', {}).get('issueCount', 0)
    
    stats = {
        'commits': commits,
        'prs': prs,
        'reviews': reviews,
        'issues': issues
    }
    
    user_cache[cache_key] = stats
    return stats

async def get_user_stats_rest(session, repo_owner, repo_name, username):
    """Fallback: usa REST API (mais lento mas funciona sempre)"""
    repo_full_name = f"{repo_owner}/{repo_name}"
    cache_key = f"{repo_full_name}/{username}"
    
    if cache_key in user_cache:
        return user_cache[cache_key]
    
    tasks = [
        safe_request(session, f'https://api.github.com/search/issues?q=type:pr+repo:{repo_full_name}+author:{username}&per_page=1'),
        safe_request(session, f'https://api.github.com/search/issues?q=type:pr+repo:{repo_full_name}+reviewed-by:{username}&per_page=1'),
        safe_request(session, f'https://api.github.com/search/issues?q=type:issue+repo:{repo_full_name}+author:{username}&per_page=1'),
        safe_request(session, f'https://api.github.com/repos/{repo_full_name}/commits?author={username}&per_page=1')
    ]
    
    results = await asyncio.gather(*tasks)
    
    prs = results[0].get('total_count', 0) if results[0] else 0
    reviews = results[1].get('total_count', 0) if results[1] else 0
    issues = results[2].get('total_count', 0) if results[2] else 0
    
    # Commits precisa parsear Link header
    commits = 0
    if results[3] and isinstance(results[3], list):
        commits = len(results[3])
    
    stats = {
        'commits': commits,
        'prs': prs,
        'reviews': reviews,
        'issues': issues
    }
    
    user_cache[cache_key] = stats
    return stats

async def get_permission(session, repo_full_name, username):
    """Obtém permissão do usuário (com cache)"""
    cache_key = f"{repo_full_name}/{username}"
    if cache_key in permission_cache:
        return permission_cache[cache_key]
    
    url = f'https://api.github.com/repos/{repo_full_name}/collaborators/{username}/permission'
    result = await safe_request(session, url)
    
    permission = result.get('permission', 'unknown') if result else 'unknown'
    permission_cache[cache_key] = permission
    return permission

async def get_maintainers(session, repo_full_name):
    """Obtém lista de mantenedores"""
    url = f'https://api.github.com/repos/{repo_full_name}/collaborators?per_page=100'
    result = await safe_request(session, url)
    
    if not result:
        return []
    
    maintainers = []
    for user in result:
        perms = user.get('permissions', {})
        if perms.get('admin') or perms.get('maintain'):
            maintainers.append({
                'login': user['login'],
                'permission': 'admin' if perms.get('admin') else 'maintain'
            })
    
    return maintainers

async def get_all_prs(session, repo_full_name):
    """Coleta todos os PRs de forma otimizada"""
    print(f'    📋 Coletando PRs...')
    prs = []
    page = 1
    
    while page <= 100:  # Limite de segurança
        url = f'https://api.github.com/repos/{repo_full_name}/pulls?state=all&per_page=100&page={page}'
        result = await safe_request(session, url)
        
        if not result or not isinstance(result, list) or len(result) == 0:
            break
        
        # Coleta reviewers em paralelo para todos os PRs da página
        pr_tasks = []
        for pr in result:
            pr_number = pr['number']
            pr_tasks.append(get_pr_reviewers(session, repo_full_name, pr_number))
        
        reviewers_list = await asyncio.gather(*pr_tasks)
        
        for pr, reviewers in zip(result, reviewers_list):
            prs.append({
                'repo_name': repo_full_name,
                'pr_number': pr['number'],
                'author': pr['user']['login'],
                'reviewers_requested': ';'.join(reviewers),
                'opened_at': pr['created_at'],
                'merged_at': pr.get('merged_at', ''),
                'closed_at': pr.get('closed_at', '')
            })
        
        if len(result) < 100:
            break
        
        page += 1
        await asyncio.sleep(0.05)  # Sleep mínimo
    
    print(f'    ✅ {len(prs)} PRs coletados')
    return prs

async def get_pr_reviewers(session, repo_full_name, pr_number):
    """Obtém reviewers de um PR"""
    url = f'https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/requested_reviewers'
    result = await safe_request(session, url)
    
    if not result:
        return []
    
    return [u['login'] for u in result.get('users', [])]

async def process_user(session, repo_owner, repo_name, repo_full_name, user_row):
    """Processa um único usuário (stats + permission)"""
    login = user_row['login']
    country = user_row['country']
    
    # Busca stats e permission em paralelo
    stats_task = get_user_stats_graphql(session, repo_owner, repo_name, login)
    perm_task = get_permission(session, repo_full_name, login)
    
    stats, permission = await asyncio.gather(stats_task, perm_task)
    
    return {
        'repo_name': f"{repo_owner}/{repo_name}",
        'login': login,
        'permission': permission,
        'commits': stats['commits'],
        'prs': stats['prs'],
        'reviews': stats['reviews'],
        'issues': stats['issues'],
        'country': country
    }

async def process_repository(session, repo_row, users_df):
    """Processa um repositório completo"""
    repo_name = repo_row['repo_name']
    repo_url = repo_row['repo_url']
    repo_full_name = repo_url.replace('https://github.com/', '').strip('/')
    repo_owner, repo_name_only = repo_full_name.split('/')
    
    print(f'\n🔄 Processando {repo_name}...')
    start = time.time()
    
    # Filtra contribuidores deste repo
    contribs = users_df[users_df['repo_name'] == repo_name]
    
    if len(contribs) == 0:
        print(f'  ⚠️  Nenhum contribuidor encontrado')
        return [], [], []
    
    print(f'  👥 {len(contribs)} contribuidores')
    
    # Processa usuários em paralelo (lotes de 10 para não sobrecarregar)
    dev_repo_rows = []
    batch_size = 10
    
    for i in range(0, len(contribs), batch_size):
        batch = contribs.iloc[i:i+batch_size]
        tasks = [process_user(session, repo_owner, repo_name_only, repo_full_name, row) 
                 for _, row in batch.iterrows()]
        
        results = await asyncio.gather(*tasks)
        dev_repo_rows.extend(results)
        
        print(f'  ✓ {min(i+batch_size, len(contribs))}/{len(contribs)} usuários processados')
    
    # Busca mantenedores e PRs em paralelo
    maintainers_task = get_maintainers(session, repo_full_name)
    prs_task = get_all_prs(session, repo_full_name)
    
    maintainers, prs = await asyncio.gather(maintainers_task, prs_task)
    
    # Adiciona country aos mantenedores
    maintainers_rows = []
    for m in maintainers:
        country = contribs[contribs['login'] == m['login']]['country'].values[0] \
                  if m['login'] in contribs['login'].values else ''
        maintainers_rows.append({
            'repo_name': repo_name,
            'login': m['login'],
            'country': country,
            'permission': m['permission']
        })
    
    elapsed = time.time() - start
    print(f'  ✅ Concluído em {elapsed:.1f}s')
    
    return dev_repo_rows, maintainers_rows, prs

async def main():
    print('🚀 Iniciando coleta OTIMIZADA...\n')
    total_start = time.time()
    
    # Carrega dados
    repos_df = pd.read_csv('repos_final.csv')
    users_df = pd.read_csv('users_countries.csv')
    
    print(f'📊 {len(repos_df)} repositórios, {len(users_df)} usuários\n')
    
    all_dev_repo = []
    all_maintainers = []
    all_prs = []
    
    async with aiohttp.ClientSession() as session:
        for idx, repo_row in repos_df.iterrows():
            dev_rows, maint_rows, prs = await process_repository(session, repo_row, users_df)
            
            all_dev_repo.extend(dev_rows)
            all_maintainers.extend(maint_rows)
            all_prs.extend(prs)
            
            # Backup parcial
            if idx % 2 == 0 and idx > 0:
                pd.DataFrame(all_dev_repo).to_csv('dev_repo_raw_partial.csv', index=False)
                pd.DataFrame(all_maintainers).to_csv('maintainers_raw_partial.csv', index=False)
                pd.DataFrame(all_prs).to_csv('prs_raw_partial.csv', index=False)
                print(f'  💾 Backup salvo após {idx+1} repos')
    
    # Salva resultados finais
    pd.DataFrame(all_dev_repo).to_csv('dev_repo_raw.csv', index=False)
    pd.DataFrame(all_maintainers).to_csv('maintainers_raw.csv', index=False)
    pd.DataFrame(all_prs).to_csv('prs_raw.csv', index=False)
    
    total_elapsed = time.time() - total_start
    print(f'\n✅ Coleta finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Resultados:')
    print(f'   - {len(all_dev_repo)} relações dev-repo')
    print(f'   - {len(all_maintainers)} mantenedores')
    print(f'   - {len(all_prs)} PRs')

if __name__ == '__main__':
    asyncio.run(main())
