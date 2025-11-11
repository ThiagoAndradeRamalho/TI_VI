"""
Script de coleta de métricas de repositórios do GitHub.

Este script lê uma lista de URLs de repositórios do arquivo 'repos_final.csv'
e coleta métricas detalhadas de cada repositório através da API do GitHub, incluindo:
- Informações básicas (nome, owner, descrição, topics, estrelas, forks)
- Estatísticas de PRs (abertos, merged, tempo médio de merge)
- Commits, contribuidores, releases
- Dias ativos e tempo médio de primeira resposta em issues

Resultado: Gera o arquivo 'repos_metrics.csv' com todas as métricas coletadas.
"""

import requests
import csv
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from token_loader import load_github_tokens

TOKENS = load_github_tokens()
# Reduzindo workers para ser mais gentil com a API
NUM_WORKERS = min(len(TOKENS) * 2, 10) if TOKENS else 1  # Max 10 workers

def get_headers(token):
 return {'Authorization': f'token {token}'}

def round_robin_tokens():
 while True:
     for token in TOKENS:
         yield token

token_gen = round_robin_tokens()

def safe_request(url, params=None, max_retries=3):
 for attempt in range(max_retries):
     for _ in range(len(TOKENS)):
         token = next(token_gen)
         headers = get_headers(token)
         try:
             # Timeout progressivo: 30s, 60s, 90s
             timeout = 30 + (attempt * 30)
             r = requests.get(url, headers=headers, params=params, timeout=timeout)
             
             # Monitora rate limit proativamente
             remaining = int(r.headers.get('X-RateLimit-Remaining', 1000))
             reset_time = int(r.headers.get('X-RateLimit-Reset', time.time() + 3600))
             
             # Se está próximo do limite, adiciona delay
             if remaining < 100:
                 wait_time = max(1, (101 - remaining) * 0.1)  # 0.1s por request restante
                 print(f"⏳ Rate limit baixo ({remaining}), aguardando {wait_time:.1f}s...")
                 time.sleep(wait_time)
             
             if r.status_code == 403 and 'rate limit' in r.text.lower():
                 wait_until = reset_time - time.time()
                 if wait_until > 0:
                     print(f"⏰ Rate limit atingido, aguardando {wait_until:.0f}s...")
                     time.sleep(min(wait_until + 5, 300))  # Max 5 min
                 continue  # Tenta o próximo token
             
             if r.status_code == 500:
                 print(f"⚠️  Erro 500 em {url} (tentativa {attempt + 1}/{max_retries})")
                 if attempt < max_retries - 1:
                     time.sleep(5 + (attempt * 5))  # 5s, 10s, 15s
                     break  # Sai do loop de tokens para tentar novamente
                 return None
             
             if r.status_code in [403, 404]:
                 print(f"Erro {r.status_code} em {url}")
                 return None  # Não retry para 403/404
             
             r.raise_for_status()
             return r
             
         except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
             print(f"⏱️  Timeout em {url} (tentativa {attempt + 1}/{max_retries})")
             if attempt < max_retries - 1:
                 time.sleep(2 + (attempt * 3))  # 2s, 5s, 8s
                 break  # Tenta novamente
             return None
             
         except requests.exceptions.RequestException as e:
             print(f"🔌 Erro de conexão em {url}: {e}")
             if attempt < max_retries - 1:
                 time.sleep(1 + attempt)  # 1s, 2s, 3s
                 continue  # Tenta próximo token
             
     # Se chegou aqui, todos os tokens falharam nesta tentativa
     if attempt < max_retries - 1:
         wait_time = 10 + (attempt * 10)  # 10s, 20s, 30s
         print(f"⏳ Aguardando {wait_time}s antes de tentar novamente...")
         time.sleep(wait_time)
 
 print(f"❌ Falha definitiva após {max_retries} tentativas: {url}")
 return None

def get_prs_stats(owner, repo):
 prs_opened = prs_merged = 0
 time_to_merge = []
 page = 1
 
 print(f"   📊 Coletando PRs de {owner}/{repo}...")
 while True:  # Sem limitação - pega todos os PRs
     url = f'https://api.github.com/repos/{owner}/{repo}/pulls'
     params = {'state': 'all', 'per_page': 100, 'page': page}
     r = safe_request(url, params)
     if r is None:
         # Erro na requisição (403, 404, 500)
         print(f"⚠️  Interrompendo coleta de PRs para {owner}/{repo} na página {page}")
         break
     
     try:
         prs = r.json()
         if not prs or 'message' in prs:
             break
         
         for pr in prs:
             prs_opened += 1
             if pr.get('merged_at'):
                 prs_merged += 1
                 created = pr['created_at']
                 merged = pr['merged_at']
                 dt_created = datetime.strptime(created, '%Y-%m-%dT%H:%M:%SZ')
                 dt_merged = datetime.strptime(merged, '%Y-%m-%dT%H:%M:%SZ')
                 time_to_merge.append((dt_merged - dt_created).total_seconds() / 3600)
         
         if len(prs) < 100:
             break
         page += 1
         
         # Progresso e throttling inteligente
         if page % 10 == 0:
             print(f"   📊 {owner}/{repo}: {page * 100} PRs processados...")
         
         # Pequeno delay entre páginas para ser gentil com a API
         time.sleep(0.1)
             
     except Exception as e:
         print(f"Erro ao processar PRs de {owner}/{repo}: {e}")
         break
 
 print(f"   ✅ {owner}/{repo}: Total de {prs_opened} PRs coletados")
 avg_time_to_merge = round(sum(time_to_merge)/len(time_to_merge), 2) if time_to_merge else 'N/A'
 return prs_opened, prs_merged, avg_time_to_merge

def get_commits_count(owner, repo):
 url = f'https://api.github.com/repos/{owner}/{repo}/commits?per_page=1'
 r = safe_request(url)
 if r is None:
     return 'N/A'
 try:
     if 'Link' in r.headers:
         last_link = [l for l in r.headers['Link'].split(',') if 'rel="last"' in l]
         if last_link:
             last_url = last_link[0].split(';')[0].strip()[1:-1]
             count = int(last_url.split('page=')[1].split('&')[0])
             return count
     return len(r.json())
 except Exception as e:
     print(f"Erro ao processar commits para {owner}/{repo}: {e}")
     return 'N/A'

def get_contributors_count(owner, repo):
 url = f'https://api.github.com/repos/{owner}/{repo}/contributors?per_page=1&anon=true'
 r = safe_request(url)
 if r is None:
     return 'N/A'
 try:
     if 'Link' in r.headers:
         last_link = [l for l in r.headers['Link'].split(',') if 'rel="last"' in l]
         if last_link:
             last_url = last_link[0].split(';')[0].strip()[1:-1]
             count = int(last_url.split('page=')[1].split('&')[0])
             return count
     return len(r.json())
 except Exception as e:
     print(f"Erro ao processar contributors para {owner}/{repo}: {e}")
     return 'N/A'

def get_release_count(owner, repo):
 url = f'https://api.github.com/repos/{owner}/{repo}/releases?per_page=1'
 r = safe_request(url)
 if r is None:
     return 'N/A'
 try:
     if 'Link' in r.headers:
         last_link = [l for l in r.headers['Link'].split(',') if 'rel="last"' in l]
         if last_link:
             last_url = last_link[0].split(';')[0].strip()[1:-1]
             count = int(last_url.split('page=')[1].split('&')[0])
             return count
     return len(r.json())
 except Exception as e:
     print(f"Erro ao processar releases para {owner}/{repo}: {e}")
     return 'N/A'

def get_active_days(owner, repo):
 url = f'https://api.github.com/repos/{owner}/{repo}/commits?per_page=100'
 days = set()
 page = 1
 
 print(f"   📅 Coletando commits de {owner}/{repo}...")
 while True:  # Sem limitação - pega todos os commits
     r = safe_request(url + f"&page={page}")
     if r is None:
         print(f"⚠️  Interrompendo coleta de commits para {owner}/{repo} na página {page}")
         break
     try:
         data = r.json()
         if not data or 'message' in data:
             break
         for commit in data:
             date = commit['commit']['author']['date'][:10]
             days.add(date)
         if len(data) < 100:
             break
         page += 1
         
         # Progresso e throttling inteligente
         if page % 20 == 0:
             print(f"   📅 {owner}/{repo}: {page * 100} commits processados...")
         
         # Pequeno delay entre páginas
         time.sleep(0.05)
             
     except Exception as e:
         print(f"Erro ao processar commits de {owner}/{repo}: {e}")
         break
 
 print(f"   ✅ {owner}/{repo}: {len(days)} dias ativos encontrados")
 return len(days)

def get_time_to_first_response(owner, repo):
 times = []
 page = 1
 
 print(f"   💬 Coletando issues de {owner}/{repo}...")
 while True:  # Pega todas as páginas de issues
     url = f'https://api.github.com/repos/{owner}/{repo}/issues?state=all&per_page=100&page={page}'
     r = safe_request(url)
     if r is None:
         print(f"⚠️  Interrompendo coleta de issues para {owner}/{repo} na página {page}")
         break
     
     try:
         issues = r.json()
         if not issues or 'message' in issues:
             break
             
         for issue in issues:
             if issue.get('comments', 0) > 0:
                 created = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                 comments_url = issue['comments_url']
                 rc = safe_request(comments_url)
                 if rc is None:
                     continue
                 comments = rc.json()
                 if comments:
                     first_comment = datetime.strptime(comments[0]['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                     times.append((first_comment - created).total_seconds() / 3600)
         
         # Se retornou menos que 100 issues, chegou ao fim
         if len(issues) < 100:
             break
         page += 1
         
         # Progresso e throttling inteligente
         if page % 10 == 0:
             print(f"   💬 {owner}/{repo}: {page * 100} issues processadas...")
         
         # Pequeno delay entre páginas
         time.sleep(0.1)
         
     except Exception as e:
         print(f"Erro ao processar tempo de resposta para {owner}/{repo}: {e}")
         break
 
 print(f"   ✅ {owner}/{repo}: {len(times)} issues com comentários analisadas")
 avg_time = round(sum(times)/len(times), 2) if times else 'N/A'
 return avg_time

def process_repo_from_url(repo_url):
 # repo_url formato: https://github.com/owner/repo
 try:
     parts = repo_url.rstrip('/').split('/')
     owner = parts[-2]
     name = parts[-1]
 except Exception as e:
     print(f"URL inválida: {repo_url}")
     return None

 # Buscar info básica do repositório
 repo_api_url = f'https://api.github.com/repos/{owner}/{name}'
 try:
     r = safe_request(repo_api_url)
     if r is None:
         print(f"Erro ao acessar repositório {owner}/{name}: Não disponível")
         return None
     repo = r.json()
 except Exception as e:
     print(f"Erro ao buscar info básica de {owner}/{name}: {e}")
     return None

 description = (repo.get('description') or '').replace('\n', ' ').replace('\r', ' ')
 print(f"Coletando: {owner}/{name}")
 try:
     prs_opened, prs_merged, avg_time_to_merge = get_prs_stats(owner, name)
     commits_count = get_commits_count(owner, name)
     contributors_count = get_contributors_count(owner, name)
     release_count = get_release_count(owner, name)
     active_days = get_active_days(owner, name)
     time_to_first_response = get_time_to_first_response(owner, name)
 except Exception as e:
     print(f"Erro em {owner}/{name}: {e}")
     prs_opened = prs_merged = avg_time_to_merge = commits_count = contributors_count = release_count = active_days = time_to_first_response = 'N/A'
 return [
     name, owner, repo.get('full_name', ''), repo_url, description, repo.get('created_at', ''), repo.get('updated_at', ''),
     ','.join(repo.get('topics', [])),
     repo.get('stargazers_count', ''), repo.get('forks_count', ''),
     prs_opened, prs_merged, commits_count, contributors_count, active_days,
     time_to_first_response, avg_time_to_merge, release_count
 ]

def main():
 # Lê o CSV recebido
 input_csv = 'scripts/csv/repos_final.csv'
 repos_urls = []
 with open(input_csv, newline='', encoding='utf-8') as f:
     reader = csv.DictReader(f)
     for row in reader:
         repo_url = row['repo_url']
         repos_urls.append(repo_url)

 print(f"Total de repositórios para processar: {len(repos_urls)}")
 
 # Prepara o arquivo de saída
 output_file = 'scripts/csv/repos_metrics.csv'
 header = [
     'repo_name', 'repo_owner', 'full_name', 'repo_url', 'description', 'created_at', 'updated_at', 'topics',
     'stars_count', 'forks_count',
     'prs_opened_count', 'prs_merged_count', 'commits_count', 'contributors_count', 'active_days',
     'time_to_first_response', 'time_to_merge', 'release_count'
 ]
 
 try:
     with open(output_file, 'x', newline='', encoding='utf-8') as f:
         writer = csv.writer(f)
         writer.writerow(header)
 except FileExistsError:
     print("Arquivo já existe, continuando...")
 
 # Processa em lotes de 10
 batch_size = 10
 results_buffer = []
 processed_count = 0
 
 with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
     futures = [executor.submit(process_repo_from_url, repo_url) for repo_url in repos_urls]
     
     try:
         for future in as_completed(futures):
             result = future.result()
             if result:
                 results_buffer.append(result)
                 processed_count += 1
                 
                 # Salva a cada 10 repositórios
                 if len(results_buffer) >= batch_size:
                     with open(output_file, 'a', newline='', encoding='utf-8') as f:
                         writer = csv.writer(f)
                         writer.writerows(results_buffer)
                     print(f"✅ Salvos {len(results_buffer)} repositórios ({processed_count}/{len(repos_urls)})")
                     results_buffer = []
         
         if results_buffer:
             with open(output_file, 'a', newline='', encoding='utf-8') as f:
                 writer = csv.writer(f)
                 writer.writerows(results_buffer)
             print(f"✅ Salvos {len(results_buffer)} repositórios finais ({processed_count}/{len(repos_urls)})")
     
     except KeyboardInterrupt:
         print("\n⚠️  Interrupção detectada! Salvando dados coletados até agora...")
         if results_buffer:
             with open(output_file, 'a', newline='', encoding='utf-8') as f:
                 writer = csv.writer(f)
                 writer.writerows(results_buffer)
             print(f"✅ Salvos {len(results_buffer)} repositórios antes da interrupção")
         print(f"Total processado: {processed_count}/{len(repos_urls)}")
         return
 
 print(f"\n🎉 Concluído! Total processado: {processed_count}/{len(repos_urls)}")

if __name__ == '__main__':
 main()
