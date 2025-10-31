"""
Carregador de tokens do GitHub a partir do arquivo .env
"""
import os

def load_github_tokens():
    """
    Carrega tokens do GitHub a partir de variáveis de ambiente ou arquivo .env
    Retorna uma lista de tokens válidos (não vazios)
    """
    tokens = []
    
    # Primeiro tenta carregar do arquivo .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    # Carrega tokens numerados
    for i in range(1, 21):
        token = os.getenv(f'GITHUB_TOKEN_{i}')
        if token and token.strip():
            tokens.append(token.strip())
    
    # Se não encontrou, tenta GITHUB_TOKEN
    if not tokens:
        token = os.getenv('GITHUB_TOKEN')
        if token and token.strip():
            tokens.append(token.strip())
    
    if tokens:
        print(f"✅ {len(tokens)} token(s) do GitHub carregados")
    else:
        print("⚠️  Configure os tokens no arquivo .env (GITHUB_TOKEN_1, GITHUB_TOKEN_2, etc.)")
    
    return tokens

if __name__ == '__main__':
    # Teste do carregamento
    tokens = load_github_tokens()
    for i, token in enumerate(tokens, 1):
        if token:
            print(f"Token {i}: {token[:10]}...{token[-4:]}")