#!/bin/bash
# Script de execução automática do pipeline completo
# Executa todos os scripts na ordem correta com monitoramento

set -e  # Para na primeira falha

echo "🚀 INICIANDO PIPELINE DE ANÁLISE OSS - TI_VI"
echo "=============================================="

# Função para log com timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Função para mostrar progresso
show_progress() {
    local current=$1
    local total=$2 
    local name=$3
    echo ""
    echo "📊 Progresso: [$current/$total] $name"
    echo "=============================================="
}

# Verificar pré-requisitos
log "🔍 Verificando pré-requisitos..."
cd /Users/2213dtidigital/Downloads/TI_VI

if ! python3 check_prerequisites.py > /dev/null 2>&1; then
    echo "❌ Pré-requisitos não atendidos. Execute:"
    echo "   python3 check_prerequisites.py"
    exit 1
fi

log "✅ Pré-requisitos OK"

# Navegar para diretório de scripts
cd scripts

# Criar diretório de logs se não existir
mkdir -p ../logs
LOG_DIR="../logs"

# Scripts para executar
declare -a SCRIPTS=(
    "select_top_repos_by_countries.py:Seleção de Repositórios:30-60 min"
    "collect_repo_metrics.py:Métricas de Repositórios:15-30 min" 
    "identify_contributors_countries.py:Identificação de Países:45-90 min"
    "collect_social_interactions.py:Interações Sociais:2-4 horas"
    "collect_structured_data_fast.py:Dados Estruturados:15-30 min"
)

TOTAL=${#SCRIPTS[@]}
SUCCESS_COUNT=0

log "🎯 Iniciando execução de $TOTAL scripts..."

# Executar cada script
for i in "${!SCRIPTS[@]}"; do
    CURRENT=$((i + 1))
    IFS=':' read -r SCRIPT_NAME SCRIPT_DESC TIME_EST <<< "${SCRIPTS[$i]}"
    
    show_progress $CURRENT $TOTAL "$SCRIPT_DESC ($TIME_EST)"
    
    LOG_FILE="$LOG_DIR/${SCRIPT_NAME%.*}_$(date +%Y%m%d_%H%M%S).log"
    
    log "▶️  Executando: $SCRIPT_NAME"
    log "📝 Log: $LOG_FILE"
    
    START_TIME=$(date +%s)
    
    if python3 "$SCRIPT_NAME" 2>&1 | tee "$LOG_FILE"; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        DURATION_MIN=$((DURATION / 60))
        
        log "✅ $SCRIPT_DESC concluído em ${DURATION_MIN}m${DURATION:$((DURATION % 60))}s"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        # Mostrar arquivos gerados
        log "📁 Verificando arquivos gerados..."
        case "$SCRIPT_NAME" in
            "select_top_repos_by_countries.py")
                [[ -f "repos_final.csv" ]] && log "   ✅ repos_final.csv gerado"
                ;;
            "collect_repo_metrics.py")
                [[ -f "repos_metrics.csv" ]] && log "   ✅ repos_metrics.csv gerado"
                ;;
            "identify_contributors_countries.py")
                [[ -f "users_countries.csv" ]] && log "   ✅ users_countries.csv gerado"
                ;;
            "collect_social_interactions.py")
                [[ -f "edges_raw.csv" ]] && log "   ✅ edges_raw.csv gerado"
                [[ -f "nodes_raw.csv" ]] && log "   ✅ nodes_raw.csv gerado"
                ;;
            "collect_structured_data_fast.py")
                [[ -f "dev_repo_raw.csv" ]] && log "   ✅ dev_repo_raw.csv gerado"
                [[ -f "maintainers_raw.csv" ]] && log "   ✅ maintainers_raw.csv gerado"
                [[ -f "prs_raw.csv" ]] && log "   ✅ prs_raw.csv gerado"
                ;;
        esac
        
    else
        log "❌ Erro em: $SCRIPT_DESC"
        log "📝 Verifique o log: $LOG_FILE"
        
        echo ""
        echo "⚠️  EXECUÇÃO INTERROMPIDA"
        echo "Script com falha: $SCRIPT_NAME"
        echo "Log de erro: $LOG_FILE"
        echo ""
        echo "Para continuar manualmente:"
        echo "cd /Users/2213dtidigital/Downloads/TI_VI/scripts"
        
        # Mostra próximos scripts
        if [[ $CURRENT -lt $TOTAL ]]; then
            echo "Próximos scripts a executar:"
            for j in $(seq $CURRENT $((TOTAL - 1))); do
                IFS=':' read -r NEXT_SCRIPT NEXT_DESC _ <<< "${SCRIPTS[$j]}"
                echo "  python3 $NEXT_SCRIPT  # $NEXT_DESC"
            done
        fi
        
        exit 1
    fi
    
    echo ""
done

# Resumo final
echo ""
echo "🎉 PIPELINE CONCLUÍDO COM SUCESSO!"
echo "=============================================="
log "✅ $SUCCESS_COUNT/$TOTAL scripts executados com sucesso"

# Mostrar estatísticas dos arquivos
echo ""
log "📊 Resumo dos arquivos gerados:"
cd /Users/2213dtidigital/Downloads/TI_VI/scripts

FILES=(
    "repos_final.csv"
    "repos_metrics.csv" 
    "users_countries.csv"
    "edges_raw.csv"
    "nodes_raw.csv"
    "dev_repo_raw.csv"
    "maintainers_raw.csv"
    "prs_raw.csv"
)

for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        size=$(du -h "$file" | cut -f1)
        lines=$(wc -l < "$file" 2>/dev/null || echo "?")
        log "   ✅ $file ($size, $lines linhas)"
    else
        log "   ⚠️  $file - não encontrado"
    fi
done

echo ""
log "🎯 Próximos passos:"
echo "   1. Analisar dados gerados"
echo "   2. Executar análises de rede social"
echo "   3. Gerar visualizações"
echo ""
log "📖 Documentação: ../EXECUTION_GUIDE.md"
log "📝 Logs salvos em: ../logs/"

echo "=============================================="
echo "✨ Análise OSS completa! ✨"