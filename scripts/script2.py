"""
Script de identificação de países de contribuidores do GitHub.

Este script lê uma lista de repositórios do arquivo 'selected_repos_and_first_user.csv',
coleta todos os contribuidores de cada repositório e identifica o país de origem de cada
um através da localização informada no perfil do GitHub. Utiliza a API do Nominatim
(OpenStreetMap) para geocodificação e normalização de nomes de países.

Resultado: Gera o arquivo 'users_countries.csv' contendo repositório, login do usuário,
profile URL, localização original e país identificado para cada contribuidor.
"""

import requests
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pycountry
from unidecode import unidecode

TOKENS = []
# Reduzido de 64 para 8 workers para evitar sobrecarga de conexões DNS
NUM_WORKERS = 8


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
                r.raise_for_status()
                return r
            except (requests.exceptions.SSLError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                print(f"Erro de conexão (tentativa {attempt + 1}/{max_retries}): {e}")
                time.sleep(5)
                continue
        time.sleep(60)
    return None


def fetch_contributors(owner, repo):
    contributors = []
    page = 1
    while True:
        url = f'https://api.github.com/repos/{owner}/{repo}/contributors'
        params = {'per_page': 100, 'page': page}
        r = safe_request(url, params)
        if r is None:
            print(f"Erro ao buscar contribuidores de {owner}/{repo}")
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


country_names = {unidecode(c.name.lower()): c.name for c in pycountry.countries}
country_alpha2 = {c.alpha_2.lower(): c.name for c in pycountry.countries}
country_alpha3 = {c.alpha_3.lower(): c.name for c in pycountry.countries}
country_official = {unidecode(getattr(c, 'official_name', '').lower()): c.name for c in pycountry.countries if hasattr(c, 'official_name')}
country_all = {**country_names, **country_alpha2, **country_alpha3, **country_official}

# INVALID LOCATIONS - patterns that should be rejected
INVALID_LOCATIONS = {
    'earth', 'world', 'internet', 'cyberspace', 'online', 'remote', 'global',
    'nowhere', 'somewhere', 'anywhere', 'everywhere', 'unknown', 'n/a', 'na',
    'localhost', '127.0.0.1', '0.0.0.0', 'my computer', 'my house', 'home',
    'the cloud', 'cloud', 'servers', 'github', 'gitlab', 'bitbucket',
    'mars', 'moon', 'space', 'universe', 'galaxy', 'milky way',
    'matrix', 'metaverse', 'virtual', 'digital',
    'my room', 'my desk', 'my bed', 'bedroom', 'office',
    'here', 'there', 'over there', 'around', 'nearby',
    'undefined', 'null', 'none', 'empty', 'blank',
    'now', 'kraftland', 'the grid', 'grid', 'lenapehoking',
    'tomorrowland', 'wonderland', 'neverland', 'atlantis',
    'wakanda', 'asgard', 'gotham', 'metropolis', 'mordor',
}

# SARCASTIC PATTERNS - reject sarcastic/joke locations
SARCASTIC_PATTERNS = [
    ';-)', ':)', ':-)', 'xd', 'lol', 'lmao', 'haha', 'jk', 'kidding',
    'just kidding', 'not really', 'maybe', 'who knows', 'guess',
    'somewhere in', 'lost in', 'stuck in', 'trapped in',
    'capital of tango', 'previously', 'used to be', 'formerly',
    'probably', 'possibly', 'perhaps', 'might be',
]

# NATIVE REGION NAMES - indigenous/historical names without modern country mapping
NATIVE_REGION_NAMES = [
    'lenapehoking', 'turtle island', 'abya yala', 'anahuac',
    'pangaea', 'gondwana', 'laurasia',
]

# SCANDINAVIAN CITIES - cities that could be in multiple Scandinavian countries
SCANDINAVIAN_CITIES = {
    'copenhagen': 'Denmark', 'kobenhavn': 'Denmark', 'aarhus': 'Denmark', 'odense': 'Denmark',
    'stockholm': 'Sweden', 'gothenburg': 'Sweden', 'malmo': 'Sweden', 'uppsala': 'Sweden',
    'oslo': 'Norway', 'bergen': 'Norway', 'trondheim': 'Norway', 'stavanger': 'Norway',
    'helsinki': 'Finland', 'espoo': 'Finland', 'tampere': 'Finland', 'vantaa': 'Finland',
    'reykjavik': 'Iceland', 'reykjavík': 'Iceland', 'akureyri': 'Iceland', 'keflavik': 'Iceland',
}

state_city_country = {
# Brasil
'sp': 'Brazil', 'sao paulo': 'Brazil', 'rj': 'Brazil', 'rio de janeiro': 'Brazil', 'mg': 'Brazil', 'minas gerais': 'Brazil',
'rs': 'Brazil', 'rio grande do sul': 'Brazil', 'pr': 'Brazil', 'parana': 'Brazil', 'sc': 'Brazil', 'santa catarina': 'Brazil',
'ba': 'Brazil', 'bahia': 'Brazil', 'ce': 'Brazil', 'ceara': 'Brazil', 'pe': 'Brazil', 'pernambuco': 'Brazil',
'recife': 'Brazil', 'porto alegre': 'Brazil', 'curitiba': 'Brazil', 'salvador': 'Brazil', 'fortaleza': 'Brazil',
'brasilia': 'Brazil', 'belo horizonte': 'Brazil', 'manaus': 'Brazil', 'goiania': 'Brazil',
# Índia
'delhi': 'India', 'new delhi': 'India', 'mumbai': 'India', 'maharashtra': 'India', 'bangalore': 'India', 'karnataka': 'India',
'chennai': 'India', 'tamil nadu': 'India', 'kolkata': 'India', 'west bengal': 'India', 'hyderabad': 'India', 'telangana': 'India',
'pune': 'India', 'ahmedabad': 'India', 'gujarat': 'India', 'jaipur': 'India', 'rajasthan': 'India',
# Alemanha
'berlin': 'Germany', 'hamburg': 'Germany', 'munich': 'Germany', 'munchen': 'Germany', 'bavaria': 'Germany', 'bayern': 'Germany',
'frankfurt': 'Germany', 'hesse': 'Germany', 'hessen': 'Germany', 'stuttgart': 'Germany', 'baden-wurttemberg': 'Germany',
'dusseldorf': 'Germany', 'dortmund': 'Germany', 'cologne': 'Germany', 'koln': 'Germany', 'north rhine-westphalia': 'Germany',
# Estados Unidos
'ny': 'United States', 'new york': 'United States', 'california': 'United States',
'tx': 'United States', 'texas': 'United States', 'fl': 'United States', 'florida': 'United States',
'il': 'United States', 'illinois': 'United States', 'wa': 'United States', 'washington': 'United States',
'los angeles': 'United States', 'san francisco': 'United States', 'chicago': 'United States', 'houston': 'United States',
'boston': 'United States', 'atlanta': 'United States', 'seattle': 'United States', 'miami': 'United States',
'dallas': 'United States', 'austin': 'United States', 'san diego': 'United States', 'philadelphia': 'United States',
'portland': 'United States', 'denver': 'United States', 'phoenix': 'United States', 'las vegas': 'United States',
# Canadá
'montreal': 'Canada', 'toronto': 'Canada', 'vancouver': 'Canada', 'ottawa': 'Canada', 'calgary': 'Canada',
'quebec': 'Canada', 'winnipeg': 'Canada', 'edmonton': 'Canada', 'ontario': 'Canada', 'british columbia': 'Canada',
# Espanha
'madrid': 'Spain', 'barcelona': 'Spain', 'valencia': 'Spain', 'sevilla': 'Spain', 'seville': 'Spain',
'bilbao': 'Spain', 'malaga': 'Spain', 'zaragoza': 'Spain', 'catalonia': 'Spain', 'andalusia': 'Spain',
# Reino Unido
'london': 'United Kingdom', 'manchester': 'United Kingdom', 'birmingham': 'United Kingdom', 'edinburgh': 'United Kingdom',
'glasgow': 'United Kingdom', 'liverpool': 'United Kingdom', 'bristol': 'United Kingdom', 'scotland': 'United Kingdom',
# França
'paris': 'France', 'marseille': 'France', 'lyon': 'France', 'toulouse': 'France', 'nice': 'France',
# China
'beijing': 'China', 'shanghai': 'China', 'guangzhou': 'China', 'shenzhen': 'China', 'chengdu': 'China',
'hangzhou': 'China', 'wuhan': 'China', 'xian': 'China', "xi'an": 'China', 'nanjing': 'China',
# Adicione mais se quiser!
}

country_aliases = {
'中国': 'China', '中國': 'China', 'china': 'China', 'prc': 'China', "people's republic of china": 'China',
'deutschland': 'Germany', 'germany': 'Germany', 'de': 'Germany',
'nederland': 'Netherlands', 'holland': 'Netherlands', 'netherlands': 'Netherlands',
'belgië': 'Belgium', 'belgique': 'Belgium', 'belgien': 'Belgium', 'belgium': 'Belgium',
'россия': 'Russia', 'russia': 'Russia', 'russian federation': 'Russia',
'україна': 'Ukraine', 'ukraine': 'Ukraine',
'sverige': 'Sweden', 'sweden': 'Sweden',
'日本': 'Japan', 'nippon': 'Japan', 'japan': 'Japan',
'台灣': 'Taiwan', '臺灣': 'Taiwan', 'taiwan': 'Taiwan',
'usa': 'United States', 'us': 'United States', 'united states': 'United States', 'united states of america': 'United States',
'brasil': 'Brazil', 'brazil': 'Brazil', 'br': 'Brazil',
'france': 'France', 'francia': 'France', 'frança': 'France', 'fr': 'France',
'england': 'United Kingdom', 'uk': 'United Kingdom', 'united kingdom': 'United Kingdom', 'great britain': 'United Kingdom', 'britain': 'United Kingdom',
'turkey': 'Turkey', 'türkiye': 'Turkey', 'turkiye': 'Turkey',
'canada': 'Canada', 'ca': 'Canada',
'portugal': 'Portugal', 'pt': 'Portugal',
'italy': 'Italy', 'italia': 'Italy', 'it': 'Italy',
'spain': 'Spain', 'españa': 'Spain', 'es': 'Spain',
'india': 'India', 'bharat': 'India', 'in': 'India',
'poland': 'Poland', 'polska': 'Poland', 'pl': 'Poland',
'australia': 'Australia', 'au': 'Australia', 'aus': 'Australia',
'denmark': 'Denmark', 'danmark': 'Denmark', 'dk': 'Denmark',
'norway': 'Norway', 'norge': 'Norway', 'no': 'Norway',
'switzerland': 'Switzerland', 'schweiz': 'Switzerland', 'suisse': 'Switzerland', 'svizzera': 'Switzerland', 'ch': 'Switzerland',
'south korea': 'Korea, Republic of', 'korea': 'Korea, Republic of', 'republic of korea': 'Korea, Republic of',
'hong kong': 'Hong Kong', 'hk': 'Hong Kong',
'singapore': 'Singapore', 'sg': 'Singapore',
'mexico': 'Mexico', 'méxico': 'Mexico', 'mx': 'Mexico',
'argentina': 'Argentina', 'ar': 'Argentina',
'iceland': 'Iceland', 'island': 'Iceland', 'is': 'Iceland',
'montreal': 'Canada', 'toronto': 'Canada', 'vancouver': 'Canada',
'bilbao': 'Spain', 'reykjavik': 'Iceland', 'reykjavík': 'Iceland',
# Adicione outros aliases conforme necessário
}


def normalize_country_name(country):
    if not country:
        return ''
    ctry = unidecode(country.strip().lower())
    if ctry in country_aliases:
        return country_aliases[ctry]
    for c in pycountry.countries:
        if ctry in [
            unidecode(c.name.lower()),
            unidecode(getattr(c, 'official_name', '').lower()),
            unidecode(getattr(c, 'common_name', '').lower()),
            unidecode(getattr(c, 'alpha_2', '').lower()),
            unidecode(getattr(c, 'alpha_3', '').lower())
        ]:
            return c.name
    for alias, norm in country_aliases.items():
        if alias in ctry:
            return norm
    return country.capitalize()


def is_valid_location(location):
    """Check if location is valid and not a joke/sarcastic/undefined entry"""
    if not location or len(location.strip()) < 2:
        return False
    
    loc_lower = unidecode(location.lower().strip())
    
    # Check INVALID_LOCATIONS
    for invalid in INVALID_LOCATIONS:
        if invalid in loc_lower:
            return False
    
    # Check SARCASTIC_PATTERNS
    for pattern in SARCASTIC_PATTERNS:
        if pattern in loc_lower:
            return False
    
    # Check NATIVE_REGION_NAMES
    for native in NATIVE_REGION_NAMES:
        if native in loc_lower:
            return False
    
    # Reject very short ambiguous entries
    if len(loc_lower) <= 2 and loc_lower not in ['us', 'uk', 'ca', 'de', 'fr', 'br', 'in', 'au', 'es', 'it', 'nl', 'ch', 'se', 'no', 'dk']:
        return False
    
    # Reject only numbers or special characters
    if all(not c.isalpha() for c in loc_lower):
        return False
    
    return True


def identify_country(location):
    """
    Identify country from location string with 15 robust validation steps.
    Returns empty string if location is invalid/undefined/ambiguous.
    """
    # VALIDATION 1: Check if location exists and is valid
    if not location or not is_valid_location(location):
        return ''
    
    location_original = location
    loc = unidecode(location.strip().lower())
    
    # VALIDATION 2: Reject sarcastic patterns explicitly
    for pattern in SARCASTIC_PATTERNS:
        if pattern in loc:
            return ''
    
    # VALIDATION 3: Reject native region names
    for native in NATIVE_REGION_NAMES:
        if native in loc:
            return ''
    
    # VALIDATION 4: Explicit China detection (handles "City of Science which may or may not in China")
    china_patterns = ['in china', 'china.', 'china,', ' china ', 'province china', 'district china', ', china', 'china)']
    for pattern in china_patterns:
        if pattern in loc:
            # Additional check: if it mentions China explicitly, it's China
            return 'China'
    
    # VALIDATION 5: Spanish cities - check for ambiguity
    spanish_cities = ['madrid', 'barcelona', 'valencia', 'sevilla', 'seville', 'bilbao', 'malaga']
    for city in spanish_cities:
        if city in loc:
            # Check if there are multiple countries mentioned (ambiguous)
            country_count = sum(1 for c in ['spain', 'españa', 'iceland', 'island', 'reykjavik', 'reykjavík'] if c in loc)
            if country_count > 1:
                return ''  # Ambiguous (e.g., "Bilbao - Reykjavík")
            return 'Spain'
    
    # VALIDATION 6: Icelandic cities - check for ambiguity
    icelandic_cities = ['reykjavik', 'reykjavík', 'akureyri', 'keflavik']
    for city in icelandic_cities:
        if city in loc:
            # Check if there are multiple countries mentioned (ambiguous)
            country_count = sum(1 for c in ['iceland', 'island', 'spain', 'españa'] if c in loc)
            if country_count > 1:
                return ''  # Ambiguous
            return 'Iceland'
    
    # VALIDATION 7: Chinese addresses with Province/District
    if ('province' in loc or 'district' in loc) and 'china' in loc:
        return 'China'
    
    # VALIDATION 8: Montreal hardcoded to Canada (not USA)
    if 'montreal' in loc:
        return 'Canada'
    
    # VALIDATION 9: Scandinavian cities - reject if ambiguous
    for city, country in SCANDINAVIAN_CITIES.items():
        if city in loc:
            # Check if multiple Scandinavian countries mentioned
            scandi_countries = ['denmark', 'sweden', 'norway', 'finland', 'iceland', 'danmark', 'sverige', 'norge', 'island']
            country_mentions = sum(1 for c in scandi_countries if c in loc)
            if country_mentions > 1:
                return ''  # Ambiguous
            return country
    
    # VALIDATION 10: Parse location parts (separators: comma, semicolon, pipe, ⮀, /)
    separators = [',', ';', '|', '⮀', '/']
    parts = [location_original.strip()]
    for sep in separators:
        if sep in location_original:
            parts = [p.strip() for p in location_original.replace(';', ',').replace('|', ',').replace('⮀', ',').replace('/', ',').split(',') if p.strip()]
            break
    
    # VALIDATION 11: Check last part first (usually country)
    if len(parts) > 1:
        last_part = unidecode(parts[-1].strip().lower())
        
        # Check in country_aliases
        if last_part in country_aliases:
            return country_aliases[last_part]
        
        # Check in state_city_country
        if last_part in state_city_country:
            return state_city_country[last_part]
        
        # Check in country_all (pycountry)
        if last_part in country_all:
            return country_all[last_part]
    
    # VALIDATION 12: Check single part or first parts
    for part_original in parts:
        part = unidecode(part_original.strip().lower())
        
        if not part or len(part) < 2:
            continue
        
        # Check country_aliases first
        if part in country_aliases:
            return country_aliases[part]
        
        # Check state_city_country
        if part in state_city_country:
            return state_city_country[part]
        
        # Check country_all (pycountry names/codes)
        if part in country_all:
            return country_all[part]
    
    # VALIDATION 13: Check for country names anywhere in location string
    for key, country in state_city_country.items():
        if key in loc and len(key) > 3:  # Only check longer keys to avoid false matches
            return country
    
    # VALIDATION 14: Nominatim API as last resort (with timeout)
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': location_original, 'format': 'json', 'addressdetails': 1, 'limit': 1},
            headers={'User-Agent': 'github-country-lookup'},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0 and 'address' in data[0]:
                addr = data[0]['address']
                if 'country' in addr:
                    country_from_api = addr['country']
                    # Normalize the country name from API
                    normalized = normalize_country_name(country_from_api)
                    return normalized
    except Exception:
        pass
    
    # VALIDATION 15: If nothing found, return empty string (undefined)
    return ''


def read_input_csv(filename):
    repos = []
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'repo_url' in row and row['repo_url']:
                try:
                    parts = row['repo_url'].rstrip('/').split('/')
                    owner = parts[-2]
                    name = parts[-1]
                    repos.append({
                        'repo_name': row.get('repo_name', name),
                        'repo_url': row['repo_url'],
                        'owner': owner,
                        'name': name
                    })
                except Exception as e:
                    print(f"Erro ao extrair owner/name de {row['repo_url']}: {e}")
            elif 'repo_name' in row and 'repo_owner' in row:
                repos.append({
                    'repo_name': row['repo_name'],
                    'repo_url': '',  # Se não tiver, deixa vazio
                    'owner': row['repo_owner'],
                    'name': row['repo_name']
                })
    return repos


def main():
    input_csv = 'reposFinal.csv' 
    repos = read_input_csv(input_csv)
    print("Coletando contribuidores e gerando CSV...")
    
    valid_entries = 0
    skipped_invalid = 0
    skipped_no_country = 0
    
    with open('users_countries.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['repo_name', 'repo_url', 'login', 'profile_url', 'location', 'country'])
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = {}
            for repo in repos:
                owner = repo['owner']
                name = repo['name']
                repo_url = repo['repo_url']
                contributors = fetch_contributors(owner, name)
                for login in contributors:
                    future = executor.submit(fetch_user, login)
                    futures[future] = (repo['repo_name'], repo_url)
            for future in as_completed(futures):
                try:
                    login, profile_url, location = future.result()
                    repo_name, repo_url = futures[future]
                    
                    # CRITICAL: Skip if location is invalid/undefined
                    if not location or not is_valid_location(location):
                        skipped_invalid += 1
                        continue
                    
                    # Identify country with robust validation
                    country = identify_country(location)
                    
                    # CRITICAL: Skip if country could not be identified (undefined)
                    if not country:
                        skipped_no_country += 1
                        print(f"⚠️  Skipping {login}: undefined location '{location}'")
                        continue
                    
                    # Normalize country name
                    country = normalize_country_name(country)
                    
                    # CRITICAL: Only write to CSV if country is valid and defined
                    if country:
                        writer.writerow([repo_name, repo_url, login, profile_url, location, country])
                        valid_entries += 1
                        print(f"✅ {login}: {location} → {country}")
                    
                    time.sleep(1)
                except Exception as e:
                    print(f"Erro ao processar usuário: {e}")
    
    print(f"\n=== RESUMO ===")
    print(f"✅ Entradas válidas gravadas: {valid_entries}")
    print(f"⚠️  Locations inválidas desconsideradas: {skipped_invalid}")
    print(f"⚠️  Locations sem país identificado: {skipped_no_country}")
    print(f"📄 CSV gerado: users_countries.csv")


if __name__ == '__main__':
    main()