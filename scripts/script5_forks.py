"""
Script 5/6: Coleta de Forks
Coleta: Usuários que fizeram fork dos repositórios
Período: 2020-2025
Limite: SEM LIMITE
"""
import pandas as pd
import time
from script5_utils import (
    get_headers, safe_request, get_user_info, is_date_in_range,
    collect_paginated_data, save_results, SLEEP_TIME
)


def collect_forks(repo_full_name, repo_name, edges, nodes):
    """Coleta todos os forks de um repositório"""
    print(f'  🔀 Coletando Forks (sem limite)...')
    forks = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/forks')
    
    # Filtra forks por data de criação
    forks_filtered = [f for f in forks if is_date_in_range(f.get('created_at', ''))]
    print(f'     Encontrados {len(forks)} forks (após filtro 2020-2025: {len(forks_filtered)})')
    
    for fork in forks_filtered:
        login = fork['owner']['login']
        fork_date = fork['created_at']
        
        nodes[login] = get_user_info(login)
        edges.append({
            'repo_name': repo_name,
            'source': login,
            'target': repo_name,
            'interaction_type': 'fork',
            'date': fork_date,
            'pr_or_issue_number': ''
        })


# Execução principal
if __name__ == '__main__':
    print('🚀 Script 5/6: Coletando Forks (2020-2025, sem limite)\n')
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
        
        collect_forks(repo_full_name, repo_name, edges, nodes)
        
        repo_elapsed = time.time() - repo_start
        print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
        
        # Backup parcial a cada 2 repos
        if idx % 2 == 0 and idx > 0:
            save_results(edges, nodes, 'forks_partial')
    
    # Salva resultados finais
    save_results(edges, nodes, 'forks')
    
    total_elapsed = time.time() - start_time
    print(f'\n✅ Coleta de Forks finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
