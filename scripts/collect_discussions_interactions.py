"""
Script 4/6: Coleta de GitHub Discussions
Coleta: Discussões e seus comentários com @mentions
Período: 2020-2025
Limite: SEM LIMITE
"""
import pandas as pd
import time
import requests
from social_interactions_utils import (
    get_headers, get_user_info, is_date_in_range,
    extract_mentions, save_results, SLEEP_TIME
)


def collect_discussion_interactions(repo_full_name, repo_name, edges, nodes):
    """Coleta todas as interações de discussions de um repositório"""
    print(f'  💭 Coletando Discussions (sem limite)...')
    
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
            body
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
    discussions_filtered = 0
    
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
            
            total_discussions += len(discussions)
            
            for discussion in discussions:
                if not discussion or not discussion.get('author'):
                    continue
                
                disc_date = discussion.get('createdAt', '')
                if not is_date_in_range(disc_date):
                    continue
                
                discussions_filtered += 1
                disc_number = discussion.get('number', '')
                disc_author = discussion['author']['login']
                disc_body = discussion.get('body', '')
                
                nodes[disc_author] = get_user_info(disc_author)
                edges.append({
                    'repo_name': repo_name,
                    'source': disc_author,
                    'target': disc_author,
                    'interaction_type': 'discussion_started',
                    'date': disc_date,
                    'pr_or_issue_number': disc_number
                })
                
                # Mentions no corpo da discussion
                mentions = extract_mentions(disc_body)
                for mentioned in mentions:
                    if mentioned != disc_author:
                        nodes[mentioned] = get_user_info(mentioned)
                        edges.append({
                            'repo_name': repo_name,
                            'source': disc_author,
                            'target': mentioned,
                            'interaction_type': 'mention',
                            'date': disc_date,
                            'pr_or_issue_number': disc_number
                        })
                
                # Comentários da discussion
                comments = discussion.get('comments', {}).get('nodes', [])
                for comment in comments:
                    if not comment or not comment.get('author'):
                        continue
                    
                    comment_date = comment.get('createdAt', '')
                    if not is_date_in_range(comment_date):
                        continue
                    
                    commenter = comment['author']['login']
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
                    
                    # Mentions nos comentários
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
            
            # Paginação
            page_info = discussions_data.get('pageInfo', {})
            has_next = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor')
            
            time.sleep(SLEEP_TIME)
            
        except Exception as e:
            print(f'     ⚠️  Erro ao processar discussions: {e}')
            break
    
    print(f'     Encontradas {total_discussions} discussions (após filtro 2020-2025: {discussions_filtered})')


# Execução principal
if __name__ == '__main__':
    print('🚀 Script 6/6: Coletando Discussions (2020-2025, sem limite)\n')
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
        
        collect_discussion_interactions(repo_full_name, repo_name, edges, nodes)
        
        repo_elapsed = time.time() - repo_start
        print(f'  ✅ Concluído em {repo_elapsed:.1f}s ({len(edges)} edges totais, {len(nodes)} nodes totais)')
        
        # Backup parcial a cada 2 repos
        if idx % 2 == 0 and idx > 0:
            save_results(edges, nodes, 'discussions_partial')
    
    # Salva resultados finais
    save_results(edges, nodes, 'discussions')
    
    total_elapsed = time.time() - start_time
    print(f'\n✅ Coleta de Discussions finalizada em {total_elapsed/60:.1f} minutos!')
    print(f'📊 Total: {len(edges)} edges, {len(nodes)} nodes')
