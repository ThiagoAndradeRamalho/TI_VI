"""
Script 4/6: Coleta de Stars
Coleta: Usuários que deram star nos repositórios
Período: 2020-2025
Limite: SEM LIMITE
Nota: A API do GitHub não fornece a data exata do star, então coletamos todos
"""
import pandas as pd
import time
import requests
from script5_utils import (
    get_headers, safe_request, get_user_info, is_date_in_range,
    collect_paginated_data, save_results, SLEEP_TIME
)


def collect_stars(repo_full_name, repo_name, edges, nodes):
    """Coleta todos os stars de um repositório"""
    print(f'  ⭐ Coletando Stars (sem limite)...')
    
    # A API do GitHub tem um endpoint especial para obter stars com timestamp
    # usando Accept: application/vnd.github.v3.star+json
    all_stargazers = []
    page = 1
    
    while True:
        url = f'https://api.github.com/repos/{repo_full_name}/stargazers?per_page=100&page={page}'
        headers = get_headers()
        headers['Accept'] = 'application/vnd.github.v3.star+json'
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
                
            data = r.json()
            if not data or not isinstance(data, list):
                break
                
            all_stargazers.extend(data)
            
            if len(data) < 100:
                break
                
            page += 1
            time.sleep(SLEEP_TIME)
        except Exception as e:
            print(f'⚠️  Erro ao coletar stars: {e}')
            break
    
    # Filtra por data
    stargazers_filtered = []
    for star in all_stargazers:
        star_date = star.get('starred_at', '')
        if is_date_in_range(star_date):
            stargazers_filtered.append(star)
    
    print(f'     Encontrados {len(all_stargazers)} stars (após filtro 2020-2025: {len(stargazers_filtered)})')
    
    for star in stargazers_filtered:
        user = star.get('user')
        if not user:
            continue
            
        login = user['login']
        star_date = star.get('starred_at', '')
        
        nodes[login] = get_user_info(login)
        edges.append({
            'repo_name': repo_name,
            'source': login,
            'target': repo_name,
            'interaction_type': 'star',
            'date': star_date,
            'pr_or_issue_number': ''
        })


# Execução principal
if __name__ == '__main__':
    print('🚀 Script 4/6: Coletando Stars (2020-2025, sem limite)\n')
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
        
        collect_stars(repo_full_name, repo_name, edges, nodes)
        
        repo_elapsed = time.time() - repo_start
        print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
        
        # Backup parcial a cada 2 repos
        if idx % 2 == 0 and idx > 0:
            save_results(edges, nodes, 'stars_partial')
    
    # Salva resultados finais
    save_results(edges, nodes, 'stars')
    
    total_elapsed = time.time() - start_time
    print(f'\n✅ Coleta de Stars finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
