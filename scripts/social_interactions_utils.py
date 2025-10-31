"""
Módulo com funções compartilhadas para coleta de dados do GitHub
"""
import requests
import pandas as pd
import time
import re
from threading import Lock
from datetime import datetime
from token_loader import load_github_tokens

# Tokens do GitHub
TOKENS = load_github_tokens()

token_idx = 0
token_lock = Lock()
SLEEP_TIME = 0.05

# Período de coleta
START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2025, 12, 31)

# Carrega dados de países uma única vez
countries_df = None
try:
    countries_df = pd.read_csv('users_countries.csv')
    print(f'✅ Carregados dados de {len(countries_df)} usuários com países')
except Exception as e:
    print(f'⚠️  Não foi possível carregar users_countries.csv: {e}')


def get_headers():
    """Retorna headers com rotação de tokens"""
    global token_idx
    with token_lock:
        headers = {'Authorization': f'token {TOKENS[token_idx]}'}
        token_idx = (token_idx + 1) % len(TOKENS)
        return headers


def safe_request(url):
    """Faz requisição com retry automático"""
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


def is_date_in_range(date_str):
    """Verifica se a data está entre 2020-2025"""
    if not date_str:
        return False
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return START_DATE <= date <= END_DATE
    except:
        return False


def extract_mentions(text):
    """Extrai @mentions de textos"""
    if not text:
        return []
    mentions = re.findall(r'@([a-zA-Z0-9-]+)', text)
    return list(set(mentions))


def get_user_info(login):
    """Retorna informações do usuário (país do CSV + followers da API)"""
    info = {
        'login': login,
        'profile_url': f'https://github.com/{login}',
        'country': '',
        'followers': 0
    }
    
    # Busca país no CSV
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


def collect_paginated_data(base_url, max_pages=None):
    """Coleta dados paginados sem limite (se max_pages=None)"""
    all_data = []
    page = 1
    
    while True:
        if max_pages and page > max_pages:
            break
            
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


def save_results(edges, nodes, output_prefix):
    """Salva edges e nodes em CSV"""
    pd.DataFrame(edges).to_csv(f'{output_prefix}_edges.csv', index=False)
    pd.DataFrame(list(nodes.values())).to_csv(f'{output_prefix}_nodes.csv', index=False)
    print(f'💾 Salvos {len(edges)} edges e {len(nodes)} nodes em {output_prefix}_*.csv')
