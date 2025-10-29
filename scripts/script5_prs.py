"""
Script 1/6: Coleta de Pull Requests (PRs)
Coleta: PRs, reviews e comentários de PRs
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


def collect_pr_details(repo_full_name, repo_name, pr_number, pr_author, edges, nodes):
    """Coleta reviews e comentários de um PR específico"""
    # Reviews
    url_reviews = f'https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews'
    r_reviews = safe_request(url_reviews)
    if r_reviews and r_reviews.status_code == 200:
        for review in r_reviews.json():
            if not review.get('user') or not review['user']:
                continue
            
            review_date = review.get('submitted_at', '')
            if not is_date_in_range(review_date):
                continue
                
            reviewer = review['user']['login']
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
            
            # Mentions no review
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
                'target': pr_author,
                'interaction_type': 'pr_comment',
                'date': comment_date,
                'pr_or_issue_number': pr_number
            })
            
            # Mentions no comentário
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


def collect_pr_interactions(repo_full_name, repo_name, edges, nodes):
    """Coleta todas as interações de PRs de um repositório"""
    print(f'  📋 Coletando PRs (sem limite)...')
    prs = collect_paginated_data(f'https://api.github.com/repos/{repo_full_name}/pulls?state=all')
    
    # Filtra PRs por data
    prs_filtered = [pr for pr in prs if pr.get('user') and pr['user'] and is_date_in_range(pr.get('created_at', ''))]
    print(f'     Encontrados {len(prs)} PRs (após filtro 2020-2025: {len(prs_filtered)})')
    
    for pr in prs_filtered:
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
        
        # Mentions no corpo do PR
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
    
    # Coleta reviews e comentários em paralelo
    print(f'  💬 Coletando reviews e comentários dos PRs...')
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for pr in prs_filtered:
            pr_number = pr['number']
            pr_author = pr['user']['login']
            futures.append(executor.submit(collect_pr_details, repo_full_name, repo_name, pr_number, pr_author, edges, nodes))
        
        for future in as_completed(futures):
            future.result()


# Execução principal
if __name__ == '__main__':
    print('🚀 Script 1/6: Coletando Pull Requests (2020-2025, sem limite)\n')
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
        
        collect_pr_interactions(repo_full_name, repo_name, edges, nodes)
        
        repo_elapsed = time.time() - repo_start
        print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
        
        # Backup parcial a cada 2 repos
        if idx % 2 == 0 and idx > 0:
            save_results(edges, nodes, 'prs_partial')
    
    # Salva resultados finais
    save_results(edges, nodes, 'prs')
    
    total_elapsed = time.time() - start_time
    print(f'\n✅ Coleta de PRs finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
