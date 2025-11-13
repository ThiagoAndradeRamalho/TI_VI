import pandas as pd
import networkx as nx
import numpy as np
from collections import defaultdict
import logging
import time
from datetime import datetime
import psutil
import os

# Configurar logging
def setup_logging():
    """Configura logging com diferentes níveis."""
    log_filename = f"logs/rq3_full_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Criar diretório de logs se não existir
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def log_memory_usage(logger, step_name):
    """Log do uso de memória atual."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    logger.info(f"📊 {step_name} - Memória: {memory_mb:.2f} MB")

def load_full_collaboration_data(logger):
    """Carregar dados completos de colaboração."""
    logger.info("🔄 Carregando dados completos de colaboração...")
    
    try:
        # Carregar dados de países
        users_countries_df = pd.read_csv('csv/users_countries.csv')
        logger.info(f"  📊 Carregados dados de {len(users_countries_df)} usuários com países")
        
        # Carregar dados de métricas
        users_metrics_df = pd.read_csv('csv/users_metrics.csv')
        logger.info(f"  � Carregados dados de métricas de {len(users_metrics_df)} usuários")
        
        # Combinar os datasets - preservando colunas de país
        combined_df = pd.merge(users_countries_df, users_metrics_df, on='login', how='inner', suffixes=('', '_dup'))
        
        # Usar a coluna de país original (sem sufixo)
        combined_df = combined_df.drop([col for col in combined_df.columns if col.endswith('_dup')], axis=1)
        
        logger.info(f"  🔗 Dados combinados: {len(combined_df)} usuários com países e métricas")
        
        # Classificar países
        emerging_countries = {
            'brazil', 'india', 'china', 'south africa', 'russia', 'mexico', 'indonesia', 
            'turkey', 'thailand', 'malaysia', 'philippines', 'vietnam', 'argentina',
            'colombia', 'chile', 'peru', 'ukraine', 'romania', 'bulgaria', 'croatia',
            'poland', 'czech republic', 'hungary', 'egypt', 'nigeria', 'kenya', 'ghana'
        }
        
        combined_df['country_type'] = combined_df['country'].str.lower().apply(
            lambda x: 'emerging' if x in emerging_countries else 'developed'
        )
        
        logger.info(f"  🌍 Classificação de países:")
        logger.info(f"    - Países emergentes: {(combined_df['country_type'] == 'emerging').sum()} usuários")
        logger.info(f"    - Países desenvolvidos: {(combined_df['country_type'] == 'developed').sum()} usuários")
        
        return combined_df
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados: {e}")
        raise

def create_optimized_collaboration_network(df, logger):
    """
    Cria rede de colaboração otimizada para processar todos os dados.
    """
    logger.info("🌐 Iniciando criação da rede de colaboração...")
    start_time = time.time()
    
    G = nx.Graph()
    
    # Análise inicial dos repositórios
    repo_stats = df.groupby('repo_name').size().reset_index(name='contributors')
    
    logger.info(f"📊 Estatísticas dos repositórios:")
    logger.info(f"  - Total de repositórios: {len(repo_stats)}")
    logger.info(f"  - Média de contribuidores por repo: {repo_stats['contributors'].mean():.2f}")
    logger.info(f"  - Mediana de contribuidores: {repo_stats['contributors'].median():.2f}")
    logger.info(f"  - Máximo de contribuidores: {repo_stats['contributors'].max()}")
    
    # SEM LIMITE - incluir TODOS os repositórios para análise completa
    logger.info(f"🌐 Incluindo TODOS os repositórios (sem filtros)")
    logger.info(f"  - Repositórios processados: {len(repo_stats)} (100%)")
    logger.info(f"  - Desenvolvedores processados: {len(df)} (100%)")
    
    # Usar todos os dados sem filtrar
    df_filtered = df
    
    # Agrupar por repositório
    repo_groups = df_filtered.groupby('repo_name')['login'].apply(list).to_dict()
    
    logger.info(f"🔗 Processando {len(repo_groups)} repositórios para criar arestas...")
    
    # Criar arestas com batches otimizados para volume maior
    edge_weights = defaultdict(int)
    batch_size = 50  # Batch maior para processar mais repositórios
    processed_repos = 0
    
    for repo_name, contributors in repo_groups.items():
        if len(contributors) > 1:
            # Conectar todos os pares de contribuidores
            for i in range(len(contributors)):
                for j in range(i + 1, len(contributors)):
                    user1, user2 = contributors[i], contributors[j]
                    # Ordenar para evitar duplicatas (user1, user2) vs (user2, user1)
                    if user1 > user2:
                        user1, user2 = user2, user1
                    edge_weights[(user1, user2)] += 1
        
        processed_repos += 1
        if processed_repos % batch_size == 0:
            logger.info(f"  - Processados {processed_repos}/{len(repo_groups)} repositórios ({processed_repos/len(repo_groups)*100:.1f}%)")
            log_memory_usage(logger, f"Batch {processed_repos//batch_size}")
    
    # Adicionar arestas ao grafo
    logger.info(f"🔗 Adicionando {len(edge_weights)} arestas ao grafo...")
    start_edges = time.time()
    
    for (user1, user2), weight in edge_weights.items():
        G.add_edge(user1, user2, weight=weight)
    
    edges_time = time.time() - start_edges
    total_time = time.time() - start_time
    
    logger.info(f"✅ Rede criada em {total_time:.2f}s (arestas: {edges_time:.2f}s)")
    logger.info(f"📊 Rede final: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")
    log_memory_usage(logger, "Rede criada")
    
    # Análise da conectividade
    components = list(nx.connected_components(G))
    largest_component_size = max(len(comp) for comp in components) if components else 0
    
    logger.info(f"🔗 Análise de conectividade:")
    logger.info(f"  - Componentes conectados: {len(components)}")
    logger.info(f"  - Maior componente: {largest_component_size} nós ({largest_component_size/G.number_of_nodes()*100:.1f}%)")
    
    return G

def calculate_centrality_metrics_parallel(G, logger):
    """Calcula métricas de centralidade de forma otimizada e paralela quando possível."""
    logger.info("📐 Iniciando cálculo de métricas de centralidade...")
    
    centrality_metrics = {}
    
    # 1. Degree Centrality (rápido)
    logger.info("  🔢 Calculando Degree Centrality...")
    start_time = time.time()
    centrality_metrics['degree'] = nx.degree_centrality(G)
    logger.info(f"    ✅ Concluído em {time.time() - start_time:.2f}s")
    
    # 2. Betweenness Centrality (usar aproximação para redes grandes)
    logger.info("  🌉 Calculando Betweenness Centrality...")
    start_time = time.time()
    
    if G.number_of_nodes() > 5000:
        # Usar aproximação com amostra maior para maior precisão
        k = min(500, G.number_of_nodes() // 10)
        logger.info(f"    📊 Usando aproximação com amostra de {k} nós")
        centrality_metrics['betweenness'] = nx.betweenness_centrality(G, k=k, normalized=True)
    else:
        centrality_metrics['betweenness'] = nx.betweenness_centrality(G, normalized=True)
    
    logger.info(f"    ✅ Concluído em {time.time() - start_time:.2f}s")
    log_memory_usage(logger, "Betweenness centrality")
    
    # 3. Closeness Centrality (calcular apenas para maior componente)
    logger.info("  📏 Calculando Closeness Centrality...")
    start_time = time.time()
    
    # Encontrar maior componente conectado
    components = list(nx.connected_components(G))
    if components:
        largest_cc = max(components, key=len)
        logger.info(f"    🔗 Maior componente: {len(largest_cc)} nós")
        
        if len(largest_cc) > 10000:
            # Para componentes muito grandes, usar amostra
            sample_size = min(5000, len(largest_cc))
            sampled_nodes = np.random.choice(list(largest_cc), sample_size, replace=False)
            subgraph = G.subgraph(sampled_nodes)
            logger.info(f"    📊 Usando amostra de {sample_size} nós do maior componente")
        else:
            subgraph = G.subgraph(largest_cc)
        
        closeness_partial = nx.closeness_centrality(subgraph)
        centrality_metrics['closeness'] = {node: closeness_partial.get(node, 0.0) for node in G.nodes()}
    else:
        centrality_metrics['closeness'] = {node: 0.0 for node in G.nodes()}
    
    logger.info(f"    ✅ Concluído em {time.time() - start_time:.2f}s")
    
    # 4. Eigenvector Centrality (com fallback para PageRank)
    logger.info("  🎯 Calculando Eigenvector Centrality...")
    start_time = time.time()
    
    try:
        centrality_metrics['eigenvector'] = nx.eigenvector_centrality(G, max_iter=1000, tol=1e-4)
        logger.info(f"    ✅ Eigenvector centrality concluído")
    except (nx.PowerIterationFailedConvergence, nx.NetworkXError) as e:
        logger.warning(f"    ⚠️ Eigenvector centrality falhou: {e}")
        logger.info(f"    🔄 Usando PageRank como fallback...")
        centrality_metrics['eigenvector'] = nx.pagerank(G, max_iter=1000, tol=1e-4)
        logger.info(f"    ✅ PageRank concluído como proxy")
    except Exception as e:
        logger.error(f"    ❌ Erro crítico: {e}")
        centrality_metrics['eigenvector'] = {node: 0.0 for node in G.nodes()}
    
    logger.info(f"    ✅ Concluído em {time.time() - start_time:.2f}s")
    log_memory_usage(logger, "Eigenvector centrality")
    
    return centrality_metrics

def calculate_structural_holes_optimized(G, logger):
    """Calcula structural holes de forma otimizada."""
    logger.info("🕳️ Calculando Structural Holes...")
    start_time = time.time()
    
    structural_holes = {}
    total_nodes = G.number_of_nodes()
    
    if total_nodes > 10000:
        logger.info("  📊 Rede grande detectada, usando algoritmo otimizado...")
        # Para redes grandes, usar effective size como proxy
        batch_size = 1000
        processed = 0
        
        for node in G.nodes():
            neighbors = list(G.neighbors(node))
            if len(neighbors) <= 1:
                structural_holes[node] = 0.0
            else:
                # Effective size simplificado
                redundancy = 0
                for neighbor in neighbors:
                    common_neighbors = len(set(G.neighbors(neighbor)) & set(neighbors))
                    redundancy += common_neighbors / len(neighbors) if neighbors else 0
                
                effective_size = len(neighbors) - redundancy
                structural_holes[node] = effective_size / len(neighbors)
            
            processed += 1
            if processed % batch_size == 0:
                logger.info(f"    📈 Processados {processed}/{total_nodes} nós ({processed/total_nodes*100:.1f}%)")
                
    else:
        logger.info("  🔍 Usando algoritmo completo de Burt constraint...")
        # Algoritmo completo para redes menores
        constraint = {}
        
        for node in G.nodes():
            neighbors = list(G.neighbors(node))
            if len(neighbors) <= 1:
                constraint[node] = 1.0
            else:
                total_constraint = 0
                degree = G.degree(node)
                
                for neighbor in neighbors:
                    direct_prop = 1.0 / degree
                    common_neighbors = set(G.neighbors(neighbor)) & set(neighbors)
                    indirect_prop = sum(1.0 / (G.degree(neighbor) * G.degree(common)) 
                                      for common in common_neighbors if common != node)
                    
                    node_constraint = (direct_prop + indirect_prop) ** 2
                    total_constraint += node_constraint
                
                constraint[node] = total_constraint
        
        # Converter para structural holes
        max_constraint = max(constraint.values()) if constraint else 1.0
        for node, c in constraint.items():
            structural_holes[node] = 1.0 - (c / max_constraint)
    
    logger.info(f"  ✅ Structural holes concluído em {time.time() - start_time:.2f}s")
    log_memory_usage(logger, "Structural holes")
    
    return structural_holes

def analyze_absence_impact_full(df, logger):
    """Análise completa de impacto da ausência."""
    logger.info("⏰ Analisando impacto da ausência...")
    start_time = time.time()
    
    absence_impact = {}
    threshold_days = 30
    
    logger.info(f"  📊 Analisando {df['login'].nunique()} usuários únicos...")
    
    for login in df['login'].unique():
        user_data = df[df['login'] == login]
        avg_time = user_data['avg_time_to_merge'].mean()
        pr_count = user_data['prs_opened'].sum()
        commits = user_data['commits_total'].sum()
        
        # Calcular impacto baseado em múltiplos fatores
        if pd.isna(avg_time) or avg_time == 0:
            impact = 0.0
        else:
            # Impacto base do tempo
            time_impact = min(avg_time / threshold_days, 2.0)  # Cap em 2.0
            
            # Ajustar por volume de atividade
            activity_weight = min((pr_count + commits/10) / 10, 1.5)  # Cap em 1.5
            
            # Impacto final normalizado
            impact = min(time_impact * activity_weight, 1.0)
        
        absence_impact[login] = impact
    
    logger.info(f"  ✅ Impacto da ausência concluído em {time.time() - start_time:.2f}s")
    
    # Estatísticas do impacto
    impacts = list(absence_impact.values())
    logger.info(f"  📈 Estatísticas de impacto:")
    logger.info(f"    - Média: {np.mean(impacts):.4f}")
    logger.info(f"    - Mediana: {np.median(impacts):.4f}")
    logger.info(f"    - Alto impacto (>0.8): {sum(1 for i in impacts if i > 0.8)} usuários")
    
    return absence_impact

def create_full_rq3_analysis():
    """Função principal para análise completa da RQ3."""
    
    # Setup logging
    logger = setup_logging()
    logger.info("🚀 Iniciando análise COMPLETA da RQ3 - Centralidade na Rede")
    logger.info("=" * 80)
    
    overall_start = time.time()
    
    try:
        # 1. Carregar dados completos
        df = load_full_collaboration_data(logger)
        
        # 2. Criar rede de colaboração
        G = create_optimized_collaboration_network(df, logger)
        
        if G.number_of_nodes() == 0:
            logger.error("❌ Rede vazia criada. Abortando análise.")
            return None
        
        # 3. Calcular métricas de centralidade
        centrality_metrics = calculate_centrality_metrics_parallel(G, logger)
        
        # 4. Calcular structural holes
        structural_holes = calculate_structural_holes_optimized(G, logger)
        
        # 5. Análise de impacto da ausência
        absence_impact = analyze_absence_impact_full(df, logger)
        
        # 6. Processar métricas por usuário com salvamento incremental
        logger.info("👥 Processando métricas por usuário...")
        start_time = time.time()
        
        all_users = df['login'].unique()
        
        # Configuração para salvamento incremental
        batch_save_size = 50
        save_counter = 0
        metrics_data = []
        
        for i, user in enumerate(all_users):
            user_data = df[df['login'] == user].iloc[0].to_dict()
            
            # Classificação de perfil
            prs = user_data.get('prs_opened', 0) + user_data.get('prs_merged', 0)
            commits = user_data.get('commits_total', 0)
            reviews = user_data.get('reviews_submitted', 0)
            permission = user_data.get('permission_level', '').lower()
            
            if permission in ['admin', 'maintain', 'owner']:
                profile = 'Core Developer / Maintainer'
            elif prs >= 3 or commits >= 5 or reviews >= 3:
                profile = 'Peripheral Developer'
            else:
                profile = 'One-time Contributor / Newcomer'
            
            metrics_data.append({
                'login': user,
                'degree_centrality': centrality_metrics['degree'].get(user, 0.0),
                'betweenness_centrality': centrality_metrics['betweenness'].get(user, 0.0),
                'closeness_centrality': centrality_metrics['closeness'].get(user, 0.0),
                'eigenvector_centrality': centrality_metrics['eigenvector'].get(user, 0.0),
                'structural_hole_spanners': structural_holes.get(user, 0.0),
                'developer_profile': profile,
                'is_maintainer': 1 if permission in ['admin', 'maintain', 'owner'] else 0,
                'absence_impact': absence_impact.get(user, 0.0),
                'degree': G.degree(user) if G.has_node(user) else 0,
                'is_isolated': user not in G.nodes() or G.degree(user) == 0,
                'country': user_data.get('country', ''),
                'prs_opened': user_data.get('prs_opened', 0),
                'commits_total': user_data.get('commits_total', 0),
                'reviews_submitted': user_data.get('reviews_submitted', 0),
            })
            
            # Salvamento incremental a cada 50 usuários
            if (i + 1) % batch_save_size == 0 or (i + 1) == len(all_users):
                save_counter += 1
                partial_df = pd.DataFrame(metrics_data)
                
                # Salvar arquivo parcial
                partial_filename = f'csv/rq3_metrics_batch_{save_counter:03d}.csv'
                partial_df.to_csv(partial_filename, index=False)
                
                logger.info(f"📄 Batch {save_counter} salvo: {partial_filename}")
                logger.info(f"   📈 Processados {i+1}/{len(all_users)} usuários ({(i+1)/len(all_users)*100:.1f}%)")
                
                # Limpar dados para próximo batch (economizar memória)
                metrics_data = []
                
                # Log de memória a cada 1000 usuários
                if (i + 1) % 1000 == 0:
                    log_memory_usage(logger, f"Usuário milestone {(i+1)//1000}k")
        
        process_time = time.time() - start_time
        logger.info(f"  ✅ Processamento concluído em {process_time:.2f}s")
        logger.info(f"  📄 Total de batches salvos: {save_counter}")
        
        # 7. Consolidar todos os arquivos em um final
        logger.info("💾 Consolidando arquivos parciais...")
        
        # Ler todos os arquivos parciais
        all_batches = []
        for batch_num in range(1, save_counter + 1):
            batch_file = f'csv/rq3_metrics_batch_{batch_num:03d}.csv'
            if os.path.exists(batch_file):
                batch_df = pd.read_csv(batch_file)
                all_batches.append(batch_df)
        
        # Concatenar todos os batches
        metrics_df = pd.concat(all_batches, ignore_index=True)
        
        output_file = 'csv/network_metrics.csv'
        metrics_df.to_csv(output_file, index=False)
        
        # Limpar arquivos parciais para manter organização
        logger.info("🧹 Limpando arquivos parciais...")
        for batch_num in range(1, save_counter + 1):
            batch_file = f'csv/rq3_metrics_batch_{batch_num:03d}.csv'
            if os.path.exists(batch_file):
                os.remove(batch_file)
        logger.info(f"   ✅ Removidos {save_counter} arquivos parciais")
        
        # 8. Relatório final
        total_time = time.time() - overall_start
        
        logger.info("=" * 80)
        logger.info("🎉 ANÁLISE COMPLETA CONCLUÍDA!")
        logger.info(f"⏱️ Tempo total: {total_time:.2f}s ({total_time/60:.1f}min)")
        logger.info(f"📁 Arquivo salvo: {output_file}")
        logger.info(f"👥 Total de usuários: {len(metrics_df)}")
        logger.info(f"🌐 Rede final: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")
        log_memory_usage(logger, "Final")
        
        # Estatísticas finais
        logger.info("\n📊 ESTATÍSTICAS FINAIS:")
        
        profile_counts = metrics_df['developer_profile'].value_counts()
        logger.info("👥 Perfis de desenvolvedores:")
        for profile, count in profile_counts.items():
            logger.info(f"  - {profile}: {count} ({count/len(metrics_df)*100:.1f}%)")
        
        maintainers = metrics_df['is_maintainer'].sum()
        logger.info(f"👑 Maintainers: {maintainers} ({maintainers/len(metrics_df)*100:.2f}%)")
        
        # Top performers
        logger.info("\n🏆 TOP PERFORMERS:")
        
        top_betweenness = metrics_df.nlargest(5, 'betweenness_centrality')
        logger.info("🌉 Top 5 Betweenness Centrality:")
        for _, row in top_betweenness.iterrows():
            logger.info(f"  - {row['login']} ({row['country']}): {row['betweenness_centrality']:.6f}")
        
        top_spanners = metrics_df.nlargest(5, 'structural_hole_spanners')
        logger.info("🕳️ Top 5 Structural Hole Spanners:")
        for _, row in top_spanners.iterrows():
            logger.info(f"  - {row['login']} ({row['country']}): {row['structural_hole_spanners']:.4f}")
        
        logger.info("=" * 80)
        
        return metrics_df
        
    except Exception as e:
        logger.error(f"❌ Erro crítico na análise: {e}")
        logger.exception("Detalhes do erro:")
        return None

if __name__ == "__main__":
    result = create_full_rq3_analysis()
    if result is not None:
        print(f"\n✅ Análise concluída com sucesso! Dataset com {len(result)} usuários criado.")
        print("📁 Arquivo: csv/network_metrics.csv")
        print("📋 Logs salvos em: logs/")
    else:
        print("❌ Análise falhou. Verifique os logs para detalhes.")
