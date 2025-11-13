"""
Análise Acadêmica Rigorosa para Determinação de Pesos
====================================================

Este script implementa métodos estatísticos para determinar pesos empiricamente
ao invés de usar valores arbitrários, seguindo padrões acadêmicos:

1. Análise de Componentes Principais (PCA) - Pesos empíricos
2. Análise de Correlação - Validação de multicolinearidade  
3. Análise Fatorial - Estrutura latente das variáveis
4. Validação Estatística - Testes de adequação

Para RQ1 (Performance)
"""

import pandas as pd
import numpy as np
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.preprocessing import StandardScaler
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

def load_and_prepare_data():
    """Carrega e prepara dados para análise"""
    print("📊 Carregando dados para análise acadêmica...")
    
    # Carregar dados principais
    df_users = pd.read_csv('scripts/csv/users_metrics.csv')
    print(f"✅ Carregados {len(df_users)} usuários")
    
    # Remover valores ausentes e outliers extremos
    df_clean = df_users.dropna()
    
    # Log dos dados para reduzir impacto de outliers
    numeric_cols = df_users.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if (df_clean[col] > 0).all():  # Só aplica log se todos valores > 0
            df_clean[f'{col}_log'] = np.log1p(df_clean[col])
    
    print(f"📈 Dataset limpo: {len(df_clean)} usuários")
    return df_clean

def analyze_rq1_performance_weights(df):
    """
    RQ1: Análise acadêmica de pesos para Performance Score
    """
    print("\n" + "="*60)
    print("🎯 RQ1: ANÁLISE ACADÊMICA DE PERFORMANCE WEIGHTS")
    print("="*60)
    
    # Definir variáveis de performance
    performance_vars = [
        'pr_accept_rate',
        'prs_opened', 
        'commits_total',
        'activity_frequency'
    ]
    
    # Verificar disponibilidade das variáveis
    available_vars = [var for var in performance_vars if var in df.columns]
    print(f"📋 Variáveis disponíveis: {available_vars}")
    
    if len(available_vars) < 2:
        print("❌ Insuficientes variáveis para análise PCA")
        return None
    
    # Preparar dados para PCA
    X = df[available_vars].copy()
    
    # 1. ANÁLISE DE CORRELAÇÃO
    print("\n📊 1. ANÁLISE DE CORRELAÇÃO")
    print("-" * 40)
    
    correlation_matrix = X.corr()
    print("Matriz de Correlação:")
    print(correlation_matrix.round(3))
    
    # Teste de adequação KMO (Kaiser-Meyer-Olkin)
    def calculate_kmo(data):
        """Calcula KMO para adequação da análise fatorial"""
        corr_matrix = data.corr()
        partial_corr = np.linalg.pinv(corr_matrix)
        partial_corr = -partial_corr / np.sqrt(np.outer(np.diag(partial_corr), np.diag(partial_corr)))
        np.fill_diagonal(partial_corr, 0)
        
        sum_sq_corr = np.sum(corr_matrix.values**2) - np.trace(corr_matrix.values**2)
        sum_sq_partial = np.sum(partial_corr**2)
        
        kmo = sum_sq_corr / (sum_sq_corr + sum_sq_partial)
        return kmo
    
    try:
        kmo_value = calculate_kmo(X)
        print(f"\n🔍 KMO (adequação): {kmo_value:.3f}")
        if kmo_value > 0.6:
            print("✅ KMO > 0.6: Adequado para análise fatorial")
        else:
            print("⚠️ KMO < 0.6: Análise fatorial pode não ser adequada")
    except:
        print("⚠️ Não foi possível calcular KMO")
    
    # 2. ANÁLISE DE COMPONENTES PRINCIPAIS (PCA)
    print("\n🔬 2. ANÁLISE DE COMPONENTES PRINCIPAIS (PCA)")
    print("-" * 50)
    
    # Padronizar dados
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Executar PCA
    pca = PCA()
    pca.fit(X_scaled)
    
    # Variância explicada
    explained_var = pca.explained_variance_ratio_
    cumulative_var = np.cumsum(explained_var)
    
    print("Variância explicada por componente:")
    for i, (var, cum_var) in enumerate(zip(explained_var, cumulative_var)):
        print(f"  PC{i+1}: {var:.3f} ({var*100:.1f}%) - Acumulada: {cum_var:.3f} ({cum_var*100:.1f}%)")
    
    # Componentes (pesos)
    components = pca.components_
    print(f"\n📊 PESOS EMPÍRICOS (Primeiro Componente - {explained_var[0]*100:.1f}% da variância):")
    
    # Normalizar pesos para somar 1
    first_component = np.abs(components[0])  # Valores absolutos
    normalized_weights = first_component / first_component.sum()
    
    weights_dict = {}
    for var, weight in zip(available_vars, normalized_weights):
        weights_dict[var] = weight
        print(f"  • {var}: {weight:.3f} ({weight*100:.1f}%)")
    
    # 3. ANÁLISE FATORIAL
    print("\n🧮 3. ANÁLISE FATORIAL")
    print("-" * 30)
    
    try:
        # Determinar número de fatores (critério Kaiser: eigenvalue > 1)
        eigenvalues = pca.explained_variance_
        n_factors = np.sum(eigenvalues > 1)
        print(f"Fatores com eigenvalue > 1: {n_factors}")
        
        if n_factors > 0:
            fa = FactorAnalysis(n_components=min(n_factors, len(available_vars)-1))
            fa.fit(X_scaled)
            
            loadings = fa.components_.T
            print("Cargas fatoriais:")
            for i, var in enumerate(available_vars):
                print(f"  • {var}: {loadings[i, 0]:.3f}")
    
    except Exception as e:
        print(f"⚠️ Erro na análise fatorial: {e}")
    
    # 4. VALIDAÇÃO ESTATÍSTICA
    print("\n✅ 4. VALIDAÇÃO ESTATÍSTICA")
    print("-" * 35)
    
    # Teste de esfericidade de Bartlett
    try:
        from scipy.stats import chi2
        n, p = X.shape
        corr_det = np.linalg.det(correlation_matrix)
        statistic = -((n - 1) - (2 * p + 5) / 6) * np.log(corr_det)
        p_value = 1 - chi2.cdf(statistic, p * (p - 1) / 2)
        
        print(f"Teste de Bartlett:")
        print(f"  Estatística: {statistic:.3f}")
        print(f"  p-valor: {p_value:.6f}")
        if p_value < 0.05:
            print("✅ p < 0.05: Correlações significativas (adequado para PCA)")
        else:
            print("⚠️ p > 0.05: Correlações não significativas")
    except:
        print("⚠️ Não foi possível realizar teste de Bartlett")
    
    # 5. RECOMENDAÇÃO FINAL
    print("\n💡 5. RECOMENDAÇÃO ACADÊMICA PARA RQ1")
    print("-" * 45)
    
    if explained_var[0] > 0.5:  # Primeiro componente explica > 50%
        print("✅ USAR PESOS EMPÍRICOS (PCA):")
        for var, weight in weights_dict.items():
            print(f"  • {var}: {weight:.3f}")
        print(f"\nJustificativa: Primeiro componente explica {explained_var[0]*100:.1f}% da variância")
    else:
        print("⚠️ USAR PESOS IGUAIS ou ANÁLISE INDIVIDUAL:")
        equal_weight = 1 / len(available_vars)
        for var in available_vars:
            print(f"  • {var}: {equal_weight:.3f}")
        print(f"Justificativa: Componentes não concentram variância suficiente")
    
    return weights_dict

def generate_report():
    """Gera relatório acadêmico completo"""
    print("\n" + "="*80)
    print("📊 RELATÓRIO ACADÊMICO: DETERMINAÇÃO EMPÍRICA DE PESOS E VARIÁVEIS")
    print("="*80)
    
    # Carregar dados
    df = load_and_prepare_data()
    
    # Análise RQ1
    rq1_weights = analyze_rq1_performance_weights(df)
    
    # Relatório final
    print("\n" + "="*60)
    print("📋 RESUMO EXECUTIVO - METODOLOGIA ACADEMICAMENTE RIGOROSA")
    print("="*60)
    
    print("\n🎯 RQ1 (PERFORMANCE):")
    print("   Método: Análise de Componentes Principais (PCA)")
    print("   Justificativa: Determinação empírica de pesos baseada na variância explicada")
    if rq1_weights:
        print("   Pesos recomendados:")
        for var, weight in rq1_weights.items():
            print(f"     • {var}: {weight:.3f} ({weight*100:.1f}%)")
    
    return {
        'rq1_weights': rq1_weights,
    }

def main():
    """Execução principal"""
    print("🎓 INICIANDO ANÁLISE ACADÊMICA RIGOROSA")
    print("Determinação empírica de pesos e variáveis dependentes")
    print("="*60)
    
    try:
        results = generate_report()
        
        # Salvar resultados
        import json
        with open('scripts/csv/weights_analysis.json', 'w') as f:
            json.dump({
                'rq1_weights': results['rq1_weights'],
                'methodology': 'PCA + Correlation Analysis',
                'timestamp': pd.Timestamp.now().isoformat()
            }, f, indent=2)
        
        print(f"\n💾 Resultados salvos em: scripts/csv/weights_analysis.json")
        print("✅ Análise acadêmica concluída!")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()