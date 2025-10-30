"""
Script 2/6: Coleta de Issues
Coleta: Issues e comentários de issues
Período: 2020-2025
Limite: SEM LIMITE
"""
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from script5_utils import (
    get_headers, safe_request, get_user_info, is_date_in_range,
    extract_mentions, collect_paginated_data, save_results, SLEEP_TIME
)


def collect_issue_comments(repo_full_name, repo_name, issue_number, issue_author, edges, nodes):
    """Coleta comentários de uma issue específica"""
    url_comments = f'https://api.github.com/repos/{repo_full_name}/issues/{issue_number}/comments'
    r_comments = safe_request(url_comments)
    if r_comments and r_comments.status_code == 200:
        for comment in r_comments.json():
            if not comment.get('user') or not comment['user']:
                continue
            
            comment_date = comment['created_at']
            if not is_date_in_range(comment_date):
                continue
                
            commenter = comment['user']['login']
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
            
            # Mentions no comentário
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


def collect_issue_interactions(repo_full_name, repo_name, edges, nodes):
    """Coleta todas as interações de issues de um repositório"""
    print(f'  🐛 Coletando Issues (sem limite)...')
    issues = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/issues?state=all')
    
    # Filtra apenas issues (remove PRs) e por data
    issues = [i for i in issues if 'pull_request' not in i]
    issues_filtered = [i for i in issues if i.get('user') and i['user'] and is_date_in_range(i.get('created_at', ''))]
    print(f'     Encontradas {len(issues)} issues (após filtro 2020-2025: {len(issues_filtered)})')
    
    for issue in issues_filtered:
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
        
        # Mentions no corpo da issue
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
        for issue in issues_filtered:
            issue_number = issue['number']
            issue_author = issue['user']['login']
            futures.append(executor.submit(collect_issue_comments, repo_full_name, repo_name, issue_number, issue_author, edges, nodes))
        
        for future in as_completed(futures):
            future.result()


# Execução principal
if __name__ == '__main__':
    print('🚀 Script 2/6: Coletando Issues (2020-2025, sem limite)\n')
    start_time = time.time()
    
    df = pd.read_csv('selected_repos_and_first_user.csv')
    edges = []
    nodes = {}
    
    for idx, row in df.iterrows():
        repo_name = row['repo_name']
        repo_url = row['repo_url']
        repo_full_name = repo_url.replace('https://github.com/', '').strip('/')
        
        repo_start = time.time()
        print(f'\n📦 [{idx+1}/{len(df)}] {repo_name}')
        
        collect_issue_interactions(repo_full_name, repo_name, edges, nodes)
        
        repo_elapsed = time.time() - repo_start
        print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
        
        # Backup parcial a cada 2 repos
        if idx % 2 == 0 and idx > 0:
            save_results(edges, nodes, 'issues_partial')
    
    # Salva resultados finais
    save_results(edges, nodes, 'issues')
    
    total_elapsed = time.time() - start_time
    print(f'\n✅ Coleta de Issues finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
