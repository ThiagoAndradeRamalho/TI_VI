"""
Aplicação de Pesos Determinados
==============================================

Este script aplica os pesos empíricos determinados pela análise PCA
ao invés de pesos arbitrários, seguindo metodologia acadêmica rigorosa.

Baseado na análise de weight_analysis.py
"""

import pandas as pd
import numpy as np
import json

def load_weights():
    """Carrega pesos determinados empiricamente"""
    with open('scripts/csv/weights_analysis.json', 'r') as f:
        analysis_results = json.load(f)
    return analysis_results

def calculate_performance_score():
    """
    Calcula Performance Score usando PESOS EMPÍRICOS (PCA)
    ao invés de pesos arbitrários
    """
    print("🎓 Calculando Performance Score com PESOS DETERMINADOS")
    print("=" * 70)
    
    # Carregar pesos empíricos
    results = load_weights()
    empirical_weights = results['rq1_weights']
    
    print("📊 PESOS EMPÍRICOS (baseados em PCA - 61% da variância explicada):")
    for var, weight in empirical_weights.items():
        print(f"   • {var}: {weight:.3f} ({weight*100:.1f}%)")
    print()
    
    # Carregar dados
    df = pd.read_csv('scripts/csv/users_metrics.csv')
    print(f"📋 Carregados dados de {len(df)} usuários")
    
    # Normalizar métricas (Min-Max normalization)
    def normalize_column(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0.0, index=series.index)
        return (series - min_val) / (max_val - min_val)
    
    df_score = df.copy()
    
    # Normalizar cada métrica
    print("📐 Normalizando métricas para escala 0-1...")
    
    # pr_accept_rate já está em %, converter para 0-1
    df_score['pr_accept_rate_norm'] = df_score['pr_accept_rate'] / 100.0
    
    # Demais métricas - normalização min-max
    df_score['prs_opened_norm'] = normalize_column(df_score['prs_opened'])
    df_score['commits_total_norm'] = normalize_column(df_score['commits_total'])
    df_score['activity_frequency_norm'] = normalize_column(df_score['activity_frequency'])
    
    # Aplicar pesos empíricos
    print("🔬 Aplicando pesos empíricos determinados por PCA...")
    df_score['performance_score'] = (
        df_score['pr_accept_rate_norm'] * empirical_weights['pr_accept_rate'] +
        df_score['prs_opened_norm'] * empirical_weights['prs_opened'] +
        df_score['commits_total_norm'] * empirical_weights['commits_total'] +
        df_score['activity_frequency_norm'] * empirical_weights['activity_frequency']
    )
    
    # Classificar países
    print("🌍 Classificando países...")
    emerging_countries = {
        'brazil', 'india', 'china', 'south africa', 'russia', 'mexico', 'indonesia', 
        'turkey', 'thailand', 'malaysia', 'philippines', 'vietnam', 'argentina',
        'colombia', 'chile', 'peru', 'ukraine', 'romania', 'bulgaria', 'croatia',
        'poland', 'czech republic', 'hungary', 'egypt', 'nigeria', 'kenya', 'ghana',
        'pakistan', 'bangladesh', 'morocco', 'algeria', 'tunisia', 'ecuador',
        'bolivia', 'paraguay', 'uruguay', 'venezuela', 'costa rica', 'panama',
        'sri lanka', 'nepal', 'myanmar', 'cambodia', 'laos', 'mongolia'
    }
    
    df_score['country_clean'] = df_score['country'].str.lower().str.strip()
    df_score['country_type'] = df_score['country_clean'].apply(
        lambda x: 'emerging' if x in emerging_countries else 'developed'
    )
    
    # Estatísticas do score acadêmico
    print("\n📊 ESTATÍSTICAS DO PERFORMANCE SCORE ACADÊMICO")
    print("-" * 50)
    
    mean = df_score['performance_score'].mean()
    median = df_score['performance_score'].median()
    std = df_score['performance_score'].std()
    emerging = df_score[df_score['country_type'] == 'emerging']['performance_score'].mean()
    developed = df_score[df_score['country_type'] == 'developed']['performance_score'].mean()
    
    print(f"📈 Estatísticas gerais:")
    print(f"   • Média: {mean:.4f}")
    print(f"   • Mediana: {median:.4f}")
    print(f"   • Desvio padrão: {std:.4f}")
    
    print(f"\n🌍 Por tipo de país:")
    print(f"   • Países emergentes: {emerging:.4f}")
    print(f"   • Países desenvolvidos: {developed:.4f}")
    print(f"   • Diferença (emergentes - desenvolvidos): {emerging - developed:.4f}")
    
    # Top performers com score acadêmico
    print(f"\n🏆 Top 10 Performance Scores (Metodologia Acadêmica):")
    top_performers = df_score.nlargest(10, 'performance_score')[
        ['login', 'country', 'country_type', 'performance_score', 'prs_opened', 'commits_total', 'activity_frequency']
    ]
    print(top_performers.to_string(index=False))
    
    # Salvar resultado acadêmico
    output_cols = [
        'login', 'repo_name', 'country', 'country_type',
        'performance_score',  # Score academicamente justificado
        'pr_accept_rate', 'pr_accept_rate_norm',
        'prs_opened', 'prs_opened_norm',
        'commits_total', 'commits_total_norm',
        'activity_frequency', 'activity_frequency_norm'
    ]
    
    df_output = df_score[output_cols]
    output_file = 'scripts/csv/performance_scores.csv'
    df_output.to_csv(output_file, index=False)
    
    print(f"\n💾 Performance scores acadêmicos salvos em: {output_file}")
    print(f"📊 Total de usuários: {len(df_output)}")
    
    return df_output

def main():
    """Execução principal com metodologia acadêmica"""
    print("🎓 METODOLOGIA ACADEMICAMENTE RIGOROSA - PERFORMANCE SCORE")
    print("Pesos empíricos determinados por PCA + Análise de correlação")
    print("=" * 70)
    print()
    
    # RQ1: Performance com pesos empíricos
    performance_data = calculate_performance_score()
    
    print(f"\n✅ Análise concluída!")
    print(f"📊 Dataset final: {len(performance_data)} usuários")
    print(f"🎯 Metodologia: Pesos empíricos baseados em PCA")

if __name__ == "__main__":
    main()