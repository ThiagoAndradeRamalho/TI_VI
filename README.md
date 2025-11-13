# Desempenho vs. Reconhecimento no OSS Global: Uma Análise sobre o Reconhecimento de Desenvolvedores de Países Emergentes no GitHub Utilizando Métricas de Centralidade

# Ordem de Execução dos Scripts 

## Visão Geral
Este documento apresenta a ordem correta de execução dos scripts da pasta `scripts/`, suas entradas, saídas e dependências.

## 📋 Ordem de Execução

### ⚙️ **token_loader.py** 
**Tipo:** **MÓDULO UTILITÁRIO** (não executar diretamente)  
**Descrição:** Carrega tokens do GitHub a partir de arquivo `.env`  
**Entrada:** Arquivo `.env` (com variáveis GITHUB_TOKEN_1, GITHUB_TOKEN_2, etc.)  
**Saída:** Lista de tokens válidos  
**Nota:** ⚠️ **NÃO EXECUTAR** - É importado automaticamente pelos outros scripts via `from token_loader import load_github_tokens`

---

### 1. **select_top_repos_by_countries.py**
**Tipo:** Coleta inicial  
**Descrição:** Busca os 1500 repositórios mais populares do GitHub e identifica o primeiro contribuidor dos países-alvo (Brasil, Índia, Alemanha, Estados Unidos)  
**Entrada:** 
- Tokens do GitHub (via token_loader.py)
- API do GitHub  
**Saída:** `repos_final.csv`  
**Colunas do CSV:** repo_name, repo_id, repo_url, login, profile_url, location, country

---

### 2. **identify_contributors_countries.py**
**Tipo:** Expansão de dados  
**Descrição:** Identifica países de todos os contribuidores dos repositórios selecionados  
**Entrada:** 
- `scripts/repos_final.csv`
- API do GitHub
- API Nominatim (OpenStreetMap)  
**Saída:** `users_countries.csv`  
**Colunas do CSV:** repo_name, repo_url, login, profile_url, location, country

---

### 3. **collect_repo_metrics.py**
**Tipo:** Coleta de métricas de repositórios  
**Descrição:** Coleta métricas detalhadas de cada repositório (PRs, commits, contribuidores, etc.)  
**Entrada:** 
- `scripts/csv/repos_final.csv`
- API do GitHub  
**Saída:** `scripts/csv/repos_metrics.csv`  
**Colunas principais:** repo_name, repo_owner, stars_count, forks_count, prs_opened_count, prs_merged_count, commits_count, contributors_count, active_days, time_to_first_response, time_to_merge, release_count

---

### 4. **collect_user_metrics_async.py**
**Tipo:** Coleta de métricas de usuários (assíncrono)  
**Descrição:** Coleta métricas de produtividade dos usuários usando programação assíncrona  
**Entrada:** 
- `scripts/csv/users_countries.csv`
- API do GitHub  
**Saída:** `scripts/csv/users_metrics.csv`  
**Colunas principais:** login, repo_name, country, prs_opened, prs_merged, pr_accept_rate, avg_time_to_merge, commits_total, issues_opened, reviews_submitted, stars_own_repos, activity_frequency, permission_level

---

### ⚙️ **script6_real_graphql.py** (Alternativo)
**Tipo:** Coleta de métricas com GraphQL  
**Descrição:** Versão otimizada usando GraphQL para coleta de métricas de usuários  
**Entrada:** 
- `users_countries.csv`
- API GraphQL do GitHub  
**Saída:** `productivity_metrics_real_graphql.csv`  
**Nota:** **ALTERNATIVA** ao script anterior - usar OU collect_user_metrics_async.py OU este, não ambos

---

### 5. **weight_analysis.py**
**Tipo:** Análise estatística  
**Descrição:** Determina pesos empíricos usando PCA e análise de correlação para cálculo de performance  
**Entrada:** 
- `scripts/csv/users_metrics.csv`  
**Saída:** `scripts/csv/weights_analysis.json`  
**Conteúdo:** Pesos empíricos determinados por PCA, metodologia e timestamp

---

### 6. **calculate_performance_scores.py**
**Tipo:** Cálculo de scores  
**Descrição:** Calcula scores de performance usando pesos empíricos determinados pela análise PCA  
**Entrada:** 
- `scripts/csv/users_metrics.csv`
- `scripts/csv/weights_analysis.json`  
**Saída:** `scripts/csv/performance_scores.csv`  
**Colunas principais:** login, repo_name, country, country_type, performance_score, pr_accept_rate, prs_opened, commits_total, activity_frequency (+ versões normalizadas)

---

### 7. **calculate_network_metrics.py**
**Tipo:** Análise de redes  
**Descrição:** Calcula métricas de centralidade na rede de colaboração (degree, betweenness, closeness, eigenvector, structural holes)  
**Entrada:** 
- `scripts/csv/users_countries.csv`
- `scripts/csv/users_metrics.csv`  
**Saída:** `scripts/csv/network_metrics.csv`  
**Colunas principais:** login, degree_centrality, betweenness_centrality, closeness_centrality, eigenvector_centrality, structural_hole_spanners, developer_profile, absence_impact, country

---

### ⚙️ **search_contributors_by_country.py** (Exemplo/Específico)
**Tipo:** Análise específica  
**Descrição:** Busca contribuidores de um repositório específico por país (exemplo com hawkinsp/tensorflow)  
**Entrada:** 
- Repositório específico (hardcoded)
- API do GitHub  
**Saída:** `contributors_by_country.csv.csv`  
**Nota:** Script de exemplo/teste para análise de um repositório específico

---

## 🔄 Fluxo de Dependências

```
[token_loader.py] (módulo utilitário - importado automaticamente)
    ↓
1. select_top_repos_by_countries.py
    ↓ (repos_final.csv)
2. identify_contributors_countries.py
    ↓ (users_countries.csv)
3. collect_repo_metrics.py ← (repos_final.csv)
    ↓ (repos_metrics.csv)
4. collect_user_metrics_async.py ← (users_countries.csv)
    ↓ (users_metrics.csv)
5. weight_analysis.py ← (users_metrics.csv)
    ↓ (weights_analysis.json)
6. calculate_performance_scores.py ← (users_metrics.csv + weights_analysis.json)
    ↓ (performance_scores.csv)
7. calculate_network_metrics.py ← (users_countries.csv + users_metrics.csv)
    ↓ (network_metrics.csv)
```

## 📁 Arquivos de Entrada Externos

1. **Arquivo `.env`** - Contém tokens do GitHub
2. **APIs externas:**
   - GitHub API REST
   - GitHub GraphQL API
   - Nominatim API (OpenStreetMap)

## 📊 Arquivos de Saída Principais

1. **repos_final.csv** - Repositórios selecionados com primeiro contribuidor por país
2. **users_countries.csv** - Todos os usuários com países identificados
3. **repos_metrics.csv** - Métricas detalhadas dos repositórios
4. **users_metrics.csv** - Métricas de produtividade dos usuários
5. **weights_analysis.json** - Pesos empíricos para cálculo de performance
6. **performance_scores.csv** - Scores de performance calculados
7. **network_metrics.csv** - Métricas de centralidade na rede

## ⚠️ Observações Importantes

1. **Tokens do GitHub**: Obrigatório configurar múltiplos tokens no arquivo `.env` para evitar rate limits
2. **Ordem de execução**: Respeitar a sequência devido às dependências entre arquivos
3. **Tempo de execução**: Alguns scripts podem levar várias horas para executar devido ao volume de dados
4. **Rate limits**: Os scripts implementam controle de rate limit, mas o processo pode ser interrompido e retomado
5. **Backup incremental**: Vários scripts salvam dados incrementalmente para permitir recuperação em caso de interrupção

## 🚀 Execução Completa

Para executar todo o pipeline:

```bash
# 1. Configurar tokens no arquivo .env (GITHUB_TOKEN_1, GITHUB_TOKEN_2, etc.)
# 2. Executar scripts na ordem (token_loader.py é importado automaticamente):

python scripts/select_top_repos_by_countries.py
python scripts/identify_contributors_countries.py
python scripts/collect_repo_metrics.py
python scripts/collect_user_metrics_async.py
python scripts/weight_analysis.py
python scripts/calculate_performance_scores.py
python scripts/calculate_network_metrics.py
```

## 📈 Resultados Finais

Os resultados finais estão em `scripts/csv/` e são utilizados pelos scripts de análise e visualização na pasta raiz do projeto para gerar as visualizações e relatórios das questões de pesquisa (RQ1, RQ2, RQ3).