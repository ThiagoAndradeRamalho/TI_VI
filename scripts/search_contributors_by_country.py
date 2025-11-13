"""
Script para buscar contribuidores de um repositório específico por país.

Este script analisa o repositório xtekky/gpt4free e busca todos os
contribuidores que pertencem a um dos países-alvo: Brasil, Índia, Alemanha ou Estados Unidos.
A identificação é feita através da localização informada no perfil do GitHub usando a mesma
lógica de validação do script3.py.

Resultado: Gera o arquivo 'contributors_by_country.csv.csv' contendo os contribuidores encontrados
com as colunas: repo_owner, repo_name, contributor_login, contributor_url, location, country

Uso:
    python script8.py
    
Repositório analisado:
    - xtekky/gpt4free
"""

import requests
import sys
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import pycountry
from unidecode import unidecode
from token_loader import load_github_tokens

TOKENS = load_github_tokens()
NUM_WORKERS = len(TOKENS) * 4


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
                    return None
                r.raise_for_status()
                return r
            except requests.exceptions.HTTPError as e:
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

# Aliases globais para nomes de países em outros idiomas
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

# Lista dos países-alvo
TARGET_COUNTRIES = ['Brazil', 'India', 'Germany', 'United States']

# Termos ambíguos ou inválidos que devem ser descartados
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
    'evm', 'hbo', 'now', 'today', 'tomorrow', 'yesterday', 'here', 'there',
    'the grid', 'kraftland', 'convergence', 'state', 'bgp', 'city', 'town',
    'village', 'country', 'continent', 'region', 'area', 'zone', 'district',
    'lenapehoking', 'tango', 'capital', 'previously', 'tiny', 'small',
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
    words = set(loc_normalized.replace(',', ' ').replace(';', ' ').replace('/', ' ').replace('(', ' ').replace(')', ' ').split())
    if words & INVALID_LOCATIONS:
        return False
    
    # NOVA VALIDAÇÃO: Descarta localizações com muitos separadores (provavelmente múltiplas localizações)
    separator_count = loc.count('·') + loc.count('||') + loc.count(' & ')
    if separator_count > 0:
        return False
    
    # NOVA VALIDAÇÃO: Descarta localizações com palavras-chave de brincadeira/sarcasmo
    sarcasm_keywords = [';-)', ':)', ':-)', ';)', 'lol', 'haha', 'joke']
    for keyword in sarcasm_keywords:
        if keyword in loc:
            return False
    
    # NOVA VALIDAÇÃO: Descarta se tem mais de 3 palavras e nenhuma é país/cidade conhecida
    words_list = [w for w in loc_normalized.replace(',', ' ').split() if len(w) > 2]
    if len(words_list) > 5:
        # Muito longa e complexa, provavelmente não é localização válida
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
    Identifica o país a partir de uma localização, retornando string vazia se inválido.
    Método mais robusto com validações múltiplas para evitar falsos positivos.
    """
    if not location or not is_valid_location(location):
        return ''
    
    loc = unidecode(location.strip().lower())
    original_location = location.strip()
    
    # VALIDAÇÃO 1: Rejeita localizações que são claramente piadas/brincadeiras
    # Ex: "Europe's capital of Tango ;-)", "A tiny town in Sweden (previously Illinois)"
    joke_indicators = [
        ';-)', ':)', 'lol', 'joke', 'kidding', 'capital of tango',
        'previously', 'just', 'tiny town', 'somewhere', 'anywhere'
    ]
    for indicator in joke_indicators:
        if indicator in loc:
            return ''
    
    # VALIDAÇÃO 2: Detecta menções explícitas de "China" no texto
    # Casos como "City of Science which may or may not in China"
    china_patterns = ['in china', 'china.', 'china,', ' china ', 'mainland china', 'prc']
    for pattern in china_patterns:
        if pattern in loc:
            return 'China'
    
    # VALIDAÇÃO 3: Detecta cidades espanholas conhecidas
    spanish_cities = ['bilbao', 'barcelona', 'madrid', 'valencia', 'sevilla', 'zaragoza', 'malaga']
    for city in spanish_cities:
        if city in loc:
            # Se tem separador (-,/), verifica se não é múltiplas localizações
            if '-' in original_location or '/' in original_location:
                parts = original_location.replace('-', '/').split('/')
                country_mentions = []
                for part in parts:
                    part_lower = unidecode(part.strip().lower())
                    if part_lower in country_aliases:
                        country_mentions.append(country_aliases[part_lower])
                # Se mencionou múltiplos países, é ambíguo - descarta
                if len(country_mentions) > 1:
                    return ''
            # Só retorna Spain se for cidade isolada
            return 'Spain'
    
    # VALIDAÇÃO 4: Detecta cidades islandesas
    icelandic_cities = ['reykjavik', 'reykjavík']
    for city in icelandic_cities:
        if city in loc:
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
    
    # VALIDAÇÃO 5: Endereços chineses completos (Shaanxi Province, China)
    if 'province' in loc and 'china' in loc:
        return 'China'
    if 'district' in loc and 'china' in loc:
        return 'China'
    
    # VALIDAÇÃO 6: Montreal sempre é Canadá
    if 'montreal' in loc:
        return 'Canada'
    
    # VALIDAÇÃO 7: Cidades escandinavas (Copenhagen, Stockholm) - evitar confusão
    scandinavian_cities = {
        'copenhagen': 'Denmark',
        'stockholm': 'Sweden',
        'oslo': 'Norway',
        'helsinki': 'Finland'
    }
    for city, country in scandinavian_cities.items():
        if city in loc:
            # Se tem "·" ou "||", pode ser múltiplas localizações - descarta
            if '·' in original_location or '||' in original_location:
                return ''
            return country
    
    # VALIDAÇÃO 8: Rejeita localizações que são claramente nomes nativos de regiões
    # mas não informam país (ex: "Lenapehoking" = nome nativo para região de NYC)
    native_place_names = ['lenapehoking']
    for name in native_place_names:
        if name in loc:
            return ''
    
    # VALIDAÇÃO 9: Remove separadores problemáticos
    if '/' in location or '⮀' in location:
        for sep in ['/', '⮀']:
            if sep in location:
                parts = [p.strip() for p in location.split(sep)]
                valid_parts_temp = [p for p in parts if p and is_valid_location(p)]
                if valid_parts_temp:
                    for part in reversed(valid_parts_temp):
                        part_loc = unidecode(part.strip().lower())
                        if part_loc in country_aliases:
                            return country_aliases[part_loc]
                        if part_loc in state_city_country:
                            return state_city_country[part_loc]
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
    
    # VALIDAÇÃO 15: Busca por cidades/estados APENAS se não mencionou China
    # Evita conflitos onde parte do texto pode ter match com cidades brasileiras
    if 'china' not in loc and '中国' not in original_location and '中國' not in original_location:
        for key, country in state_city_country.items():
            if key in loc:
                # VALIDAÇÃO EXTRA: Checa se a localização é APENAS a cidade/estado
                # ou se tem contexto que confirma (ex: "Bangalore, Karnataka, India")
                if loc == key or f'{key},' in loc or f', {key}' in loc:
                    return country
    
    # Se chegou aqui, não conseguiu identificar de forma confiável
    return ''
    
    # Primeiro, verifica se a localização completa é um alias conhecido (ex: "shanghai", "beijing")
    if loc in country_aliases:
        return country_aliases[loc]
    
    # Separa por vírgula (formato comum: "City, Country")
    parts = [p.strip() for p in loc.replace(';', ',').replace('|', ',').split(',') if p.strip()]
    
    # Filtra partes inválidas
    valid_parts = [p for p in parts if is_valid_location(p)]
    if not valid_parts:
        return ''
    
    # Verifica cada parte nos aliases e dicionários conhecidos
    # Prioriza a última parte (geralmente o país)
    for part in reversed(valid_parts):
        if part in country_aliases:
            return country_aliases[part]
        if part in state_city_country:
            return state_city_country[part]
        if part in country_all:
            return country_all[part]
    
    # Se tem mais de uma parte válida, tenta Nominatim com a localização completa
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
                        return addr['country']
        except Exception:
            pass
    
    # Se só tem uma palavra válida, tenta como país (sigla ou nome)
    if len(valid_parts) == 1:
        part = valid_parts[0]
        if part in country_all:
            return country_all[part]
        if part in state_city_country:
            return state_city_country[part]
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
                        return addr['country']
        except Exception:
            pass
    
    # CORREÇÃO 6: Busca por cidades/estados conhecidos APENAS se não mencionou China explicitamente
    # Evita que cidades brasileiras sejam detectadas quando há menção à China
    if 'china' not in loc and '中国' not in original_location and '中國' not in original_location:
        for key, country in state_city_country.items():
            if key in loc:
                return country
    
    return ''


def fetch_contributors(owner, repo):
    """Busca todos os contribuidores de um repositório."""
    print(f"\n🔍 Buscando contribuidores de {owner}/{repo}...")
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
        print(f"  Página {page}: {len(data)} contribuidores")
        if len(data) < 100:
            break
        page += 1
    
    print(f"  Total de contribuidores: {len(contributors)}")
    return contributors


def fetch_user(login):
    """Busca informações de um usuário específico."""
    url = f'https://api.github.com/users/{login}'
    r = safe_request(url)
    if r is None:
        return login, '', ''
    data = r.json()
    location = data.get('location', '') or ''
    profile_url = data.get('html_url', '')
    return login, profile_url, location


def search_contributors_by_country(owner, repo):
    """
    Busca contribuidores de um repositório específico filtrando por países-alvo.
    """
    contributors = fetch_contributors(owner, repo)
    
    if not contributors:
        print("❌ Nenhum contribuidor encontrado!")
        return []
    
    print(f"\n🌍 Analisando localizações dos contribuidores...")
    results = []
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_login = {executor.submit(fetch_user, login): login for login in contributors}
        
        for idx, future in enumerate(as_completed(future_to_login), 1):
            try:
                login, profile_url, location = future.result()
                
                print(f"  [{idx}/{len(contributors)}] Analisando {login}...", end=' ')
                
                # Pula se não conseguiu buscar o usuário
                if not profile_url:
                    print("❌ Usuário não encontrado")
                    continue
                
                # Pula se a localização é inválida ou ambígua
                if not is_valid_location(location):
                    print(f"⚠️  Localização inválida: '{location}'")
                    continue
                
                country = identify_country(location)
                
                # Pula se não conseguiu identificar o país
                if not country:
                    print(f"⚠️  País não identificado: '{location}'")
                    continue
                
                country = normalize_country_name(country)
                
                # Valida se o país identificado realmente corresponde à localização
                if not validate_country_match(location, country):
                    print(f"⚠️  País '{country}' não corresponde à localização '{location}'")
                    continue
                
                if country in TARGET_COUNTRIES:
                    results.append({
                        'login': login,
                        'profile_url': profile_url,
                        'location': location,
                        'country': country
                    })
                    print(f"✅ {country}")
                else:
                    print(f"ℹ️  {country} (não é país-alvo)")
                    
            except Exception as e:
                print(f"⚠️  Erro: {e}")
                continue
    
    return results


def save_to_csv(all_results, filename='contributors_by_country.csv.csv'):
    """Salva os resultados em um arquivo CSV."""
    print(f"\n💾 Salvando resultados em '{filename}'...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Cabeçalho
        writer.writerow(['repo_owner', 'repo_name', 'contributor_login', 'contributor_url', 'location', 'country'])
        
        # Dados
        row_count = 0
        for repo_name, results in all_results.items():
            owner, repo = repo_name.split('/')
            for r in results:
                writer.writerow([
                    owner,
                    repo,
                    r['login'],
                    r['profile_url'],
                    r['location'],
                    r['country']
                ])
                row_count += 1
        
    print(f"✅ CSV salvo com sucesso! ({row_count} linhas de dados)")
    return filename


def print_results(owner, repo, results):
    """Exibe os resultados de forma formatada."""
    print("\n" + "="*80)
    print(f"📊 RESULTADOS PARA {owner}/{repo}")
    print("="*80)
    
    if not results:
        print("\n❌ Nenhum contribuidor dos países-alvo foi encontrado.")
        return
    
    # Agrupa por país
    by_country = {}
    for r in results:
        country = r['country']
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(r)
    
    print(f"\n✅ Total de contribuidores encontrados: {len(results)}")
    print("\nDistribuição por país:")
    for country in TARGET_COUNTRIES:
        count = len(by_country.get(country, []))
        print(f"  • {country}: {count} contribuidor(es)")
    
    print("\n" + "-"*80)
    print("LISTA COMPLETA DE CONTRIBUIDORES:")
    print("-"*80)
    
    for country in TARGET_COUNTRIES:
        if country in by_country:
            print(f"\n🌍 {country.upper()} ({len(by_country[country])} contribuidor(es)):")
            print("-"*80)
            for r in by_country[country]:
                print(f"  • Login: {r['login']}")
                print(f"    URL: {r['profile_url']}")
                print(f"    Localização: {r['location']}")
                print()


def main():
    # Repositório fixo para análise
    owner = 'hawkinsp'
    repo = 'tensorflow'
    
    
    print("="*80)
    print(f"🔎 BUSCA DE CONTRIBUIDORES POR PAÍS")
    print("="*80)
    print(f"Repositório: {owner}/{repo}")
    print(f"Países-alvo: {', '.join(TARGET_COUNTRIES)}")
    print("="*80)
    
    # Processa o repositório
    results = search_contributors_by_country(owner, repo)
    print_results(owner, repo, results)
    
    # Salva os resultados em CSV
    if results:
        all_results = {f"{owner}/{repo}": results}
        save_to_csv(all_results)
    else:
        print("\n⚠️  Nenhum contribuidor encontrado. CSV não foi gerado.")



if __name__ == '__main__':
    main()
