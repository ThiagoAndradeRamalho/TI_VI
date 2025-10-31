import requests
import pandas as pd
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from token_loader import load_github_tokens

TOKENS = load_github_tokens()

token_idx = 0
token_lock = Lock()
SLEEP_TIME = 0.05  # Reduzido de 0.5s para 0.05s (10x mais rápido)

# Carrega dados de países uma única vez no início
countries_df = None
try:
    countries_df = pd.read_csv('users_countries.csv')
    print(f'✅ Carregados dados de {len(countries_df)} usuários com países')
except Exception as e:
    print(f'⚠️  Não foi possível carregar users_countries.csv: {e}')

def get_headers():
    global token_idx
    with token_lock:
        headers = {'Authorization': f'token {TOKENS[token_idx]}'}
        token_idx = (token_idx + 1) % len(TOKENS)
        return headers

def safe_request(url):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=get_headers(), timeout=10)
            if r.status_code == 403 and 'rate limit' in r.text.lower():
                print('⚠️  Rate limit, aguardando 60s...')
                time.sleep(60)
                continue
            return r
        except Exception as e:
            if attempt < max_retries - 1:
                print(f'Erro em request (tentativa {attempt + 1}/{max_retries}): {e}')
                time.sleep(2)
            else:
                print(f'❌ Falha após {max_retries} tentativas: {url}')
                return None
    return None

def extract_mentions(text):
    """Extrai @mentions de textos (corpo de PRs, issues, comentários)"""
    if not text:
        return []
    # Regex para capturar @username (permite letras, números, hífens)
    mentions = re.findall(r'@([a-zA-Z0-9-]+)', text)
    return list(set(mentions))  # Remove duplicatas

def get_user_info(login):
    """Retorna informações do usuário incluindo país (do CSV) e followers (da API)"""
    info = {
        'login': login,
        'profile_url': f'https://github.com/{login}',
        'country': '',
        'followers': 0
    }
    
    # Busca país no CSV carregado
    if countries_df is not None:
        user_data = countries_df[countries_df['login'] == login]
        if not user_data.empty:
            info['country'] = user_data.iloc[0].get('country', '')
    
    # Busca followers na API
    try:
        r = safe_request(f'https://api.github.com/users/{login}')
        if r and r.status_code == 200:
            user_json = r.json()
            info['followers'] = user_json.get('followers', 0)
            time.sleep(SLEEP_TIME)
    except Exception as e:
        print(f'⚠️  Erro ao buscar followers de {login}: {e}')
    
    return info

def collect_paginated_data(base_url, max_pages=100):  # Aumentado de 10 para 100 páginas
    """Coleta dados paginados de forma mais eficiente"""
    all_data = []
    page = 1
    
    while page <= max_pages:
        url = f'{base_url}{"&" if "?" in base_url else "?"}per_page=100&page={page}'
        r = safe_request(url)
        
        if not r or r.status_code != 200:
            break
            
        data = r.json()
        if not data or not isinstance(data, list):
            break
            
        all_data.extend(data)
        
        # Se retornou menos de 100, é a última página
        if len(data) < 100:
            break
            
        page += 1
        time.sleep(SLEEP_TIME)
    
    return all_data

def collect_pr_interactions(repo_full_name, repo_name, edges, nodes):
    print(f'  📋 Coletando PRs...')
    prs = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/pulls?state=all')
    
    print(f'     Encontrados {len(prs)} PRs')
    
    for pr in prs:
        # Verificar se user existe
        if not pr.get('user') or not pr['user']:
            continue
        pr_number = pr['number']
        pr_author = pr['user']['login']
        pr_date = pr['created_at']
        pr_body = pr.get('body', '')
        
        nodes[pr_author] = get_user_info(pr_author)
        edges.append({
            'repo_name': repo_name,
            'source': pr_author,
            'target': pr_author,
            'interaction_type': 'pr_opened',
            'date': pr_date,
            'pr_or_issue_number': pr_number
        })
        
        # Extrai mentions do corpo do PR
        mentions = extract_mentions(pr_body)
        for mentioned in mentions:
            if mentioned != pr_author:
                nodes[mentioned] = get_user_info(mentioned)
                edges.append({
                    'repo_name': repo_name,
                    'source': pr_author,
                    'target': mentioned,
                    'interaction_type': 'mention',
                    'date': pr_date,
                    'pr_or_issue_number': pr_number
                })
    
    # Coleta reviews e comentários em paralelo (mais rápido)
    print(f'  💬 Coletando reviews e comentários dos PRs...')
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for pr in prs:  # SEM LIMITE - coleta TODOS os PRs
            # Verificar se user existe
            if not pr.get('user') or not pr['user']:
                continue
            pr_number = pr['number']
            pr_author = pr['user']['login']
            futures.append(executor.submit(collect_pr_details, repo_full_name, repo_name, pr_number, pr_author, edges, nodes))
        
        for future in as_completed(futures):
            future.result()

def collect_pr_details(repo_full_name, repo_name, pr_number, pr_author, edges, nodes):
    # Reviews
    url_reviews = f'https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews'
    r_reviews = safe_request(url_reviews)
    if r_reviews and r_reviews.status_code == 200:
        for review in r_reviews.json():
            # Verificar se user existe (pode ser None para bots ou contas deletadas)
            if not review.get('user') or not review['user']:
                continue
            reviewer = review['user']['login']
            review_date = review.get('submitted_at', '')
            review_body = review.get('body', '')
            nodes[reviewer] = get_user_info(reviewer)
            edges.append({
                'repo_name': repo_name,
                'source': reviewer,
                'target': pr_author,
                'interaction_type': 'pr_review',
                'date': review_date,
                'pr_or_issue_number': pr_number
            })
            
            # Extrai mentions do corpo do review
            mentions = extract_mentions(review_body)
            for mentioned in mentions:
                if mentioned != pr_author and mentioned != reviewer:
                    nodes[mentioned] = get_user_info(mentioned)
                    edges.append({
                        'repo_name': repo_name,
                        'source': reviewer,
                        'target': mentioned,
                        'interaction_type': 'mention',
                        'date': review_date,
                        'pr_or_issue_number': pr_number
                    })
    
    # Comentários
    url_comments = f'https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments'
    r_comments = safe_request(url_comments)
    if r_comments and r_comments.status_code == 200:
        for comment in r_comments.json():
            # Verificar se user existe
            if not comment.get('user') or not comment['user']:
                continue
            commenter = comment['user']['login']
            comment_date = comment['created_at']
            comment_body = comment.get('body', '')
            nodes[commenter] = get_user_info(commenter)
            edges.append({
                'repo_name': repo_name,
                'source': commenter,
                'target': pr_author,
                'interaction_type': 'pr_comment',
                'date': comment_date,
                'pr_or_issue_number': pr_number
            })
            
            # Extrai mentions do corpo do comentário
            mentions = extract_mentions(comment_body)
            for mentioned in mentions:
                if mentioned != pr_author and mentioned != commenter:
                    nodes[mentioned] = get_user_info(mentioned)
                    edges.append({
                        'repo_name': repo_name,
                        'source': commenter,
                        'target': mentioned,
                        'interaction_type': 'mention',
                        'date': comment_date,
                        'pr_or_issue_number': pr_number
                    })

def collect_issue_interactions(repo_full_name, repo_name, edges, nodes):
    print(f'  🐛 Coletando Issues...')
    issues = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/issues?state=all')
    
    # Filtra apenas issues (remove PRs)
    issues = [i for i in issues if 'pull_request' not in i]
    print(f'     Encontradas {len(issues)} issues')
    
    for issue in issues:
        # Verificar se user existe
        if not issue.get('user') or not issue['user']:
            continue
        issue_number = issue['number']
        issue_author = issue['user']['login']
        issue_date = issue['created_at']
        issue_body = issue.get('body', '')
        
        nodes[issue_author] = get_user_info(issue_author)
        edges.append({
            'repo_name': repo_name,
            'source': issue_author,
            'target': issue_author,
            'interaction_type': 'issue_opened',
            'date': issue_date,
            'pr_or_issue_number': issue_number
        })
        
        # Extrai mentions do corpo da issue
        mentions = extract_mentions(issue_body)
        for mentioned in mentions:
            if mentioned != issue_author:
                nodes[mentioned] = get_user_info(mentioned)
                edges.append({
                    'repo_name': repo_name,
                    'source': issue_author,
                    'target': mentioned,
                    'interaction_type': 'mention',
                    'date': issue_date,
                    'pr_or_issue_number': issue_number
                })
    
    # Coleta comentários em paralelo
    print(f'  💬 Coletando comentários das issues...')
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for issue in issues:  # SEM LIMITE - coleta TODAS as issues
            # Verificar se user existe
            if not issue.get('user') or not issue['user']:
                continue
            issue_number = issue['number']
            issue_author = issue['user']['login']
            futures.append(executor.submit(collect_issue_comments, repo_full_name, repo_name, issue_number, issue_author, edges, nodes))
        
        for future in as_completed(futures):
            future.result()

def collect_issue_comments(repo_full_name, repo_name, issue_number, issue_author, edges, nodes):
    url_comments = f'https://api.github.com/repos/{repo_full_name}/issues/{issue_number}/comments'
    r_comments = safe_request(url_comments)
    if r_comments and r_comments.status_code == 200:
        for comment in r_comments.json():
            # Verificar se user existe
            if not comment.get('user') or not comment['user']:
                continue
            commenter = comment['user']['login']
            comment_date = comment['created_at']
            comment_body = comment.get('body', '')
            nodes[commenter] = get_user_info(commenter)
            edges.append({
                'repo_name': repo_name,
                'source': commenter,
                'target': issue_author,
                'interaction_type': 'issue_comment',
                'date': comment_date,
                'pr_or_issue_number': issue_number
            })
            
            # Extrai mentions do corpo do comentário
            mentions = extract_mentions(comment_body)
            for mentioned in mentions:
                if mentioned != issue_author and mentioned != commenter:
                    nodes[mentioned] = get_user_info(mentioned)
                    edges.append({
                        'repo_name': repo_name,
                        'source': commenter,
                        'target': mentioned,
                        'interaction_type': 'mention',
                        'date': comment_date,
                        'pr_or_issue_number': issue_number
                    })

def collect_commit_interactions(repo_full_name, repo_name, edges, nodes):
    print(f'  💾 Coletando Commits...')
    commits = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/commits', max_pages=100)  # Aumentado de 5 para 100
    print(f'     Encontrados {len(commits)} commits')
    
    for commit in commits:
        if commit.get('author'):
            author = commit['author']['login']
            nodes[author] = get_user_info(author)
            commit_date = commit['commit']['author']['date']
            edges.append({
                'repo_name': repo_name,
                'source': author,
                'target': author,
                'interaction_type': 'commit',
                'date': commit_date,
                'pr_or_issue_number': ''
            })
            
            # Co-autores
            if 'commit' in commit and 'message' in commit['commit']:
                message = commit['commit']['message']
                for line in message.split('\n'):
                    if line.lower().startswith('co-authored-by:'):
                        coauthor = line.split(':')[1].split('<')[0].strip()
                        if coauthor:
                            nodes[coauthor] = get_user_info(coauthor)
                            edges.append({
                                'repo_name': repo_name,
                                'source': coauthor,
                                'target': author,
                                'interaction_type': 'co_authored_commit',
                                'date': commit_date,
                                'pr_or_issue_number': ''
                            })

def collect_stars(repo_full_name, repo_name, edges, nodes):
    print(f'  ⭐ Coletando Stars...')
    stargazers = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/stargazers', max_pages=100)  # Aumentado de 5 para 100
    print(f'     Encontrados {len(stargazers)} stargazers')
    
    for user in stargazers:
        login = user['login']
        nodes[login] = get_user_info(login)
        edges.append({
            'repo_name': repo_name,
            'source': login,
            'target': repo_name,
            'interaction_type': 'star',
            'date': '',
            'pr_or_issue_number': ''
        })

def collect_forks(repo_full_name, repo_name, edges, nodes):
    print(f'  🔀 Coletando Forks...')
    forks = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/forks', max_pages=100)  # Aumentado de 3 para 100
    print(f'     Encontrados {len(forks)} forks')
    
    for fork in forks:
        login = fork['owner']['login']
        nodes[login] = get_user_info(login)
        edges.append({
            'repo_name': repo_name,
            'source': login,
            'target': repo_name,
            'interaction_type': 'fork',
            'date': fork['created_at'],
            'pr_or_issue_number': ''
        })

def collect_discussion_interactions(repo_full_name, repo_name, edges, nodes):
    """Coleta interações de GitHub Discussions usando GraphQL"""
    print(f'  💭 Coletando Discussions...')
    
    # Query GraphQL para buscar discussions
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        discussions(first: 100, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            number
            author {
              login
            }
            createdAt
            comments(first: 100) {
              nodes {
                author {
                  login
                }
                createdAt
                body
              }
            }
          }
        }
      }
    }
    """
    
    owner, name = repo_full_name.split('/')
    has_next = True
    cursor = None
    total_discussions = 0
    
    while has_next:
        variables = {
            'owner': owner,
            'name': name,
            'cursor': cursor
        }
        
        try:
            r = requests.post(
                'https://api.github.com/graphql',
                json={'query': query, 'variables': variables},
                headers=get_headers(),
                timeout=10
            )
            
            if r.status_code != 200:
                print(f'     ⚠️  Erro ao buscar discussions: {r.status_code}')
                break
            
            data = r.json()
            
            # Verifica se há erro (repo pode não ter discussions habilitadas)
            if 'errors' in data:
                print(f'     ⚠️  Discussions não habilitadas ou erro: {data["errors"][0].get("message", "")}')
                break
            
            discussions_data = data.get('data', {}).get('repository', {}).get('discussions', {})
            discussions = discussions_data.get('nodes', [])
            
            for discussion in discussions:
                if not discussion or not discussion.get('author'):
                    continue
                    
                disc_number = discussion.get('number', '')
                disc_author = discussion['author']['login']
                disc_date = discussion.get('createdAt', '')
                
                nodes[disc_author] = get_user_info(disc_author)
                edges.append({
                    'repo_name': repo_name,
                    'source': disc_author,
                    'target': disc_author,
                    'interaction_type': 'discussion_started',
                    'date': disc_date,
                    'pr_or_issue_number': disc_number
                })
                
                # Comentários da discussion
                comments = discussion.get('comments', {}).get('nodes', [])
                for comment in comments:
                    if not comment or not comment.get('author'):
                        continue
                        
                    commenter = comment['author']['login']
                    comment_date = comment.get('createdAt', '')
                    comment_body = comment.get('body', '')
                    
                    nodes[commenter] = get_user_info(commenter)
                    edges.append({
                        'repo_name': repo_name,
                        'source': commenter,
                        'target': disc_author,
                        'interaction_type': 'discussion_reply',
                        'date': comment_date,
                        'pr_or_issue_number': disc_number
                    })
                    
                    # Extrai mentions dos comentários
                    mentions = extract_mentions(comment_body)
                    for mentioned in mentions:
                        if mentioned != disc_author and mentioned != commenter:
                            nodes[mentioned] = get_user_info(mentioned)
                            edges.append({
                                'repo_name': repo_name,
                                'source': commenter,
                                'target': mentioned,
                                'interaction_type': 'mention',
                                'date': comment_date,
                                'pr_or_issue_number': disc_number
                            })
            
            total_discussions += len(discussions)
            
            # Paginação
            page_info = discussions_data.get('pageInfo', {})
            has_next = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor')
            
            time.sleep(SLEEP_TIME)
            
        except Exception as e:
            print(f'     ⚠️  Erro ao processar discussions: {e}')
            break
    
    print(f'     Encontradas {total_discussions} discussions')

# Execução principal
print('🚀 Iniciando coleta otimizada...\n')
start_time = time.time()

df = pd.read_csv('repos_final.csv')
edges = []
nodes = {}

for idx, row in df.iterrows():
    repo_name = row['repo_name']
    repo_url = row['repo_url']
    repo_full_name = repo_url.replace('https://github.com/', '').strip('/')
    
    repo_start = time.time()
    print(f'\n📦 [{idx+1}/{len(df)}] {repo_name}')
    
    collect_pr_interactions(repo_full_name, repo_name, edges, nodes)
    collect_issue_interactions(repo_full_name, repo_name, edges, nodes)
    collect_commit_interactions(repo_full_name, repo_name, edges, nodes)
    collect_stars(repo_full_name, repo_name, edges, nodes)
    collect_forks(repo_full_name, repo_name, edges, nodes)
    collect_discussion_interactions(repo_full_name, repo_name, edges, nodes)
    
    repo_elapsed = time.time() - repo_start
    print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
    
    # Backup parcial
    if idx % 2 == 0 and idx > 0:
        pd.DataFrame(edges).to_csv('edges_raw_partial.csv', index=False)
        pd.DataFrame(list(nodes.values())).to_csv('nodes_raw_partial.csv', index=False)
        print(f'  💾 Backup salvo')

# Salva resultados finais
pd.DataFrame(edges).to_csv('edges_raw.csv', index=False)
pd.DataFrame(list(nodes.values())).to_csv('nodes_raw.csv', index=False)

total_elapsed = time.time() - start_time
print(f'\n✅ Coleta finalizada em {total_elapsed/60:.1f} minutos!')
print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
