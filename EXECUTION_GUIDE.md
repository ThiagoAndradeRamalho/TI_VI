# Guia de Execução - Análise OSS GitHub

Este guia descreve a ordem correta para executar os scripts de análise, incluindo pré-requisitos e dependências.

## 🔧 Pré-requisitos

### 1. Ambiente Python
```bash
# Verificar se Python 3.8+ está instalado
python3 --version

# Se não estiver instalado, instalar Python 3.8+
# macOS: brew install python3
# Ubuntu: sudo apt install python3 python3-pip
```

### 2. Instalar Dependências
```bash
# Navegar para o diretório do projeto
cd /Users/2213dtidigital/Downloads/TI_VI

# Executar script de instalação automática
chmod +x install_dependencies.sh
./install_dependencies.sh

# OU instalar manualmente
pip3 install -r requirements.txt
```

### 3. Configurar Tokens GitHub
Você precisa de tokens do GitHub para evitar rate limits:

```bash
# Criar arquivo .env na raiz do projeto
touch .env

# Adicionar tokens (um por linha)
echo "GITHUB_TOKEN_1=seu_token_aqui" >> .env
echo "GITHUB_TOKEN_2=seu_segundo_token" >> .env
echo "GITHUB_TOKEN_3=seu_terceiro_token" >> .env
# ... adicione quantos tokens tiver
```

**Como obter tokens GitHub:**
1. Acesse https://github.com/settings/tokens
2. Clique em "Generate new token (classic)"
3. Selecione escopo "public_repo" 
4. Copie o token gerado

### 4. Testar Configuração
```bash
# Testar se tokens estão funcionando
cd scripts
python3 token_loader.py
```

## 📋 Ordem de Execução

### **FLUXO COMPLETO (Execução do Zero)**

```bash
cd /Users/2213dtidigital/Downloads/TI_VI/scripts
```

#### **Etapa 1: Seleção de Repositórios** ⭐
```bash
# Busca os top ~1500 repositórios populares do GitHub
# Filtra apenas repos com contribuidores dos países-alvo (Brasil, Índia, Alemanha, EUA)
# Tempo: ~30-60 minutos
python3 select_top_repos_by_countries.py

# Arquivo gerado: repos_final.csv
```

#### **Etapa 2: Métricas de Repositórios** 📊
```bash
# Coleta métricas detalhadas de cada repositório selecionado
# Tempo: ~15-30 minutos (depende do número de repos)
python3 collect_repo_metrics.py

# Arquivo gerado: repos_metrics.csv
```

#### **Etapa 3: Identificação de Países** 🌍
```bash
# Identifica o país de origem de todos os contribuidores
# Usa geolocalização avançada com validações
# Tempo: ~45-90 minutos
python3 identify_contributors_countries.py

# Arquivo gerado: users_countries.csv
```

#### **Etapa 4: Coleta de Interações Sociais** 🤝
```bash
# Coleta TODAS as interações entre desenvolvedores
# PRs, Issues, Commits, Stars, Forks, Discussions, @mentions
# Tempo: ~2-4 horas (processo mais demorado)
python3 collect_social_interactions.py

# Arquivos gerados: edges_raw.csv, nodes_raw.csv
```

#### **Etapa 5A: Métricas de Usuários (Assíncrono)** ⚡
```bash
# Coleta métricas detalhadas de usuários de forma otimizada
# Tempo: ~30-60 minutos
python3 collect_user_metrics_async.py

# Arquivo gerado: users_metrics_async.csv
```

#### **Etapa 5B: Dados Estruturados (GraphQL)** 🚀
```bash
# Coleta dados estruturados usando GraphQL (MUITO mais rápido)
# Relações dev-repo, maintainers, PRs detalhados
# Tempo: ~15-30 minutos
python3 collect_structured_data_fast.py

# Arquivos gerados: dev_repo_raw.csv, maintainers_raw.csv, prs_raw.csv
```

### **FLUXO MODULAR (Execução Específica)**

Se você quiser executar apenas partes específicas:

#### **Apenas Commits**
```bash
python3 collect_commits_interactions.py
# Gera: commits_edges.csv, commits_nodes.csv
```

#### **Apenas PRs**
```bash
python3 collect_prs_interactions.py
# Gera: prs_edges.csv, prs_nodes.csv
```

#### **Apenas Issues**
```bash
python3 collect_issues_interactions.py
# Gera: issues_edges.csv, issues_nodes.csv
```

#### **Apenas Discussions**
```bash
python3 collect_discussions_interactions.py
# Gera: discussions_edges.csv, discussions_nodes.csv
```

#### **Apenas Stars**
```bash
python3 collect_stars_interactions.py
# Gera: stars_edges.csv, stars_nodes.csv
```

#### **Apenas Forks**
```bash
python3 collect_forks_interactions.py
# Gera: forks_edges.csv, forks_nodes.csv
```

## 📁 Arquivos Gerados

| Script | Arquivo de Saída | Descrição |
|--------|------------------|-----------|
| `select_top_repos_by_countries.py` | `repos_final.csv` | Lista de repositórios selecionados |
| `collect_repo_metrics.py` | `repos_metrics.csv` | Métricas básicas dos repositórios |
| `identify_contributors_countries.py` | `users_countries.csv` | Usuários e seus países |
| `collect_social_interactions.py` | `edges_raw.csv`, `nodes_raw.csv` | Rede completa de interações |
| `collect_user_metrics_async.py` | `users_metrics_async.csv` | Métricas detalhadas dos usuários |
| `collect_structured_data_fast.py` | `dev_repo_raw.csv`, `maintainers_raw.csv`, `prs_raw.csv` | Dados estruturados |

## ⚠️ Considerações Importantes

### **Rate Limits**
- **Recomendado:** 8+ tokens para execução completa
- **Mínimo:** 3 tokens para execução básica
- Os scripts fazem rotação automática de tokens

### **Tempo Total Estimado**
- **Execução completa:** ~4-7 horas
- **Fluxo otimizado (GraphQL):** ~2-3 horas
- **Execução modular:** 15 minutos - 2 horas (por módulo)

### **Espaço em Disco**
- **Total estimado:** ~500MB - 2GB
- **Arquivos grandes:** `edges_raw.csv`, `users_countries.csv`

### **Recursos do Sistema**
- **RAM:** 4GB+ recomendado
- **CPU:** Processos paralelos intensivos
- **Rede:** ~10GB de tráfego total

### **Backup Automático**
- Todos os scripts salvam progresso parcial
- Arquivos `*_partial.csv` são criados durante execução
- Execução pode ser retomada em caso de interrupção

## 🛠️ Solução de Problemas

### **Erro: "Rate limit exceeded"**
```bash
# Adicionar mais tokens ao .env
echo "GITHUB_TOKEN_4=novo_token" >> ../.env
```

### **Erro: "ModuleNotFoundError"**
```bash
# Reinstalar dependências
pip3 install -r ../requirements.txt
```

### **Erro: "Permission denied"**
```bash
# Dar permissões ao script
chmod +x ../install_dependencies.sh
```

### **Arquivos não encontrados**
```bash
# Verificar se está no diretório correto
pwd
# Deve mostrar: /Users/2213dtidigital/Downloads/TI_VI/scripts

# Verificar se arquivo de entrada existe
ls -la repos_final.csv
```

## 🎯 Fluxos Recomendados por Objetivo

### **Para Análise Completa (Pesquisa Acadêmica)**
```bash
# Execução sequencial completa
python3 select_top_repos_by_countries.py
python3 collect_repo_metrics.py
python3 identify_contributors_countries.py
python3 collect_social_interactions.py
python3 collect_structured_data_fast.py
```

### **Para Prototipagem Rápida**
```bash
# Apenas dados essenciais
python3 select_top_repos_by_countries.py
python3 identify_contributors_countries.py
python3 collect_structured_data_fast.py
```

### **Para Análise de Redes Sociais**
```bash
# Foco em interações
python3 select_top_repos_by_countries.py
python3 collect_social_interactions.py
```

### **Para Análise de Performance**
```bash
# Foco em métricas
python3 select_top_repos_by_countries.py
python3 collect_user_metrics_async.py
python3 collect_repo_metrics.py
```