"""
Script de seleção de repositórios populares do GitHub por país.

Este script busca os 1500 repositórios mais populares do GitHub (por estrelas) e para cada
repositório identifica o primeiro contribuidor que pertence a um dos países-alvo
(Brasil, Índia, Alemanha ou Estados Unidos). A identificação é feita através da localização
informada no perfil do GitHub de cada contribuidor.

Resultado: Gera o arquivo 'repos_final.csv' contendo os repositórios
selecionados e o primeiro usuário de cada país-alvo encontrado como contribuidor.
"""

import requests
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pycountry
from unidecode import unidecode
from token_loader import load_github_tokens

TOKENS = load_github_tokens()
NUM_WORKERS = len(TOKENS) * 8 if TOKENS else 1


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
                r = requests.get(url, headers=headers, params=params, timeout=30)
                if r.status_code == 403 and 'rate limit' in r.text.lower():
                    continue
                if r.status_code == 404:
                    # Usuário não encontrado (bots, contas deletadas, etc)
                    return None
                r.raise_for_status()
                return r
            except requests.exceptions.HTTPError as e:
                # Trata erros HTTP (404, 403, etc)
                if e.response.status_code == 404:
                    return None
                print(f"Erro HTTP (tentativa {attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
                continue
            except (requests.exceptions.SSLError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                print(f"Erro de conexão (tentativa {attempt + 1}/{max_retries}): {e}")
                time.sleep(5)
                continue
        time.sleep(60)
    return None


def fetch_top_repos():
    """
    Busca os top 1500 repositórios do GitHub.
    Como a API limita a 1000 resultados por query, fazemos múltiplas queries
    com diferentes faixas de estrelas.
    """
    url = 'https://api.github.com/search/repositories'
    repos = []
    
    # Estratégia: dividir em faixas de estrelas para evitar o limite de 1000 resultados
    # Primeira query: top 1000 (páginas 1-10)
    print("Buscando top 1000 repositórios...")
    for page in range(1, 11):  # páginas 1-10 = 1000 repos
        params = {
            'q': 'stars:>0',
            'sort': 'stars',
            'order': 'desc',
            'per_page': 100,
            'page': page
        }
        print(f"  Buscando página {page}/10...")
        r = safe_request(url, params)
        if r is None:
            print(f"  Erro ao buscar página {page}.")
            break
        data = r.json()
        if 'items' not in data:
            break
        repos.extend(data['items'])
        if len(data['items']) < 100:
            break
    
    print(f"Coletados {len(repos)} repositórios na primeira query.")
    
    # Se conseguimos os 1000, pegamos o número de estrelas do último para usar como limite superior
    if len(repos) >= 1000:
        min_stars = repos[-1]['stargazers_count']
        print(f"Buscando mais 500 repositórios com até {min_stars} estrelas...")
        
        # Segunda query: próximos 500 com estrelas <= ao último da primeira query
        for page in range(1, 6):  # páginas 1-5 = 500 repos
            params = {
                'q': f'stars:<{min_stars}',
                'sort': 'stars',
                'order': 'desc',
                'per_page': 100,
                'page': page
            }
            print(f"  Buscando página {page}/5...")
            r = safe_request(url, params)
            if r is None:
                print(f"  Erro ao buscar página {page}.")
                break
            data = r.json()
            if 'items' not in data:
                break
            repos.extend(data['items'])
            if len(data['items']) < 100:
                break
    
    print(f"Total de repositórios encontrados: {len(repos)}")
    return repos


def fetch_contributors(owner, repo):
    contributors = []
    page = 1
    while True:
        url = f'https://api.github.com/repos/{owner}/{repo}/contributors'
        params = {'per_page': 100, 'page': page}
        r = safe_request(url, params)
        if r is None:
            break
        data = r.json()
        if not data or 'message' in data:
            break
        for user in data:
            if 'login' in user:
                contributors.append(user['login'])
        if len(data) < 100:
            break
        page += 1
    return contributors


def fetch_user(login):
    url = f'https://api.github.com/users/{login}'
    r = safe_request(url)
    if r is None:
        return login, '', ''
    data = r.json()
    location = data.get('location', '') or ''
    profile_url = data.get('html_url', '')
    return login, profile_url, location


# Países
country_names = {unidecode(c.name.lower()): c.name for c in pycountry.countries}
country_alpha2 = {c.alpha_2.lower(): c.name for c in pycountry.countries}
country_alpha3 = {c.alpha_3.lower(): c.name for c in pycountry.countries}
country_official = {unidecode(getattr(c, 'official_name', '').lower()): c.name for c in pycountry.countries if hasattr(c, 'official_name')}
country_all = {**country_names, **country_alpha2, **country_alpha3, **country_official}

# Principais cidades e estados dos 4 países
state_city_country = {
# Brasil
'sp': 'Brazil', 'sao paulo': 'Brazil', 'rj': 'Brazil', 'rio de janeiro': 'Brazil', 'mg': 'Brazil', 'minas gerais': 'Brazil',
'bh': 'Brazil', 'belo horizonte': 'Brazil',
'rs': 'Brazil', 'rio grande do sul': 'Brazil', 'pr': 'Brazil', 'parana': 'Brazil', 'sc': 'Brazil', 'santa catarina': 'Brazil',
'ba': 'Brazil', 'bahia': 'Brazil', 'ce': 'Brazil', 'ceara': 'Brazil', 'pe': 'Brazil', 'pernambuco': 'Brazil',
'recife': 'Brazil', 'porto alegre': 'Brazil', 'curitiba': 'Brazil', 'salvador': 'Brazil', 'fortaleza': 'Brazil',
'brasilia': 'Brazil', 'campo grande': 'Brazil', 'natal': 'Brazil', 'campinas': 'Brazil', 'sao jose do rio preto': 'Brazil',
'bauru': 'Brazil', 'maringa': 'Brazil', 'dourados': 'Brazil', 'teresina': 'Brazil', 'florianopolis': 'Brazil',
# Índia
'delhi': 'India', 'new delhi': 'India', 'mumbai': 'India', 'maharashtra': 'India', 'bangalore': 'India', 'karnataka': 'India',
'chennai': 'India', 'tamil nadu': 'India', 'kolkata': 'India', 'west bengal': 'India', 'hyderabad': 'India', 'telangana': 'India',
'bengaluru': 'India', 'pune': 'India', 'ahmedabad': 'India', 'gujarat': 'India', 'kochi': 'India', 'kerala': 'India',
'noida': 'India', 'gurgaon': 'India', 'chandigarh': 'India', 'indore': 'India', 'nagpur': 'India', 'dehradun': 'India',
'mysore': 'India', 'kottayam': 'India', 'nanded': 'India', 'mangalore': 'India', 'bhopal': 'India', 'gandhinagar': 'India',
# Alemanha
'berlin': 'Germany', 'hamburg': 'Germany', 'munich': 'Germany', 'bavaria': 'Germany', 'frankfurt': 'Germany', 'hesse': 'Germany',
'stuttgart': 'Germany', 'baden-wurttemberg': 'Germany', 'dusseldorf': 'Germany', 'north rhine-westphalia': 'Germany',
'cologne': 'Germany', 'dresden': 'Germany', 'hannover': 'Germany', 'leipzig': 'Germany', 'darmstadt': 'Germany',
'karlsruhe': 'Germany', 'augsburg': 'Germany', 'magdeburg': 'Germany', 'muhltal': 'Germany', 'aachen': 'Germany',
'bonn': 'Germany', 'castrop-rauxel': 'Germany', 'deutschland': 'Germany', 'neustadt': 'Germany',
# Estados Unidos
'ny': 'United States', 'new york': 'United States', 'ca': 'United States', 'california': 'United States',
'tx': 'United States', 'texas': 'United States', 'fl': 'United States', 'florida': 'United States',
'il': 'United States', 'illinois': 'United States', 'wa': 'United States', 'washington': 'United States',
'los angeles': 'United States', 'san francisco': 'United States', 'chicago': 'United States', 'houston': 'United States',
'boston': 'United States', 'atlanta': 'United States', 'seattle': 'United States', 'miami': 'United States',
'dallas': 'United States', 'austin': 'United States', 'san diego': 'United States', 'philadelphia': 'United States',
'portland': 'United States', 'denver': 'United States', 'phoenix': 'United States', 'minneapolis': 'United States',
'oakland': 'United States', 'brooklyn': 'United States', 'manhattan': 'United States', 'bay area': 'United States',
'silicon valley': 'United States', 'palo alto': 'United States', 'mountain view': 'United States', 'sunnyvale': 'United States',
'san jose': 'United States', 'redmond': 'United States', 'menlo park': 'United States', 'berkeley': 'United States',
'pittsburgh': 'United States', 'cleveland': 'United States', 'detroit': 'United States', 'baltimore': 'United States',
}

country_aliases = {
'中国': 'China', '中國': 'China', 'china': 'China',
'shanghai': 'China', 'beijing': 'China', 'bei jing': 'China', 'wuhan': 'China', 'wu han': 'China',
'shenzhen': 'China', 'guangzhou': 'China', 'chengdu': 'China', 'tianjin': 'China', 'hangzhou': 'China',
'mainland china': 'China', 'hong kong': 'Hong Kong', 'hk': 'Hong Kong', 'taipei': 'Taiwan', 'tapipei': 'Taiwan',
'taiwan': 'Taiwan', '台灣': 'Taiwan', '臺灣': 'Taiwan',
'deutschland': 'Germany', 'germany': 'Germany',
'nederland': 'Netherlands', 'holland': 'Netherlands',
'belgië': 'Belgium', 'belgique': 'Belgium', 'belgien': 'Belgium', 'belgium': 'Belgium',
'россия': 'Russia', 'russia': 'Russia',
'україна': 'Ukraine', 'ukraine': 'Ukraine',
'sverige': 'Sweden', 'sweden': 'Sweden',
'日本': 'Japan', 'nippon': 'Japan', 'japan': 'Japan', 'tokyo': 'Japan',
'usa': 'United States', 'us': 'United States', 'united states': 'United States', 'united states of america': 'United States',
'brasil': 'Brazil', 'brazil': 'Brazil',
'france': 'France', 'francia': 'France', 'frança': 'France', 'paris': 'France',
'england': 'United Kingdom', 'uk': 'United Kingdom', 'united kingdom': 'United Kingdom', 'london': 'United Kingdom',
'turkey': 'Turkey', 'türkiye': 'Turkey', 'turkiye': 'Turkey',
'canada': 'Canada', 'montreal': 'Canada', 'toronto': 'Canada', 'vancouver': 'Canada', 'ottawa': 'Canada',
'portugal': 'Portugal',
'italy': 'Italy', 'italia': 'Italy',
'spain': 'Spain', 'españa': 'Spain', 'barcelona': 'Spain', 'galicia': 'Spain', 'bilbao': 'Spain',
'madrid': 'Spain', 'valencia': 'Spain', 'sevilla': 'Spain', 'zaragoza': 'Spain', 'malaga': 'Spain',
'india': 'India', 'bharat': 'India',
'iceland': 'Iceland', 'reykjavik': 'Iceland', 'reykjavík': 'Iceland',
'poland': 'Poland', 'polska': 'Poland',
'australia': 'Australia',
'netherlands': 'Netherlands', 'amsterdam': 'Netherlands',
'denmark': 'Denmark', 'danmark': 'Denmark',
'norway': 'Norway', 'norge': 'Norway',
'switzerland': 'Switzerland', 'schweiz': 'Switzerland', 'suisse': 'Switzerland', 'svizzera': 'Switzerland',
'armenia': 'Armenia', 'yerevan': 'Armenia',
'greece': 'Greece', 'athens': 'Greece',
'czechoslovakia': 'Czechia', 'prague': 'Czechia',
}

TARGET_COUNTRIES = ['Brazil', 'India', 'Germany', 'United States']

INVALID_LOCATIONS = {
    'earth', 'world', 'internet', 'global', 'remote', 'worldwide', 'cyberspace',
    'milky way', 'universe', 'parallel universe', 'virtual', 'online', 'somewhere',
    'everywhere', 'nowhere', 'localhost', 'home', '127.0.0.1', 'cloud', 'web',
    'matrix', 'metaverse', 'cyber', 'digital', 'planet earth', 'terra', 'mundo',
    'n/a', 'none', 'unknown', 'undefined', 'null', 'secret', 'hidden', 'private',
    'your heart', 'your mind', 'your computer', 'your screen', 'behind you',
    'international', 'multinational', 'pan-european', 'european union', 'eu',
    'asia', 'europe', 'africa', 'south america', 'north america', 'oceania',
    'antarctica', 'arctic', 'atlantic', 'pacific', 'some', 'any', 'all',
    'galaxy', 'solar system', 'space', 'cosmos', 'void', 'limbo', 'purgatory',
    'heaven', 'hell', 'olympus', 'valhalla', 'asgard', 'narnia', 'wonderland',
    'neverland', 'atlantis', 'utopia', 'dystopia', 'middle earth', 'hogwarts',
    'wakanda', 'gotham', 'metropolis', 'pandora', 'tatooine', 'westeros',
    'in the', 'on the', 'at the', 'near the', 'from the', 'to the', 'building',
    'wandering', 'still', 'simulation', 'nomad', 'interstellar', 'dream', 'in a dream',
    'ponyville', 'equestria', 'wonkaville', 'mare tranquillitatis', 'in my room',
    'oasis', 'your dream', 'in your heart', 'javascript', 'typescript', 'python',
    'java', 'c++', 'rust', 'object location', 'bluelovers', 'the place', 'darkness',
    'evm', 'hbo', 'the grid', 'grid', 'now', 'kraftland', 'lenapehoking',
}

# Padrões sarcásticos que invalidam a localização
SARCASTIC_PATTERNS = [';-)', ':)', ':-)', 'kidding', 'just kidding', 'lol', 'haha', 
                      'capital of tango', 'previously', 'tiny town']

# Nomes nativos de regiões que devem ser invalidados
NATIVE_REGION_NAMES = ['lenapehoking']

# Cidades escandinavas conhecidas
SCANDINAVIAN_CITIES = {
    'copenhagen': 'Denmark', 'københavn': 'Denmark',
    'stockholm': 'Sweden',
    'oslo': 'Norway',
    'helsinki': 'Finland',
    'reykjavik': 'Iceland', 'reykjavík': 'Iceland'
}

# Padrões técnicos/programação que invalidam a localização
TECH_PATTERNS = [
    'javascript', 'typescript', 'python', 'java', 'c++', 'rust', 'golang', 'ruby',
    'php', 'html', 'css', 'react', 'vue', 'angular', 'node', 'django', 'flask',
    '127.0.0.1', 'localhost', '/home/', '/usr/', 'http://', 'https://',
    '.com', '.org', '.net', '.io', 'github.com', 'gitlab.com',
]

# Emojis e símbolos que indicam localização inválida
INVALID_PATTERNS = ['🌍', '🌎', '🌏', '🌐', '💻', '🖥️', '⌨️', '🚀', '🛸', '👽', '♥', '❤️', '⮀']


def is_valid_location(location):
    """Verifica se a localização é válida e não é ambígua."""
    if not location or not location.strip():
        return False
    
    loc = location.strip().lower()
    loc_normalized = unidecode(loc)
    
    # Verifica se contém emojis/símbolos inválidos
    for pattern in INVALID_PATTERNS:
        if pattern in location:
            return False
    
    # Verifica se contém padrões técnicos
    for pattern in TECH_PATTERNS:
        if pattern in loc_normalized:
            return False
    
    # Verifica se a localização inteira é um termo inválido
    if loc_normalized in INVALID_LOCATIONS:
        return False
    
    # Verifica se contém termos inválidos (pode ser parte de uma frase)
    words = set(loc_normalized.replace(',', ' ').replace(';', ' ').replace('/', ' ').split())
    if words & INVALID_LOCATIONS:
        return False
    
    # Descarta se contém múltiplas cidades/países separados por "/" ou "⮀"
    # mas permite "City, State" ou "City, Country" normais
    if '/' in location or '⮀' in location:
        separators = ['/', '⮀']
        for sep in separators:
            if sep in location:
                parts = location.split(sep)
                # Se tem mais de 2 partes, provavelmente é múltiplas localizações
                if len(parts) > 2:
                    return False
    
    # Se tem apenas 1-2 caracteres e não é sigla de país conhecida, descarta
    if len(loc_normalized) <= 2 and loc_normalized not in country_alpha2:
        return False
    
    # Descarta endereços IP (formato xxx.xxx.xxx.xxx ou com porta)
    if ':' in loc_normalized and any(c.isdigit() for c in loc_normalized):
        return False
    
    # Descarta caminhos de sistema
    if loc_normalized.startswith('/') or loc_normalized.startswith('\\'):
        return False
    
    return True


def normalize_country_name(country):
    """Normaliza o nome do país retornado por APIs ou aliases."""
    if not country:
        return ''
    ctry = unidecode(country.strip().lower())
    
    # Checa no alias primeiro
    if ctry in country_aliases:
        return country_aliases[ctry]
    
    # Checa por nome oficial, sigla, etc no pycountry
    for c in pycountry.countries:
        if ctry in [
            unidecode(c.name.lower()),
            unidecode(getattr(c, 'official_name', '').lower()),
            unidecode(getattr(c, 'common_name', '').lower()),
            unidecode(getattr(c, 'alpha_2', '').lower()),
            unidecode(getattr(c, 'alpha_3', '').lower())
        ]:
            return c.name
    
    # Checa se é parte de uma string maior (ex: "belgique / belgien / belgium")
    for alias, norm in country_aliases.items():
        if alias in ctry:
            return norm
    
    # Se não encontrou, retorna capitalizado
    return country.capitalize()


def validate_country_match(location, country):
    """
    Valida se o país identificado realmente corresponde à localização.
    Evita falsos positivos onde uma cidade de um país é identificada como outro.
    """
    if not country or not location:
        return False
    
    loc_lower = unidecode(location.lower())
    
    # Lista de cidades chinesas que não devem ser confundidas com outros países
    chinese_cities = ['shanghai', 'beijing', 'bei jing', 'wuhan', 'wu han', 'shenzhen', 
                      'guangzhou', 'chengdu', 'hangzhou', 'tianjin']
    
    # Se detectou China mas a localização tem indicação explícita de China
    if country == 'China':
        china_indicators = ['china', '中国', '中國', 'mainland china', 'prc', 'shanghai', 
                           'beijing', 'wuhan', 'shenzhen']
        if any(ind in loc_lower for ind in china_indicators):
            return True
        # Se não tem indicador de China e não é uma cidade chinesa conhecida, pode ser falso positivo
        if not any(city in loc_lower for city in chinese_cities):
            return False
    
    # Se é Taiwan, valida
    if country == 'Taiwan':
        taiwan_indicators = ['taiwan', '台灣', '臺灣', 'taipei', 'tapipei']
        if any(ind in loc_lower for ind in taiwan_indicators):
            return True
        return False
    
    # Para países-alvo, sempre aceita se for identificado
    if country in TARGET_COUNTRIES:
        return True
    
    # Para outros países, rejeita se houver conflito
    return False


def identify_country(location):
    """
    Identifica o país a partir de uma localização com validações robustas.
    Retorna string vazia se a localização for inválida ou ambígua.
    """
    if not location or not is_valid_location(location):
        return ''
    
    loc = unidecode(location.strip().lower())
    original_location = location.strip()
    
    # VALIDAÇÃO 1: Rejeita localizações sarcásticas ou piadas
    for pattern in SARCASTIC_PATTERNS:
        if pattern in loc:
            return ''
    
    # VALIDAÇÃO 2: Rejeita nomes nativos de regiões
    for native_name in NATIVE_REGION_NAMES:
        if native_name in loc:
            return ''
    
    # VALIDAÇÃO 3: Detecta menções explícitas de "China" no texto
    # Casos como "City of Science which may or may not in China" devem retornar China
    china_patterns = ['in china', 'china.', 'china,', ' china ', 'mainland china', 'prc']
    for pattern in china_patterns:
        if pattern in loc:
            return 'China'
    
    # VALIDAÇÃO 4: Detecta cidades espanholas conhecidas
    spanish_cities = ['bilbao', 'barcelona', 'madrid', 'valencia', 'sevilla', 'zaragoza', 'malaga']
    for city in spanish_cities:
        if city in loc:
            # Verifica se não é uma localização múltipla ambígua
            if '-' in original_location or '/' in original_location:
                # Se tem separador, só retorna Espanha se não mencionar outro país
                parts = original_location.replace('-', '/').split('/')
                country_mentions = []
                for part in parts:
                    part_lower = unidecode(part.strip().lower())
                    if part_lower in country_aliases:
                        country_mentions.append(country_aliases[part_lower])
                # Se mencionou múltiplos países, retorna vazio (ambíguo)
                if len(country_mentions) > 1:
                    return ''
            return 'Spain'
    
    # VALIDAÇÃO 5: Detecta cidades islandesas
    icelandic_cities = ['reykjavik', 'reykjavík']
    for city in icelandic_cities:
        if city in loc:
            # Similar à lógica de cidades espanholas
            if '-' in original_location or '/' in original_location:
                parts = original_location.replace('-', '/').split('/')
                country_mentions = []
                for part in parts:
                    part_lower = unidecode(part.strip().lower())
                    if part_lower in country_aliases:
                        country_mentions.append(country_aliases[part_lower])
                if len(country_mentions) > 1:
                    return ''
            return 'Iceland'
    
    # VALIDAÇÃO 6: Valida endereços chineses completos (Shaanxi Province, China)
    if 'province' in loc and 'china' in loc:
        return 'China'
    if 'district' in loc and 'china' in loc:
        return 'China'
    
    # VALIDAÇÃO 7: Montreal sempre é no Canadá
    if 'montreal' in loc:
        return 'Canada'
    
    # VALIDAÇÃO 8: Detecta cidades escandinavas
    for city, country in SCANDINAVIAN_CITIES.items():
        if city in loc:
            # Se menciona múltiplos países, retorna vazio
            if '-' in original_location or '/' in original_location:
                parts = original_location.replace('-', '/').split('/')
                country_mentions = []
                for part in parts:
                    part_lower = unidecode(part.strip().lower())
                    if part_lower in country_aliases:
                        country_mentions.append(country_aliases[part_lower])
                if len(country_mentions) > 1:
                    return ''
            # Retorna apenas se for país-alvo
            if country in TARGET_COUNTRIES:
                return country
            # Se não é país-alvo, retorna vazio (não nos interessa)
            return ''
    
    # VALIDAÇÃO 9: Remove separadores problemáticos e pega apenas a parte mais relevante
    if '/' in location or '⮀' in location:
        for sep in ['/', '⮀']:
            if sep in location:
                parts = [p.strip() for p in location.split(sep)]
                # Filtra partes vazias ou inválidas
                valid_parts_temp = [p for p in parts if p and is_valid_location(p)]
                if valid_parts_temp:
                    # Tenta a última parte primeiro (geralmente a mais específica)
                    for part in reversed(valid_parts_temp):
                        part_loc = unidecode(part.strip().lower())
                        # Checa se é cidade/país conhecido
                        if part_loc in country_aliases:
                            return country_aliases[part_loc]
                        if part_loc in state_city_country:
                            return state_city_country[part_loc]
                    # Se nenhuma parte foi reconhecida, continua com o fluxo normal
                    location = valid_parts_temp[-1]
                    loc = unidecode(location.strip().lower())
    
    # VALIDAÇÃO 10: Verifica aliases de países primeiro
    if loc in country_aliases:
        return country_aliases[loc]
    
    # VALIDAÇÃO 11: Separa por vírgula (formato comum: "City, Country")
    parts = [p.strip() for p in loc.replace(';', ',').replace('|', ',').split(',') if p.strip()]
    
    # Filtra partes inválidas
    valid_parts = [p for p in parts if is_valid_location(p)]
    if not valid_parts:
        return ''
    
    # VALIDAÇÃO 12: Verifica cada parte nos dicionários (prioriza última parte = país)
    for part in reversed(valid_parts):
        if part in country_aliases:
            return country_aliases[part]
        if part in state_city_country:
            return state_city_country[part]
        if part in country_all:
            return country_all[part]
    
    # VALIDAÇÃO 13: Tenta API Nominatim apenas se tem 2+ partes válidas
    if len(valid_parts) > 1:
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': location, 'format': 'json', 'addressdetails': 1, 'limit': 1},
                headers={'User-Agent': 'github-country-lookup'},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and 'address' in data[0]:
                    addr = data[0]['address']
                    if 'country' in addr:
                        country_found = addr['country']
                        # Normaliza e valida se está nos países-alvo
                        normalized = normalize_country_name(country_found)
                        if normalized in TARGET_COUNTRIES:
                            return normalized
        except Exception:
            pass
    
    # VALIDAÇÃO 14: Se tem 1 palavra, tenta como país
    if len(valid_parts) == 1:
        part = valid_parts[0]
        if part in country_all:
            return country_all[part]
        if part in state_city_country:
            return state_city_country[part]
    
    # VALIDAÇÃO 15: Busca por cidades/estados conhecidos APENAS se não mencionou China
    # Evita que cidades brasileiras sejam detectadas quando há menção à China
    if 'china' not in loc and '中国' not in original_location and '中國' not in original_location:
        for key, country in state_city_country.items():
            if key in loc:
                return country
    
    return ''


def main():
    repos = fetch_top_repos()
    print(f"Buscando contribuidores dos {len(repos)} repositórios...")
    rows = []
    repo_count = 0
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        for repo in repos:
            repo_count += 1
            owner = repo['owner']['login']
            name = repo['name']
            repo_id = repo['id']
            repo_url = repo['html_url']
            
            print(f"[{repo_count}/{len(repos)}] Processando: {name}...")
            contributors = fetch_contributors(owner, name)
            
            if not contributors:
                print(f"  ⚠️  Nenhum contribuidor encontrado")
                continue
            
            found = False
            future_to_login = {executor.submit(fetch_user, login): login for login in contributors}
            
            for future in as_completed(future_to_login):
                try:
                    login, profile_url, location = future.result()
                    
                    # Pula se não conseguiu buscar o usuário
                    if not profile_url:
                        continue
                    
                    # Pula se a localização é inválida ou ambígua
                    if not is_valid_location(location):
                        print(f"  ⚠️  Localização inválida/ambígua para {login}: '{location}'")
                        continue
                    
                    country = identify_country(location)
                    
                    # Pula se não conseguiu identificar o país
                    if not country:
                        print(f"  ⚠️  País não identificado para {login}: '{location}'")
                        continue
                    
                    country = normalize_country_name(country)
                    
                    # Valida se o país identificado realmente corresponde à localização
                    if not validate_country_match(location, country):
                        print(f"  ⚠️  País '{country}' não corresponde à localização '{location}' para {login}")
                        continue
                    
                    if country in TARGET_COUNTRIES:
                        rows.append([name, repo_id, repo_url, login, profile_url, location, country])
                        print(f"  ✅ Encontrado: {login} ({country})")
                        found = True
                        break  # Só salva o primeiro!
                except Exception as e:
                    print(f"  ⚠️  Erro ao processar usuário: {e}")
                    continue
            
            if found:
                # Salva progresso a cada repo encontrado
                with open('repos_final.csv', 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['repo_name', 'repo_id', 'repo_url', 'login', 'profile_url', 'location', 'country'])
                    for row in rows:
                        writer.writerow(row)
            
    print(f"\n✅ Concluído! Total de repositórios com país-alvo: {len(rows)}")
    print("Salvando no CSV final...")
    with open('repos_final.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['repo_name', 'repo_id', 'repo_url', 'login', 'profile_url', 'location', 'country'])
        for row in rows:
            writer.writerow(row)


if __name__ == '__main__':
    main()