#!/usr/bin/env python3
"""
Script de verificação de pré-requisitos para o projeto TI_VI
Verifica se tudo está configurado corretamente antes da execução
"""

import os
import sys
import subprocess
import importlib.util

def check_python_version():
    """Verifica se a versão do Python é adequada"""
    print("🐍 Verificando versão do Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Requer Python 3.8+")
        return False

def check_pip():
    """Verifica se pip está disponível"""
    print("📦 Verificando pip...")
    try:
        subprocess.run(['pip3', '--version'], capture_output=True, check=True)
        print("   ✅ pip3 - OK")
        return True
    except:
        print("   ❌ pip3 não encontrado")
        return False

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print("📚 Verificando dependências...")
    
    required_packages = [
        'requests',
        'pandas', 
        'aiohttp',
        'pycountry',
        'unidecode',
        'tqdm'
    ]
    
    missing = []
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing.append(package)
        else:
            print(f"   ✅ {package} - OK")
    
    if missing:
        print(f"   ❌ Pacotes faltando: {', '.join(missing)}")
        print("   💡 Execute: pip3 install -r requirements.txt")
        return False
    
    return True

def check_tokens():
    """Verifica se tokens do GitHub estão configurados"""
    print("🔑 Verificando tokens do GitHub...")
    
    # Importa o token_loader do diretório scripts
    sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
    try:
        from token_loader import load_github_tokens
        tokens = load_github_tokens()
        
        if not tokens:
            print("   ❌ Nenhum token configurado")
            print("   💡 Configure tokens no arquivo .env")
            return False
        
        if len(tokens) < 3:
            print(f"   ⚠️  Apenas {len(tokens)} token(s) - Recomendado: 3+")
            print("   💡 Adicione mais tokens para melhor performance")
        else:
            print(f"   ✅ {len(tokens)} tokens configurados - OK")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro ao carregar tokens: {e}")
        return False

def check_files():
    """Verifica se os arquivos necessários existem"""
    print("📁 Verificando arquivos...")
    
    required_files = [
        'requirements.txt',
        'scripts/token_loader.py',
        'scripts/select_top_repos_by_countries.py',
        'scripts/collect_repo_metrics.py',
        'scripts/identify_contributors_countries.py',
        'scripts/collect_social_interactions.py'
    ]
    
    missing = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path} - OK")
        else:
            missing.append(file_path)
            print(f"   ❌ {file_path} - Não encontrado")
    
    if missing:
        return False
    
    return True

def check_disk_space():
    """Verifica espaço em disco disponível"""
    print("💾 Verificando espaço em disco...")
    
    try:
        stat = os.statvfs('.')
        free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        if free_space_gb >= 5:
            print(f"   ✅ {free_space_gb:.1f} GB disponível - OK")
            return True
        else:
            print(f"   ⚠️  Apenas {free_space_gb:.1f} GB disponível - Recomendado: 5GB+")
            return True  # Não bloqueia execução
    except:
        print("   ⚠️  Não foi possível verificar espaço em disco")
        return True

def suggest_execution_order():
    """Sugere ordem de execução baseada nas verificações"""
    print("\n🎯 Ordem de execução recomendada:")
    print("   1. cd scripts")
    print("   2. python3 select_top_repos_by_countries.py")
    print("   3. python3 collect_repo_metrics.py") 
    print("   4. python3 identify_contributors_countries.py")
    print("   5. python3 collect_social_interactions.py")
    print("   6. python3 collect_structured_data_fast.py")
    print("\n📖 Guia completo: EXECUTION_GUIDE.md")

def main():
    print("🔍 VERIFICAÇÃO DE PRÉ-REQUISITOS - Projeto TI_VI")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_pip(),
        check_dependencies(),
        check_files(),
        check_tokens(),
        check_disk_space()
    ]
    
    print("\n" + "=" * 50)
    
    if all(checks):
        print("🎉 TUDO PRONTO! Você pode executar os scripts.")
        suggest_execution_order()
        return 0
    else:
        print("⚠️  AÇÃO NECESSÁRIA: Corrija os problemas acima antes de continuar.")
        print("\n💡 Passos para corrigir:")
        if not checks[1] or not checks[2]:
            print("   • Execute: ./install_dependencies.sh")
        if not checks[4]:
            print("   • Configure tokens no arquivo .env (veja .env.example)")
        print("   • Consulte EXECUTION_GUIDE.md para instruções detalhadas")
        return 1

if __name__ == '__main__':
    sys.exit(main())