# Desempenho vs. Reconhecimento no OSS Global: Uma Análise sobre o Reconhecimento de Desenvolvedores de Países Emergentes no GitHub Utilizando Métricas de Centralidade


### Contexto e Justificativa

A participação de desenvolvedores de países emergentes, como Brasil e Índia, em projetos de software de código aberto (OSS) é objeto de atenção em estudos recentes. Pesquisas como The Geography of Open Source Software apontam para uma presença crescente desses países no ecossistema global de OSS. Entretanto, grande parte dessas análises enfatiza o volume de contribuições, sem necessariamente esclarecer o tipo de papel exercido por esses desenvolvedores. Permanecem abertas questões como: até que ponto estão envolvidos em funções centrais de coordenação e decisão? Ou sua atuação se concentra, sobretudo, em tarefas mais periféricas dentro dos projetos?
A subvalorização sistemática desses profissionais já é documentada no mercado tradicional. Segundo o HackerRank Developer Skills Report (2020), desenvolvedores americanos ganham quase três vezes mais ($109.167/ano) que seus pares indianos ($38.229/ano). Esta disparidade não apenas persiste, mas se expande para novos contextos geográficos. O mercado de trabalho remoto tem testemunhado a emergência de outros países emergentes, como o Brasil, competindo por posições similares às tradicionalmente ocupadas por desenvolvedores indianos, evidenciando a institucionalização de hierarquias salariais baseadas em geografia ao invés de mérito técnico.
O diferencial desta pesquisa reside em fornecer evidências quantitativas e objetivas para investigar se esse padrão de subvalorização se replica no ambiente OSS. Enquanto discussões sobre subvalorização frequentemente se baseiam em percepções ou evidências relativas, propomos uma abordagem metodologicamente através de métricas quantitativas de centralidade de rede. 
Nesse sentido, utilizamos tanto as métricas tradicionais de atividade (número de commits, PRs) quanto ferramentas avançadas de análise de redes sociais (SNA) para investigar a posição de cada desenvolvedor na rede de colaboração. Através de métricas como centralidade de intermediação (betweenness), decomposição k-core e identificação de Structural Hole Spanners (SHP), nosso objetivo é quantificar objetivamente se desenvolvedores de Brasil e Índia funcionam como "pontes" e "núcleos" vitais para a comunicação e a estabilidade dos projetos, permitindo assim uma avaliação empírica abrangente da relação entre volume de contribuições, importância estrutural e reconhecimento formal no ecossistema OSS.
Por que GitHub?
O GitHub é a maior plataforma OSS, onde devs constroem reputação pública. Embora não traga salários, oferece proxies de reconhecimento e influência (seguidores, estrelas, papéis de maintainer), além de métricas de desempenho (PRs, issues, tempo de resposta). Isso permite investigar desempenho vs. reconhecimento em escala global.

## Scripts de Coleta de Dados

Os scripts de análise foram organizados com nomes descritivos que refletem suas funções específicas:

### Scripts Principais
1. **`select_top_repos_by_countries.py`** - Seleciona repositórios populares com contribuidores dos países-alvo (Brasil, Índia, Alemanha, EUA)
2. **`collect_repo_metrics.py`** - Coleta métricas básicas de repositórios (estrelas, forks, PRs, commits, etc.)
3. **`identify_contributors_countries.py`** - Identifica países dos contribuidores via geolocalização de perfis
4. **`collect_social_interactions.py`** - Coleta completa de interações sociais entre desenvolvedores
5. **`collect_user_metrics_async.py`** - Coleta assíncrona otimizada de métricas de usuários
6. **`collect_structured_data_fast.py`** - Coleta estruturada usando GraphQL (20-50x mais rápida)

### Módulos Especializados
- **`collect_commits_interactions.py`** - Interações de commits e co-autores
- **`collect_discussions_interactions.py`** - GitHub Discussions e comentários
- **`collect_issues_interactions.py`** - Issues e comentários
- **`collect_prs_interactions.py`** - Pull Requests, reviews e comentários
- **`collect_forks_interactions.py`** - Usuários que fizeram fork
- **`collect_stars_interactions.py`** - Usuários que deram estrela

Documentação completa dos scripts está disponível em [`scripts/SCRIPTS_DOCUMENTATION.md`](scripts/SCRIPTS_DOCUMENTATION.md).

## 🚀 Como Executar

### Verificação Rápida
```bash
# Verifica se tudo está configurado corretamente
python3 check_prerequisites.py
```

### Execução Completa (Ordem Recomendada)
```bash
# 1. Instalar dependências
./install_dependencies.sh

# 2. Configurar tokens GitHub (copie .env.example para .env e configure)
cp .env.example .env
# Edite o arquivo .env e adicione seus tokens

# 3. Executar scripts na ordem
cd scripts
python3 select_top_repos_by_countries.py      # ~30-60 min
python3 collect_repo_metrics.py               # ~15-30 min  
python3 identify_contributors_countries.py    # ~45-90 min
python3 collect_social_interactions.py        # ~2-4 horas
python3 collect_structured_data_fast.py       # ~15-30 min
```

**📖 Guia detalhado:** [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md)

### Objetivo

Investigar se desenvolvedores de países emergentes (Brasil, Índia) são subvalorizados em termos de reconhecimento e influência em projetos open source internacionais, mesmo quando apresentam desempenho e participação comparáveis (ou superiores) aos de países desenvolvidos, caracterizando o fenômeno da “mão de obra barata” no ecossistema global de software.
