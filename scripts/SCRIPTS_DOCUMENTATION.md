# Scripts Renomeados - Análise OSS

Este documento descreve os scripts renomeados com nomes mais descritivos que refletem suas funcionalidades.

## Scripts Principais

### 1. `collect_repo_metrics.py` (anteriormente `script1.py`)
**Função:** Coleta métricas básicas de repositórios do GitHub
- **Entrada:** `repos_final.csv` (lista de repositórios)  
- **Saída:** `repos_metrics.csv`
- **Métricas coletadas:**
  - Informações básicas (nome, owner, descrição, linguagem, topics)
  - Estatísticas (estrelas, forks, issues, PRs)
  - Métricas de atividade (commits, contributors, releases)
  - Tempo médio de resposta e merge

### 2. `identify_contributors_countries.py` (anteriormente `script2.py`)
**Função:** Identifica países de origem dos contribuidores via geolocalização
- **Entrada:** `repos_final.csv` ou `reposFinal.csv`
- **Saída:** `users_countries.csv`
- **Processo:**
  - Busca contribuidores de cada repositório
  - Analisa localização do perfil GitHub
  - Usa APIs de geocodificação (Nominatim/OpenStreetMap)
  - Aplica validações robustas contra localizações falsas/ambíguas

### 3. `select_top_repos_by_countries.py` (anteriormente `script3.py`)
**Função:** Seleciona repositórios populares com contribuidores dos países-alvo
- **Entrada:** API GitHub (busca top 1500 repositórios)
- **Saída:** `repos_final.csv`
- **Países-alvo:** Brasil, Índia, Alemanha, Estados Unidos
- **Processo:**
  - Busca os repositórios mais populares do GitHub
  - Para cada repo, identifica primeiro contribuidor dos países-alvo
  - Aplica validações de localização rigorosas

### 4. `collect_user_metrics_async.py` (anteriormente `script4.py`)
**Função:** Coleta métricas detalhadas de usuários usando programação assíncrona
- **Entrada:** `users_countries.csv`
- **Saída:** `users_metrics_async.csv`
- **Métricas coletadas:**
  - PRs (abertos, merged, taxa de aceitação, tempo médio)
  - Commits, issues, reviews
  - Estrelas em repositórios próprios
  - Atividade e permissões no repositório

### 5. `collect_social_interactions.py` (anteriormente `script5.py`)
**Função:** Coleta completa de interações sociais entre desenvolvedores
- **Entrada:** `repos_final.csv`
- **Saída:** `edges_raw.csv`, `nodes_raw.csv`
- **Interações coletadas:**
  - Pull Requests (autores, reviewers, comentários)
  - Issues (autores, comentários)
  - Commits (autores, co-autores)
  - Stars e Forks
  - GitHub Discussions
  - @mentions em todos os contextos

### 6. `collect_structured_data_fast.py` (anteriormente `script6_fast.py`)
**Função:** Coleta otimizada usando GraphQL e processamento assíncrono
- **Entrada:** `repos_final.csv`, `users_countries.csv`
- **Saída:** `dev_repo_raw.csv`, `maintainers_raw.csv`, `prs_raw.csv`
- **Otimizações:**
  - GraphQL API (1 request vs 4-5 REST)
  - Requisições assíncronas em paralelo
  - Cache inteligente
  - 20-50x mais rápido que versão síncrona

## Scripts Especializados (Módulos do collect_social_interactions)

### `collect_commits_interactions.py` (anteriormente `script5_commits.py`)
- Coleta commits individuais e identifica co-autores
- Período: 2020-2025

### `collect_discussions_interactions.py` (anteriormente `script5_discussions.py`)
- Coleta GitHub Discussions e comentários
- Identifica @mentions em discussões

### `collect_forks_interactions.py` (anteriormente `script5_forks.py`)
- Coleta usuários que fizeram fork dos repositórios

### `collect_issues_interactions.py` (anteriormente `script5_issues.py`)
- Coleta issues e seus comentários
- Identifica @mentions

### `collect_prs_interactions.py` (anteriormente `script5_prs.py`)
- Coleta Pull Requests, reviews e comentários
- Identifica @mentions

### `collect_stars_interactions.py` (anteriormente `script5_stars.py`)
- Coleta usuários que deram star nos repositórios

### `social_interactions_utils.py` (anteriormente `script5_utils.py`)
- Utilitários compartilhados para coleta de interações
- Funções de autenticação, rate limiting, geocodificação

## Arquivos de Suporte

### `token_loader.py`
- Carrega tokens do GitHub para autenticação
- Gerencia rotação de tokens para evitar rate limits

### `repos_final.csv`
- Dados dos repositórios selecionados para análise
- Contém repo_name, repo_id, repo_url, login, profile_url, location, country

## Fluxo de Execução Recomendado

1. **`select_top_repos_by_countries.py`** - Seleciona repositórios populares
2. **`collect_repo_metrics.py`** - Coleta métricas básicas dos repositórios
3. **`identify_contributors_countries.py`** - Identifica países dos contribuidores
4. **`collect_social_interactions.py`** - Coleta interações sociais completas
5. **`collect_structured_data_fast.py`** - Coleta dados estruturados otimizada

## Observações

- Todos os scripts usam múltiplos tokens GitHub para maximizar rate limits
- Scripts assíncronos são significativamente mais rápidos
- Validações robustas são aplicadas para garantir qualidade dos dados
- Backups parciais são salvos durante execução para recuperação