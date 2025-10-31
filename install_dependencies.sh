#!/bin/bash
# Script de instalação das dependências do projeto TI_VI

echo "🚀 Instalando dependências do projeto TI_VI..."
echo ""

# Verifica se o pip está disponível
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 não encontrado. Por favor, instale o Python 3 e pip primeiro."
    exit 1
fi

# Atualiza o pip
echo "📦 Atualizando pip..."
pip3 install --upgrade pip

# Instala as dependências
echo "📦 Instalando dependências..."
pip3 install -r requirements.txt

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure seus tokens no arquivo .env"
echo "2. Execute: python3 scripts/token_loader.py para testar"
echo "3. Execute qualquer script: python3 scripts/collect_repo_metrics.py"
echo ""
echo "� Documentação completa dos scripts: scripts/SCRIPTS_DOCUMENTATION.md"