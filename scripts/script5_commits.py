"""
Script 3/6: Coleta de Commits
Coleta: Commits individuais e co-autores
Período: 2020-2025
Limite: SEM LIMITE
"""
import pandas as pd
import time
from script5_utils import (
    get_headers, safe_request, get_user_info, is_date_in_range,
    collect_paginated_data, save_results, SLEEP_TIME
)


def collect_commit_interactions(repo_full_name, repo_name, edges, nodes):
    """Coleta todas as interações de commits de um repositório"""
    print(f'  💾 Coletando Commits (sem limite)...')
    commits = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/commits')
    
    # Filtra commits por data
    commits_filtered = []
    for commit in commits:
        if commit.get('commit') and commit['commit'].get('author'):
            commit_date = commit['commit']['author'].get('date', '')
            if is_date_in_range(commit_date):
                commits_filtered.append(commit)
    
    print(f'     Encontrados {len(commits)} commits (após filtro 2020-2025: {len(commits_filtered)})')
    
    for commit in commits_filtered:
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
                        # Extrai nome do co-autor (formato: "Co-authored-by: Nome <email>")
                        try:
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
                        except:
                            pass


# Execução principal
if __name__ == '__main__':
    print('🚀 Script 3/6: Coletando Commits (2020-2025, sem limite)\n')
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
        
        collect_commit_interactions(repo_full_name, repo_name, edges, nodes)
        
        repo_elapsed = time.time() - repo_start
        print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
        
        # Backup parcial a cada 2 repos
        if idx % 2 == 0 and idx > 0:
            save_results(edges, nodes, 'commits_partial')
    
    # Salva resultados finais
    save_results(edges, nodes, 'commits')
    
    total_elapsed = time.time() - start_time
    print(f'\n✅ Coleta de Commits finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
